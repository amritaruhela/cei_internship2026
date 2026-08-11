"""
Gold Layer Metrics Aggregator

Computes monitoring-ready metrics from Silver layer data:
- Daily quality metrics per source
- Cross-system comparison metrics (daily grain)
- Volume statistics for drift detection baseline
- Schema snapshots

Business rule (documented):
  Billing recognized revenue = SUM(amount WHERE status='completed')
  Analytics total_revenue = daily aggregate from analytics platform
  These are compared at daily grain.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class GoldAggregator:
    """Computes Gold layer metrics from Silver data."""

    def __init__(self, gold_dir: Path, run_id: Optional[str] = None):
        self.gold_dir = Path(gold_dir)
        self.gold_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or str(uuid.uuid4())
        self.computed_at = datetime.now(timezone.utc).isoformat()

    # ──────────────────────────────────────────────────
    # DATA QUALITY METRICS
    # ──────────────────────────────────────────────────

    def compute_quality_metrics(
        self,
        billing_df: pd.DataFrame,
        analytics_df: pd.DataFrame,
        crm_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Compute per-source data quality metrics.
        Returns a DataFrame with one row per source system.
        """
        rows = []

        rows.append(self._quality_for_billing(billing_df))
        rows.append(self._quality_for_analytics(analytics_df))
        if crm_df is not None and len(crm_df) > 0:
            rows.append(self._quality_for_crm(crm_df))

        df = pd.DataFrame(rows)
        df["_computed_at"] = self.computed_at
        df["_run_id"] = self.run_id
        return df

    def _quality_for_billing(self, df: pd.DataFrame) -> dict:
        total = len(df)
        null_amount = df["amount"].isna().sum() if "amount" in df.columns else 0
        dup_txn = df["transaction_id"].duplicated().sum() if "transaction_id" in df.columns else 0
        valid_status = df["status"].isin(["completed", "pending", "failed", "refunded"]).sum() if "status" in df.columns else total

        # Ghost customers (GHOST prefix)
        ghost_count = 0
        if "customer_id" in df.columns:
            ghost_count = df["customer_id"].str.startswith("GHOST", na=False).sum()

        return {
            "source_system": "billing",
            "total_records": total,
            "completeness_score": round(1 - (null_amount / max(total, 1)), 4),
            "uniqueness_score": round(1 - (dup_txn / max(total, 1)), 4),
            "validity_score": round(valid_status / max(total, 1), 4),
            "null_count": int(null_amount),
            "duplicate_count": int(dup_txn),
            "ghost_customer_count": int(ghost_count),
            "referential_integrity_score": round(1 - (ghost_count / max(total, 1)), 4),
        }

    def _quality_for_analytics(self, df: pd.DataFrame) -> dict:
        total = len(df)
        null_revenue = df["total_revenue"].isna().sum() if "total_revenue" in df.columns else 0
        null_customers = df["total_customers"].isna().sum() if "total_customers" in df.columns else 0
        dup_dates = df["date"].duplicated().sum() if "date" in df.columns else 0

        # Internal inconsistency: customers=0 but revenue > 0
        inconsistent = 0
        if "total_customers" in df.columns and "total_revenue" in df.columns:
            inconsistent = ((df["total_customers"] == 0) & (df["total_revenue"] > 0) & df["total_revenue"].notna()).sum()

        completeness = 1 - ((null_revenue + null_customers) / max(total * 2, 1))

        return {
            "source_system": "analytics",
            "total_records": total,
            "completeness_score": round(completeness, 4),
            "uniqueness_score": round(1 - (dup_dates / max(total, 1)), 4),
            "validity_score": round(1 - (inconsistent / max(total, 1)), 4),
            "null_count": int(null_revenue + null_customers),
            "duplicate_count": int(dup_dates),
            "ghost_customer_count": 0,
            "referential_integrity_score": 1.0,
            "null_revenue_count": int(null_revenue),
            "inconsistent_count": int(inconsistent),
        }

    def _quality_for_crm(self, df: pd.DataFrame) -> dict:
        total = len(df)
        null_email = df["email"].isna().sum() if "email" in df.columns else 0
        dup_cid = df["customer_id"].duplicated().sum() if "customer_id" in df.columns else 0

        return {
            "source_system": "crm",
            "total_records": total,
            "completeness_score": round(1 - (null_email / max(total, 1)), 4),
            "uniqueness_score": round(1 - (dup_cid / max(total, 1)), 4),
            "validity_score": 1.0,
            "null_count": int(null_email),
            "duplicate_count": int(dup_cid),
            "ghost_customer_count": 0,
            "referential_integrity_score": 1.0,
        }

    # ──────────────────────────────────────────────────
    # CROSS-SYSTEM COMPARISON (Daily Grain)
    # ──────────────────────────────────────────────────

    def compute_cross_system_comparison(
        self,
        billing_df: pd.DataFrame,
        analytics_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Compare Billing daily aggregates vs Analytics daily aggregates.
        
        GRAIN DOCUMENTED:
        Analytics is daily aggregate. Billing is transaction-level.
        Billing must be aggregated to daily before comparison.
        
        Business rule: Only 'completed' billing transactions count as
        recognized revenue for reconciliation purposes.
        """
        # Billing daily aggregation — recognized revenue only
        billing = billing_df.copy()
        if "transaction_date" in billing.columns:
            billing["transaction_date"] = pd.to_datetime(billing["transaction_date"]).dt.date
        
        completed = billing[billing["status"] == "completed"].copy()
        
        billing_daily = completed.groupby("transaction_date").agg(
            billing_revenue=("amount", "sum"),
            billing_customers=("customer_id", "nunique"),
            billing_avg_transaction=("amount", "mean"),
            billing_tx_count=("transaction_id", "count"),
        ).reset_index()
        billing_daily.rename(columns={"transaction_date": "date"}, inplace=True)

        # Analytics daily
        analytics = analytics_df.copy()
        if "date" in analytics.columns:
            analytics["date"] = pd.to_datetime(analytics["date"]).dt.date

        # Join on date
        merged = pd.merge(billing_daily, analytics, on="date", how="outer", suffixes=("_billing", "_analytics"))
        
        # Compute differences
        merged["revenue_absolute_diff"] = (merged["billing_revenue"] - merged["total_revenue"]).abs()
        merged["revenue_pct_diff"] = (
            merged["revenue_absolute_diff"] / merged["total_revenue"].replace(0, float("nan"))
        ).fillna(0)

        merged["customer_absolute_diff"] = (merged["billing_customers"] - merged["total_customers"]).abs()
        merged["customer_pct_diff"] = (
            merged["customer_absolute_diff"] / merged["total_customers"].replace(0, float("nan"))
        ).fillna(0)

        merged["avg_tx_absolute_diff"] = (merged["billing_avg_transaction"] - merged["avg_transaction"]).abs()
        merged["avg_tx_pct_diff"] = (
            merged["avg_tx_absolute_diff"] / merged["avg_transaction"].replace(0, float("nan"))
        ).fillna(0)

        # Threshold status (configurable, using defaults from thresholds.yaml)
        REVENUE_THRESHOLD = 0.05
        CUSTOMER_THRESHOLD = 0.10
        AVG_TX_THRESHOLD = 0.05

        merged["revenue_threshold_status"] = merged["revenue_pct_diff"].apply(
            lambda x: _threshold_label(x, REVENUE_THRESHOLD)
        )
        merged["customer_threshold_status"] = merged["customer_pct_diff"].apply(
            lambda x: _threshold_label(x, CUSTOMER_THRESHOLD)
        )

        merged["_computed_at"] = self.computed_at
        merged["_run_id"] = self.run_id

        logger.info(f"Cross-system comparison: {len(merged)} dates compared")
        return merged

    # ──────────────────────────────────────────────────
    # VOLUME STATISTICS
    # ──────────────────────────────────────────────────

    def compute_volume_stats(self, billing_df: pd.DataFrame) -> pd.DataFrame:
        """Compute daily billing volume for drift detection baseline."""
        df = billing_df.copy()
        if "transaction_date" in df.columns:
            df["transaction_date"] = pd.to_datetime(df["transaction_date"]).dt.date

        daily = df.groupby("transaction_date").agg(
            tx_count=("transaction_id", "count"),
            revenue=("amount", "sum"),
            unique_customers=("customer_id", "nunique"),
        ).reset_index()
        daily.rename(columns={"transaction_date": "date"}, inplace=True)
        daily["_computed_at"] = self.computed_at
        daily["_run_id"] = self.run_id
        return daily

    # ──────────────────────────────────────────────────
    # PERSISTENCE
    # ──────────────────────────────────────────────────

    def save(self, df: pd.DataFrame, table_name: str) -> Path:
        output_dir = self.gold_dir / table_name
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{table_name}_{self.run_id[:8]}.parquet"
        df.to_parquet(output_path, index=False)
        logger.info(f"Saved gold.{table_name} → {output_path} ({len(df)} rows)")
        return output_path

    def read(self, table_name: str) -> pd.DataFrame:
        table_dir = self.gold_dir / table_name
        if not table_dir.exists():
            return pd.DataFrame()
        files = sorted(table_dir.glob("*.parquet"))
        if not files:
            return pd.DataFrame()
        dfs = [pd.read_parquet(f) for f in files]
        return pd.concat(dfs, ignore_index=True).drop_duplicates()


def _threshold_label(pct: float, threshold: float) -> str:
    if pct > threshold * 2:
        return "CRITICAL"
    elif pct > threshold:
        return "HIGH"
    elif pct > threshold * 0.5:
        return "MEDIUM"
    elif pct > 0:
        return "LOW"
    return "OK"
