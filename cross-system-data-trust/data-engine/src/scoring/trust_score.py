"""
Trust Score Calculator

Computes a transparent, explainable Data Trust Score (0–100) for each source system.

Formula:
    trust_score = (
        completeness_score   * 0.20 +
        consistency_score    * 0.25 +
        accuracy_score       * 0.20 +
        freshness_score      * 0.15 +
        uniqueness_score     * 0.10 +
        drift_stability_score * 0.10
    ) * 100

All weights are configurable via thresholds.yaml.

Explainability:
    The calculator returns not just the final score, but all component
    scores and a list of human-readable explanations for score reductions.
    Example:
        "Score reduced by 8 points: Billing revenue differs from Analytics
         by 4.2% (threshold: 5%)"
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


DEFAULT_WEIGHTS = {
    "completeness": 0.20,
    "consistency": 0.25,
    "accuracy": 0.20,
    "freshness": 0.15,
    "uniqueness": 0.10,
    "drift_stability": 0.10,
}


@dataclass
class TrustScoreBreakdown:
    source_system: str
    overall_score: float          # 0-100
    completeness_score: float     # 0-1
    consistency_score: float      # 0-1
    accuracy_score: float         # 0-1
    freshness_score: float        # 0-1
    uniqueness_score: float       # 0-1
    drift_stability_score: float  # 0-1
    weights: dict = field(default_factory=dict)
    explanations: list[str] = field(default_factory=list)
    computed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    run_id: str = ""

    @property
    def grade(self) -> str:
        if self.overall_score >= 90:
            return "A"
        elif self.overall_score >= 80:
            return "B"
        elif self.overall_score >= 70:
            return "C"
        elif self.overall_score >= 60:
            return "D"
        return "F"

    @property
    def health_status(self) -> str:
        if self.overall_score >= 85:
            return "HEALTHY"
        elif self.overall_score >= 70:
            return "WARNING"
        elif self.overall_score >= 50:
            return "DEGRADED"
        return "CRITICAL"

    def to_dict(self) -> dict:
        return {
            "source_system": self.source_system,
            "overall_score": round(self.overall_score, 2),
            "grade": self.grade,
            "health_status": self.health_status,
            "components": {
                "completeness": round(self.completeness_score * 100, 2),
                "consistency": round(self.consistency_score * 100, 2),
                "accuracy": round(self.accuracy_score * 100, 2),
                "freshness": round(self.freshness_score * 100, 2),
                "uniqueness": round(self.uniqueness_score * 100, 2),
                "drift_stability": round(self.drift_stability_score * 100, 2),
            },
            "weights": self.weights,
            "explanations": self.explanations,
            "computed_at": self.computed_at,
            "run_id": self.run_id,
        }


class TrustScoreCalculator:
    """
    Calculates explainable trust scores per source system.
    
    All score reductions are logged with human-readable explanations
    so the UI can display "why" a score was lowered.
    """

    def __init__(self, weights: Optional[dict] = None):
        self.weights = weights or DEFAULT_WEIGHTS
        # Normalize weights to sum to 1
        total = sum(self.weights.values())
        self.weights = {k: v / total for k, v in self.weights.items()}

    def calculate(
        self,
        source_system: str,
        quality_metrics: dict[str, Any],
        freshness_status: str = "FRESH",
        freshness_delay_hours: float = 0.0,
        drift_results: Optional[list] = None,
        reconciliation_metrics: Optional[dict] = None,
        run_id: str = "",
    ) -> TrustScoreBreakdown:
        """
        Calculate trust score with full explainability.
        
        Args:
            source_system: Name of the source system
            quality_metrics: Dict with completeness_score, uniqueness_score, etc.
            freshness_status: FRESH / WARNING / STALE / CRITICAL
            freshness_delay_hours: Actual delay in hours
            drift_results: List of DriftResult objects
            reconciliation_metrics: Dict with mismatch percentages
            run_id: Pipeline run ID for traceability
        
        Returns:
            TrustScoreBreakdown with score and explanations
        """
        explanations = []

        # ── COMPLETENESS (0–1)
        completeness = float(quality_metrics.get("completeness_score", 1.0))
        if completeness < 1.0:
            loss_pts = round((1 - completeness) * self.weights["completeness"] * 100, 1)
            null_count = quality_metrics.get("null_count", "unknown")
            explanations.append(
                f"Completeness: {completeness*100:.1f}% "
                f"(-{loss_pts} pts, {null_count} null values)"
            )

        # ── UNIQUENESS (0–1)
        uniqueness = float(quality_metrics.get("uniqueness_score", 1.0))
        if uniqueness < 1.0:
            loss_pts = round((1 - uniqueness) * self.weights["uniqueness"] * 100, 1)
            dup_count = quality_metrics.get("duplicate_count", "unknown")
            explanations.append(
                f"Uniqueness: {uniqueness*100:.1f}% "
                f"(-{loss_pts} pts, {dup_count} duplicates)"
            )

        # ── CONSISTENCY (0–1) — validity + referential integrity
        validity = float(quality_metrics.get("validity_score", 1.0))
        ref_integrity = float(quality_metrics.get("referential_integrity_score", 1.0))
        consistency = (validity + ref_integrity) / 2.0

        if consistency < 1.0:
            loss_pts = round((1 - consistency) * self.weights["consistency"] * 100, 1)
            ghost_count = quality_metrics.get("ghost_customer_count", 0)
            msg = f"Consistency: {consistency*100:.1f}% (-{loss_pts} pts"
            if ghost_count > 0:
                msg += f", {ghost_count} ghost customer records (referential integrity violation)"
            msg += ")"
            explanations.append(msg)

        # ── ACCURACY / RECONCILIATION (0–1)
        accuracy = 1.0
        if reconciliation_metrics:
            rev_diff = reconciliation_metrics.get("avg_revenue_pct_diff", 0.0)
            cust_diff = reconciliation_metrics.get("avg_customer_pct_diff", 0.0)
            accuracy = max(0.0, 1.0 - (rev_diff * 0.6 + cust_diff * 0.4))

            if rev_diff > 0.001:
                loss_pts = round((1 - accuracy) * self.weights["accuracy"] * 100, 1)
                explanations.append(
                    f"Accuracy/Reconciliation: Revenue differs by {rev_diff*100:.1f}% "
                    f"vs Analytics (-{loss_pts} pts)"
                )
            if cust_diff > 0.01:
                explanations.append(
                    f"Customer count differs by {cust_diff*100:.1f}% "
                    f"between Billing and Analytics"
                )

        # ── FRESHNESS (0–1)
        freshness_map = {"FRESH": 1.0, "WARNING": 0.75, "STALE": 0.50, "CRITICAL": 0.25}
        freshness = freshness_map.get(freshness_status, 0.5)

        if freshness < 1.0:
            loss_pts = round((1 - freshness) * self.weights["freshness"] * 100, 1)
            explanations.append(
                f"Freshness: {freshness_status} "
                f"(last update {freshness_delay_hours:.1f}h ago, -{ loss_pts} pts)"
            )

        # ── DRIFT STABILITY (0–1)
        drift_stability = 1.0
        if drift_results:
            drifted = [d for d in drift_results if getattr(d, "is_drifted", False)]
            critical_drift = [d for d in drifted if getattr(d, "severity", "") in ("CRITICAL", "HIGH")]
            medium_drift = [d for d in drifted if getattr(d, "severity", "") == "MEDIUM"]
            
            penalty = len(critical_drift) * 0.15 + len(medium_drift) * 0.07
            drift_stability = max(0.0, 1.0 - penalty)

            if drifted:
                loss_pts = round((1 - drift_stability) * self.weights["drift_stability"] * 100, 1)
                drift_types = set(getattr(d, "drift_type", "unknown") for d in drifted)
                explanations.append(
                    f"Drift Stability: {len(drifted)} drift issue(s) detected "
                    f"({', '.join(drift_types)}) (-{loss_pts} pts)"
                )

        # ── FINAL SCORE
        overall = (
            completeness    * self.weights["completeness"] +
            consistency     * self.weights["consistency"] +
            accuracy        * self.weights["accuracy"] +
            freshness       * self.weights["freshness"] +
            uniqueness      * self.weights["uniqueness"] +
            drift_stability * self.weights["drift_stability"]
        ) * 100

        overall = round(max(0.0, min(100.0, overall)), 2)

        if not explanations:
            explanations.append("All checks passed — no score reductions")

        logger.info(
            f"Trust score for {source_system}: {overall:.1f}/100 "
            f"({len(explanations)} issue(s))"
        )

        return TrustScoreBreakdown(
            source_system=source_system,
            overall_score=overall,
            completeness_score=completeness,
            consistency_score=consistency,
            accuracy_score=accuracy,
            freshness_score=freshness,
            uniqueness_score=uniqueness,
            drift_stability_score=drift_stability,
            weights=self.weights,
            explanations=explanations,
            run_id=run_id,
        )

    def calculate_platform_score(self, source_scores: list[TrustScoreBreakdown]) -> dict:
        """
        Calculate overall platform trust score as weighted average of source scores.
        """
        if not source_scores:
            return {"overall_score": 0.0, "sources": []}
        
        avg_score = sum(s.overall_score for s in source_scores) / len(source_scores)
        return {
            "overall_score": round(avg_score, 2),
            "source_count": len(source_scores),
            "sources": [s.to_dict() for s in source_scores],
            "health_status": (
                "HEALTHY" if avg_score >= 85 else
                "WARNING" if avg_score >= 70 else
                "DEGRADED" if avg_score >= 50 else "CRITICAL"
            ),
        }
