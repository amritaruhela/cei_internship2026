"""
Spark Session Factory
Creates and manages a singleton SparkSession with Delta Lake support.
Supports both local development mode and Databricks deployment.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_spark_session: Optional[object] = None


def get_spark(app_name: str = "DataTrust", master: str = "local[*]", driver_memory: str = "2g"):
    """
    Get or create a SparkSession with Delta Lake enabled.
    
    In local mode: uses delta-spark with local filesystem.
    In Databricks mode: uses the pre-existing SparkSession from the cluster.
    """
    global _spark_session
    if _spark_session is not None:
        return _spark_session

    try:
        from pyspark.sql import SparkSession
        import delta

        _spark_session = (
            SparkSession.builder.appName(app_name)
            .master(master)
            .config("spark.driver.memory", driver_memory)
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config(
                "spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog",
            )
            .config("spark.sql.shuffle.partitions", "8")
            .config("spark.default.parallelism", "8")
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.databricks.delta.retentionDurationCheck.enabled", "false")
            .getOrCreate()
        )

        # Suppress noisy Spark logs
        _spark_session.sparkContext.setLogLevel("WARN")
        logger.info(f"SparkSession created: {app_name} @ {master}")
        return _spark_session

    except ImportError as e:
        logger.warning(f"Delta/PySpark not available, falling back to pandas mode: {e}")
        return None


def stop_spark() -> None:
    global _spark_session
    if _spark_session is not None:
        _spark_session.stop()
        _spark_session = None
        logger.info("SparkSession stopped")


def get_databricks_spark():
    """
    For Databricks deployment: returns the existing cluster SparkSession.
    This is the standard pattern inside Databricks notebooks.
    """
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()
        logger.info("Using existing Databricks SparkSession")
        return spark
    except Exception as e:
        logger.error(f"Failed to get Databricks SparkSession: {e}")
        raise
