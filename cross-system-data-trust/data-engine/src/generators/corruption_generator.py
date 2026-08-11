"""
Corruption / Anomaly Injection Generator
Produces controlled data quality scenarios for testing the monitoring platform.

Scenarios:
  healthy              - Clean baseline data
  missing_records      - 5% of billing records removed
  duplicates           - 3% duplicate transaction IDs injected
  revenue_mismatch     - Analytics revenue inflated by 7%
  schema_drift         - New column added to billing, type change in analytics
  volume_spike         - Billing volume 3x normal for recent period
  volume_drop          - Billing volume drops 40% for recent period
  distribution_drift   - Transaction amounts shift to much higher values
  null_injection       - Heavy nulls injected into key fields
  ghost_customers      - Extra GHOST customer_ids in billing (already in real data)
  mixed                - Multiple issues simultaneously
"""
from __future__ import annotations

import copy
import logging
import random
from datetime import date, timedelta
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


SCENARIO_DESCRIPTIONS = {
    "healthy": "Clean baseline data with no injected anomalies",
    "missing_records": "5% of billing records randomly removed (missing records detection)",
    "duplicates": "3% duplicate transaction IDs with slightly modified amounts",
    "revenue_mismatch": "Analytics total_revenue inflated by 7% for last 30 days",
    "schema_drift": "New 'discount_code' column added to billing; analytics 'total_customers' changed to float",
    "volume_spike": "Billing volume spikes 3x normal for last 7 days",
    "volume_drop": "Billing volume drops 40% for last 14 days",
    "distribution_drift": "Transaction amounts shifted to 3x normal for last 30 days",
    "null_injection": "Heavy null injection into amount and total_revenue fields",
    "ghost_customers": "Additional GHOST customer IDs injected into billing (referential integrity violations)",
    "mixed": "Multiple anomalies: revenue_mismatch + volume_drop + null_injection",
}


