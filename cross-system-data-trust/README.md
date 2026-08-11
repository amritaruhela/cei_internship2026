# DataTrust | Cross-System Data Drift & Trust Monitoring Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![PySpark](https://img.shields.io/badge/PySpark-3.5.3-orange.svg)](https://spark.apache.org/)
[![Delta Lake](https://img.shields.io/badge/Delta_Lake-3.2.0-blue.svg)](https://delta.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-emerald.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-sky.svg)](https://reactjs.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38bdf8.svg)](https://tailwindcss.com/)
[![License](https://img.shields.io/badge/License-Enterprise-indigo.svg)]()

> **Production-grade enterprise Data Observability platform** designed to monitor, score, and reconcile data consistency, referential integrity, and statistical drift across **CRM**, **Billing**, and **Analytics** systems.

---

## 📌 Executive Summary & Business Problem

Modern enterprise tech stacks maintain core business information across decoupled, independent systems:
1. **CRM**: Customer profiles, signups, and account statuses.
2. **Billing**: Transactional records, payment events, and invoices.
3. **Analytics**: Aggregated daily business KPIs, revenue metrics, and user analytics.

Because these platforms update asynchronously and follow independent ingestion schedules, modern data lakes are prone to **silent data drift**, **referential integrity violations**, **unannounced schema evolution**, and **revenue discrepancies**.

### Key Challenges Solved:
- **GHOST Records**: Detects billing transactions associated with non-existent CRM customer IDs.
- **Grain & Revenue Recognition Mismatch**: Reconciles daily transaction aggregates (`SUM(amount) WHERE status = 'completed'`) against analytics platforms.
- **Statistical Distribution Shift**: Quantifies population drift using **Population Stability Index (PSI)** and **Kolmogorov-Smirnov (KS)** tests.
- **Volume Anomalies**: Flags sudden traffic spikes or drops using a **30-day rolling Z-Score**.
- **Non-Destructive Quarantine**: Routes invalid records to `data/silver/quarantine/` with audit metadata instead of dropping data silently.

---

## 🏗 Architecture & Design System

DataTrust implements the industry-standard **Medallion (Lakehouse) Architecture**:

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

---

## 🧮 Data Trust Score Methodology

DataTrust calculates a **0–100 Data Trust Score** for each system and across the platform using the following weighted formula:

$$\text{Trust Score} = \left( 0.20 \cdot \text{Completeness} + 0.25 \cdot \text{Consistency} + 0.20 \cdot \text{Accuracy} + 0.15 \cdot \text{Freshness} + 0.10 \cdot \text{Uniqueness} + 0.10 \cdot \text{Drift} \right) \times 100$$

Every score reduction is attached to a **human-readable explanation log**:
- *"Completeness: 83.4% (-3.3 pts, 1941 null values)"*
- *"Consistency: 94.9% (-1.3 pts, 1200 ghost customer records)"*
- *"Accuracy/Reconciliation: Revenue differs by 11.3% vs Analytics (-4.6 pts)"*

---

## 🚀 Quickstart Guide

### 1. Run End-to-End Pipeline Demo (Local Execution)
Execute the end-to-end data pipeline simulation with controlled anomaly injection:

```bash
# Execute full pipeline with mixed anomaly scenario
python scripts/run_demo.py --scenario mixed
```

Supported scenario flags:
- `--scenario healthy`: Baseline pristine data flow.
- `--scenario missing_records`: Simulates 5% record loss.
- `--scenario duplicates`: Injects duplicate transactions.
- `--scenario revenue_mismatch`: Injects revenue recognition discrepancies.
- `--scenario schema_drift`: Injects unexpected new columns.
- `--scenario mixed`: Runs full suite of data anomalies.

### 2. Run Data Engine Unit Test Suite
```bash
python -m pytest data-engine/tests --verbose
```

### 3. Run Full Platform Stack via Docker Compose
```bash
docker compose up --build
```
Services spun up:
- **PostgreSQL**: `localhost:5432` (Metadata & alerts DB)
- **FastAPI Backend**: `http://localhost:8000/docs` (Interactive OpenAPI Swagger UI)
- **React Dashboard**: `http://localhost:3000` (Enterprise Observability Frontend)

---

## 📁 Repository Structure

```
cross-system-data-trust/
├── data-engine/              # Core PySpark & Data Processing Engine
│   ├── config/               # YAML quality rules, thresholds, and mappings
│   ├── src/
│   │   ├── bronze/           # Raw ingestion handlers
│   │   ├── silver/           # Cleaning, deduplication, & quarantine
│   │   ├── gold/             # Aggregators & reconciliation
│   │   ├── quality/          # Generic Quality Rule Engine
│   │   ├── drift/            # Volume (z-score), Distribution (PSI/KS), Schema drift
│   │   ├── reconciliation/   # Cross-system missing/extra/mismatch engine
│   │   ├── scoring/          # Explainable Data Trust Score calculator
│   │   ├── alerts/           # Configurable alerting engine
│   │   └── pipeline.py       # Main pipeline orchestrator
│   └── tests/                # Pytest unit & integration test suite
├── backend/                  # FastAPI Backend API Service
│   ├── app/
│   │   ├── api/v1/           # REST endpoints (Dashboard, Alerts, Drift, Quality, Pipelines)
│   │   ├── core/             # JWT Security & Config settings
│   │   ├── database/         # SQLAlchemy async session
│   │   ├── models/           # PostgreSQL ORM models
│   │   └── schemas/          # Pydantic request/response models
├── frontend/                 # React + TypeScript + Vite + Tailwind Dashboard
│   ├── src/
│   │   ├── pages/            # 10 Enterprise Observability Pages
│   │   ├── components/       # Navbar, Sidebar, Recharts UI elements
│   │   └── api/              # Axios API client with fallback data
├── databricks/               # Databricks PySpark Production Notebooks
├── sql/                      # PostgreSQL DDL Schemas, Views, & Seed scripts
├── docs/                     # Architecture & Databricks Deployment guides
├── scripts/                  # Executable CLI & Demo scripts
└── docker-compose.yml        # Multi-container orchestration
```

---

## 🛠 Technology Stack

- **Data Processing**: Python 3.10+, PySpark 3.5, Pandas, SciPy (KS-test, Chi-square), Delta Lake 3.2, PyYAML.
- **Backend API**: FastAPI, Uvicorn, AsyncSQLAlchemy, AsyncPG, Pydantic v2, JWT Security.
- **Frontend Dashboard**: React 18, TypeScript, Vite, Tailwind CSS, Lucide React, Recharts.
- **Database & DevOps**: PostgreSQL 15, Docker, Docker Compose, GitHub Actions CI/CD.
- **Cloud & Lakehouse**: Databricks Workflows, Unity Catalog, Delta Lake.

---

## 📄 License & Attribution
Designed & Built for Enterprise Data Platform & Data Observability Standards.
