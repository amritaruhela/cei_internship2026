# Databricks Deployment Guide

This guide explains how to deploy the DataTrust monitoring engine to Azure Databricks, AWS Databricks, or Databricks Community Edition.

## Prerequisites
- Databricks Workspace (Runtime 13.3 LTS or higher with Spark 3.4+)
- Unity Catalog enabled (optional, standard DBFS also supported)
- `delta-spark` package (pre-installed on Databricks Runtime)

## Step 1: Upload Notebooks
Upload the notebooks from `databricks/notebooks/` into your Databricks workspace folder `/Workspace/DataTrust/`:
- `01_ingest_bronze.py`
- `02_silver_transform.py`
- `03_gold_trust_monitoring.py`

## Step 2: Configure Workspace Widgets & Catalogs
Run the setup SQL command in Databricks SQL Editor or a Notebook:

```sql
CREATE CATALOG IF NOT EXISTS main;
CREATE SCHEMA IF NOT EXISTS main.datatrust_bronze;
CREATE SCHEMA IF NOT EXISTS main.datatrust_silver;
CREATE SCHEMA IF NOT EXISTS main.datatrust_gold;
```

## Step 3: Run Ingestion & Monitoring Job Workflow
You can schedule the notebooks as a multi-task Databricks Workflows job:

1. **Task 1 (Ingest Bronze)**: Run `01_ingest_bronze`
   - Parameter `raw_path`: `dbfs:/mnt/datatrust/raw`
   - Parameter `target_catalog`: `main`
2. **Task 2 (Silver Transform)**: Depends on Task 1. Run `02_silver_transform`
3. **Task 3 (Gold Trust & Drift)**: Depends on Task 2. Run `03_gold_trust_monitoring`

## Step 4: Connecting FastAPI Backend to Databricks SQL
To query Databricks Delta tables directly from the DataTrust FastAPI backend, configure `.env`:

```env
DATABRICKS_HOST=https://<your-databricks-instance>.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/endpoints/<endpoint-id>
DATABRICKS_TOKEN=dapi<your-access-token>
```
