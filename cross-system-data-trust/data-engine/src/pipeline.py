"""
Main Pipeline Orchestrator

Runs the full end-to-end data pipeline:
  1. Ingest raw data → Bronze
  2. Transform → Silver (with quarantine)
  3. Aggregate → Gold
  4. Quality checks
  5. Cross-system reconciliation
  6. Drift detection (volume, distribution, schema)
  7. Trust score calculation
  8. Alert generation
  9. Persist results to DB (via API or direct)

Can be invoked via CLI, demo script, or scheduled.
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


class PipelineOrchestrator:
    def __init__(
        self,
        raw_dir: Path,
        bronze_dir: Path,
        silver_dir: Path,
        gold_dir: Path,
        generated_dir: Path,
        api_base_url: Optional[str] = None,
    ):
        self.raw_dir = Path(raw_dir)
        self.bronze_dir = Path(bronze_dir)
        self.silver_dir = Path(silver_dir)
        self.gold_dir = Path(gold_dir)
        self.generated_dir = Path(generated_dir)
        self.api_base_url = api_base_url
        self.run_id = str(uuid.uuid4())
        self.started_at = datetime.now(timezone.utc)

    def run(
        self,
        scenario: str = "healthy",
        generate_crm: bool = True,
        crm_count: int = 10500,
        crm_seed: int = 42,
    ) -> dict[str, Any]:
        """
        Execute full pipeline and return a summary dict.
        """
        logger.info(f"Pipeline run started: {self.run_id} | scenario={scenario}")

        summary: dict[str, Any] = {
            "run_id": self.run_id,
            "scenario": scenario,
            "started_at": self.started_at.isoformat(),
            "stages": {},
            "alerts": [],
            "trust_scores": {},
            "status": "RUNNING",
        }

        try:
            # ── STAGE 1: Generate CRM data
            if generate_crm:
                summary["stages"]["crm_generation"] = self._stage_generate_crm(
                    crm_count, crm_seed
                )

            # ── STAGE 2: Apply corruption scenario (if not healthy)
            summary["stages"]["scenario"] = self._stage_apply_scenario(scenario)

            # ── STAGE 3: Bronze ingestion
            summary["stages"]["bronze"] = self._stage_bronze()

            # ── STAGE 4: Silver transformation
            summary["stages"]["silver"] = self._stage_silver()

            # ── STAGE 5: Gold aggregation
            summary["stages"]["gold"] = self._stage_gold()

            # ── STAGE 6: Drift detection
            summary["stages"]["drift"] = self._stage_drift()

            # ── STAGE 7: Trust scores + alerts
            scores, alerts = self._stage_scoring_and_alerts(
                summary["stages"].get("gold", {}),
                summary["stages"].get("drift", {}).get("results", []),
            )
            summary["trust_scores"] = scores
            summary["alerts"] = alerts

            # ── STAGE 8: Persist to API if configured
            if self.api_base_url:
                summary["stages"]["api_persist"] = self._stage_persist_to_api(
                    summary
                )

            summary["status"] = "SUCCESS"

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            summary["status"] = "FAILED"
            summary["error"] = str(e)

        summary["ended_at"] = datetime.now(timezone.utc).isoformat()
        duration = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        summary["duration_seconds"] = round(duration, 2)

        # Save run summary
        self._save_run_summary(summary)
        return summary

    # ──────────────────────────────────────────────────────────
    # STAGE IMPLEMENTATIONS
    # ──────────────────────────────────────────────────────────

    def _stage_generate_crm(self, count: int, seed: int) -> dict:
        from src.generators.crm_generator import generate_crm_records, save_crm_csv
        output = self.generated_dir / "crm.csv"
        records = generate_crm_records(count=count, seed=seed)
        save_crm_csv(records, output)
        return {"status": "SUCCESS", "records_generated": len(records), "output": str(output)}

    def _stage_apply_scenario(self, scenario: str) -> dict:
        if scenario == "healthy":
            return {"status": "SUCCESS", "scenario": "healthy", "changes": []}

        from src.generators.corruption_generator import DataCorruptor
        billing_raw = self.raw_dir / "billing_dataset.csv"
        analytics_raw = self.raw_dir / "analytics_dataset.csv"

        billing_df = pd.read_csv(billing_raw)
        analytics_df = pd.read_csv(analytics_raw)

        corruptor = DataCorruptor(seed=42)
        b_out, a_out, meta = corruptor.apply_scenario(billing_df, analytics_df, scenario)

        b_path = self.generated_dir / "billing_scenario.csv"
        a_path = self.generated_dir / "analytics_scenario.csv"
        b_out.to_csv(b_path, index=False)
        a_out.to_csv(a_path, index=False)

        # Point raw_dir to generated for subsequent stages
        self._scenario_billing = b_path
        self._scenario_analytics = a_path

        return {"status": "SUCCESS", "scenario": scenario, "changes": meta["changes"]}

    def _stage_bronze(self) -> dict:
        from src.ingestion.bronze_ingester import BronzeIngester
        ingester = BronzeIngester(self.bronze_dir, run_id=self.run_id)

        results = []
        # Use scenario files if available, otherwise raw
        billing_src = getattr(self, "_scenario_billing", self.raw_dir / "billing_dataset.csv")
        analytics_src = getattr(self, "_scenario_analytics", self.raw_dir / "analytics_dataset.csv")
        crm_src = self.generated_dir / "crm.csv"

        if billing_src.exists():
            results.append(ingester.ingest_csv(billing_src, "billing"))
        if analytics_src.exists():
            results.append(ingester.ingest_csv(analytics_src, "analytics"))
        if crm_src.exists():
            results.append(ingester.ingest_csv(crm_src, "crm"))

        self._bronze_ingester = ingester
        return {
            "status": "SUCCESS",
            "sources_ingested": len(results),
            "total_records": sum(r["records_read"] for r in results),
        }

    def _stage_silver(self) -> dict:
        from src.silver.transformer import SilverTransformer
        transformer = SilverTransformer(self.silver_dir, run_id=self.run_id)
        ingester = getattr(self, "_bronze_ingester", None)

        stats = {}

        # Billing
        try:
            billing_bronze = ingester.read_bronze("billing") if ingester else pd.DataFrame()
            billing_silver = transformer.transform_billing(billing_bronze)
            transformer.save_silver(billing_silver, "billing")
            self._billing_silver = billing_silver
            stats["billing"] = {"records": len(billing_silver)}
        except Exception as e:
            stats["billing"] = {"error": str(e)}

        # Analytics
        try:
            analytics_bronze = ingester.read_bronze("analytics") if ingester else pd.DataFrame()
            analytics_silver = transformer.transform_analytics(analytics_bronze)
            transformer.save_silver(analytics_silver, "analytics")
            self._analytics_silver = analytics_silver
            stats["analytics"] = {"records": len(analytics_silver)}
        except Exception as e:
            stats["analytics"] = {"error": str(e)}

        # CRM
        try:
            crm_bronze = ingester.read_bronze("crm") if ingester else pd.DataFrame()
            crm_silver = transformer.transform_crm(crm_bronze)
            transformer.save_silver(crm_silver, "crm")
            self._crm_silver = crm_silver
            stats["crm"] = {"records": len(crm_silver)}
        except Exception as e:
            stats["crm"] = {"error": str(e)}

        # Quarantine
        qpath = transformer.save_quarantine()
        self._transformer = transformer
        return {
            "status": "SUCCESS",
            "stats": stats,
            "quarantine_records": len(transformer.quarantine_records),
            "quarantine_path": str(qpath) if qpath else None,
        }

    def _stage_gold(self) -> dict:
        from src.gold.aggregator import GoldAggregator
        aggregator = GoldAggregator(self.gold_dir, run_id=self.run_id)

        billing = getattr(self, "_billing_silver", pd.DataFrame())
        analytics = getattr(self, "_analytics_silver", pd.DataFrame())
        crm = getattr(self, "_crm_silver", None)

        # Quality metrics
        quality_df = aggregator.compute_quality_metrics(billing, analytics, crm)
        aggregator.save(quality_df, "data_quality_metrics")

        # Cross-system comparison
        comparison_df = aggregator.compute_cross_system_comparison(billing, analytics)
        aggregator.save(comparison_df, "cross_system_comparison")

        # Volume stats
        volume_df = aggregator.compute_volume_stats(billing)
        aggregator.save(volume_df, "volume_stats")

        self._gold_aggregator = aggregator
        self._quality_df = quality_df
        self._comparison_df = comparison_df
        self._volume_df = volume_df

        return {
            "status": "SUCCESS",
            "quality_rows": len(quality_df),
            "comparison_rows": len(comparison_df),
            "volume_rows": len(volume_df),
        }

    def _stage_drift(self) -> dict:
        from src.drift.detector import (
            VolumeDriftDetector, DistributionDriftDetector, SchemaDriftDetector
        )

        all_results = []

        # Volume drift
        volume_df = getattr(self, "_volume_df", pd.DataFrame())
        if not volume_df.empty:
            vd = VolumeDriftDetector()
            for col in ["tx_count", "revenue"]:
                if col in volume_df.columns:
                    results = vd.detect(volume_df, count_col=col, source_system="billing")
                    all_results.extend(results)

        # Distribution drift — billing amounts
        billing = getattr(self, "_billing_silver", pd.DataFrame())
        if not billing.empty and "amount" in billing.columns and "transaction_date" in billing.columns:
            billing_sorted = billing.sort_values("transaction_date")
            split = int(len(billing_sorted) * 0.7)
            baseline_df = billing_sorted.iloc[:split]
            current_df = billing_sorted.iloc[split:]

            dd = DistributionDriftDetector()
            dist_results = dd.detect_all(
                baseline_df, current_df,
                source_system="billing",
                numerical_cols=["amount"],
                categorical_cols=["status"],
            )
            all_results.extend(dist_results)

        # Distribution drift — analytics
        analytics = getattr(self, "_analytics_silver", pd.DataFrame())
        if not analytics.empty and "total_revenue" in analytics.columns:
            analytics_sorted = analytics.sort_values("date")
            split = int(len(analytics_sorted) * 0.7)
            baseline_df = analytics_sorted.iloc[:split]
            current_df = analytics_sorted.iloc[split:]

            dd2 = DistributionDriftDetector()
            dist_results2 = dd2.detect_all(
                baseline_df, current_df,
                source_system="analytics",
                numerical_cols=["total_revenue", "total_customers"],
            )
            all_results.extend(dist_results2)

        # Schema drift
        snapshots_dir = self.gold_dir / "schema_snapshots"
        sd = SchemaDriftDetector(snapshots_dir)
        for name, df in [
            ("billing", billing),
            ("analytics", analytics),
        ]:
            if not df.empty:
                schema_results = sd.detect(df, name, self.run_id)
                all_results.extend(schema_results)

        self._drift_results = all_results

        drifted_count = sum(1 for r in all_results if getattr(r, "is_drifted", False))
        logger.info(f"Drift detection: {drifted_count}/{len(all_results)} checks flagged")

        return {
            "status": "SUCCESS",
            "total_checks": len(all_results),
            "drifted": drifted_count,
            "results": all_results,
        }

    def _stage_scoring_and_alerts(
        self, gold_stage: dict, drift_results: list
    ) -> tuple[dict, list]:
        from src.scoring.trust_score import TrustScoreCalculator
        from src.alerts.generator import AlertGenerator

        calculator = TrustScoreCalculator()
        alert_gen = AlertGenerator(run_id=self.run_id)
        quality_df = getattr(self, "_quality_df", pd.DataFrame())
        comparison_df = getattr(self, "_comparison_df", pd.DataFrame())

        source_scores = []

        # Compute reconciliation summary for accuracy score
        recon_metrics = {}
        if not comparison_df.empty:
            recon_metrics = {
                "avg_revenue_pct_diff": float(comparison_df["revenue_pct_diff"].dropna().mean()) if "revenue_pct_diff" in comparison_df else 0.0,
                "avg_customer_pct_diff": float(comparison_df["customer_pct_diff"].dropna().mean()) if "customer_pct_diff" in comparison_df else 0.0,
            }

        for _, row in quality_df.iterrows():
            qm = row.to_dict()
            source = qm.get("source_system", "unknown")

            score = calculator.calculate(
                source_system=source,
                quality_metrics=qm,
                freshness_status="FRESH",
                freshness_delay_hours=0.0,
                drift_results=[d for d in drift_results if getattr(d, "source_system", "") == source],
                reconciliation_metrics=recon_metrics if source == "billing" else {},
                run_id=self.run_id,
            )
            source_scores.append(score)

            # Quality alerts
            thresholds = {"completeness": {"critical_rate": 0.80, "high_rate": 0.90},
                          "uniqueness": {"critical_rate": 0.95, "high_rate": 0.98}}
            alert_gen.from_quality_metrics(qm, thresholds=thresholds)

        # Drift alerts
        alert_gen.from_drift_results(drift_results)

        # Reconciliation alerts
        alert_gen.from_reconciliation(comparison_df)

        platform_scores = calculator.calculate_platform_score(source_scores)
        all_alerts = alert_gen.get_all_alerts()

        logger.info(
            f"Trust scores computed. Platform: {platform_scores['overall_score']:.1f}. "
            f"Alerts: {len(all_alerts)}"
        )

        return platform_scores, all_alerts

    def _stage_persist_to_api(self, summary: dict) -> dict:
        """Persist pipeline results to the FastAPI backend."""
        import httpx
        try:
            # Post pipeline run
            resp = httpx.post(
                f"{self.api_base_url}/api/v1/pipelines/runs",
                json={
                    "run_id": summary["run_id"],
                    "pipeline_name": f"full_pipeline_{summary['scenario']}",
                    "scenario": summary["scenario"],
                    "status": summary["status"],
                    "started_at": summary["started_at"],
                    "ended_at": summary.get("ended_at"),
                    "trust_scores": summary.get("trust_scores", {}),
                    "alerts": summary.get("alerts", []),
                    "stage_summary": {
                        k: {kk: vv for kk, vv in v.items() if kk != "results"}
                        for k, v in summary["stages"].items()
                    },
                },
                timeout=30.0,
            )
            return {"status": "SUCCESS", "response_code": resp.status_code}
        except Exception as e:
            logger.warning(f"Failed to persist to API: {e}")
            return {"status": "FAILED", "error": str(e)}

    def _save_run_summary(self, summary: dict) -> None:
        """Save run summary to disk for debugging."""
        runs_dir = self.gold_dir / "pipeline_runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        path = runs_dir / f"run_{self.run_id[:8]}.json"

        # Serialize drift results (not JSON-serializable by default)
        serializable = json.loads(json.dumps(summary, default=str))
        with open(path, "w") as f:
            json.dump(serializable, f, indent=2, default=str)
        logger.info(f"Run summary saved: {path}")
