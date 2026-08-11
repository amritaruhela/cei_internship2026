# DataTrust Architecture & Design Specification

## Overview
DataTrust is an enterprise-grade Data Observability and Data Quality Monitoring platform built using PySpark, SQL, FastAPI, and React. It automatically detects cross-system data drift, referential violations, and quality anomalies across CRM, Billing, and Analytics platforms.

```
┌─────────────────┐      ┌──────────────────┐      ┌───────────────────┐
│   CRM System    │      │  Billing System  │      │ Analytics Platform│
│  (Customer DB)  │      │ (Transactions)   │      │ (Daily Aggregates)│
└────────┬────────┘      └────────┬─────────┘      └─────────┬─────────┘
         │                        │                          │
         ▼                        ▼                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                            BRONZE LAYER                              │
│         Raw Data Ingestion + Audit Metadata (_ingested_at)           │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                            SILVER LAYER                              │
│       Standardization, Deduplication, Type Cleaning & Quarantine     │
│   (Invalid records isolated to data/silver/quarantine/ with audit)   │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                             GOLD LAYER                               │
│        Quality Metrics, Reconciliation, & Statistical Drift          │
│   - Volume Drift (30-day Z-Score)                                    │
│   - Distribution Drift (PSI & KS-Test)                               │
│   - Schema Evolution Snapshot Diffing                                │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     TRUST SCORING & ALERTING                         │
│       - Explainable 0-100 Trust Score per Source & Platform          │
│       - Configurable Alert Engine (CRITICAL/HIGH/MEDIUM)             │
└──────────────────────────────────────────────────────────────────────┘
```

## Medallion Architecture Specification

### Bronze Layer (Raw Ingestion)
- Reads raw CSV/JSON batch files or streaming event payloads.
- Appends system metadata:
  - `_ingested_at`: UTC timestamp of ingestion.
  - `_source_file`: Original file path or stream partition.
  - `_run_id`: UUID for pipeline run traceability.
- Saved in Parquet/Delta Lake format at `data/bronze/{source}/`.

### Silver Layer (Cleaned & Standardized)
- Normalizes column names (snake_case), parses ISO-8601 dates, and enforces numeric types.
- Deduplicates on business keys (`transaction_id`, `customer_id`, `date`).
- **Non-Destructive Quarantine Mechanism**:
  Invalid or corrupt records (e.g., GHOST customer IDs, missing mandatory fields) are **NOT deleted or silently dropped**. Instead, they are routed to `data/silver/quarantine/` attached with:
  - `reason`: Exact business or quality rule violation.
  - `rule_id`: Identifier of violated quality rule.
  - `run_id`: Execution pipeline run ID.
  - `raw_record`: Original payload for debugging and reprocessing.

### Gold Layer (Aggregated Metrics & Drift Detection)
1. **Quality Metrics**: Computes completeness, uniqueness, validity, referential integrity, and freshness per source.
2. **Reconciliation**:
   - **Grain Rule**: Analytics operates at the *daily grain* (1 row/day). Billing operates at the *transaction grain*.
   - **Revenue Recognition Rule**: Billing revenue is aggregated to daily grain using `SUM(amount) WHERE status = 'completed'`.
   - Compares daily recognized revenue and transacting customer counts across systems.
3. **Statistical Drift Detection**:
   - **Volume Drift**: Compares current day transaction count vs 30-day rolling mean using Z-Score: \(Z = \frac{|x - \mu|}{\sigma}\). Flagged if \(|Z| > 2.5\) or relative change exceeds threshold.
   - **Distribution Drift**: Measures feature shift using Population Stability Index (PSI):
     \[
     \text{PSI} = \sum \left( P_{\text{current}} - P_{\text{baseline}} \right) \times \ln\left( \frac{P_{\text{current}}}{P_{\text{baseline}}} \right)
     \]
     - \(\text{PSI} < 0.10\): Stable (No drift)
     - \(0.10 \le \text{PSI} < 0.20\): Moderate shift
     - \(\text{PSI} \ge 0.20\): Critical distribution drift
     Supplemented by Kolmogorov-Smirnov 2-sample test (\(p\text{-value} < 0.05\)).
   - **Schema Drift**: JSON schema snapshot diffing detecting new columns, removed columns, and type changes.

## Data Trust Score Formula & Explainability
\[
\text{Trust Score} = \left( 0.20 \cdot \text{Completeness} + 0.25 \cdot \text{Consistency} + 0.20 \cdot \text{Accuracy} + 0.15 \cdot \text{Freshness} + 0.10 \cdot \text{Uniqueness} + 0.10 \cdot \text{Drift Stability} \right) \times 100
\]

Every reduction in trust score is logged with a human-readable explanation (e.g., *"Score reduced by 8 pts: 18 GHOST customer records present"*).
