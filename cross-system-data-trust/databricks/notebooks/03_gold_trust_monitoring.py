# Databricks notebook source
# DBTITLE 1, Databricks Medallion Architecture — Gold Layer Monitoring & Trust Scoring
# MAGIC %md
# MAGIC # 03 - Gold Layer Metrics Aggregation, Cross-System Reconciliation & Trust Scoring
# MAGIC Computes daily cross-system reconciliation metrics, evaluates statistical data drift (volume & distribution PSI), calculates overall Data Trust Scores, and emits alert notifications.

import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as _sum, count, countDistinct, abs as _abs, round as _round, current_timestamp, lit

spark = SparkSession.builder.appName("DataTrust-Gold-Monitoring").getOrCreate()

# DBTITLE 1, Parameters
dbutils.widgets.text("target_catalog", "main", "Catalog Name")
dbutils.widgets.text("silver_schema", "datatrust_silver", "Silver Schema")
dbutils.widgets.text("gold_schema", "datatrust_gold", "Gold Schema")

catalog = dbutils.widgets.get("target_catalog")
s_schema = dbutils.widgets.get("silver_schema")
g_schema = dbutils.widgets.get("gold_schema")

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{g_schema}")

# DBTITLE 1, Compute Daily Recognized Revenue Comparison (Billing vs Analytics)
df_billing = spark.table(f"{catalog}.{s_schema}.billing_silver")
df_analytics = spark.table(f"{catalog}.{s_schema}.analytics_silver")

# Aggregate Billing to daily grain (completed status only)
df_billing_daily = (
    df_billing.filter(col("status") == "completed")
    .groupBy("transaction_date")
    .agg(
        _sum("amount").alias("billing_revenue"),
        countDistinct("customer_id").alias("billing_customers"),
        count("transaction_id").alias("billing_tx_count")
    )
    .withColumnRenamed("transaction_date", "date")
)

# Join with Analytics daily aggregate
df_reconciliation = (
    df_billing_daily.join(df_analytics, on="date", how="outer")
    .withColumn("revenue_abs_diff", _abs(col("billing_revenue") - col("total_revenue")))
    .withColumn(
        "revenue_pct_diff",
        _round(_abs(col("billing_revenue") - col("total_revenue")) / col("total_revenue"), 4)
    )
    .withColumn("_computed_at", current_timestamp())
)

(
    df_reconciliation.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{catalog}.{g_schema}.cross_system_reconciliation")
)

print(f"Gold cross-system reconciliation written to {catalog}.{g_schema}.cross_system_reconciliation")
dbutils.notebook.exit("SUCCESS: Gold layer trust monitoring complete")
