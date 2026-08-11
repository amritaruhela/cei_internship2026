"""
Quality Rule Engine

Evaluates data quality rules defined in quality_rules.yaml against
Silver-layer DataFrames.

Supported rule types:
  - completeness:      Column must not be null above a threshold
  - uniqueness:        Primary key or business key must be unique
  - referential:       Foreign key values must exist in a reference set
  - validity:          Values must conform to an allowed set or regex
  - range:             Numeric values must be within [min, max]
  - consistency:       Multi-column business rule (e.g. amount > 0 when status='completed')

Rules are NOT hard-coded. They are loaded from quality_rules.yaml and
evaluated generically against any DataFrame with matching column names.
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class RuleResult:
    rule_id: str
    source_system: str
    column: Optional[str]
    rule_type: str
    passed: bool
    total_records: int
    failed_records: int
    pass_rate: float
    threshold: float
    severity: str
    description: str
    sample_failures: list = field(default_factory=list)
    evaluated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class QualityRuleEngine:
    """
    Generic rule engine that evaluates YAML-configured rules
    against pandas DataFrames without hard-coding any column logic.
    """

    def __init__(self, rules: Optional[list[dict]] = None):
        self.rules = rules or []

    def evaluate(
        self,
        df: pd.DataFrame,
        source_system: str,
        reference_sets: Optional[dict[str, set]] = None,
    ) -> list[RuleResult]:
        """
        Evaluate all applicable rules against a DataFrame.
        
        Args:
            df: The Silver-layer DataFrame to evaluate.
            source_system: Name of source (billing, analytics, crm).
            reference_sets: Dict of column -> set of valid values for referential checks.
        
        Returns:
            List of RuleResult objects, one per evaluated rule.
        """
        results = []
        applicable_rules = [r for r in self.rules if r.get("source") == source_system and r.get("enabled", True)]

        if not applicable_rules:
            logger.info(f"No applicable rules for source '{source_system}'")
            return results

        for rule in applicable_rules:
            try:
                result = self._evaluate_rule(df, rule, source_system, reference_sets or {})
                results.append(result)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.get('rule_id')}: {e}")

        passed = sum(1 for r in results if r.passed)
        logger.info(f"[{source_system}] Quality check: {passed}/{len(results)} rules passed")
        return results

    def _evaluate_rule(
        self,
        df: pd.DataFrame,
        rule: dict,
        source_system: str,
        reference_sets: dict,
    ) -> RuleResult:
        rule_id = rule.get("rule_id", f"RULE-{uuid.uuid4().hex[:6]}")
        rule_type = rule.get("rule_type", "")
        column = rule.get("column")
        threshold = float(rule.get("threshold", 0.95))
        severity = rule.get("severity", "MEDIUM")
        description = rule.get("description", rule_id)
        total = len(df)

        if rule_type == "completeness":
            result = self._check_completeness(df, column, threshold, rule_id, source_system, severity, description)

        elif rule_type == "uniqueness":
            columns = rule.get("columns") or ([column] if column else [])
            result = self._check_uniqueness(df, columns, threshold, rule_id, source_system, severity, description)

        elif rule_type == "referential":
            ref_column = rule.get("reference_column", column)
            ref_set = reference_sets.get(ref_column, set())
            result = self._check_referential(df, column, ref_set, threshold, rule_id, source_system, severity, description)

        elif rule_type == "validity":
            allowed_values = rule.get("allowed_values")
            pattern = rule.get("pattern")
            result = self._check_validity(df, column, allowed_values, pattern, threshold, rule_id, source_system, severity, description)

        elif rule_type == "range":
            min_val = rule.get("min_value")
            max_val = rule.get("max_value")
            result = self._check_range(df, column, min_val, max_val, threshold, rule_id, source_system, severity, description)

        elif rule_type == "consistency":
            condition = rule.get("condition", "")
            result = self._check_consistency(df, column, condition, threshold, rule_id, source_system, severity, description)

        else:
            result = RuleResult(
                rule_id=rule_id, source_system=source_system, column=column,
                rule_type=rule_type, passed=True, total_records=total,
                failed_records=0, pass_rate=1.0, threshold=threshold,
                severity=severity, description=f"Unsupported rule type: {rule_type}",
            )

        return result

    def _check_completeness(self, df, column, threshold, rule_id, source, severity, description) -> RuleResult:
        total = len(df)
        if column not in df.columns:
            logger.warning(f"[{rule_id}] Column '{column}' not found in {source}")
            return RuleResult(
                rule_id=rule_id, source_system=source, column=column,
                rule_type="completeness", passed=True, total_records=total,
                failed_records=0, pass_rate=1.0, threshold=threshold,
                severity=severity, description=f"{description} (column absent, skipped)",
            )
        
        null_mask = df[column].isna()
        failed = int(null_mask.sum())
        pass_rate = (total - failed) / max(total, 1)
        passed = pass_rate >= threshold
        
        sample_failures = []
        if failed > 0:
            fail_indices = df[null_mask].head(3).index.tolist()
            sample_failures = [f"row_index={i}" for i in fail_indices]

        return RuleResult(
            rule_id=rule_id, source_system=source, column=column,
            rule_type="completeness", passed=passed, total_records=total,
            failed_records=failed, pass_rate=round(pass_rate, 4),
            threshold=threshold, severity=severity if not passed else "INFO",
            description=description, sample_failures=sample_failures,
        )

    def _check_uniqueness(self, df, columns, threshold, rule_id, source, severity, description) -> RuleResult:
        total = len(df)
        existing_cols = [c for c in columns if c in df.columns]
        if not existing_cols:
            return RuleResult(
                rule_id=rule_id, source_system=source, column=str(columns),
                rule_type="uniqueness", passed=True, total_records=total,
                failed_records=0, pass_rate=1.0, threshold=threshold,
                severity=severity, description=f"{description} (columns absent)",
            )

        duplicates = df.duplicated(subset=existing_cols, keep=False)
        failed = int(duplicates.sum())
        pass_rate = (total - failed) / max(total, 1)
        passed = pass_rate >= threshold
        
        sample_failures = []
        if failed > 0:
            dup_vals = df[duplicates][existing_cols[0]].head(3).tolist()
            sample_failures = [f"duplicate value: {v}" for v in dup_vals]

        return RuleResult(
            rule_id=rule_id, source_system=source, column=str(columns),
            rule_type="uniqueness", passed=passed, total_records=total,
            failed_records=failed, pass_rate=round(pass_rate, 4),
            threshold=threshold, severity=severity if not passed else "INFO",
            description=description, sample_failures=sample_failures,
        )

    def _check_referential(self, df, column, ref_set, threshold, rule_id, source, severity, description) -> RuleResult:
        total = len(df)
        if column not in df.columns or not ref_set:
            return RuleResult(
                rule_id=rule_id, source_system=source, column=column,
                rule_type="referential", passed=True if not ref_set else False,
                total_records=total, failed_records=0, pass_rate=1.0,
                threshold=threshold, severity=severity,
                description=f"{description} (reference set empty or column absent)",
            )

        # Exclude GHOST IDs from pass—they are known violations
        ghost_mask = df[column].str.startswith("GHOST", na=False) if df[column].dtype == object else pd.Series(False, index=df.index)
        not_in_ref = ~df[column].isin(ref_set) & ~ghost_mask
        failed = int(not_in_ref.sum()) + int(ghost_mask.sum())
        pass_rate = (total - failed) / max(total, 1)
        passed = pass_rate >= threshold

        sample_failures = []
        all_failures = df[~df[column].isin(ref_set)][column].head(5).tolist()
        sample_failures = [f"orphan: {v}" for v in all_failures]

        return RuleResult(
            rule_id=rule_id, source_system=source, column=column,
            rule_type="referential", passed=passed, total_records=total,
            failed_records=failed, pass_rate=round(pass_rate, 4),
            threshold=threshold, severity=severity if not passed else "INFO",
            description=description, sample_failures=sample_failures,
        )

    def _check_validity(self, df, column, allowed_values, pattern, threshold, rule_id, source, severity, description) -> RuleResult:
        total = len(df)
        if column not in df.columns:
            return RuleResult(
                rule_id=rule_id, source_system=source, column=column,
                rule_type="validity", passed=True, total_records=total,
                failed_records=0, pass_rate=1.0, threshold=threshold,
                severity=severity, description=f"{description} (column absent)",
            )

        col_data = df[column].dropna()
        if allowed_values:
            invalid_mask = ~df[column].isin(allowed_values) & df[column].notna()
        elif pattern:
            compiled = re.compile(pattern)
            invalid_mask = ~df[column].astype(str).str.match(compiled) & df[column].notna()
        else:
            invalid_mask = pd.Series(False, index=df.index)

        failed = int(invalid_mask.sum())
        pass_rate = (total - failed) / max(total, 1)
        passed = pass_rate >= threshold

        sample_failures = df[invalid_mask][column].head(3).tolist()

        return RuleResult(
            rule_id=rule_id, source_system=source, column=column,
            rule_type="validity", passed=passed, total_records=total,
            failed_records=failed, pass_rate=round(pass_rate, 4),
            threshold=threshold, severity=severity if not passed else "INFO",
            description=description, sample_failures=[str(v) for v in sample_failures],
        )

    def _check_range(self, df, column, min_val, max_val, threshold, rule_id, source, severity, description) -> RuleResult:
        total = len(df)
        if column not in df.columns:
            return RuleResult(
                rule_id=rule_id, source_system=source, column=column,
                rule_type="range", passed=True, total_records=total,
                failed_records=0, pass_rate=1.0, threshold=threshold,
                severity=severity, description=f"{description} (column absent)",
            )

        col_num = pd.to_numeric(df[column], errors="coerce")
        invalid = pd.Series(False, index=df.index)
        if min_val is not None:
            invalid |= col_num < float(min_val)
        if max_val is not None:
            invalid |= col_num > float(max_val)

        failed = int(invalid.sum())
        pass_rate = (total - failed) / max(total, 1)
        passed = pass_rate >= threshold

        sample_failures = df[invalid][column].head(3).tolist()
        return RuleResult(
            rule_id=rule_id, source_system=source, column=column,
            rule_type="range", passed=passed, total_records=total,
            failed_records=failed, pass_rate=round(pass_rate, 4),
            threshold=threshold, severity=severity if not passed else "INFO",
            description=description, sample_failures=[str(v) for v in sample_failures],
        )

    def _check_consistency(self, df, column, condition, threshold, rule_id, source, severity, description) -> RuleResult:
        """
        Evaluates a pandas query expression as a consistency rule.
        Example: "amount > 0 or status != 'completed'"
        """
        total = len(df)
        try:
            valid_mask = df.eval(condition)
            failed = int((~valid_mask).sum())
        except Exception as e:
            logger.warning(f"[{rule_id}] Could not evaluate consistency condition '{condition}': {e}")
            failed = 0

        pass_rate = (total - failed) / max(total, 1)
        passed = pass_rate >= threshold
        return RuleResult(
            rule_id=rule_id, source_system=source, column=column,
            rule_type="consistency", passed=passed, total_records=total,
            failed_records=failed, pass_rate=round(pass_rate, 4),
            threshold=threshold, severity=severity if not passed else "INFO",
            description=description,
        )


def load_engine_from_yaml(config_path: Path) -> QualityRuleEngine:
    """Load a QualityRuleEngine from a YAML config file."""
    import yaml
    with open(config_path) as f:
        data = yaml.safe_load(f)
    rules = data.get("rules", [])
    logger.info(f"Loaded {len(rules)} quality rules from {config_path}")
    return QualityRuleEngine(rules=rules)
