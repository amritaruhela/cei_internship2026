"""Unit tests for Quality Rule Engine."""
import pandas as pd
import pytest
from src.quality.engine import QualityRuleEngine


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "transaction_id": ["TXN001", "TXN002", "TXN003", "TXN004", "TXN005"],
        "customer_id": ["CRM000001", "CRM000002", "GHOST0001", "CRM000004", "CRM000005"],
        "amount": [100.0, None, 250.0, 400.0, 500.0],
        "status": ["completed", "completed", "failed", "pending", "invalid_status"],
    })


def test_completeness_check(sample_df):
    rules = [{
        "rule_id": "TEST-COMP",
        "source": "billing",
        "column": "amount",
        "rule_type": "completeness",
        "threshold": 0.90,
        "severity": "HIGH",
        "enabled": True,
    }]
    engine = QualityRuleEngine(rules=rules)
    results = engine.evaluate(sample_df, "billing")

    assert len(results) == 1
    res = results[0]
    assert res.failed_records == 1  # 1 null
    assert res.pass_rate == 0.8  # 4/5 = 0.8
    assert res.passed is False  # 0.8 < 0.9 threshold


def test_uniqueness_check(sample_df):
    rules = [{
        "rule_id": "TEST-UNIQ",
        "source": "billing",
        "column": "transaction_id",
        "rule_type": "uniqueness",
        "threshold": 0.99,
        "severity": "CRITICAL",
        "enabled": True,
    }]
    engine = QualityRuleEngine(rules=rules)
    results = engine.evaluate(sample_df, "billing")

    assert len(results) == 1
    assert results[0].passed is True
    assert results[0].failed_records == 0


def test_validity_check(sample_df):
    rules = [{
        "rule_id": "TEST-VAL",
        "source": "billing",
        "column": "status",
        "rule_type": "validity",
        "allowed_values": ["completed", "pending", "failed", "refunded"],
        "threshold": 0.90,
        "severity": "MEDIUM",
        "enabled": True,
    }]
    engine = QualityRuleEngine(rules=rules)
    results = engine.evaluate(sample_df, "billing")

    assert len(results) == 1
    res = results[0]
    assert res.failed_records == 1  # "invalid_status" is not allowed
    assert res.passed is False  # 0.8 < 0.9 threshold
