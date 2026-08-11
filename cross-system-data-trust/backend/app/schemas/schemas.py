"""Pydantic schemas for all API requests and responses."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


# ──────────────────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str
    password: str = Field(..., min_length=8)
    role: str = Field(default="VIEWER", pattern="^(ADMIN|DATA_ENGINEER|VIEWER)$")


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────
# PIPELINE RUNS
# ──────────────────────────────────────────────────────────

class PipelineRunCreate(BaseModel):
    run_id: str
    pipeline_name: str
    source: Optional[str] = None
    scenario: Optional[str] = None
    status: str = "RUNNING"
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    records_read: int = 0
    records_written: int = 0
    records_rejected: int = 0
    records_quarantined: int = 0
    error_message: Optional[str] = None
    stage_summary: Optional[dict] = None
    trust_scores: Optional[dict] = None
    alerts: Optional[list] = None


class PipelineRunResponse(BaseModel):
    id: str
    run_id: str
    pipeline_name: str
    source: Optional[str]
    scenario: Optional[str]
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    duration_seconds: Optional[float]
    records_read: int
    records_written: int
    records_rejected: int
    records_quarantined: int
    error_message: Optional[str]
    stage_summary: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class TriggerPipelineRequest(BaseModel):
    scenario: str = Field(
        default="healthy",
        description="Data quality scenario to simulate",
        examples=["healthy", "missing_records", "duplicates", "revenue_mismatch",
                  "schema_drift", "volume_spike", "volume_drop", "distribution_drift",
                  "null_injection", "mixed"],
    )
    generate_crm: bool = True
    crm_count: int = Field(default=10500, ge=100, le=500000)
    crm_seed: int = 42


# ──────────────────────────────────────────────────────────
# TRUST SCORES
# ──────────────────────────────────────────────────────────

class TrustScoreResponse(BaseModel):
    id: str
    source_system: str
    overall_score: float
    grade: Optional[str]
    health_status: Optional[str]
    completeness_score: float
    consistency_score: float
    accuracy_score: float
    freshness_score: float
    uniqueness_score: float
    drift_stability_score: float
    weights: Optional[dict]
    explanations: Optional[list]
    computed_at: datetime

    model_config = {"from_attributes": True}


class PlatformTrustScoreResponse(BaseModel):
    overall_score: float
    health_status: str
    source_count: int
    sources: list[dict]


# ──────────────────────────────────────────────────────────
# ALERTS
# ──────────────────────────────────────────────────────────

class AlertCreate(BaseModel):
    alert_id: str
    run_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    source: str
    metric: str
    issue_type: str
    severity: str = Field(..., pattern="^(CRITICAL|HIGH|MEDIUM|LOW|INFO)$")
    observed_value: Optional[str] = None
    expected_value: Optional[str] = None
    threshold: Optional[float] = None
    description: str
    rule_id: Optional[str] = None


class AlertResponse(BaseModel):
    id: str
    alert_id: str
    run_id: Optional[str]
    timestamp: Optional[datetime]
    source: str
    metric: str
    issue_type: str
    severity: str
    observed_value: Optional[str]
    expected_value: Optional[str]
    threshold: Optional[float]
    description: str
    status: str
    rule_id: Optional[str]
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    resolution_note: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(OPEN|ACKNOWLEDGED|RESOLVED|IGNORED)$")
    acknowledged_by: Optional[str] = None
    resolution_note: Optional[str] = None


# ──────────────────────────────────────────────────────────
# DRIFT RESULTS
# ──────────────────────────────────────────────────────────

class DriftResultResponse(BaseModel):
    id: str
    run_id: Optional[str]
    drift_type: str
    source_system: str
    column_name: Optional[str]
    is_drifted: bool
    drift_score: float
    severity: Optional[str]
    baseline_value: Optional[str]
    current_value: Optional[str]
    threshold: Optional[float]
    description: Optional[str]
    details: Optional[dict]
    detected_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────
# DATA QUALITY METRICS
# ──────────────────────────────────────────────────────────

class DataQualityMetricResponse(BaseModel):
    id: str
    run_id: Optional[str]
    source_system: str
    total_records: int
    completeness_score: float
    uniqueness_score: float
    validity_score: float
    referential_integrity_score: float
    null_count: int
    duplicate_count: int
    ghost_customer_count: int
    null_revenue_count: int
    inconsistent_count: int
    computed_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────
# COMPARISON RESULTS
# ──────────────────────────────────────────────────────────

class ComparisonResultResponse(BaseModel):
    id: str
    run_id: Optional[str]
    source_a: str
    source_b: str
    comparison_date: Optional[datetime]
    metric_name: str
    value_a: Optional[float]
    value_b: Optional[float]
    absolute_difference: Optional[float]
    percentage_difference: Optional[float]
    threshold_status: Optional[str]
    computed_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────────────────────

class DashboardSummary(BaseModel):
    platform_trust_score: float
    healthy_sources: int
    warning_sources: int
    critical_sources: int
    total_alerts: int
    critical_alerts: int
    high_alerts: int
    open_alerts: int
    pipeline_success_rate: float
    last_pipeline_run: Optional[datetime]
    sources: list[dict]
    recent_alerts: list[dict]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    database: str
    timestamp: datetime


# ──────────────────────────────────────────────────────────
# QUALITY RULES
# ──────────────────────────────────────────────────────────

class QualityRuleResponse(BaseModel):
    id: str
    rule_id: str
    source: str
    column: Optional[str]
    rule_type: str
    description: Optional[str]
    threshold: Optional[float]
    severity: str
    enabled: bool
    config: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}
