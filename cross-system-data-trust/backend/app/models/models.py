"""
SQLAlchemy ORM Models for DataTrust Platform
All application-level metadata is stored in PostgreSQL.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Index,
    Integer, String, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.session import Base


def _now():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


# ──────────────────────────────────────────────────────────
# USER MODEL
# ──────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="VIEWER")  # ADMIN, DATA_ENGINEER, VIEWER
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    last_login = Column(DateTime(timezone=True), nullable=True)


# ──────────────────────────────────────────────────────────
# PIPELINE RUNS
# ──────────────────────────────────────────────────────────

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    __table_args__ = (
        Index("ix_pipeline_runs_started_at", "started_at"),
        Index("ix_pipeline_runs_status", "status"),
        Index("ix_pipeline_runs_source", "source"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_id = Column(String(64), unique=True, nullable=False, index=True)
    pipeline_name = Column(String(255), nullable=False)
    source = Column(String(100), nullable=True)
    scenario = Column(String(100), nullable=True)
    status = Column(String(50), default="RUNNING")  # RUNNING/SUCCESS/PARTIAL_SUCCESS/FAILED
    started_at = Column(DateTime(timezone=True), default=_now)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    records_read = Column(Integer, default=0)
    records_written = Column(Integer, default=0)
    records_rejected = Column(Integer, default=0)
    records_quarantined = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    stage_summary = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_now)

    alerts = relationship("Alert", back_populates="pipeline_run", lazy="selectin")
    trust_scores = relationship("TrustScore", back_populates="pipeline_run", lazy="selectin")


# ──────────────────────────────────────────────────────────
# TRUST SCORES
# ──────────────────────────────────────────────────────────

class TrustScore(Base):
    __tablename__ = "trust_scores"
    __table_args__ = (
        Index("ix_trust_scores_source", "source_system"),
        Index("ix_trust_scores_computed_at", "computed_at"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    pipeline_run_id = Column(UUID(as_uuid=False), ForeignKey("pipeline_runs.id"), nullable=True)
    run_id = Column(String(64), nullable=True)
    source_system = Column(String(100), nullable=False)
    overall_score = Column(Float, nullable=False)
    grade = Column(String(5), nullable=True)
    health_status = Column(String(50), nullable=True)
    completeness_score = Column(Float, default=1.0)
    consistency_score = Column(Float, default=1.0)
    accuracy_score = Column(Float, default=1.0)
    freshness_score = Column(Float, default=1.0)
    uniqueness_score = Column(Float, default=1.0)
    drift_stability_score = Column(Float, default=1.0)
    weights = Column(JSON, default=dict)
    explanations = Column(JSON, default=list)
    computed_at = Column(DateTime(timezone=True), default=_now)

    pipeline_run = relationship("PipelineRun", back_populates="trust_scores")


# ──────────────────────────────────────────────────────────
# ALERTS
# ──────────────────────────────────────────────────────────

class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_severity", "severity"),
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_source", "source"),
        Index("ix_alerts_timestamp", "timestamp"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    alert_id = Column(String(64), unique=True, nullable=False, index=True)
    pipeline_run_id = Column(UUID(as_uuid=False), ForeignKey("pipeline_runs.id"), nullable=True)
    run_id = Column(String(64), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=_now)
    source = Column(String(100), nullable=False)
    metric = Column(String(255), nullable=False)
    issue_type = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=False)  # CRITICAL/HIGH/MEDIUM/LOW/INFO
    observed_value = Column(Text, nullable=True)
    expected_value = Column(Text, nullable=True)
    threshold = Column(Float, nullable=True)
    description = Column(Text, nullable=False)
    status = Column(String(50), default="OPEN")  # OPEN/ACKNOWLEDGED/RESOLVED/IGNORED
    rule_id = Column(String(100), nullable=True)
    acknowledged_by = Column(String(255), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolution_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    pipeline_run = relationship("PipelineRun", back_populates="alerts")


# ──────────────────────────────────────────────────────────
# DRIFT RESULTS
# ──────────────────────────────────────────────────────────

class DriftResult(Base):
    __tablename__ = "drift_results"
    __table_args__ = (
        Index("ix_drift_source", "source_system"),
        Index("ix_drift_type", "drift_type"),
        Index("ix_drift_detected_at", "detected_at"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_id = Column(String(64), nullable=True)
    drift_type = Column(String(50), nullable=False)  # volume/distribution/schema
    source_system = Column(String(100), nullable=False)
    column_name = Column(String(255), nullable=True)
    is_drifted = Column(Boolean, default=False)
    drift_score = Column(Float, default=0.0)
    severity = Column(String(50), nullable=True)
    baseline_value = Column(Text, nullable=True)
    current_value = Column(Text, nullable=True)
    threshold = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    details = Column(JSON, default=dict)
    detected_at = Column(DateTime(timezone=True), default=_now)


# ──────────────────────────────────────────────────────────
# DATA QUALITY METRICS
# ──────────────────────────────────────────────────────────

class DataQualityMetric(Base):
    __tablename__ = "data_quality_metrics"
    __table_args__ = (
        Index("ix_dqm_source", "source_system"),
        Index("ix_dqm_computed_at", "computed_at"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_id = Column(String(64), nullable=True)
    source_system = Column(String(100), nullable=False)
    total_records = Column(Integer, default=0)
    completeness_score = Column(Float, default=1.0)
    uniqueness_score = Column(Float, default=1.0)
    validity_score = Column(Float, default=1.0)
    referential_integrity_score = Column(Float, default=1.0)
    null_count = Column(Integer, default=0)
    duplicate_count = Column(Integer, default=0)
    ghost_customer_count = Column(Integer, default=0)
    null_revenue_count = Column(Integer, default=0)
    inconsistent_count = Column(Integer, default=0)
    extra_metrics = Column(JSON, default=dict)
    computed_at = Column(DateTime(timezone=True), default=_now)


# ──────────────────────────────────────────────────────────
# COMPARISON RESULTS
# ──────────────────────────────────────────────────────────

class ComparisonResult(Base):
    __tablename__ = "comparison_results"
    __table_args__ = (
        Index("ix_comp_sources", "source_a", "source_b"),
        Index("ix_comp_date", "comparison_date"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_id = Column(String(64), nullable=True)
    source_a = Column(String(100), nullable=False)
    source_b = Column(String(100), nullable=False)
    comparison_date = Column(DateTime(timezone=True), nullable=True)
    metric_name = Column(String(255), nullable=False)
    value_a = Column(Float, nullable=True)
    value_b = Column(Float, nullable=True)
    absolute_difference = Column(Float, nullable=True)
    percentage_difference = Column(Float, nullable=True)
    threshold_status = Column(String(50), nullable=True)
    computed_at = Column(DateTime(timezone=True), default=_now)


# ──────────────────────────────────────────────────────────
# SCHEMA SNAPSHOTS
# ──────────────────────────────────────────────────────────

class SchemaSnapshot(Base):
    __tablename__ = "schema_snapshots"
    __table_args__ = (
        Index("ix_schema_source", "source_system"),
        Index("ix_schema_captured_at", "captured_at"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_id = Column(String(64), nullable=True)
    source_system = Column(String(100), nullable=False)
    version = Column(Integer, default=1)
    schema_json = Column(JSON, nullable=False, default=dict)
    column_count = Column(Integer, default=0)
    columns = Column(JSON, default=list)
    captured_at = Column(DateTime(timezone=True), default=_now)


# ──────────────────────────────────────────────────────────
# DATA QUALITY RULES
# ──────────────────────────────────────────────────────────

class QualityRule(Base):
    __tablename__ = "quality_rules"
    __table_args__ = (
        Index("ix_rules_source", "source"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    rule_id = Column(String(50), unique=True, nullable=False)
    source = Column(String(100), nullable=False)
    column = Column(String(255), nullable=True)
    rule_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    threshold = Column(Float, nullable=True)
    severity = Column(String(50), default="MEDIUM")
    enabled = Column(Boolean, default=True)
    config = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)
