"""Main API v1 router — aggregates all sub-routers."""
from fastapi import APIRouter

from app.api.v1 import (
    health, auth, dashboard, pipelines, alerts,
    trust_scores, drift, quality, comparisons, rules
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(pipelines.router, prefix="/pipelines", tags=["Pipelines"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(trust_scores.router, prefix="/trust-scores", tags=["Trust Scores"])
api_router.include_router(drift.router, prefix="/drift", tags=["Drift"])
api_router.include_router(quality.router, prefix="/quality", tags=["Data Quality"])
api_router.include_router(comparisons.router, prefix="/comparisons", tags=["Comparisons"])
api_router.include_router(rules.router, prefix="/rules", tags=["Quality Rules"])
