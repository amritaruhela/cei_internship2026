"""Unit tests for Volume, Distribution, and Schema Drift detectors."""
import numpy as np
import pandas as pd
import pytest
from src.drift.detector import VolumeDriftDetector, DistributionDriftDetector


def test_volume_drift_detection():
    # Build 35 days of daily counts
    np.random.seed(42)
    baseline_counts = np.random.normal(loc=100, scale=5, size=28)
    dropped_counts = np.random.normal(loc=40, scale=5, size=7)  # Significant drop

    df = pd.DataFrame({
        "date": pd.date_range("2024-05-01", periods=35, freq="D"),
        "tx_count": np.concatenate([baseline_counts, dropped_counts]),
    })

    detector = VolumeDriftDetector(z_score_threshold=2.0)
    results = detector.detect(df, count_col="tx_count", source_system="billing")

    assert len(results) == 1
    res = results[0]
    assert bool(res.is_drifted) is True
    assert res.drift_type == "volume"
    assert res.severity in ["CRITICAL", "HIGH"]


def test_distribution_drift_psi():
    np.random.seed(42)
    base_data = pd.Series(np.random.normal(loc=100, scale=15, size=1000))
    shifted_data = pd.Series(np.random.normal(loc=150, scale=20, size=1000))  # Significant shift

    detector = DistributionDriftDetector()
    res = detector.detect_numerical(base_data, shifted_data, "amount", "billing")

    assert res.is_drifted is True
    assert res.drift_score > 0.10  # PSI should exceed threshold
    assert res.drift_type == "distribution"
