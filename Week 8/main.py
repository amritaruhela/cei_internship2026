"""
OmniMarket Intelligence System (OMIS) - Main Application Entrypoint
Root script to run the interactive CLI reporting app or execute automated end-to-end pipeline.
"""

import sys
import argparse
from src.reporting.cli import CLIApplication


def main():
    parser = argparse.ArgumentParser(
        description="OmniMarket Customer & Order Intelligence System (OMIS)"
    )
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="Execute full end-to-end data generation, cleaning, loading, analytics, and chart generation pipeline non-interactively.",
    )

    args = parser.parse_args()

    app = CLIApplication()
    if args.pipeline:
        app.execute_full_pipeline()
    else:
        app.run()


if __name__ == "__main__":
    main()
