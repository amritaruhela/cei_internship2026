"""
OmniMarket Intelligence System (OMIS) - SQL Analytics Engine
Python wrapper to execute basic, intermediate, and advanced SQL analytical queries against SQLite.
"""

from typing import Dict
import pandas as pd
from src.database.db_manager import DatabaseManager
from src.config import SQL_DIR


class AnalyticsEngine:
    """Orchestrates SQL analytics execution and provides DataFrame output APIs."""

    def __init__(self, db_manager: DatabaseManager = None):
        self.db = db_manager or DatabaseManager()

    def run_basic_analytics(self) -> Dict[str, pd.DataFrame]:
        """Executes basic SQL suite (Category revenue, Top customers, Monthly trends)."""
        script_path = SQL_DIR / "basic.sql"
        return self.db.execute_sql_script(str(script_path))

    def run_intermediate_analytics(self) -> Dict[str, pd.DataFrame]:
        """Executes intermediate SQL suite (Zero purchase customers, Product returns, Category return rate, AOV by tier, Regional contribution)."""
        script_path = SQL_DIR / "intermediate.sql"
        return self.db.execute_sql_script(str(script_path))

    def run_advanced_analytics(self) -> Dict[str, pd.DataFrame]:
        """Executes advanced SQL suite (Window functions, CTEs, Cohort, YoY, Basket analysis)."""
        script_path = SQL_DIR / "advanced.sql"
        return self.db.execute_sql_script(str(script_path))

    def run_all_analytics(self) -> Dict[str, pd.DataFrame]:
        """Runs all analytical suites and consolidates results into a dictionary."""
        all_results = {}
        all_results["basic"] = self.run_basic_analytics()
        all_results["intermediate"] = self.run_intermediate_analytics()
        all_results["advanced"] = self.run_advanced_analytics()
        return all_results


if __name__ == "__main__":
    engine = AnalyticsEngine()
    results = engine.run_all_analytics()
    print("All SQL Analytics Queries Executed Successfully!")
    print(f"  - Basic Queries Executed: {len(results['basic'])}")
    print(f"  - Intermediate Queries Executed: {len(results['intermediate'])}")
    print(f"  - Advanced Queries Executed: {len(results['advanced'])}")
