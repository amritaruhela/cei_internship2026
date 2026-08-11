"""
Cross-System Reconciliation Engine

Implements three reconciliation modes:

1. MISSING RECORDS:  Records in Source A not in Source B (left-anti join on business key)
2. EXTRA RECORDS:    Records in Source B not in Source A (right-anti join on business key)
3. FIELD MISMATCH:   Records in both but field values differ beyond tolerance

The engine is generic — no column logic is hard-coded. Comparison keys
and tolerance thresholds are passed at call time.

Design note: This engine works on pandas DataFrames (Silver layer).
For large-scale use, swap to PySpark joins using the exact same logic.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationResult:
    reconciliation_id: str
    source_a: str
    source_b: str
    join_key: str
    check_type: str  # MISSING_RECORDS | EXTRA_RECORDS | FIELD_MISMATCH | AGGREGATION_MISMATCH
    
    total_a: int
    total_b: int
    
    missing_count: int  # In A but not B
    extra_count: int    # In B but not A
    matched_count: int  # In both
    mismatch_count: int # Matched but values differ
    
    match_rate: float
    is_compliant: bool
    severity: str
    
    field_mismatches: list[dict] = field(default_factory=list)
    missing_samples: list[Any] = field(default_factory=list)
    extra_samples: list[Any] = field(default_factory=list)
    
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    run_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class ReconciliationEngine:
    """
    Compares two DataFrames representing the same business entity across systems.
    Detects missing, extra, and mismatched records without hard-coding columns.
    """

    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or str(uuid.uuid4())[:8]

    def compare(
        self,
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
        source_a: str,
        source_b: str,
        join_key: str,
        compare_fields: Optional[list[str]] = None,
        tolerance: float = 0.01,
        compliance_threshold: float = 0.95,
    ) -> ReconciliationResult:
        """
        Full reconciliation between two DataFrames.
        
        Args:
            df_a: Left DataFrame (e.g., billing).
            df_b: Right DataFrame (e.g., analytics).
            source_a: Name of left source.
            source_b: Name of right source.
            join_key: Column name to join on.
            compare_fields: List of (numeric) columns to compare for value drift.
            tolerance: Max relative difference tolerated before flagging mismatch (0.01 = 1%).
            compliance_threshold: Overall match rate required to be "compliant".
        
        Returns:
            ReconciliationResult with full detail.
        """
        total_a = len(df_a)
        total_b = len(df_b)

        # Ensure join key is present in both
        if join_key not in df_a.columns or join_key not in df_b.columns:
            logger.error(f"Join key '{join_key}' missing from one or both DataFrames")
            return ReconciliationResult(
                reconciliation_id=uuid.uuid4().hex[:12],
                source_a=source_a, source_b=source_b,
                join_key=join_key, check_type="ERROR",
                total_a=total_a, total_b=total_b,
                missing_count=0, extra_count=0,
                matched_count=0, mismatch_count=0,
                match_rate=0.0, is_compliant=False,
                severity="CRITICAL",
                run_id=self.run_id,
            )

        set_a = set(df_a[join_key].dropna().astype(str))
        set_b = set(df_b[join_key].dropna().astype(str))

        missing_keys = set_a - set_b    # In A, not in B
        extra_keys = set_b - set_a      # In B, not in A
        matched_keys = set_a & set_b

        missing_count = len(missing_keys)
        extra_count = len(extra_keys)
        matched_count = len(matched_keys)

        # Field-level mismatch check on matched records
        mismatch_count = 0
        field_mismatches = []

        if compare_fields and matched_keys:
            merged = pd.merge(
                df_a[df_a[join_key].astype(str).isin(matched_keys)],
                df_b[df_b[join_key].astype(str).isin(matched_keys)],
                on=join_key,
                suffixes=("_a", "_b"),
            )
            for col in compare_fields:
                col_a = f"{col}_a"
                col_b = f"{col}_b"
                if col_a in merged.columns and col_b in merged.columns:
                    diff = (
                        (pd.to_numeric(merged[col_a], errors="coerce") -
                         pd.to_numeric(merged[col_b], errors="coerce")).abs()
                        / pd.to_numeric(merged[col_b], errors="coerce").abs().replace(0, float("nan"))
                    ).fillna(0)
                    field_failed = int((diff > tolerance).sum())
                    if field_failed > 0:
                        avg_diff = float(diff.mean())
                        max_diff = float(diff.max())
                        mismatch_count += field_failed
                        field_mismatches.append({
                            "field": col,
                            "failed_records": field_failed,
                            "avg_pct_diff": round(avg_diff * 100, 2),
                            "max_pct_diff": round(max_diff * 100, 2),
                            "tolerance_pct": tolerance * 100,
                        })

        # Overall match rate
        total_union = max(len(set_a | set_b), 1)
        match_rate = matched_count / total_union
        is_compliant = match_rate >= compliance_threshold and mismatch_count == 0

        severity = "OK" if is_compliant else (
            "CRITICAL" if match_rate < 0.80 else
            "HIGH" if match_rate < 0.90 else
            "MEDIUM"
        )

        logger.info(
            f"Reconciliation {source_a} vs {source_b}: "
            f"{matched_count} matched, {missing_count} missing, "
            f"{extra_count} extra, {mismatch_count} field mismatches"
        )

        return ReconciliationResult(
            reconciliation_id=uuid.uuid4().hex[:12],
            source_a=source_a, source_b=source_b,
            join_key=join_key, check_type="FULL_COMPARISON",
            total_a=total_a, total_b=total_b,
            missing_count=missing_count, extra_count=extra_count,
            matched_count=matched_count, mismatch_count=mismatch_count,
            match_rate=round(match_rate, 4), is_compliant=is_compliant,
            severity=severity,
            field_mismatches=field_mismatches,
            missing_samples=sorted(missing_keys)[:10],
            extra_samples=sorted(extra_keys)[:10],
            run_id=self.run_id,
        )

    def compare_aggregations(
        self,
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
        source_a: str,
        source_b: str,
        group_by: str,
        metrics_a: dict[str, str],  # {output_col: source_col}
        metrics_b: dict[str, str],
        tolerance: float = 0.05,
    ) -> list[dict]:
        """
        Aggregate-level comparison (e.g., daily revenue).
        Groups both DataFrames by group_by key and compares aggregated metrics.
        
        Example:
            metrics_a = {"revenue": "amount"}   → billing.groupby("date").agg(revenue=("amount","sum"))
            metrics_b = {"revenue": "total_revenue"} → analytics already aggregated
        
        Returns list of per-group comparison dicts.
        """
        df_a = df_a.copy()
        df_b = df_b.copy()

        if group_by not in df_a.columns or group_by not in df_b.columns:
            logger.warning(f"Group-by column '{group_by}' not in one or both DataFrames")
            return []

        # Aggregate df_a
        agg_ops_a = {out_col: pd.NamedAgg(column=src_col, aggfunc="sum")
                     for out_col, src_col in metrics_a.items() if src_col in df_a.columns}
        if not agg_ops_a:
            grouped_a = df_a.groupby(group_by)[[list(metrics_a.values())[0]]].sum().rename(
                columns={list(metrics_a.values())[0]: list(metrics_a.keys())[0]}
            )
        else:
            grouped_a = df_a.groupby(group_by).agg(**agg_ops_a).reset_index()

        # df_b is already aggregated (analytics daily grain)
        b_cols = {src_col: out_col for out_col, src_col in metrics_b.items()}
        df_b_renamed = df_b[[group_by] + list(metrics_b.values())].rename(columns=b_cols)

        merged = pd.merge(grouped_a, df_b_renamed, on=group_by, how="outer", suffixes=("_a", "_b"))
        
        results = []
        for _, row in merged.iterrows():
            row_result = {group_by: str(row[group_by])}
            for metric_name in metrics_a.keys():
                col_a = f"{metric_name}_a"
                col_b = f"{metric_name}_b"
                if col_a in row and col_b in row:
                    val_a = float(row[col_a]) if pd.notna(row.get(col_a)) else None
                    val_b = float(row[col_b]) if pd.notna(row.get(col_b)) else None
                    if val_a is not None and val_b is not None and val_b != 0:
                        pct_diff = abs(val_a - val_b) / abs(val_b)
                    else:
                        pct_diff = None
                    
                    row_result[f"{metric_name}_a"] = round(val_a, 2) if val_a else None
                    row_result[f"{metric_name}_b"] = round(val_b, 2) if val_b else None
                    row_result[f"{metric_name}_pct_diff"] = round(pct_diff * 100, 2) if pct_diff is not None else None
                    row_result[f"{metric_name}_status"] = (
                        "CRITICAL" if pct_diff and pct_diff > tolerance * 2 else
                        "MISMATCH" if pct_diff and pct_diff > tolerance else
                        "OK" if pct_diff is not None else "NULL_VALUE"
                    )
            results.append(row_result)

        return results
