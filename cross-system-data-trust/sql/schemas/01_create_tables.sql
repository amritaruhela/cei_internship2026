-- ============================================================
-- Cross-System Data Drift & Trust Monitoring Platform
-- SQL DDL Schemas (PostgreSQL & Delta Lake compatible)
-- ============================================================

-- 1. USERS
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'VIEWER',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- 2. PIPELINE RUNS
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id VARCHAR(36) PRIMARY KEY,
    run_id VARCHAR(64) UNIQUE NOT NULL,
    pipeline_name VARCHAR(255) NOT NULL,
    source VARCHAR(100),
    scenario VARCHAR(100),
    status VARCHAR(50) DEFAULT 'RUNNING',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_seconds FLOAT,
    records_read INT DEFAULT 0,
    records_written INT DEFAULT 0,
    records_rejected INT DEFAULT 0,
    records_quarantined INT DEFAULT 0,
    error_message TEXT,
    stage_summary JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_pipeline_runs_started_at ON pipeline_runs (started_at DESC);
CREATE INDEX IF NOT EXISTS ix_pipeline_runs_status ON pipeline_runs (status);

-- 3. TRUST SCORES
CREATE TABLE IF NOT EXISTS trust_scores (
    id VARCHAR(36) PRIMARY KEY,
    pipeline_run_id VARCHAR(36) REFERENCES pipeline_runs(id),
    run_id VARCHAR(64),
    source_system VARCHAR(100) NOT NULL,
    overall_score FLOAT NOT NULL,
    grade VARCHAR(5),
    health_status VARCHAR(50),
    completeness_score FLOAT DEFAULT 1.0,
    consistency_score FLOAT DEFAULT 1.0,
    accuracy_score FLOAT DEFAULT 1.0,
    freshness_score FLOAT DEFAULT 1.0,
    uniqueness_score FLOAT DEFAULT 1.0,
    drift_stability_score FLOAT DEFAULT 1.0,
    weights JSONB,
    explanations JSONB,
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_trust_scores_source ON trust_scores (source_system);
CREATE INDEX IF NOT EXISTS ix_trust_scores_computed_at ON trust_scores (computed_at DESC);

-- 4. ALERTS
CREATE TABLE IF NOT EXISTS alerts (
    id VARCHAR(36) PRIMARY KEY,
    alert_id VARCHAR(64) UNIQUE NOT NULL,
    pipeline_run_id VARCHAR(36) REFERENCES pipeline_runs(id),
    run_id VARCHAR(64),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(100) NOT NULL,
    metric VARCHAR(255) NOT NULL,
    issue_type VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    observed_value TEXT,
    expected_value TEXT,
    threshold FLOAT,
    description TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'OPEN',
    rule_id VARCHAR(100),
    acknowledged_by VARCHAR(255),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolution_note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_alerts_severity ON alerts (severity);
CREATE INDEX IF NOT EXISTS ix_alerts_status ON alerts (status);
CREATE INDEX IF NOT EXISTS ix_alerts_source ON alerts (source);

-- 5. DRIFT RESULTS
CREATE TABLE IF NOT EXISTS drift_results (
    id VARCHAR(36) PRIMARY KEY,
    run_id VARCHAR(64),
    drift_type VARCHAR(50) NOT NULL,
    source_system VARCHAR(100) NOT NULL,
    column_name VARCHAR(255),
    is_drifted BOOLEAN DEFAULT FALSE,
    drift_score FLOAT DEFAULT 0.0,
    severity VARCHAR(50),
    baseline_value TEXT,
    current_value TEXT,
    threshold FLOAT,
    description TEXT,
    details JSONB,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_drift_source ON drift_results (source_system);
CREATE INDEX IF NOT EXISTS ix_drift_type ON drift_results (drift_type);

-- 6. DATA QUALITY METRICS
CREATE TABLE IF NOT EXISTS data_quality_metrics (
    id VARCHAR(36) PRIMARY KEY,
    run_id VARCHAR(64),
    source_system VARCHAR(100) NOT NULL,
    total_records INT DEFAULT 0,
    completeness_score FLOAT DEFAULT 1.0,
    uniqueness_score FLOAT DEFAULT 1.0,
    validity_score FLOAT DEFAULT 1.0,
    referential_integrity_score FLOAT DEFAULT 1.0,
    null_count INT DEFAULT 0,
    duplicate_count INT DEFAULT 0,
    ghost_customer_count INT DEFAULT 0,
    null_revenue_count INT DEFAULT 0,
    inconsistent_count INT DEFAULT 0,
    extra_metrics JSONB,
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. QUALITY RULES
CREATE TABLE IF NOT EXISTS quality_rules (
    id VARCHAR(36) PRIMARY KEY,
    rule_id VARCHAR(50) UNIQUE NOT NULL,
    source VARCHAR(100) NOT NULL,
    column_name VARCHAR(255),
    rule_type VARCHAR(100) NOT NULL,
    description TEXT,
    threshold FLOAT,
    severity VARCHAR(50) DEFAULT 'MEDIUM',
    enabled BOOLEAN DEFAULT TRUE,
    config JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
