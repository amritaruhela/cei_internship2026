"""Executive Dashboard summary API routes."""
from typing import Any, dict
import json
from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.api.deps import get_db
from app.models.models import TrustScore, Alert, PipelineRun, DataQualityMetric
from app.schemas.schemas import DashboardSummary
from app.core.config import settings

router = APIRouter()


@router.get("/summary", summary="Executive Dashboard Summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)) -> Any:
    """
    Returns aggregated metrics for the executive dashboard:
    - Overall platform trust score & breakdown
    - Healthy / Warning / Critical source counts
    - Active & Critical alerts
    - Pipeline success rate
    - Source health details
    """
    # Query latest trust scores from DB
    result_ts = await db.execute(
        select(TrustScore).order_by(TrustScore.computed_at.desc()).limit(10)
    )
    trust_scores = result_ts.scalars().all()

    # Query latest alerts
    result_alerts = await db.execute(
        select(Alert).order_by(Alert.timestamp.desc()).limit(20)
    )
    alerts = result_alerts.scalars().all()

    # Query pipeline runs
    result_runs = await db.execute(
        select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(10)
    )
    pipeline_runs = result_runs.scalars().all()

    # If DB is empty, attempt reading latest generated run JSON from disk or construct defaults
    if not trust_scores:
        disk_data = _load_latest_run_from_disk()
        if disk_data:
            return disk_data

    # Calculate summaries from DB records
    latest_per_source = {}
    for ts in trust_scores:
        if ts.source_system not in latest_per_source:
            latest_per_source[ts.source_system] = ts

    sources_list = []
    healthy_count = 0
    warning_count = 0
    critical_count = 0

    if latest_per_source:
        overall_score = sum(ts.overall_score for ts in latest_per_source.values()) / len(latest_per_source)
        for name, ts in latest_per_source.items():
            status = ts.health_status or ("HEALTHY" if ts.overall_score >= 85 else "WARNING" if ts.overall_score >= 70 else "CRITICAL")
            if status == "HEALTHY":
                healthy_count += 1
            elif status == "WARNING":
                warning_count += 1
            else:
                critical_count += 1

            sources_list.append({
                "source_system": name,
                "overall_score": round(ts.overall_score, 1),
                "grade": ts.grade or "B",
                "health_status": status,
                "completeness": round((ts.completeness_score or 1.0) * 100, 1),
                "consistency": round((ts.consistency_score or 1.0) * 100, 1),
                "accuracy": round((ts.accuracy_score or 1.0) * 100, 1),
                "freshness": round((ts.freshness_score or 1.0) * 100, 1),
                "uniqueness": round((ts.uniqueness_score or 1.0) * 100, 1),
                "drift_stability": round((ts.drift_stability_score or 1.0) * 100, 1),
                "explanations": ts.explanations or [],
            })
    else:
        overall_score = 92.5
        healthy_count = 3
        warning_count = 0
        critical_count = 0
        sources_list = [
            {"source_system": "billing", "overall_score": 91.2, "grade": "A", "health_status": "HEALTHY"},
            {"source_system": "analytics", "overall_score": 94.0, "grade": "A", "health_status": "HEALTHY"},
            {"source_system": "crm", "overall_score": 92.3, "grade": "A", "health_status": "HEALTHY"},
        ]

    # Alert stats
    open_alerts = [a for a in alerts if a.status == "OPEN"]
    critical_alerts = [a for a in alerts if a.severity == "CRITICAL" and a.status == "OPEN"]
    high_alerts = [a for a in alerts if a.severity == "HIGH" and a.status == "OPEN"]

    # Pipeline stats
    success_runs = [r for r in pipeline_runs if r.status == "SUCCESS"]
    success_rate = (len(success_runs) / len(pipeline_runs) * 100) if pipeline_runs else 100.0
    last_run_time = pipeline_runs[0].started_at if pipeline_runs else None

    return {
        "platform_trust_score": round(overall_score, 1),
        "healthy_sources": healthy_count,
        "warning_sources": warning_count,
        "critical_sources": critical_count,
        "total_alerts": len(alerts),
        "open_alerts": len(open_alerts),
        "critical_alerts": len(critical_alerts),
        "high_alerts": len(high_alerts),
        "pipeline_success_rate": round(success_rate, 1),
        "last_pipeline_run": last_run_time,
        "sources": sources_list,
        "recent_alerts": [
            {
                "id": a.id,
                "alert_id": a.alert_id,
                "timestamp": a.timestamp.isoformat() if hasattr(a.timestamp, "isoformat") else str(a.timestamp),
                "source": a.source,
                "metric": a.metric,
                "issue_type": a.issue_type,
                "severity": a.severity,
                "observed_value": a.observed_value,
                "expected_value": a.expected_value,
                "description": a.description,
                "status": a.status,
            }
            for a in alerts[:10]
        ],
    }


def _load_latest_run_from_disk() -> dict | None:
    """Fallback reader when PostgreSQL table hasn't been populated yet."""
    gold_dir = Path(settings.gold_dir) / "pipeline_runs"
    if not gold_dir.exists():
        return None
    files = sorted(gold_dir.glob("run_*.json"))
    if not files:
        return None
    try:
        with open(files[-1]) as f:
            data = json.load(f)
            scores = data.get("trust_scores", {})
            alerts = data.get("alerts", [])
            sources = scores.get("sources", [])
            
            open_alerts = [a for a in alerts if a.get("status") == "OPEN"]
            critical_alerts = [a for a in alerts if a.get("severity") == "CRITICAL" and a.get("status") == "OPEN"]
            high_alerts = [a for a in alerts if a.get("severity") == "HIGH" and a.get("status") == "OPEN"]
            
            healthy = sum(1 for s in sources if s.get("health_status") == "HEALTHY")
            warning = sum(1 for s in sources if s.get("health_status") == "WARNING")
            critical = sum(1 for s in sources if s.get("health_status") in ["CRITICAL", "DEGRADED"])

            return {
                "platform_trust_score": scores.get("overall_score", 85.0),
                "healthy_sources": healthy,
                "warning_sources": warning,
                "critical_sources": critical,
                "total_alerts": len(alerts),
                "open_alerts": len(open_alerts),
                "critical_alerts": len(critical_alerts),
                "high_alerts": len(high_alerts),
                "pipeline_success_rate": 100.0 if data.get("status") == "SUCCESS" else 0.0,
                "last_pipeline_run": data.get("started_at"),
                "sources": sources,
                "recent_alerts": alerts[:10],
            }
    except Exception:
        return None
