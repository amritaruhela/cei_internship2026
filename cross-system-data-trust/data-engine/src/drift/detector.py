"""
Drift Detection Engine

Three drift categories implemented:
1. Volume Drift   - Row count change vs rolling baseline, z-score flagging
2. Distribution Drift - PSI (numerical), chi-square (categorical)
3. Schema Drift   - JSON schema snapshot diff

Methodology documented for each technique.
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────

@dataclass
class DriftResult:
    drift_type: str          # "volume", "distribution", "schema"
    source_system: str
    column: Optional[str]    # None for volume/schema drift
    is_drifted: bool
    drift_score: float       # 0-1 (higher = more drift)
    severity: str            # CRITICAL / HIGH / MEDIUM / LOW / INFO
    baseline_value: Any
    current_value: Any
    threshold: float
    description: str
    details: dict = field(default_factory=dict)
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["baseline_value"] = str(d["baseline_value"])
        d["current_value"] = str(d["current_value"])
        return d


# ──────────────────────────────────────────────────────────
# VOLUME DRIFT
# ──────────────────────────────────────────────────────────

class VolumeDriftDetector:
    """
    Detects volume drift using:
    - Rolling 30-day baseline mean and std
    - Z-score to flag anomalies
    - Percentage change as secondary metric
    
    Methodology: Z-score = (current - mean) / std
    If |z-score| > threshold (default 2.5), volume drift detected.
    Also checks % change against configured thresholds.
    """

    def __init__(
        self,
        baseline_window_days: int = 30,
        z_score_threshold: float = 2.5,
        pct_thresholds: Optional[dict] = None,
    ):
        self.baseline_window_days = baseline_window_days
        self.z_score_threshold = z_score_threshold
        self.pct_thresholds = pct_thresholds or {
            "CRITICAL": 0.40,
            "HIGH": 0.20,
            "MEDIUM": 0.10,
            "LOW": 0.05,
        }

    def detect(
        self,
        daily_df: pd.DataFrame,
        date_col: str = "date",
        count_col: str = "tx_count",
        source_system: str = "billing",
    ) -> list[DriftResult]:
        """
        Detect volume drift from a daily time-series DataFrame.
        Expects columns: date, count_col (e.g., tx_count).
        """
        results = []
        if daily_df.empty or count_col not in daily_df.columns:
            logger.warning(f"No data for volume drift detection: {source_system}")
            return results

        df = daily_df.copy().sort_values(date_col)
        df[date_col] = pd.to_datetime(df[date_col])

        if len(df) < 7:
            logger.warning("Insufficient history for volume drift (need >=7 days)")
            return results

        # Split into baseline (all except last 7 days) and current (last 7 days)
        split_date = df[date_col].max() - pd.Timedelta(days=7)
        baseline_df = df[df[date_col] <= split_date].tail(self.baseline_window_days)
        current_df = df[df[date_col] > split_date]

        if len(baseline_df) < 7:
            logger.warning("Insufficient baseline for volume drift detection")
            return results

        baseline_mean = baseline_df[count_col].mean()
        baseline_std = baseline_df[count_col].std()
        current_mean = current_df[count_col].mean() if not current_df.empty else 0

        # Z-score
        z_score = abs(current_mean - baseline_mean) / max(baseline_std, 1e-6)
        pct_change = abs(current_mean - baseline_mean) / max(baseline_mean, 1e-6)

        is_drifted = z_score > self.z_score_threshold or pct_change > self.pct_thresholds["LOW"]
        severity = self._severity(pct_change)
        drift_score = min(pct_change, 1.0)

        results.append(DriftResult(
            drift_type="volume",
            source_system=source_system,
            column=count_col,
            is_drifted=is_drifted,
            drift_score=round(drift_score, 4),
            severity=severity,
            baseline_value=round(baseline_mean, 2),
            current_value=round(current_mean, 2),
            threshold=self.pct_thresholds["MEDIUM"],
            description=(
                f"Volume drift: {count_col} changed from "
                f"{baseline_mean:.1f} (baseline) to {current_mean:.1f} "
                f"({pct_change*100:.1f}% change, z={z_score:.2f})"
            ),
            details={
                "z_score": round(z_score, 4),
                "pct_change": round(pct_change, 4),
                "baseline_mean": round(baseline_mean, 2),
                "baseline_std": round(baseline_std, 2),
                "baseline_window_days": self.baseline_window_days,
                "current_window_days": len(current_df),
            },
        ))

        return results

    def _severity(self, pct_change: float) -> str:
        if pct_change >= self.pct_thresholds["CRITICAL"]:
            return "CRITICAL"
        elif pct_change >= self.pct_thresholds["HIGH"]:
            return "HIGH"
        elif pct_change >= self.pct_thresholds["MEDIUM"]:
            return "MEDIUM"
        elif pct_change >= self.pct_thresholds["LOW"]:
            return "LOW"
        return "INFO"


# ──────────────────────────────────────────────────────────
# DISTRIBUTION DRIFT
# ──────────────────────────────────────────────────────────

class DistributionDriftDetector:
    """
    Detects distribution drift using:
    
    For numerical columns:
      - PSI (Population Stability Index): measures how much distribution
        has shifted from baseline. PSI < 0.1 = stable, 0.1-0.2 = minor,
        > 0.2 = significant drift.
      - KS test: non-parametric test for distribution equality.
        p-value < 0.05 = distributions differ significantly.
    
    For categorical columns:
      - Chi-square test of proportions.
      - Category frequency comparison.
    
    Baseline: all data before a cutoff (typically 30 days ago).
    Current: data after the cutoff (typically last 7-30 days).
    
    We use PSI as the primary metric because it provides a continuous
    drift score and is widely used in credit/financial ML monitoring.
    KS test supplements as a statistical significance test.
    """

    def __init__(
        self,
        psi_bins: int = 10,
        psi_thresholds: Optional[dict] = None,
        ks_pvalue_threshold: float = 0.05,
        min_sample_size: int = 30,
    ):
        self.psi_bins = psi_bins
        self.psi_thresholds = psi_thresholds or {
            "CRITICAL": 0.25,
            "HIGH": 0.20,
            "MEDIUM": 0.10,
            "LOW": 0.05,
        }
        self.ks_pvalue_threshold = ks_pvalue_threshold
        self.min_sample_size = min_sample_size

    def detect_numerical(
        self,
        baseline: pd.Series,
        current: pd.Series,
        column: str,
        source_system: str,
    ) -> DriftResult:
        """PSI + KS test for numerical columns."""
        baseline_clean = baseline.dropna()
        current_clean = current.dropna()

        if len(baseline_clean) < self.min_sample_size or len(current_clean) < self.min_sample_size:
            return DriftResult(
                drift_type="distribution",
                source_system=source_system,
                column=column,
                is_drifted=False,
                drift_score=0.0,
                severity="INFO",
                baseline_value=f"n={len(baseline_clean)}",
                current_value=f"n={len(current_clean)}",
                threshold=self.psi_thresholds["MEDIUM"],
                description=f"Insufficient sample size for drift detection (need >={self.min_sample_size})",
            )

        # PSI calculation
        psi = self._compute_psi(baseline_clean, current_clean)

        # KS test
        ks_stat, ks_pvalue = stats.ks_2samp(baseline_clean.values, current_clean.values)
        ks_drifted = ks_pvalue < self.ks_pvalue_threshold

        # Primary determination: PSI
        is_drifted = psi > self.psi_thresholds["LOW"] or ks_drifted
        severity = self._psi_severity(psi)

        return DriftResult(
            drift_type="distribution",
            source_system=source_system,
            column=column,
            is_drifted=is_drifted,
            drift_score=round(min(psi, 1.0), 4),
            severity=severity,
            baseline_value={
                "mean": round(float(baseline_clean.mean()), 2),
                "std": round(float(baseline_clean.std()), 2),
                "p50": round(float(baseline_clean.quantile(0.5)), 2),
                "n": len(baseline_clean),
            },
            current_value={
                "mean": round(float(current_clean.mean()), 2),
                "std": round(float(current_clean.std()), 2),
                "p50": round(float(current_clean.quantile(0.5)), 2),
                "n": len(current_clean),
            },
            threshold=self.psi_thresholds["MEDIUM"],
            description=(
                f"Distribution drift in {column}: "
                f"PSI={psi:.4f}, KS p-value={ks_pvalue:.4f}"
            ),
            details={
                "psi": round(psi, 6),
                "ks_statistic": round(float(ks_stat), 6),
                "ks_pvalue": round(float(ks_pvalue), 6),
                "ks_drifted": ks_drifted,
                "psi_bins": self.psi_bins,
                "technique": "PSI + KS-test",
            },
        )

    def detect_categorical(
        self,
        baseline: pd.Series,
        current: pd.Series,
        column: str,
        source_system: str,
    ) -> DriftResult:
        """Chi-square test + frequency comparison for categorical columns."""
        baseline_clean = baseline.dropna()
        current_clean = current.dropna()

        if len(baseline_clean) < self.min_sample_size or len(current_clean) < self.min_sample_size:
            return DriftResult(
                drift_type="distribution",
                source_system=source_system,
                column=column,
                is_drifted=False,
                drift_score=0.0,
                severity="INFO",
                baseline_value={},
                current_value={},
                threshold=0.05,
                description="Insufficient sample size",
            )

        # Frequency distributions
        base_freq = baseline_clean.value_counts(normalize=True).to_dict()
        curr_freq = current_clean.value_counts(normalize=True).to_dict()

        # Chi-square test
        all_cats = set(base_freq) | set(curr_freq)
        base_counts = [baseline_clean.value_counts().get(c, 0) for c in all_cats]
        curr_counts = [current_clean.value_counts().get(c, 0) for c in all_cats]

        try:
            chi2, p_value = stats.chisquare(
                f_obs=curr_counts,
                f_exp=[
                    (b / sum(base_counts)) * sum(curr_counts)
                    for b in base_counts
                ],
            )
            chi2_drifted = p_value < 0.05
        except Exception:
            chi2, p_value, chi2_drifted = 0.0, 1.0, False

        # Max frequency delta as drift score proxy
        drift_score = max(
            abs(curr_freq.get(c, 0) - base_freq.get(c, 0)) for c in all_cats
        ) if all_cats else 0.0

        is_drifted = chi2_drifted or drift_score > 0.10
        severity = "HIGH" if drift_score > 0.20 else ("MEDIUM" if drift_score > 0.10 else "LOW")

        return DriftResult(
            drift_type="distribution",
            source_system=source_system,
            column=column,
            is_drifted=is_drifted,
            drift_score=round(drift_score, 4),
            severity=severity if is_drifted else "INFO",
            baseline_value=base_freq,
            current_value=curr_freq,
            threshold=0.10,
            description=(
                f"Categorical drift in {column}: "
                f"chi2={chi2:.2f}, p={p_value:.4f}, max_delta={drift_score:.3f}"
            ),
            details={
                "chi2_statistic": round(float(chi2), 4),
                "chi2_pvalue": round(float(p_value), 6),
                "chi2_drifted": chi2_drifted,
                "max_freq_delta": round(drift_score, 4),
                "technique": "chi-square + frequency comparison",
            },
        )

    def detect_all(
        self,
        baseline_df: pd.DataFrame,
        current_df: pd.DataFrame,
        source_system: str,
        numerical_cols: Optional[list[str]] = None,
        categorical_cols: Optional[list[str]] = None,
    ) -> list[DriftResult]:
        """Run distribution drift detection on all specified columns."""
        results = []

        for col in (numerical_cols or []):
            if col in baseline_df.columns and col in current_df.columns:
                result = self.detect_numerical(
                    baseline_df[col], current_df[col], col, source_system
                )
                results.append(result)

        for col in (categorical_cols or []):
            if col in baseline_df.columns and col in current_df.columns:
                result = self.detect_categorical(
                    baseline_df[col], current_df[col], col, source_system
                )
                results.append(result)

        return results

    def _compute_psi(self, baseline: pd.Series, current: pd.Series) -> float:
        """
        Compute Population Stability Index (PSI).
        PSI = Σ (P_current - P_baseline) * ln(P_current / P_baseline)
        """
        min_val = min(baseline.min(), current.min())
        max_val = max(baseline.max(), current.max())

        if max_val <= min_val:
            return 0.0

        bins = np.linspace(min_val, max_val + 1e-6, self.psi_bins + 1)
        base_hist, _ = np.histogram(baseline, bins=bins)
        curr_hist, _ = np.histogram(current, bins=bins)

        # Add epsilon to avoid log(0)
        eps = 1e-6
        base_pct = (base_hist / len(baseline)) + eps
        curr_pct = (curr_hist / len(current)) + eps

        psi = float(np.sum((curr_pct - base_pct) * np.log(curr_pct / base_pct)))
        return max(0.0, psi)

    def _psi_severity(self, psi: float) -> str:
        if psi >= self.psi_thresholds["CRITICAL"]:
            return "CRITICAL"
        elif psi >= self.psi_thresholds["HIGH"]:
            return "HIGH"
        elif psi >= self.psi_thresholds["MEDIUM"]:
            return "MEDIUM"
        elif psi >= self.psi_thresholds["LOW"]:
            return "LOW"
        return "INFO"


# ──────────────────────────────────────────────────────────
# SCHEMA DRIFT
# ──────────────────────────────────────────────────────────

class SchemaDriftDetector:
    """
    Detects schema drift by comparing JSON schema snapshots.
    
    Tracks:
    - New columns added
    - Columns removed
    - Data type changes
    - Nullable changes
    """

    def __init__(self, snapshots_dir: Path):
        self.snapshots_dir = Path(snapshots_dir)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def capture_snapshot(
        self, df: pd.DataFrame, source_system: str, run_id: str
    ) -> dict:
        """Capture current schema and save as JSON snapshot."""
        schema = {
            col: {
                "dtype": str(df[col].dtype),
                "nullable": bool(df[col].isna().any()),
                "sample_values": [str(v) for v in df[col].dropna().head(3).tolist()],
            }
            for col in df.columns
            if not col.startswith("_")  # Skip metadata columns
        }
        snapshot = {
            "source_system": source_system,
            "run_id": run_id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "columns": list(schema.keys()),
            "schema": schema,
            "column_count": len(schema),
        }
        path = self.snapshots_dir / f"{source_system}_{run_id[:8]}.json"
        with open(path, "w") as f:
            json.dump(snapshot, f, indent=2)
        logger.info(f"Schema snapshot saved: {path}")
        return snapshot

    def load_previous_snapshot(self, source_system: str) -> Optional[dict]:
        """Load the most recent previous schema snapshot."""
        files = sorted(self.snapshots_dir.glob(f"{source_system}_*.json"))
        if len(files) < 2:
            return None
        # Second-to-last is "previous"
        with open(files[-2]) as f:
            return json.load(f)

    def detect(
        self, current_df: pd.DataFrame, source_system: str, run_id: str
    ) -> list[DriftResult]:
        """Detect schema drift vs previous snapshot."""
        results = []
        current_snapshot = self.capture_snapshot(current_df, source_system, run_id)
        previous_snapshot = self.load_previous_snapshot(source_system)

        if previous_snapshot is None:
            logger.info(f"No previous snapshot for {source_system} — first run")
            return results

        prev_schema = previous_snapshot.get("schema", {})
        curr_schema = current_snapshot.get("schema", {})
        prev_cols = set(prev_schema.keys())
        curr_cols = set(curr_schema.keys())

        # New columns
        for col in curr_cols - prev_cols:
            results.append(DriftResult(
                drift_type="schema",
                source_system=source_system,
                column=col,
                is_drifted=True,
                drift_score=1.0,
                severity="HIGH",
                baseline_value="column_absent",
                current_value=curr_schema[col]["dtype"],
                threshold=0.0,
                description=f"New column added to {source_system}: '{col}' ({curr_schema[col]['dtype']})",
                details={"change_type": "new_column"},
            ))

        # Removed columns
        for col in prev_cols - curr_cols:
            results.append(DriftResult(
                drift_type="schema",
                source_system=source_system,
                column=col,
                is_drifted=True,
                drift_score=1.0,
                severity="CRITICAL",
                baseline_value=prev_schema[col]["dtype"],
                current_value="column_removed",
                threshold=0.0,
                description=f"Column removed from {source_system}: '{col}'",
                details={"change_type": "removed_column"},
            ))

        # Type changes
        for col in prev_cols & curr_cols:
            prev_type = prev_schema[col]["dtype"]
            curr_type = curr_schema[col]["dtype"]
            if prev_type != curr_type:
                results.append(DriftResult(
                    drift_type="schema",
                    source_system=source_system,
                    column=col,
                    is_drifted=True,
                    drift_score=0.8,
                    severity="HIGH",
                    baseline_value=prev_type,
                    current_value=curr_type,
                    threshold=0.0,
                    description=(
                        f"Type change in {source_system}.{col}: "
                        f"{prev_type} → {curr_type}"
                    ),
                    details={"change_type": "type_change"},
                ))

        if not results:
            logger.info(f"No schema drift detected for {source_system}")
        else:
            logger.warning(f"Schema drift detected: {len(results)} change(s) in {source_system}")

        return results
