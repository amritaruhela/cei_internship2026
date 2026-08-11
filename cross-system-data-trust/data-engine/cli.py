"""
CLI for Cross-System Data Drift & Trust Monitoring Platform
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cli")


def main():
    parser = argparse.ArgumentParser(
        description="DataTrust CLI — Data Drift & Trust Monitoring Engine"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # generate-crm
    p_crm = subparsers.add_parser("generate-crm", help="Generate synthetic CRM dataset")
    p_crm.add_argument("--count", type=int, default=10500)
    p_crm.add_argument("--seed", type=int, default=42)
    p_crm.add_argument("--output", type=str, default="../data/generated/crm.csv")

    # apply-scenario
    p_scen = subparsers.add_parser("apply-scenario", help="Apply controlled corruption scenario")
    p_scen.add_argument("--scenario", type=str, required=True)
    p_scen.add_argument("--billing-input", type=str, default="../data/raw/billing_dataset.csv")
    p_scen.add_argument("--analytics-input", type=str, default="../data/raw/analytics_dataset.csv")
    p_scen.add_argument("--output-dir", type=str, default="../data/generated")

    # ingest
    p_ing = subparsers.add_parser("ingest", help="Ingest raw data into Bronze layer")

    # run-all / demo
    p_demo = subparsers.add_parser("demo", help="Run end-to-end demo workflow")
    p_demo.add_argument("--scenario", type=str, default="healthy")

    args = parser.parse_args()

    if args.command == "generate-crm":
        from src.generators.crm_generator import generate_crm_records, save_crm_csv
        records = generate_crm_records(count=args.count, seed=args.seed)
        save_crm_csv(records, Path(args.output))
        print(f"✓ Generated {len(records)} CRM records → {args.output}")

    elif args.command == "apply-scenario":
        import pandas as pd
        from src.generators.corruption_generator import DataCorruptor
        b_df = pd.read_csv(args.billing_input)
        a_df = pd.read_csv(args.analytics_input)
        corruptor = DataCorruptor(seed=42)
        b_out, a_out, meta = corruptor.apply_scenario(b_df, a_df, args.scenario)
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        b_out.to_csv(out / f"billing_{args.scenario}.csv", index=False)
        a_out.to_csv(out / f"analytics_{args.scenario}.csv", index=False)
        print(f"✓ Applied scenario '{args.scenario}'")

    elif args.command == "ingest":
        from src.ingestion.bronze_ingester import BronzeIngester
        from src.config import settings
        ingester = BronzeIngester(settings.bronze_dir)
        results = ingester.ingest_all(settings.raw_dir, settings.generated_dir)
        print(f"✓ Ingested {len(results)} sources into Bronze layer")

    elif args.command == "demo" or args.command == "run-all":
        from src.pipeline import PipelineOrchestrator
        from src.config import settings
        orchestrator = PipelineOrchestrator(
            raw_dir=settings.raw_dir,
            bronze_dir=settings.bronze_dir,
            silver_dir=settings.silver_dir,
            gold_dir=settings.gold_dir,
            generated_dir=settings.generated_dir,
        )
        scenario = getattr(args, "scenario", "healthy")
        summary = orchestrator.run(scenario=scenario)
        print("\n" + "=" * 60)
        print("DATATRUST END-TO-END RUN COMPLETE")
        print("=" * 60)
        print(f"Run ID:        {summary['run_id']}")
        print(f"Scenario:      {summary['scenario']}")
        print(f"Status:        {summary['status']}")
        print(f"Duration:      {summary.get('duration_seconds')}s")
        print(f"Trust Score:   {summary.get('trust_scores', {}).get('overall_score')}/100")
        print(f"Alerts:        {len(summary.get('alerts', []))}")
        print("=" * 60 + "\n")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
