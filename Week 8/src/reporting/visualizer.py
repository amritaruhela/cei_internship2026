"""
OmniMarket Intelligence System (OMIS) - Chart & Visualization Generator
Renders high-resolution analytical charts for executive reports and documentation.
"""

import os
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from src.config import CHARTS_DIR
from src.database.db_manager import DatabaseManager
from src.analytics.cohort_analysis import CohortAnalytics


class Visualizer:
    """Generates analytical charts and visualizations."""

    def __init__(self, db_manager: DatabaseManager = None):
        self.db = db_manager or DatabaseManager()
        self.cohort_analytics = CohortAnalytics(self.db)
        os.makedirs(CHARTS_DIR, exist_ok=True)
        # Apply dark sleek modern aesthetic styling
        plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    def generate_all_charts(self) -> None:
        """Generates all analytical charts and saves to docs/charts/."""
        print("Generating analytical visualizations...")
        self.plot_revenue_by_category()
        self.plot_monthly_revenue_trend()
        self.plot_regional_revenue()
        self.plot_customer_segment_distribution()
        self.plot_top_products()
        self.plot_category_return_rates()
        self.plot_cohort_retention_heatmap()
        self.plot_product_co_purchases()
        print(f"All 8 analytical charts successfully generated in {CHARTS_DIR}")

    def plot_revenue_by_category(self) -> None:
        """Chart 1: Revenue by Product Category."""
        query = """
        SELECT p.category_name, ROUND(SUM(l.line_total_usd), 2) AS net_revenue
        FROM fact_order_lines l
        JOIN dim_products p ON l.product_id = p.product_id
        JOIN fact_orders o ON l.order_id = o.order_id
        WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
        GROUP BY p.category_name
        ORDER BY net_revenue DESC
        """
        df = self.db.execute_query(query)

        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(df["category_name"], df["net_revenue"], color="#1f77b4", width=0.55, edgecolor="#0d3b66", linewidth=1.2)
        ax.set_title("Net Revenue by Product Category ($ USD)", fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Product Category", fontsize=11, labelpad=10)
        ax.set_ylabel("Net Revenue ($ USD)", fontsize=11)
        ax.yaxis.set_major_formatter("${x:,.0f}")
        plt.xticks(rotation=15, ha="right")

        for bar in bars:
            height = bar.get_height()
            ax.annotate(f"${height:,.2f}",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 5), textcoords="offset points",
                        ha="center", va="bottom", fontsize=9, fontweight="bold")

        plt.tight_layout()
        plt.savefig(CHARTS_DIR / "01_revenue_by_category.png", dpi=300)
        plt.close()

    def plot_monthly_revenue_trend(self) -> None:
        """Chart 2: Monthly Revenue & Order Volume Trends."""
        query = """
        SELECT 
            STRFTIME('%Y-%m', o.order_timestamp) AS order_month,
            COUNT(DISTINCT o.order_id) AS total_orders,
            ROUND(SUM(l.line_total_usd), 2) AS net_revenue
        FROM fact_orders o
        JOIN fact_order_lines l ON o.order_id = l.order_id
        WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
        GROUP BY STRFTIME('%Y-%m', o.order_timestamp)
        ORDER BY order_month ASC
        """
        df = self.db.execute_query(query)

        fig, ax1 = plt.subplots(figsize=(12, 6))

        color1 = "#2ca02c"
        ax1.set_xlabel("Order Month", fontsize=11, labelpad=10)
        ax1.set_ylabel("Net Revenue ($ USD)", color=color1, fontsize=11)
        line1 = ax1.plot(df["order_month"], df["net_revenue"], color=color1, marker="o", linewidth=2.5, label="Net Revenue ($)")
        ax1.tick_params(axis="y", labelcolor=color1)
        ax1.yaxis.set_major_formatter("${x:,.0f}")
        plt.xticks(rotation=45, ha="right")

        ax2 = ax1.twinx()
        color2 = "#ff7f0e"
        ax2.set_ylabel("Order Count", color=color2, fontsize=11)
        line2 = ax2.plot(df["order_month"], df["total_orders"], color=color2, marker="s", linestyle="--", linewidth=2, label="Order Count")
        ax2.tick_params(axis="y", labelcolor=color2)

        plt.title("Monthly Revenue & Order Volume Trajectory", fontsize=14, fontweight="bold", pad=15)
        fig.tight_layout()
        plt.savefig(CHARTS_DIR / "02_monthly_revenue_trend.png", dpi=300)
        plt.close()

    def plot_regional_revenue(self) -> None:
        """Chart 3: Regional Revenue Distribution."""
        query = """
        SELECT o.shipping_state, ROUND(SUM(l.line_total_usd), 2) AS regional_revenue
        FROM fact_orders o
        JOIN fact_order_lines l ON o.order_id = l.order_id
        WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
        GROUP BY o.shipping_state
        ORDER BY regional_revenue ASC
        """
        df = self.db.execute_query(query)

        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.barh(df["shipping_state"], df["regional_revenue"], color="#9467bd", height=0.6)
        ax.set_title("Regional Revenue Contribution by State ($ USD)", fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Net Revenue ($ USD)", fontsize=11)
        ax.xaxis.set_major_formatter("${x:,.0f}")

        for bar in bars:
            width = bar.get_width()
            ax.annotate(f"${width:,.2f}",
                        xy=(width, bar.get_y() + bar.get_height() / 2),
                        xytext=(5, 0), textcoords="offset points",
                        ha="left", va="center", fontsize=9)

        plt.tight_layout()
        plt.savefig(CHARTS_DIR / "03_regional_revenue_distribution.png", dpi=300)
        plt.close()

    def plot_customer_segment_distribution(self) -> None:
        """Chart 4: Customer Segment Distribution (RFM Donut Chart)."""
        rfm_df = self.cohort_analytics.compute_rfm_segmentation()
        segment_counts = rfm_df["rfm_segment"].value_counts()

        colors = ["#2b5c8f", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02"]
        fig, ax = plt.subplots(figsize=(8, 8))
        wedges, texts, autotexts = ax.pie(
            segment_counts,
            labels=segment_counts.index,
            autopct="%1.1f%%",
            startangle=140,
            colors=colors[: len(segment_counts)],
            wedgeprops=dict(width=0.4, edgecolor="w", linewidth=2),
        )

        plt.setp(autotexts, size=10, weight="bold", color="white")
        plt.setp(texts, size=11)
        ax.set_title("Customer Segmentation Distribution (RFM Analysis)", fontsize=14, fontweight="bold", pad=15)
        plt.tight_layout()
        plt.savefig(CHARTS_DIR / "04_customer_segment_distribution.png", dpi=300)
        plt.close()

    def plot_top_products(self) -> None:
        """Chart 5: Top 10 Products by Net Revenue."""
        query = """
        SELECT p.product_name, ROUND(SUM(l.line_total_usd), 2) AS product_revenue
        FROM dim_products p
        JOIN fact_order_lines l ON p.product_id = l.product_id
        JOIN fact_orders o ON l.order_id = o.order_id
        WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
        GROUP BY p.product_name
        ORDER BY product_revenue DESC
        LIMIT 10
        """
        df = self.db.execute_query(query).iloc[::-1]  # Reverse for top-to-bottom horizontal bar

        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.barh(df["product_name"], df["product_revenue"], color="#17becf", height=0.6)
        ax.set_title("Top 10 Products by Net Revenue ($ USD)", fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Net Revenue ($ USD)", fontsize=11)
        ax.xaxis.set_major_formatter("${x:,.0f}")

        for bar in bars:
            width = bar.get_width()
            ax.annotate(f"${width:,.2f}",
                        xy=(width, bar.get_y() + bar.get_height() / 2),
                        xytext=(5, 0), textcoords="offset points",
                        ha="left", va="center", fontsize=8, fontweight="bold")

        plt.tight_layout()
        plt.savefig(CHARTS_DIR / "05_top_products_performance.png", dpi=300)
        plt.close()

    def plot_category_return_rates(self) -> None:
        """Chart 6: Category Return Rates Percentage."""
        query = """
        SELECT 
            p.category_name,
            ROUND(
                (CAST(COALESCE(SUM(r.returned_qty), 0) AS REAL) / SUM(l.order_qty)) * 100.0, 
                2
            ) AS category_return_rate_pct
        FROM dim_products p
        JOIN fact_order_lines l ON p.product_id = l.product_id
        LEFT JOIN fact_returns r ON l.order_id = r.order_id AND l.product_id = r.product_id
        GROUP BY p.category_name
        ORDER BY category_return_rate_pct DESC
        """
        df = self.db.execute_query(query)

        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.bar(df["category_name"], df["category_return_rate_pct"], color="#d62728", width=0.5)
        ax.set_title("Return Rate Percentage by Product Category (%)", fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Product Category", fontsize=11, labelpad=10)
        ax.set_ylabel("Return Rate (%)", fontsize=11)
        plt.xticks(rotation=15, ha="right")

        for bar in bars:
            height = bar.get_height()
            ax.annotate(f"{height:.2f}%",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 5), textcoords="offset points",
                        ha="center", va="bottom", fontsize=10, fontweight="bold")

        plt.tight_layout()
        plt.savefig(CHARTS_DIR / "06_category_return_rates.png", dpi=300)
        plt.close()

    def plot_cohort_retention_heatmap(self) -> None:
        """Chart 7: Customer Cohort Retention Heatmap."""
        _, pct_df = self.cohort_analytics.generate_cohort_matrix()

        # Limit to first 6 retention months for clean visualization
        sub_pct = pct_df.iloc[:12, :6].fillna(0)

        fig, ax = plt.subplots(figsize=(11, 7))
        cax = ax.matshow(sub_pct, cmap="YlGnBu")
        fig.colorbar(cax)

        ax.set_xticks(range(len(sub_pct.columns)))
        ax.set_yticks(range(len(sub_pct.index)))
        ax.set_xticklabels([f"Month {c}" for c in sub_pct.columns])
        ax.set_yticklabels(sub_pct.index)

        plt.title("Customer Cohort Retention Rate (%) Heatmap", fontsize=14, fontweight="bold", pad=20)
        plt.xlabel("Months Since Registration", fontsize=11, labelpad=10)
        plt.ylabel("Signup Cohort Month", fontsize=11, labelpad=10)

        for i in range(len(sub_pct.index)):
            for j in range(len(sub_pct.columns)):
                val = sub_pct.iloc[i, j]
                ax.text(j, i, f"{val:.1f}%", ha="center", va="center", color="black" if val < 50 else "white", fontsize=8)

        plt.tight_layout()
        plt.savefig(CHARTS_DIR / "07_cohort_retention_heatmap.png", dpi=300)
        plt.close()

    def plot_product_co_purchases(self) -> None:
        """Chart 8: Top Product Co-Purchases."""
        query = """
        SELECT 
            (p1.product_name || ' + ' || p2.product_name) AS product_pair,
            COUNT(DISTINCT l1.order_id) AS co_purchase_count
        FROM fact_order_lines l1
        JOIN fact_order_lines l2 ON l1.order_id = l2.order_id AND l1.product_id < l2.product_id
        JOIN dim_products p1 ON l1.product_id = p1.product_id
        JOIN dim_products p2 ON l2.product_id = p2.product_id
        JOIN fact_orders o ON l1.order_id = o.order_id
        WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
        GROUP BY product_pair
        HAVING co_purchase_count >= 2
        ORDER BY co_purchase_count DESC
        LIMIT 8
        """
        df = self.db.execute_query(query).iloc[::-1]

        fig, ax = plt.subplots(figsize=(11, 6))
        bars = ax.barh(df["product_pair"], df["co_purchase_count"], color="#8c564b", height=0.55)
        ax.set_title("Top Frequently Co-Purchased Product Pairs in Single Orders", fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Co-Purchase Count (Orders)", fontsize=11)

        for bar in bars:
            width = bar.get_width()
            ax.annotate(f"{int(width)} orders",
                        xy=(width, bar.get_y() + bar.get_height() / 2),
                        xytext=(5, 0), textcoords="offset points",
                        ha="left", va="center", fontsize=9, fontweight="bold")

        plt.tight_layout()
        plt.savefig(CHARTS_DIR / "08_product_co_purchases.png", dpi=300)
        plt.close()


if __name__ == "__main__":
    viz = Visualizer()
    viz.generate_all_charts()
