"""
OmniMarket Intelligence System (OMIS) - Interactive Reporting CLI Application
Provides terminal reporting for daily, weekly, monthly, and custom date range intelligence with Period-over-Period (PoP) comparative analytics.
"""

import sys
from datetime import datetime, timedelta
from typing import Tuple, Dict, Optional
import pandas as pd

from src.database.db_manager import DatabaseManager
from src.generation.generator import DataGenerator
from src.cleaning.cleaner import DataCleaner
from src.analytics.analytics_engine import AnalyticsEngine
from src.reporting.visualizer import Visualizer


class CLIApplication:
    """Terminal UI & Executive Reporting Application."""

    def __init__(self):
        self.db = DatabaseManager()

    def display_header(self) -> None:
        """Prints branded terminal banner."""
        print("=" * 80)
        print("   OMNIMARKET CUSTOMER & ORDER INTELLIGENCE SYSTEM (OMIS)")
        print("   Executive BI Reporting & Automated Data Pipeline CLI")
        print("=" * 80)

    def print_menu(self) -> None:
        """Displays interactive menu choices."""
        print("\nSELECT AN OPTION:")
        print("  [1] Daily Intelligence Summary")
        print("  [2] Weekly Performance Report")
        print("  [3] Monthly Executive Report & MoM Analysis")
        print("  [4] Custom Date Range Report")
        print("  [5] Execute Full End-to-End Data Pipeline")
        print("  [6] Run SQL Analytics Suite (Basic, Intermediate, Advanced)")
        print("  [7] Generate Visualizations & High-Res Charts")
        print("  [8] Exit")

    def run(self) -> None:
        """Main event loop for CLI application."""
        self.display_header()
        while True:
            self.print_menu()
            choice = input("\nEnter choice [1-8]: ").strip()

            if choice == "1":
                self.handle_period_report("daily")
            elif choice == "2":
                self.handle_period_report("weekly")
            elif choice == "3":
                self.handle_period_report("monthly")
            elif choice == "4":
                self.handle_custom_date_report()
            elif choice == "5":
                self.execute_full_pipeline()
            elif choice == "6":
                self.run_sql_suite()
            elif choice == "7":
                self.generate_charts()
            elif choice == "8":
                print("\nExiting OmniMarket Intelligence System. Goodbye!\n")
                sys.exit(0)
            else:
                print("\n[ERROR] Invalid menu choice. Please select a valid number [1-8].")

    def get_max_db_date(self) -> datetime:
        """Fetches latest order timestamp in database."""
        try:
            df = self.db.execute_query("SELECT MAX(order_timestamp) AS max_ts FROM fact_orders")
            if not df.empty and df["max_ts"].iloc[0]:
                return pd.to_datetime(df["max_ts"].iloc[0])
        except Exception:
            pass
        return datetime(2026, 8, 1)

    def calculate_period_dates(self, period_type: str) -> Tuple[datetime, datetime, datetime, datetime]:
        """Calculates current and previous equivalent period date ranges."""
        max_dt = self.get_max_db_date()

        if period_type == "daily":
            curr_end = max_dt
            curr_start = curr_end - timedelta(days=1)
            prev_end = curr_start
            prev_start = prev_end - timedelta(days=1)
        elif period_type == "weekly":
            curr_end = max_dt
            curr_start = curr_end - timedelta(days=7)
            prev_end = curr_start
            prev_start = prev_end - timedelta(days=7)
        elif period_type == "monthly":
            curr_end = max_dt
            curr_start = curr_end - timedelta(days=30)
            prev_end = curr_start
            prev_start = prev_end - timedelta(days=30)
        else:
            raise ValueError(f"Unknown period_type: {period_type}")

        return curr_start, curr_end, prev_start, prev_end

    def fetch_period_metrics(self, start_dt: datetime, end_dt: datetime) -> Dict:
        """Queries database for key performance indicators (KPIs) within a date range."""
        start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")

        query = """
        SELECT 
            COUNT(DISTINCT o.order_id) AS total_orders,
            COUNT(DISTINCT o.customer_id) AS unique_customers,
            COALESCE(SUM(l.order_qty * l.unit_price_usd), 0.0) AS gross_revenue,
            COALESCE(SUM(l.line_total_usd), 0.0) AS net_revenue,
            COALESCE(SUM(l.order_qty), 0) AS total_units_sold
        FROM fact_orders o
        LEFT JOIN fact_order_lines l ON o.order_id = l.order_id
        WHERE o.order_timestamp >= ? AND o.order_timestamp <= ?
          AND o.fulfillment_status IN ('Delivered', 'Shipped')
        """
        kpi_df = self.db.execute_query(query, params=(start_str, end_str))

        returns_query = """
        SELECT COALESCE(SUM(r.returned_qty), 0) AS returned_units
        FROM fact_returns r
        WHERE r.return_timestamp >= ? AND r.return_timestamp <= ?
        """
        ret_df = self.db.execute_query(returns_query, params=(start_str, end_str))

        orders = int(kpi_df["total_orders"].iloc[0])
        custs = int(kpi_df["unique_customers"].iloc[0])
        gross = float(kpi_df["gross_revenue"].iloc[0])
        net = float(kpi_df["net_revenue"].iloc[0])
        units = int(kpi_df["total_units_sold"].iloc[0])
        ret_units = int(ret_df["returned_units"].iloc[0]) if not ret_df.empty else 0

        aov = round(net / orders, 2) if orders > 0 else 0.0
        return_rate = round((ret_units / units) * 100.0, 2) if units > 0 else 0.0

        top_products_query = """
        SELECT p.product_name, SUM(l.order_qty) AS units_sold, ROUND(SUM(l.line_total_usd), 2) AS revenue
        FROM fact_orders o
        JOIN fact_order_lines l ON o.order_id = l.order_id
        JOIN dim_products p ON l.product_id = p.product_id
        WHERE o.order_timestamp >= ? AND o.order_timestamp <= ?
          AND o.fulfillment_status IN ('Delivered', 'Shipped')
        GROUP BY p.product_name
        ORDER BY revenue DESC
        LIMIT 3
        """
        top_prod_df = self.db.execute_query(top_products_query, params=(start_str, end_str))

        return {
            "start": start_str,
            "end": end_str,
            "orders": orders,
            "customers": custs,
            "gross_revenue": gross,
            "net_revenue": net,
            "aov": aov,
            "return_rate": return_rate,
            "top_products": top_prod_df,
        }

    def render_pop_comparison(self, title: str, curr: Dict, prev: Dict) -> None:
        """Renders Period-over-Period comparative table."""
        print(f"\n==========================================================================")
        print(f" {title.upper()} PERFORMANCE REPORT & PERIOD-OVER-PERIOD COMPARISON")
        print(f"==========================================================================")
        print(f" Current Period  : {curr['start'][:10]} to {curr['end'][:10]}")
        print(f" Previous Period : {prev['start'][:10]} to {prev['end'][:10]}")
        print(f"--------------------------------------------------------------------------")

        def pct_change(c, p):
            if p == 0:
                return "+100.0%" if c > 0 else "0.0%"
            diff = ((c - p) / p) * 100.0
            return f"{'+' if diff >= 0 else ''}{diff:.1f}%"

        print(f" {'Metric':<25} | {'Current Period':<15} | {'Previous Period':<15} | {'PoP Growth':<10}")
        print(f"--------------------------------------------------------------------------")
        print(f" {'Total Completed Orders':<25} | {curr['orders']:<15} | {prev['orders']:<15} | {pct_change(curr['orders'], prev['orders']):<10}")
        print(f" {'Active Unique Customers':<25} | {curr['customers']:<15} | {prev['customers']:<15} | {pct_change(curr['customers'], prev['customers']):<10}")
        print(f" {'Net Revenue ($ USD)':<25} | ${curr['net_revenue']:<14,.2f} | ${prev['net_revenue']:<14,.2f} | {pct_change(curr['net_revenue'], prev['net_revenue']):<10}")
        print(f" {'Average Order Value ($)':<25} | ${curr['aov']:<14,.2f} | ${prev['aov']:<14,.2f} | {pct_change(curr['aov'], prev['aov']):<10}")
        print(f" {'Return Rate (%)':<25} | {curr['return_rate']:<14.2f}% | {prev['return_rate']:<14.2f}% | {pct_change(curr['return_rate'], prev['return_rate']):<10}")
        print(f"--------------------------------------------------------------------------")

        print("\nTOP PRODUCTS IN CURRENT PERIOD:")
        if not curr["top_products"].empty:
            for idx, row in curr["top_products"].iterrows():
                print(f"  {idx+1}. {row['product_name']} - {row['units_sold']} units (${row['revenue']:,.2f})")
        else:
            print("  No product sales recorded in current period.")
        print("==========================================================================\n")

    def handle_period_report(self, period_type: str) -> None:
        """Generates daily, weekly, or monthly report."""
        try:
            curr_s, curr_e, prev_s, prev_e = self.calculate_period_dates(period_type)
            curr_metrics = self.fetch_period_metrics(curr_s, curr_e)
            prev_metrics = self.fetch_period_metrics(prev_s, prev_e)
            self.render_pop_comparison(period_type, curr_metrics, prev_metrics)
        except Exception as e:
            print(f"\n[ERROR] Failed to generate {period_type} report: {str(e)}")

    def handle_custom_date_report(self) -> None:
        """Prompts user for custom start and end dates and displays metrics."""
        print("\n--- Custom Date Range Analysis ---")
        start_in = input("Enter Start Date (YYYY-MM-DD) [e.g. 2025-01-01]: ").strip()
        end_in = input("Enter End Date (YYYY-MM-DD) [e.g. 2025-06-30]: ").strip()

        try:
            start_dt = datetime.strptime(start_in, "%Y-%m-%d")
            end_dt = datetime.strptime(end_in, "%Y-%m-%d") + timedelta(hours=23, minutes=59, seconds=59)

            if start_dt > end_dt:
                print("[ERROR] Start date cannot be after End date.")
                return

            days_diff = (end_dt - start_dt).days + 1
            prev_end = start_dt - timedelta(seconds=1)
            prev_start = prev_end - timedelta(days=days_diff)

            curr_metrics = self.fetch_period_metrics(start_dt, end_dt)
            prev_metrics = self.fetch_period_metrics(prev_start, prev_end)
            self.render_pop_comparison(f"Custom Range ({start_in} to {end_in})", curr_metrics, prev_metrics)
        except ValueError:
            print("[ERROR] Invalid date format. Please use YYYY-MM-DD format.")
        except Exception as e:
            print(f"[ERROR] Failed to execute custom report: {str(e)}")

    def execute_full_pipeline(self) -> None:
        """Executes full automated pipeline from scratch."""
        print("\n==========================================================================")
        print(" RUNNING END-TO-END AUTOMATED MARKETPLACE ANALYTICS PIPELINE")
        print("==========================================================================")
        print("Step 1/5: Generating synthetic raw datasets...")
        DataGenerator().generate_all()

        print("\nStep 2/5: Cleaning, imputing, and quarantining raw data...")
        clean_res = DataCleaner().run_cleaning_pipeline()

        print("\nStep 3/5: Initializing SQLite schema and loading clean relational tables...")
        self.db.initialize_database()
        self.db.load_cleaned_data()

        print("\nStep 4/5: Running SQL analytics suite...")
        AnalyticsEngine(self.db).run_all_analytics()

        print("\nStep 5/5: Rendering analytical visualizations...")
        Visualizer(self.db).generate_all_charts()

        print("\n[SUCCESS] End-to-End Pipeline Executed Successfully!")
        print(f"Data Quality Report saved to: data/reports/data_quality_report.md")
        print(f"Database file created at    : data/omnimarket_analytics.db")
        print(f"Visualizations saved to     : docs/charts/")
        print("==========================================================================\n")

    def run_sql_suite(self) -> None:
        """Executes and prints summary of SQL analytics suite."""
        print("\nExecuting full SQL Analytical Suite...")
        engine = AnalyticsEngine(self.db)
        results = engine.run_all_analytics()

        print("\nSQL EXECUTION SUMMARY:")
        print("--------------------------------------------------------------------------")
        for category, query_dict in results.items():
            print(f" [{category.upper()} SUITE]")
            for q_name, df in query_dict.items():
                print(f"   - {q_name}: Returned {len(df)} rows | Columns: {list(df.columns[:4])}...")
        print("--------------------------------------------------------------------------\n")

    def generate_charts(self) -> None:
        """Triggers visual chart generation."""
        Visualizer(self.db).generate_all_charts()


if __name__ == "__main__":
    app = CLIApplication()
    app.run()
