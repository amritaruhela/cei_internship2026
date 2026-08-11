# Databricks notebook source
# DBTITLE 1, Databricks Medallion Architecture — Bronze Ingestion Pipeline
# MAGIC %md
# MAGIC # 01 - Bronze Layer Raw Data Ingestion
# MAGIC Ingests raw CRM, Billing, and Analytics datasets into Delta Lake Bronze tables with ingestion metadata (`_ingested_at`, `_source_file`, `_run_id`).

import os
import uuid
from datetime import datetime, timezone
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, lit, input_file_name

spark = SparkSession.builder.appName("DataTrust-Bronze-Ingestion").getOrCreate()

# DBTITLE 1, Parameters
dbutils.widgets.text("raw_path", "/mnt/data/raw", "Raw Data Path")
dbutils.widgets.text("target_catalog", "main", "Catalog Name")
dbutils.widgets.text("target_schema", "datatrust_bronze", "Target Schema")
dbutils.widgets.text("run_id", "", "Pipeline Run ID")

raw_path = dbutils.widgets.get("raw_path")
catalog = dbutils.widgets.get("target_catalog")
schema = dbutils.widgets.get("target_schema")
run_id = dbutils.widgets.get("run_id") or str(uuid.uuid4())

spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")

# DBTITLE 1, Ingest Billing Raw Data -> Bronze Delta Table
billing_path = os.path.join(raw_path, "billing_dataset.csv")
print(f"Reading Billing raw data from {billing_path}...")

df_billing_raw = (
    spark.read.format("csv")
    .option("header", "true")
    .option("inferSchema", "true")
    .load(billing_path)
    .withColumn("_ingested_at", current_timestamp())
    .withColumn("_source_file", input_file_name())
    .withColumn("_run_id", lit(run_id))
)

(
    df_billing_raw.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{catalog}.{schema}.billing_bronze")
)
print(f"Billing Bronze written to {catalog}.{schema}.billing_bronze")

# DBTITLE 1, Ingest Analytics Raw Data -> Bronze Delta Table
analytics_path = os.path.join(raw_path, "analytics_dataset.csv")
print(f"Reading Analytics raw data from {analytics_path}...")

df_analytics_raw = (
    spark.read.format("csv")
    .option("header", "true")
    .option("inferSchema", "true")
    .load(analytics_path)
    .withColumn("_ingested_at", current_timestamp())
    .withColumn("_source_file", input_file_name())
    .withColumn("_run_id", lit(run_id))
)

(
    df_analytics_raw.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{catalog}.{schema}.analytics_bronze")
)
print(f"Analytics Bronze written to {catalog}.{schema}.analytics_bronze")

# DBTITLE 1, Ingest CRM Raw Data -> Bronze Delta Table
crm_path = os.path.join(raw_path, "crm.csv")
if os.path.exists(crm_path):
    print(f"Reading CRM raw data from {crm_path}...")
    df_crm_raw = (
        spark.read.format("csv")
        .option("header", "true")
        .option("inferSchema", "true")
        .load(crm_path)
        .withColumn("_ingested_at", current_timestamp())
        .withColumn("_source_file", input_file_name())
        .withColumn("_run_id", lit(run_id))
    )
    (
        df_crm_raw.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(f"{catalog}.{schema}.crm_bronze")
    )
    print(f"CRM Bronze written to {catalog}.{schema}.crm_bronze")

dbutils.notebook.exit(f"SUCCESS: Ingested raw datasets to Bronze catalog {catalog}.{schema}")
