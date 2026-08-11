"""
FastAPI Backend Application Entry Point
Cross-System Data Drift & Trust Monitoring Platform
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.database.session import init_db
from app.api.v1.router import api_router

# ── Structured logging setup
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("DataTrust API starting up", env=settings.environment)
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("DataTrust API shutting down")


app = FastAPI(
    title="DataTrust API",
    description="""
# Cross-System Data Drift & Trust Monitoring Platform

Enterprise-grade data observability API for monitoring data quality,
detecting drift, and calculating trust scores across CRM, Billing, and Analytics systems.

## Features
- 🔍 Real-time data quality monitoring
- 📊 Cross-system reconciliation (Billing vs Analytics vs CRM)
- 📈 Volume, distribution, and schema drift detection
- 🏆 Explainable trust scores (0–100)
- 🚨 Configurable alerting engine
- 📋 Complete pipeline audit trail
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Routers
app.include_router(api_router, prefix=settings.api_v1_str)


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "DataTrust API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled exception", exc_info=exc, path=str(request.url))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )
