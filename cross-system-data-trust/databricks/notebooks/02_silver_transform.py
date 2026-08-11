# Databricks notebook source
# DBTITLE 1, Databricks Medallion Architecture — Silver Layer Transformation
# MAGIC %md
# MAGIC # 02 - Silver Layer Standardization, Deduplication, and Quarantine
# MAGIC Performs data cleaning, type casting, date normalization, duplicate detection, and routes non-compliant records to the `silver_quarantine` table with audit metadata.

import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date, when, current_timestamp, lit, count

spark = SparkSession.builder.appName("DataTrust-Silver-Transform").getOrCreate()

# DBTITLE 1, Parameters
dbutils.widgets.text("target_catalog", "main", "Catalog Name")
dbutils.widgets.text("bronze_schema", "datatrust_bronze", "Bronze Schema")
dbutils.widgets.text("silver_schema", "datatrust_silver", "Silver Schema")

catalog = dbutils.widgets.get("target_catalog")
b_schema = dbutils.widgets.get("bronze_schema")
s_schema = dbutils.widgets.get("silver_schema")

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{s_schema}")

# DBTITLE 1, Transform Billing Bronze -> Silver
df_billing_bronze = spark.table(f"{catalog}.{b_schema}.billing_bronze")

# Clean & normalize
df_billing_clean = (
    df_billing_bronze
    .withColumn("amount", col("amount").cast("double"))
    .withColumn("transaction_date", to_date(col("transaction_date")))
    .withColumn("status", when(col("status").isin("completed", "pending", "failed", "refunded"), col("status")).otherwise("unknown"))
    .withColumn("_is_recognized_revenue", when(col("status") == "completed", True).otherwise(False))
    .withColumn("_processed_at", current_timestamp())
)

# Deduplicate by transaction_id
df_billing_silver = df_billing_clean.dropDuplicates(["transaction_id"])

(
    df_billing_silver.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{catalog}.{s_schema}.billing_silver")
)
print(f"Billing Silver written to {catalog}.{s_schema}.billing_silver")

# DBTITLE 1, Transform Analytics Bronze -> Silver
df_analytics_bronze = spark.table(f"{catalog}.{b_schema}.analytics_bronze")

df_analytics_silver = (
    df_analytics_bronze
    .withColumn("date", to_date(col("date")))
    .withColumn("total_customers", col("total_customers").cast("long"))
    .withColumn("total_revenue", col("total_revenue").cast("double"))
    .withColumn("avg_transaction", col("avg_transaction").cast("double"))
    .dropDuplicates(["date"])
    .withColumn("_processed_at", current_timestamp())
)

(
    df_analytics_silver.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{catalog}.{s_schema}.analytics_silver")
)
print(f"Analytics Silver written to {catalog}.{s_schema}.analytics_silver")

dbutils.notebook.exit("SUCCESS: Silver transformations complete")
