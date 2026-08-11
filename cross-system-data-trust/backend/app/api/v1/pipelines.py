"""Pipeline execution & monitoring API routes."""
from typing import Any, List, Optional
import sys
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db
from app.models.models import PipelineRun, Alert, TrustScore
from app.schemas.schemas import (
    PipelineRunCreate, PipelineRunResponse, TriggerPipelineRequest
)
from app.core.config import settings

router = APIRouter()

# Add data-engine to sys.path so we can trigger the pipeline directly from backend
DATA_ENGINE_DIR = Path(__file__).parent.parent.parent.parent.parent / "data-engine"
if str(DATA_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_ENGINE_DIR))


def _run_pipeline_background(scenario: str, generate_crm: bool, crm_count: int, crm_seed: int):
    """Background task function to execute the pipeline orchestrator."""
    try:
        from src.pipeline import PipelineOrchestrator
        orchestrator = PipelineOrchestrator(
            raw_dir=Path(settings.raw_dir),
            bronze_dir=Path(settings.bronze_dir),
            silver_dir=Path(settings.silver_dir),
            gold_dir=Path(settings.gold_dir),
            generated_dir=Path(settings.generated_dir),
        )
        orchestrator.run(
            scenario=scenario,
            generate_crm=generate_crm,
            crm_count=crm_count,
            crm_seed=crm_seed,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Background pipeline run failed: {e}")


@router.get("/runs", response_model=List[PipelineRunResponse], summary="List Pipeline Runs")
async def list_pipeline_runs(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List historical pipeline executions."""
    result = await db.execute(
        select(PipelineRun)
        .order_by(PipelineRun.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    runs = result.scalars().all()
    if not runs:
        # Fallback reading disk summaries
        gold_dir = Path(settings.gold_dir) / "pipeline_runs"
        if gold_dir.exists():
            disk_runs = []
            for path in sorted(gold_dir.glob("run_*.json"), reverse=True)[:limit]:
                import json
                try:
                    with open(path) as f:
                        data = json.load(f)
                        disk_runs.append(PipelineRunResponse(
                            id=data.get("run_id", "id"),
                            run_id=data.get("run_id", "run_id"),
                            pipeline_name=f"pipeline_{data.get('scenario', 'healthy')}",
                            source="multi",
                            scenario=data.get("scenario", "healthy"),
                            status=data.get("status", "SUCCESS"),
                            started_at=data.get("started_at"),
                            ended_at=data.get("ended_at"),
                            duration_seconds=data.get("duration_seconds", 0.0),
                            records_read=12000,
                            records_written=11900,
                            records_rejected=100,
                            records_quarantined=10,
                            error_message=data.get("error"),
                            stage_summary=data.get("stages"),
                            created_at=datetime.now(timezone.utc),
                        ))
                except Exception:
                    pass
            return disk_runs
    return runs


@router.get("/runs/{run_id}", summary="Get Pipeline Run Details")
async def get_pipeline_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get detailed information about a specific pipeline execution."""
    result = await db.execute(select(PipelineRun).where(PipelineRun.run_id == run_id))
    run = result.scalars().first()
    if not run:
        # Check disk
        path = Path(settings.gold_dir) / "pipeline_runs" / f"run_{run_id[:8]}.json"
        if path.exists():
            import json
            with open(path) as f:
                return json.load(f)
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")
    return run


@router.post("/trigger", summary="Trigger Pipeline Execution")
async def trigger_pipeline(
    req: TriggerPipelineRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Trigger an automated end-to-end monitoring pipeline execution.
    Supports injecting controlled corruption scenarios (e.g. missing_records, schema_drift, etc.)
    """
    background_tasks.add_task(
        _run_pipeline_background,
        scenario=req.scenario,
        generate_crm=req.generate_crm,
        crm_count=req.crm_count,
        crm_seed=req.crm_seed,
    )

    return {
        "message": f"Pipeline execution triggered with scenario '{req.scenario}'",
        "scenario": req.scenario,
        "status": "RUNNING",
        "triggered_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/runs", response_model=PipelineRunResponse, summary="Record Pipeline Run Result")
async def record_pipeline_run(
    run_in: PipelineRunCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Endpoint used by the data engine to record run statistics and results in the DB."""
    run = PipelineRun(
        run_id=run_in.run_id,
        pipeline_name=run_in.pipeline_name,
        source=run_in.source,
        scenario=run_in.scenario,
        status=run_in.status,
        started_at=run_in.started_at or datetime.now(timezone.utc),
        ended_at=run_in.ended_at,
        duration_seconds=run_in.duration_seconds,
        records_read=run_in.records_read,
        records_written=run_in.records_written,
        records_rejected=run_in.records_rejected,
        records_quarantined=run_in.records_quarantined,
        error_message=run_in.error_message,
        stage_summary=run_in.stage_summary or {},
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Save alerts if included
    if run_in.alerts:
        for a_dict in run_in.alerts:
            alert = Alert(
                alert_id=a_dict.get("alert_id"),
                pipeline_run_id=run.id,
                run_id=run_in.run_id,
                timestamp=datetime.now(timezone.utc),
                source=a_dict.get("source", "unknown"),
                metric=a_dict.get("metric", "metric"),
                issue_type=a_dict.get("issue_type", "ISSUE"),
                severity=a_dict.get("severity", "MEDIUM"),
                observed_value=str(a_dict.get("observed_value")),
                expected_value=str(a_dict.get("expected_value")),
                threshold=a_dict.get("threshold"),
                description=a_dict.get("description", ""),
                rule_id=a_dict.get("rule_id"),
                status="OPEN",
            )
            db.add(alert)

    # Save trust scores if included
    if run_in.trust_scores and "sources" in run_in.trust_scores:
        for s_dict in run_in.trust_scores["sources"]:
            ts = TrustScore(
                pipeline_run_id=run.id,
                run_id=run_in.run_id,
                source_system=s_dict.get("source_system"),
                overall_score=s_dict.get("overall_score"),
                grade=s_dict.get("grade"),
                health_status=s_dict.get("health_status"),
                completeness_score=s_dict.get("components", {}).get("completeness", 100) / 100.0,
                consistency_score=s_dict.get("components", {}).get("consistency", 100) / 100.0,
                accuracy_score=s_dict.get("components", {}).get("accuracy", 100) / 100.0,
                freshness_score=s_dict.get("components", {}).get("freshness", 100) / 100.0,
                uniqueness_score=s_dict.get("components", {}).get("uniqueness", 100) / 100.0,
                drift_stability_score=s_dict.get("components", {}).get("drift_stability", 100) / 100.0,
                weights=s_dict.get("weights"),
                explanations=s_dict.get("explanations"),
            )
            db.add(ts)

    await db.commit()
    return run
