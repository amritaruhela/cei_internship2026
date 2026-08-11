"""
Demo Script for Cross-System Data Drift & Trust Monitoring Platform
"""
import argparse
import sys
from pathlib import Path

# Add data-engine to sys.path
data_engine_path = Path(__file__).parent.parent / "data-engine"
sys.path.insert(0, str(data_engine_path))
sys.path.insert(0, str(data_engine_path / "src"))

from src.pipeline import PipelineOrchestrator
from src.config import settings


def run_demo(scenario: str = "mixed"):
    print("\n" + "=" * 60)
    print("  CROSS-SYSTEM DATA DRIFT & TRUST MONITORING PLATFORM")
    print("  Running End-to-End Demo Workflow...")
    print("=" * 60 + "\n")

    orchestrator = PipelineOrchestrator(
        raw_dir=settings.raw_dir,
        bronze_dir=settings.bronze_dir,
        silver_dir=settings.silver_dir,
        gold_dir=settings.gold_dir,
        generated_dir=settings.generated_dir,
    )

    summary = orchestrator.run(
        scenario=scenario,
        generate_crm=True,
        crm_count=10500,
        crm_seed=42,
    )

    print("\n" + "DEMO EXECUTION SUMMARY " + "=" * 38)
    print(f"  Run ID:                {summary['run_id']}")
    print(f"  Execution Scenario:    {summary['scenario']}")
    print(f"  Execution Status:      {summary['status']}")
    print(f"  Duration:              {summary['duration_seconds']} seconds")
    
    scores = summary.get("trust_scores", {})
    print(f"\n  OVERALL TRUST SCORE:   {scores.get('overall_score', 0)} / 100 ({scores.get('health_status', 'UNKNOWN')})")
    
    print("\n  SOURCE BREAKDOWN:")
    for s in scores.get("sources", []):
        print(f"    * {s['source_system'].upper():<10} Score: {s['overall_score']:<5} Grade: {s['grade']} Status: {s['health_status']}")
        for exp in s.get("explanations", []):
            print(f"        + {exp}")

    alerts = summary.get("alerts", [])
    print(f"\n  ALERTS GENERATED ({len(alerts)}):")
    for a in alerts[:8]:
        print(f"    [{a['severity']:<8}] {a['source']} - {a['issue_type']}: {a['description'][:85]}")

    if len(alerts) > 8:
        print(f"    ... and {len(alerts) - 8} more alerts.")

    print("\n" + "=" * 60)
    print("Demo execution complete! Dashboard data is prepared.")
    print("============================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DataTrust Demo Runner")
    parser.add_argument(
        "--scenario",
        type=str,
        default="mixed",
        help="Scenario to run: healthy, missing_records, duplicates, revenue_mismatch, schema_drift, volume_spike, volume_drop, distribution_drift, null_injection, mixed",
    )
    args = parser.parse_args()
    run_demo(scenario=args.scenario)
