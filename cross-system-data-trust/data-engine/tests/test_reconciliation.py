"""Unit tests for Reconciliation Engine and Trust Score Calculator."""
import pandas as pd
import pytest
from src.reconciliation.engine import ReconciliationEngine
from src.scoring.trust_score import TrustScoreCalculator


def test_reconciliation_missing_extra_records():
    df_a = pd.DataFrame({"customer_id": ["C1", "C2", "C3", "C4"], "val": [10, 20, 30, 40]})
    df_b = pd.DataFrame({"customer_id": ["C2", "C3", "C5"], "val": [20, 30, 50]})

    engine = ReconciliationEngine()
    res = engine.compare(df_a, df_b, "billing", "analytics", join_key="customer_id")

    assert res.missing_count == 2  # C1, C4 in A not B
    assert res.extra_count == 1    # C5 in B not A
    assert res.matched_count == 2  # C2, C3 in both
    assert "C1" in res.missing_samples


def test_trust_score_calculation():
    calculator = TrustScoreCalculator()

    quality_metrics = {
        "completeness_score": 0.95,
        "uniqueness_score": 1.0,
        "validity_score": 0.98,
        "referential_integrity_score": 0.90,  # Ghost records penalty
        "null_count": 50,
        "duplicate_count": 0,
        "ghost_customer_count": 100,
    }

    recon_metrics = {
        "avg_revenue_pct_diff": 0.04,  # 4% diff
        "avg_customer_pct_diff": 0.02,
    }

    score = calculator.calculate(
        source_system="billing",
        quality_metrics=quality_metrics,
        reconciliation_metrics=recon_metrics,
    )

    assert 0.0 <= score.overall_score <= 100.0
    assert len(score.explanations) > 0
    assert score.grade in ["A", "B", "C", "D", "F"]
