"""
OmniMarket Intelligence System (OMIS) - Customer Cohort & RFM Analytics
Generates Customer Cohort Retention Matrix (Month 0 to Month 6+) and RFM Customer Segments.
"""

from typing import Dict, Tuple
import pandas as pd
import numpy as np

from src.database.db_manager import DatabaseManager


class CohortAnalytics:
    """Computes Customer Cohorts and RFM Segmentation."""

    def __init__(self, db_manager: DatabaseManager = None):
        self.db = db_manager or DatabaseManager()

    def generate_cohort_matrix(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Computes Cohort Retention Matrix:
        Cohort Month vs Months Since Registration (0, 1, 2, 3, 4, 5+).
        Returns counts DataFrame and percentage DataFrame.
        """
        query = """
        SELECT 
            c.customer_id,
            STRFTIME('%Y-%m', c.registration_date) AS cohort_month,
            STRFTIME('%Y-%m', o.order_timestamp) AS order_month
        FROM dim_customers c
        JOIN fact_orders o ON c.customer_id = o.customer_id
        WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
        """
        df = self.db.execute_query(query)

        df["cohort_dt"] = pd.to_datetime(df["cohort_month"] + "-01")
        df["order_dt"] = pd.to_datetime(df["order_month"] + "-01")

        # Calculate month difference
        df["period_number"] = (
            (df["order_dt"].dt.year - df["cohort_dt"].dt.year) * 12
            + (df["order_dt"].dt.month - df["cohort_dt"].dt.month)
        )

        # Pivot to create matrix
        cohort_counts = df.pivot_table(
            index="cohort_month",
            columns="period_number",
            values="customer_id",
            aggfunc="nunique",
            fill_value=0,
        )

        # Get initial cohort sizes
        cohort_sizes_query = """
        SELECT STRFTIME('%Y-%m', registration_date) AS cohort_month, COUNT(customer_id) AS total_customers
        FROM dim_customers
        GROUP BY STRFTIME('%Y-%m', registration_date)
        """
        sizes_df = self.db.execute_query(cohort_sizes_query).set_index("cohort_month")

        cohort_counts.insert(0, "Cohort Size", sizes_df["total_customers"])

        # Calculate percentage retention matrix
        cohort_pct = cohort_counts.iloc[:, 1:].div(cohort_counts["Cohort Size"], axis=0) * 100.0
        cohort_pct = cohort_pct.round(1)

        return cohort_counts, cohort_pct

    def compute_rfm_segmentation(self) -> pd.DataFrame:
        """
        Computes Recency, Frequency, and Monetary (RFM) metrics per customer,
        and assigns deterministic customer segments (VIP, High Value, Regular, Occasional, At Risk).
        """
        query = """
        SELECT 
            c.customer_id,
            c.full_name,
            c.account_tier,
            c.geo_state,
            MAX(o.order_timestamp) AS latest_order_ts,
            COUNT(DISTINCT o.order_id) AS total_orders,
            ROUND(SUM(l.line_total_usd), 2) AS total_spend_usd
        FROM dim_customers c
        JOIN fact_orders o ON c.customer_id = o.customer_id
        JOIN fact_order_lines l ON o.order_id = l.order_id
        WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
        GROUP BY c.customer_id, c.full_name, c.account_tier, c.geo_state
        """
        df = self.db.execute_query(query)

        # Anchor date as max order date in system + 1 day
        max_dt = pd.to_datetime(df["latest_order_ts"]).max()
        anchor_dt = max_dt + pd.Timedelta(days=1)

        df["recency_days"] = (anchor_dt - pd.to_datetime(df["latest_order_ts"])).dt.days

        def assign_segment(row):
            spend = row["total_spend_usd"]
            orders = row["total_orders"]
            recency = row["recency_days"]

            if spend >= 1000 or (spend >= 750 and orders >= 4):
                return "VIP"
            elif spend >= 400 or orders >= 3:
                return "High Value"
            elif recency <= 90:
                return "Regular"
            elif recency <= 180:
                return "Occasional"
            else:
                return "At Risk"

        df["rfm_segment"] = df.apply(assign_segment, axis=1)
        return df


if __name__ == "__main__":
    cohort = CohortAnalytics()
    counts, pct = cohort.generate_cohort_matrix()
    rfm = cohort.compute_rfm_segmentation()
    print("Cohort Analytics Execution Completed:")
    print(f"  - Cohort Matrix Shape: {counts.shape}")
    print(f"  - RFM Segment Counts:\n{rfm['rfm_segment'].value_counts()}")
