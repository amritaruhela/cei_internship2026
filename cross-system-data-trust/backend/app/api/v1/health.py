"""Health check endpoints."""
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.database.session import AsyncSessionLocal
from app.schemas.schemas import HealthResponse

router = APIRouter()


@router.get("", response_model=HealthResponse, summary="Service health check")
async def health():
    """Liveness probe — returns 200 if service is up."""
    db_status = "unknown"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        service="DataTrust API",
        version="1.0.0",
        environment=settings.environment,
        database=db_status,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/ready", summary="Readiness probe")
async def readiness():
    """Readiness probe for k8s/Docker health checks."""
    return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/live", summary="Liveness probe")
async def liveness():
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}
