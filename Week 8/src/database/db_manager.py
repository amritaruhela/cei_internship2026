"""
OmniMarket Intelligence System (OMIS) - Database Manager
Handles SQLite connection lifecycle, schema initialization, data ingestion, and query execution.
"""

import os
import sqlite3
from typing import Dict, Union, Optional
import pandas as pd

from src.config import DB_PATH, SQL_DIR, CLEANED_DATA_DIR


class DatabaseManager:
    """Manages SQLite database creation, schema execution, and data loading."""

    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        """Establishes and returns SQLite connection with Foreign Keys enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def initialize_database(self) -> None:
        """Executes schema.sql to initialize database tables and indexes."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        schema_file = SQL_DIR / "schema.sql"

        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found at {schema_file}")

        with open(schema_file, "r", encoding="utf-8") as f:
            schema_script = f.read()

        with self.get_connection() as conn:
            conn.executescript(schema_script)
            conn.commit()

        print(f"Database schema initialized successfully at {self.db_path}")

    def load_cleaned_data(self) -> Dict[str, int]:
        """Loads cleaned CSV datasets into corresponding SQLite relational tables."""
        cust_df = pd.read_csv(CLEANED_DATA_DIR / "customers.csv")
        prod_df = pd.read_csv(CLEANED_DATA_DIR / "products.csv")
        orders_df = pd.read_csv(CLEANED_DATA_DIR / "orders.csv")
        lines_df = pd.read_csv(CLEANED_DATA_DIR / "order_lines.csv")
        returns_df = pd.read_csv(CLEANED_DATA_DIR / "returns.csv")

        # Map column names from CSV to SQL schema
        cust_mapped = cust_df.rename(columns={
            "customer_key": "customer_id",
            "customer_name": "full_name",
            "email": "email_address",
            "signup_date": "registration_date",
            "customer_segment": "account_tier",
            "city": "geo_city",
            "region": "geo_state",
            "acquisition_channel": "signup_channel",
        })

        prod_mapped = prod_df.rename(columns={
            "product_key": "product_id",
            "category": "category_name",
            "subcategory": "subcategory_name",
            "brand": "brand_tier",
            "unit_cost": "unit_cost_usd",
            "selling_price": "list_price_usd",
        })

        orders_mapped = orders_df.rename(columns={
            "order_key": "order_id",
            "customer_key": "customer_id",
            "order_status": "fulfillment_status",
            "payment_method": "payment_gateway",
            "shipping_region": "shipping_state",
        })

        lines_mapped = lines_df.rename(columns={
            "line_key": "line_item_id",
            "order_key": "order_id",
            "product_key": "product_id",
            "quantity": "order_qty",
            "unit_price": "unit_price_usd",
            "discount_pct": "discount_rate",
        })

        returns_mapped = returns_df.rename(columns={
            "return_key": "return_id",
            "order_key": "order_id",
            "product_key": "product_id",
            "return_date": "return_timestamp",
            "return_quantity": "returned_qty",
            "return_reason": "return_reason_code",
        })

        counts = {}
        with self.get_connection() as conn:
            cust_mapped.to_sql("dim_customers", conn, if_exists="append", index=False)
            counts["dim_customers"] = len(cust_mapped)

            prod_mapped.to_sql("dim_products", conn, if_exists="append", index=False)
            counts["dim_products"] = len(prod_mapped)

            orders_mapped.to_sql("fact_orders", conn, if_exists="append", index=False)
            counts["fact_orders"] = len(orders_mapped)

            lines_mapped.to_sql("fact_order_lines", conn, if_exists="append", index=False)
            counts["fact_order_lines"] = len(lines_mapped)

            returns_mapped.to_sql("fact_returns", conn, if_exists="append", index=False)
            counts["fact_returns"] = len(returns_mapped)

            conn.commit()

        print("Cleaned datasets loaded into SQLite relational tables:")
        for tbl, cnt in counts.items():
            print(f"  - {tbl}: {cnt} rows ingested")

        return counts

    def execute_query(self, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """Executes SQL query and returns results as a pandas DataFrame."""
        with self.get_connection() as conn:
            if params:
                return pd.read_sql_query(query, conn, params=params)
            return pd.read_sql_query(query, conn)

    def execute_sql_script(self, script_path: str) -> Dict[str, pd.DataFrame]:
        """Executes multi-statement SQL script separated by double hyphens or query titles."""
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"SQL file not found: {script_path}")

        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split queries by semicolon
        raw_queries = [q.strip() for q in content.split(";") if q.strip()]
        results = {}

        idx = 1
        with self.get_connection() as conn:
            for q in raw_queries:
                # Strip leading SQL comments
                clean_q_lines = [line for line in q.splitlines() if not line.strip().startswith("--")]
                clean_q = "\n".join(clean_q_lines).strip()

                if not clean_q:
                    continue

                if clean_q.upper().startswith("SELECT") or clean_q.upper().startswith("WITH"):
                    df = pd.read_sql_query(clean_q, conn)
                    results[f"query_{idx}"] = df
                    idx += 1
                else:
                    conn.execute(clean_q)

        return results


if __name__ == "__main__":
    db = DatabaseManager()
    db.initialize_database()
    db.load_cleaned_data()
