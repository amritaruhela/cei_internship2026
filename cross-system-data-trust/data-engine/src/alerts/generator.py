"""
Alert Generator and Severity Engine

Generates structured alerts from monitoring results.
Alert lifecycle: OPEN → ACKNOWLEDGED → RESOLVED / IGNORED

Alert structure matches the API schema for direct persistence.
Severity is configurable through thresholds.yaml.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}


@dataclass
class Alert:
    alert_id: str
    timestamp: str
    source: str
    metric: str
    issue_type: str
    severity: str
    observed_value: Any
    expected_value: Any
    threshold: float
    description: str
    status: str = "OPEN"
    rule_id: str = ""
    run_id: str = ""
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    resolution_note: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["observed_value"] = str(d["observed_value"])
        d["expected_value"] = str(d["expected_value"])
        return d


class AlertGenerator:
    """
    Generates alerts from quality metrics, drift results, and reconciliation data.
    Does NOT hard-code thresholds — reads from config.
    """

    def __init__(self, run_id: str = ""):
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.alerts: list[Alert] = []

    def _new_alert(
        self,
        source: str,
        metric: str,
        issue_type: str,
        severity: str,
        observed_value: Any,
        expected_value: Any,
        threshold: float,
        description: str,
        rule_id: str = "",
    ) -> Alert:
        alert = Alert(
            alert_id=f"ALERT-{uuid.uuid4().hex[:8].upper()}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source,
            metric=metric,
            issue_type=issue_type,
            severity=severity,
            observed_value=observed_value,
            expected_value=expected_value,
            threshold=threshold,
            description=description,
            rule_id=rule_id,
            run_id=self.run_id,
        )
        self.alerts.append(alert)
        logger.info(f"[{severity}] Alert generated: {alert.alert_id} — {description[:80]}")
        return alert

    # ──────────────────────────────────────────────────
    # QUALITY ALERTS
    # ──────────────────────────────────────────────────

    def from_quality_metrics(
        self,
        metrics: dict[str, Any],
        thresholds: Optional[dict] = None,
    ) -> list[Alert]:
        """Generate alerts from quality metrics dict."""
        thresholds = thresholds or {}
        source = metrics.get("source_system", "unknown")
        new_alerts = []

        completeness = metrics.get("completeness_score", 1.0)
        comp_thresholds = thresholds.get("completeness", {})
        if completeness < comp_thresholds.get("critical_rate", 0.80):
            a = self._new_alert(
                source=source, metric="completeness",
                issue_type="COMPLETENESS_VIOLATION", severity="CRITICAL",
                observed_value=f"{completeness*100:.1f}%",
                expected_value=f">{comp_thresholds.get('critical_rate', 0.80)*100:.0f}%",
                threshold=comp_thresholds.get("critical_rate", 0.80),
                description=f"{source} completeness critical: {completeness*100:.1f}% "
                            f"(threshold: {comp_thresholds.get('critical_rate', 0.80)*100:.0f}%)",
                rule_id="DQ-COMP-001",
            )
            new_alerts.append(a)
        elif completeness < comp_thresholds.get("high_rate", 0.90):
            a = self._new_alert(
                source=source, metric="completeness",
                issue_type="COMPLETENESS_VIOLATION", severity="HIGH",
                observed_value=f"{completeness*100:.1f}%",
                expected_value=f">{comp_thresholds.get('high_rate', 0.90)*100:.0f}%",
                threshold=comp_thresholds.get("high_rate", 0.90),
                description=f"{source} completeness degraded: {completeness*100:.1f}%",
                rule_id="DQ-COMP-001",
            )
            new_alerts.append(a)

        uniqueness = metrics.get("uniqueness_score", 1.0)
        uniq_thresholds = thresholds.get("uniqueness", {})
        if uniqueness < uniq_thresholds.get("critical_rate", 0.95):
            dup_count = metrics.get("duplicate_count", "unknown")
            a = self._new_alert(
                source=source, metric="uniqueness",
                issue_type="DUPLICATE_RECORDS", severity="CRITICAL",
                observed_value=f"{uniqueness*100:.1f}% ({dup_count} duplicates)",
                expected_value="100%",
                threshold=1.0,
                description=f"{source} has {dup_count} duplicate records (uniqueness: {uniqueness*100:.1f}%)",
                rule_id="DQ-UNIQ-001",
            )
            new_alerts.append(a)

        # Ghost customers
        ghost_count = metrics.get("ghost_customer_count", 0)
        if ghost_count > 0:
            ref_score = metrics.get("referential_integrity_score", 1.0)
            a = self._new_alert(
                source=source, metric="referential_integrity",
                issue_type="REFERENTIAL_INTEGRITY_VIOLATION", severity="HIGH",
                observed_value=f"{ghost_count} ghost records",
                expected_value="0 ghost records",
                threshold=0.995,
                description=(
                    f"{source} has {ghost_count} billing transactions for customers "
                    f"not found in CRM (GHOST IDs). Referential integrity: {ref_score*100:.1f}%"
                ),
                rule_id="DQ-B003",
            )
            new_alerts.append(a)

        return new_alerts

    # ──────────────────────────────────────────────────
    # DRIFT ALERTS
    # ──────────────────────────────────────────────────

    def from_drift_results(self, drift_results: list) -> list[Alert]:
        """Generate alerts from DriftResult objects."""
        new_alerts = []
        for drift in drift_results:
            if not getattr(drift, "is_drifted", False):
                continue

            issue_type_map = {
                "volume": "VOLUME_DRIFT",
                "distribution": "DISTRIBUTION_DRIFT",
                "schema": "SCHEMA_DRIFT",
            }

            a = self._new_alert(
                source=drift.source_system,
                metric=drift.column or drift.drift_type,
                issue_type=issue_type_map.get(drift.drift_type, "DRIFT"),
                severity=drift.severity,
                observed_value=drift.current_value,
                expected_value=drift.baseline_value,
                threshold=drift.threshold,
                description=drift.description,
                rule_id=f"DRIFT-{drift.drift_type.upper()[:3]}-001",
            )
            new_alerts.append(a)

        return new_alerts

    # ──────────────────────────────────────────────────
    # RECONCILIATION ALERTS
    # ──────────────────────────────────────────────────

    def from_reconciliation(
        self,
        comparison_df,  # pd.DataFrame
        revenue_threshold: float = 0.05,
        customer_threshold: float = 0.10,
    ) -> list[Alert]:
        """Generate alerts from cross-system comparison DataFrame."""
        import pandas as pd
        new_alerts = []

        if comparison_df is None or len(comparison_df) == 0:
            return new_alerts

        # Compute summary stats
        rev_diff = comparison_df["revenue_pct_diff"].dropna()
        cust_diff = comparison_df["customer_pct_diff"].dropna()

        if len(rev_diff) > 0:
            avg_rev_diff = rev_diff.mean()
            max_rev_diff = rev_diff.max()

            if avg_rev_diff > revenue_threshold:
                severity = (
                    "CRITICAL" if avg_rev_diff > revenue_threshold * 2 else "HIGH"
                )
                a = self._new_alert(
                    source="billing_vs_analytics",
                    metric="revenue_reconciliation",
                    issue_type="AGGREGATION_MISMATCH",
                    severity=severity,
                    observed_value=f"{avg_rev_diff*100:.2f}% avg diff (max {max_rev_diff*100:.2f}%)",
                    expected_value=f"<{revenue_threshold*100:.0f}%",
                    threshold=revenue_threshold,
                    description=(
                        f"Revenue mismatch: Billing vs Analytics diverges by "
                        f"{avg_rev_diff*100:.2f}% on average (threshold: {revenue_threshold*100:.0f}%). "
                        f"Max single-day difference: {max_rev_diff*100:.2f}%"
                    ),
                    rule_id="DQ-R001",
                )
                new_alerts.append(a)

        if len(cust_diff) > 0:
            avg_cust_diff = cust_diff.mean()
            if avg_cust_diff > customer_threshold:
                a = self._new_alert(
                    source="billing_vs_analytics",
                    metric="customer_count_reconciliation",
                    issue_type="AGGREGATION_MISMATCH",
                    severity="HIGH",
                    observed_value=f"{avg_cust_diff*100:.2f}% avg diff",
                    expected_value=f"<{customer_threshold*100:.0f}%",
                    threshold=customer_threshold,
                    description=(
                        f"Customer count mismatch: Billing vs Analytics diverges by "
                        f"{avg_cust_diff*100:.2f}% on average (threshold: {customer_threshold*100:.0f}%)"
                    ),
                    rule_id="DQ-R002",
                )
                new_alerts.append(a)

        return new_alerts

    # ──────────────────────────────────────────────────
    # FRESHNESS ALERTS
    # ──────────────────────────────────────────────────

    def from_freshness(
        self,
        source: str,
        last_updated_at: datetime,
        expected_frequency_hours: float = 24.0,
        warning_delay_hours: float = 30.0,
        critical_delay_hours: float = 48.0,
    ) -> list[Alert]:
        now = datetime.now(timezone.utc)
        delay_hours = (now - last_updated_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        new_alerts = []

        if delay_hours >= critical_delay_hours:
            a = self._new_alert(
                source=source, metric="freshness",
                issue_type="FRESHNESS_VIOLATION", severity="CRITICAL",
                observed_value=f"{delay_hours:.1f}h since last update",
                expected_value=f"every {expected_frequency_hours:.0f}h",
                threshold=critical_delay_hours,
                description=(
                    f"{source} data is STALE: last update was "
                    f"{delay_hours:.1f} hours ago (critical threshold: {critical_delay_hours}h)"
                ),
                rule_id=f"DQ-FRESH-{source.upper()[:3]}",
            )
            new_alerts.append(a)
        elif delay_hours >= warning_delay_hours:
            a = self._new_alert(
                source=source, metric="freshness",
                issue_type="FRESHNESS_WARNING", severity="MEDIUM",
                observed_value=f"{delay_hours:.1f}h since last update",
                expected_value=f"every {expected_frequency_hours:.0f}h",
                threshold=warning_delay_hours,
                description=f"{source} data is delayed: {delay_hours:.1f}h (warning threshold: {warning_delay_hours}h)",
                rule_id=f"DQ-FRESH-{source.upper()[:3]}",
            )
            new_alerts.append(a)

        return new_alerts

    def get_all_alerts(self) -> list[dict]:
        """Return all generated alerts as serializable dicts."""
        return [a.to_dict() for a in self.alerts]

    def get_summary(self) -> dict:
        return {
            "total": len(self.alerts),
            "by_severity": {
                sev: sum(1 for a in self.alerts if a.severity == sev)
                for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
            },
            "by_type": {},
        }