class DataCorruptor:
    """
    Injects controlled anomalies into datasets for scenario testing.
    All operations return copies — original data is not modified.
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.np_rng = None
        try:
            import numpy as np
            self.np_rng = np.random.RandomState(seed)
        except ImportError:
            pass

    def apply_scenario(
        self,
        billing_df: pd.DataFrame,
        analytics_df: pd.DataFrame,
        scenario: str,
    ) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
        """
        Apply a named corruption scenario.
        Returns: (corrupted_billing, corrupted_analytics, metadata)
        """
        billing = billing_df.copy()
        analytics = analytics_df.copy()
        metadata: dict[str, Any] = {
            "scenario": scenario,
            "description": SCENARIO_DESCRIPTIONS.get(scenario, "Unknown scenario"),
            "changes": [],
        }

        fn = getattr(self, f"_scenario_{scenario}", None)
        if fn is None:
            raise ValueError(f"Unknown scenario: '{scenario}'. Available: {list(SCENARIO_DESCRIPTIONS)}")

        billing, analytics, changes = fn(billing, analytics)
        metadata["changes"] = changes
        logger.info(f"Applied scenario '{scenario}': {len(changes)} change(s)")
        return billing, analytics, metadata

    def _scenario_healthy(
        self, billing: pd.DataFrame, analytics: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, list]:
        return billing, analytics, [{"type": "none", "description": "No changes applied"}]

    def _scenario_missing_records(
        self, billing: pd.DataFrame, analytics: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, list]:
        n_remove = int(len(billing) * 0.05)
        drop_idx = self.rng.sample(list(billing.index), n_remove)
        billing = billing.drop(index=drop_idx).reset_index(drop=True)
        return billing, analytics, [
            {"type": "missing_records", "count": n_remove,
             "description": f"Removed {n_remove} billing records ({n_remove/len(billing_df):.1%})"}
        ]

    def _scenario_duplicates(
        self, billing: pd.DataFrame, analytics: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, list]:
        n_dupe = int(len(billing) * 0.03)
        dupe_rows = billing.sample(n=n_dupe, random_state=self.rng.randint(0, 9999)).copy()
        # Modify amount slightly so they're not exact copies
        dupe_rows["amount"] = dupe_rows["amount"] * 1.001
        billing = pd.concat([billing, dupe_rows], ignore_index=True)
        return billing, analytics, [
            {"type": "duplicates", "count": n_dupe,
             "description": f"Injected {n_dupe} duplicate transaction_ids with slightly different amounts"}
        ]

    def _scenario_revenue_mismatch(
        self, billing: pd.DataFrame, analytics: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, list]:
        # Inflate analytics revenue by 7% for the last 30 days
        cutoff = (pd.Timestamp.now() - pd.Timedelta(days=30)).date()
        analytics["date"] = pd.to_datetime(analytics["date"]).dt.date
        mask = analytics["date"] >= cutoff
        n_affected = mask.sum()
        analytics.loc[mask, "total_revenue"] = analytics.loc[mask, "total_revenue"] * 1.07
        return billing, analytics, [
            {"type": "revenue_mismatch", "pct": 7.0, "rows": int(n_affected),
             "description": f"Analytics revenue inflated 7% for last 30 days ({n_affected} rows)"}
        ]

    def _scenario_schema_drift(
        self, billing: pd.DataFrame, analytics: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, list]:
        billing["discount_code"] = None
        billing.loc[billing.sample(frac=0.3, random_state=42).index, "discount_code"] = "PROMO2024"
        analytics["total_customers"] = analytics["total_customers"].astype(float)
        return billing, analytics, [
            {"type": "schema_drift", "change": "new_column",
             "description": "Added 'discount_code' column to billing"},
            {"type": "schema_drift", "change": "type_change",
             "description": "analytics.total_customers changed from int to float"},
        ]

    def _scenario_volume_spike(
        self, billing: pd.DataFrame, analytics: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, list]:
        recent = billing.sort_values("transaction_date").tail(200).copy()
        recent["transaction_id"] = [
            f"TXN_SPIKE_{i:06d}" for i in range(len(recent))
        ]
        billing = pd.concat([billing, recent, recent], ignore_index=True)
        return billing, analytics, [
            {"type": "volume_spike", "factor": 3.0,
             "description": "Billing volume ~3x normal for recent 200 records"}
        ]

    def _scenario_volume_drop(
        self, billing: pd.DataFrame, analytics: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, list]:
        billing = billing.sort_values("transaction_date")
        recent_mask = billing["transaction_date"] >= (
            pd.Timestamp.now() - pd.Timedelta(days=14)
        ).strftime("%Y-%m-%d")
        recent_idx = billing[recent_mask].index
        keep = self.rng.sample(list(recent_idx), int(len(recent_idx) * 0.60))
        drop_idx = [i for i in recent_idx if i not in keep]
        billing = billing.drop(index=drop_idx).reset_index(drop=True)
        return billing, analytics, [
            {"type": "volume_drop", "pct": 40.0,
             "description": f"Dropped 40% of recent 14-day billing records ({len(drop_idx)} rows)"}
        ]

    def _scenario_distribution_drift(
        self, billing: pd.DataFrame, analytics: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, list]:
        billing = billing.sort_values("transaction_date")
        n_recent = int(len(billing) * 0.30)
        billing.iloc[-n_recent:, billing.columns.get_loc("amount")] = (
            billing.iloc[-n_recent:]["amount"] * 3.0
        )
        return billing, analytics, [
            {"type": "distribution_drift", "factor": 3.0,
             "description": f"Transaction amounts 3x normal for most recent {n_recent} records (PSI will trigger)"}
        ]

    def _scenario_null_injection(
        self, billing: pd.DataFrame, analytics: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, list]:
        # 15% null amounts in billing
        n_null_billing = int(len(billing) * 0.15)
        null_idx = self.rng.sample(list(billing.index), n_null_billing)
        billing.loc[null_idx, "amount"] = None

        # 20% null total_revenue in analytics
        n_null_analytics = int(len(analytics) * 0.20)
        null_idx_a = self.rng.sample(list(analytics.index), n_null_analytics)
        analytics.loc[null_idx_a, "total_revenue"] = None

        return billing, analytics, [
            {"type": "null_injection", "source": "billing.amount",
             "count": n_null_billing, "description": f"Injected {n_null_billing} nulls into billing.amount (15%)"},
            {"type": "null_injection", "source": "analytics.total_revenue",
             "count": n_null_analytics, "description": f"Injected {n_null_analytics} nulls into analytics.total_revenue (20%)"},
        ]

    def _scenario_ghost_customers(
        self, billing: pd.DataFrame, analytics: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, list]:
        n_ghosts = 200
        ghost_records = []
        for i in range(n_ghosts):
            ghost_records.append({
                "transaction_id": f"TXN_GHOST_{i:06d}",
                "customer_id": f"GHOST{(9000 + i):05d}",
                "amount": round(self.rng.uniform(50, 500), 2),
                "transaction_date": "2024-06-01",
                "status": "completed",
            })
        ghost_df = pd.DataFrame(ghost_records)
        billing = pd.concat([billing, ghost_df], ignore_index=True)
        return billing, analytics, [
            {"type": "ghost_customers", "count": n_ghosts,
             "description": f"Injected {n_ghosts} additional GHOST customer_id records into billing"}
        ]

    def _scenario_mixed(
        self, billing: pd.DataFrame, analytics: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, list]:
        all_changes = []
        billing, analytics, c = self._scenario_revenue_mismatch(billing, analytics)
        all_changes.extend(c)
        billing, analytics, c = self._scenario_volume_drop(billing, analytics)
        all_changes.extend(c)
        billing, analytics, c = self._scenario_null_injection(billing, analytics)
        all_changes.extend(c)
        return billing, analytics, all_changes


def list_scenarios() -> None:
    print("\nAvailable Corruption Scenarios:")
    print("=" * 60)
    for name, desc in SCENARIO_DESCRIPTIONS.items():
        print(f"  {name:<25} {desc}")
    print()


if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Data Corruption Generator")
    parser.add_argument("--scenario", type=str, default="healthy")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--billing-input", type=str, default="./data/raw/billing_dataset.csv")
    parser.add_argument("--analytics-input", type=str, default="./data/raw/analytics_dataset.csv")
    parser.add_argument("--output-dir", type=str, default="./data/generated")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.list:
        list_scenarios()
        sys.exit(0)

    billing_df = pd.read_csv(args.billing_input)
    analytics_df = pd.read_csv(args.analytics_input)

    corruptor = DataCorruptor(seed=args.seed)
    b_out, a_out, meta = corruptor.apply_scenario(billing_df, analytics_df, args.scenario)

    from pathlib import Path
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    b_out.to_csv(out / f"billing_{args.scenario}.csv", index=False)
    a_out.to_csv(out / f"analytics_{args.scenario}.csv", index=False)
    print(f"✓ Scenario '{args.scenario}' applied")
    for change in meta["changes"]:
        print(f"  → {change['description']}")
