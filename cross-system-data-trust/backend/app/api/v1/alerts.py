"""Alert Center API routes."""
from typing import Any, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db
from app.models.models import Alert
from app.schemas.schemas import AlertCreate, AlertResponse, AlertUpdateRequest
from app.api.v1.dashboard import _load_latest_run_from_disk

router = APIRouter()


@router.get("", response_model=List[AlertResponse], summary="List Alerts")
async def list_alerts(
    severity: Optional[str] = Query(None, description="Filter by CRITICAL, HIGH, MEDIUM, LOW"),
    status: Optional[str] = Query(None, description="Filter by OPEN, ACKNOWLEDGED, RESOLVED, IGNORED"),
    source: Optional[str] = Query(None, description="Filter by crm, billing, analytics, etc."),
    issue_type: Optional[str] = Query(None, description="Filter by issue type"),
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retrieve filtered monitoring alerts."""
    query = select(Alert).order_by(Alert.timestamp.desc())

    if severity:
        query = query.where(Alert.severity == severity.upper())
    if status:
        query = query.where(Alert.status == status.upper())
    if source:
        query = query.where(Alert.source == source.lower())
    if issue_type:
        query = query.where(Alert.issue_type == issue_type)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    alerts = result.scalars().all()

    if not alerts:
        disk_data = _load_latest_run_from_disk()
        if disk_data and "recent_alerts" in disk_data:
            disk_alerts = []
            for idx, a in enumerate(disk_data["recent_alerts"]):
                if severity and a.get("severity") != severity.upper():
                    continue
                if status and a.get("status") != status.upper():
                    continue
                if source and a.get("source") != source.lower():
                    continue

                ts = datetime.now(timezone.utc)
                disk_alerts.append(AlertResponse(
                    id=str(idx),
                    alert_id=a.get("alert_id", f"ALERT-{idx}"),
                    run_id=a.get("run_id"),
                    timestamp=ts,
                    source=a.get("source", "billing"),
                    metric=a.get("metric", "metric"),
                    issue_type=a.get("issue_type", "ANOMALY"),
                    severity=a.get("severity", "HIGH"),
                    observed_value=str(a.get("observed_value")),
                    expected_value=str(a.get("expected_value")),
                    threshold=a.get("threshold"),
                    description=a.get("description", "Alert description"),
                    status=a.get("status", "OPEN"),
                    rule_id=a.get("rule_id"),
                    acknowledged_by=a.get("acknowledged_by"),
                    acknowledged_at=None,
                    resolution_note=a.get("resolution_note"),
                    created_at=ts,
                ))
            return disk_alerts

    return alerts


@router.get("/{alert_id}", response_model=AlertResponse, summary="Get Alert Details")
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db)) -> Any:
    result = await db.execute(select(Alert).where(Alert.alert_id == alert_id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return alert


@router.patch("/{alert_id}", response_model=AlertResponse, summary="Update Alert Status")
async def update_alert_status(
    alert_id: str,
    update_data: AlertUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Acknowledge, resolve, or ignore an alert."""
    result = await db.execute(select(Alert).where(Alert.alert_id == alert_id))
    alert = result.scalars().first()

    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    alert.status = update_data.status.upper()
    if update_data.status.upper() == "ACKNOWLEDGED":
        alert.acknowledged_by = update_data.acknowledged_by or "user"
        alert.acknowledged_at = datetime.now(timezone.utc)
    elif update_data.status.upper() == "RESOLVED":
        alert.resolution_note = update_data.resolution_note or "Resolved by user"

    await db.commit()
    await db.refresh(alert)
    return alert


@router.post("", response_model=AlertResponse, summary="Create Alert")
async def create_alert(alert_in: AlertCreate, db: AsyncSession = Depends(get_db)) -> Any:
    alert = Alert(
        alert_id=alert_in.alert_id,
        run_id=alert_in.run_id,
        timestamp=alert_in.timestamp or datetime.now(timezone.utc),
        source=alert_in.source,
        metric=alert_in.metric,
        issue_type=alert_in.issue_type,
        severity=alert_in.severity,
        observed_value=alert_in.observed_value,
        expected_value=alert_in.expected_value,
        threshold=alert_in.threshold,
        description=alert_in.description,
        rule_id=alert_in.rule_id,
        status="OPEN",
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert
