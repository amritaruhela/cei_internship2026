"""
OmniMarket Intelligence System (OMIS) - Synthetic Data Generator
Generates realistic marketplace datasets with controlled, documented data-quality anomalies.
"""

import os
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from src.config import (
    RAW_DATA_DIR,
    RANDOM_SEED,
    NUM_CUSTOMERS,
    NUM_PRODUCTS,
    NUM_ORDERS,
    NUM_ORDER_LINES,
    NUM_RETURNS,
    VALID_TIERS,
    VALID_CHANNELS,
    VALID_ORDER_STATUSES,
    VALID_PAYMENT_METHODS,
    VALID_FULFILLMENT_CENTERS,
    VALID_RETURN_REASONS,
)


class DataGenerator:
    """Generates synthetic e-commerce marketplace data with intentional errors for DQ validation."""

    def __init__(self, seed: int = RANDOM_SEED):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        random.seed(seed)

        # Reference taxonomies
        self.categories_map = {
            "Consumer Electronics": {
                "subcategories": ["Smartphones", "Laptops", "Audio & Headphones", "Wearables", "Accessories"],
                "brands": ["TechPulse", "AuraSound", "NexusGear", "VoltEdge", "ApexTech"],
                "price_range": (19.99, 1499.99),
            },
            "Home & Kitchen": {
                "subcategories": ["Cookware", "Small Appliances", "Home Decor", "Bedding", "Storage"],
                "brands": ["ChefMaster", "LuminaHome", "CozyNest", "PureCraft", "ArtisanLiving"],
                "price_range": (14.99, 499.99),
            },
            "Apparel & Footwear": {
                "subcategories": ["Men's Wear", "Women's Wear", "Athletic Shoes", "Outerwear", "Fashion Accessories"],
                "brands": ["UrbanStitch", "AeroStyle", "VerveFit", "NordicThread", "ZenithAttire"],
                "price_range": (12.50, 249.99),
            },
            "Books & Media": {
                "subcategories": ["Fiction", "Non-Fiction", "Technical & Engineering", "Self-Help", "Children's Books"],
                "brands": ["ApexPublishing", "BeaconPress", "InsightBooks", "OmniReads", "ScholarHouse"],
                "price_range": (8.99, 119.99),
            },
            "Health & Personal Care": {
                "subcategories": ["Skincare", "Vitamins & Supplements", "Hair Care", "Fitness Equipment", "Personal Hygiene"],
                "brands": ["GlowBotanic", "VitalityPlus", "PureSilk", "FlexFit", "RadiantSkin"],
                "price_range": (9.99, 199.99),
            },
        }

        self.cities_states = [
            ("New York", "NY"), ("Los Angeles", "CA"), ("Chicago", "IL"),
            ("Houston", "TX"), ("Phoenix", "AZ"), ("Philadelphia", "PA"),
            ("San Antonio", "TX"), ("San Diego", "CA"), ("Dallas", "TX"),
            ("San Jose", "CA"), ("Austin", "TX"), ("Jacksonville", "FL"),
            ("Fort Worth", "TX"), ("Columbus", "OH"), ("Charlotte", "NC"),
            ("San Francisco", "CA"), ("Indianapolis", "IN"), ("Seattle", "WA"),
            ("Denver", "CO"), ("Washington", "DC"), ("Boston", "MA"),
            ("Miami", "FL"), ("Atlanta", "GA"), ("Detroit", "MI")
        ]

        self.first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Dakota",
                           "Reese", "Quinn", "Skyler", "Cameron", "Sam", "Peyton", "Hayden", "Kendall",
                           "Harper", "Rowan", "Emerson", "Finley", "Adrian", "Logan", "Sawyer", "Elliot"]
        self.last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
                          "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
                          "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White"]

    def generate_all(self):
        """Executes full synthetic dataset generation and saves raw CSV files."""
        os.makedirs(RAW_DATA_DIR, exist_ok=True)
        print("Starting synthetic data generation...")

        df_cust = self.generate_customers()
        df_prod = self.generate_products()
        df_orders = self.generate_orders(df_cust)
        df_lines = self.generate_order_lines(df_orders, df_prod)
        df_returns = self.generate_returns(df_orders, df_lines)

        df_cust.to_csv(RAW_DATA_DIR / "customers.csv", index=False)
        df_prod.to_csv(RAW_DATA_DIR / "products.csv", index=False)
        df_orders.to_csv(RAW_DATA_DIR / "orders.csv", index=False)
        df_lines.to_csv(RAW_DATA_DIR / "order_lines.csv", index=False)
        df_returns.to_csv(RAW_DATA_DIR / "returns.csv", index=False)

        print(f"Data Generation Completed successfully:")
        print(f"  - Customers: {len(df_cust)} rows saved to customers.csv")
        print(f"  - Products: {len(df_prod)} rows saved to products.csv")
        print(f"  - Orders: {len(df_orders)} rows saved to orders.csv")
        print(f"  - Order Lines: {len(df_lines)} rows saved to order_lines.csv")
        print(f"  - Returns: {len(df_returns)} rows saved to returns.csv")

    def generate_customers(self) -> pd.DataFrame:
        """Generates raw customers dataset with intentional errors."""
        customers = []
        start_date = datetime(2024, 1, 1)

        for i in range(1, NUM_CUSTOMERS + 1):
            cust_id = f"CUST-{i:06d}"
            fn = random.choice(self.first_names)
            ln = random.choice(self.last_names)
            full_name = f"{fn} {ln}"

            # Standard valid email
            domain = random.choice(["gmail.com", "yahoo.com", "outlook.com", "icloud.com", "enterprise.org"])
            email = f"{fn.lower()}.{ln.lower()}{random.randint(10, 999)}@{domain}"

            # Signup date
            days_offset = random.randint(0, 700)
            signup_dt = (start_date + timedelta(days=days_offset)).strftime("%Y-%m-%d")

            # Account tier distribution
            tier = self.rng.choice(VALID_TIERS, p=[0.60, 0.25, 0.10, 0.05])
            city, state = random.choice(self.cities_states)
            channel = random.choice(VALID_CHANNELS)
            is_active = random.choice([1, 1, 1, 1, 0])  # 80% active

            customers.append({
                "customer_key": cust_id,
                "customer_name": full_name,
                "email": email,
                "signup_date": signup_dt,
                "customer_segment": tier,
                "city": city,
                "region": state,
                "acquisition_channel": channel,
                "is_active": is_active,
            })

        df = pd.DataFrame(customers)

        # Inject controlled DQ Anomalies
        # 1. Invalid emails (~30)
        invalid_email_indices = self.rng.choice(df.index, size=30, replace=False)
        bad_email_formats = [
            "missing_at_symbol.com",
            "double@@atdomain.com",
            "invalid_user@domain..com",
            "plainaddress_no_tld@",
            "user@.invalid_tld",
        ]
        for idx in invalid_email_indices:
            df.loc[idx, "email"] = random.choice(bad_email_formats)

        # 2. Whitespace & Capitalization (~25)
        ws_indices = self.rng.choice(df.index, size=25, replace=False)
        for idx in ws_indices:
            name = df.loc[idx, "customer_name"]
            df.loc[idx, "customer_name"] = f"  {name.swapcase()}  "
            df.loc[idx, "city"] = f" {df.loc[idx, 'city'].lower()} "

        # 3. Missing/Null region or city (~15)
        null_indices = self.rng.choice(df.index, size=15, replace=False)
        for idx in null_indices:
            df.loc[idx, "region"] = None
            df.loc[idx, "city"] = ""

        # 4. Duplicate customer keys (~10)
        dup_indices = self.rng.choice(df.index, size=10, replace=False)
        for idx in dup_indices:
            df.loc[idx, "customer_key"] = f"CUST-{(idx % 50) + 1:06d}"

        return df

    def generate_products(self) -> pd.DataFrame:
        """Generates raw products dataset with intentional errors."""
        products = []
        prod_counter = 1

        for cat, info in self.categories_map.items():
            subcats = info["subcategories"]
            brands = info["brands"]
            min_p, max_p = info["price_range"]

            items_per_cat = NUM_PRODUCTS // len(self.categories_map)
            for _ in range(items_per_cat):
                prod_id = f"PROD-{prod_counter:06d}"
                subcat = random.choice(subcats)
                brand = random.choice(brands)
                prod_name = f"{brand} {subcat} {random.choice(['Pro', 'Max', 'Lite', 'Plus', 'Ultra', 'Standard'])} {random.randint(100, 999)}"

                selling_price = round(random.uniform(min_p, max_p), 2)
                margin = random.uniform(0.30, 0.65)
                unit_cost = round(selling_price * (1 - margin), 2)

                products.append({
                    "product_key": prod_id,
                    "product_name": prod_name,
                    "category": cat,
                    "subcategory": subcat,
                    "brand": brand,
                    "unit_cost": unit_cost,
                    "selling_price": selling_price,
                })
                prod_counter += 1

        df = pd.DataFrame(products)

        # Inject controlled DQ Anomalies
        # 1. Invalid/negative prices or zero prices (~15)
        bad_price_idx = self.rng.choice(df.index, size=15, replace=False)
        for idx in bad_price_idx:
            if random.random() > 0.5:
                df.loc[idx, "selling_price"] = -round(random.uniform(10, 100), 2)
            else:
                df.loc[idx, "selling_price"] = 0.00
                df.loc[idx, "unit_cost"] = 45.00  # Cost exceeds selling price

        # 2. Duplicate product keys (~10)
        dup_idx = self.rng.choice(df.index, size=10, replace=False)
        for idx in dup_idx:
            df.loc[idx, "product_key"] = f"PROD-{(idx % 30) + 1:06d}"

        # 3. Missing subcategory (~15)
        null_subcat_idx = self.rng.choice(df.index, size=15, replace=False)
        for idx in null_subcat_idx:
            df.loc[idx, "subcategory"] = None

        return df

    def generate_orders(self, df_customers: pd.DataFrame) -> pd.DataFrame:
        """Generates raw orders dataset with intentional errors."""
        orders = []
        valid_cust_ids = df_customers["customer_key"].unique().tolist()
        start_date = datetime(2024, 2, 1)

        for i in range(1, NUM_ORDERS + 1):
            order_id = f"ORD-{i:06d}"
            cust_id = random.choice(valid_cust_ids)

            days_offset = random.randint(0, 900)
            order_dt = start_date + timedelta(days=days_offset, hours=random.randint(0, 23), minutes=random.randint(0, 59))
            order_ts = order_dt.strftime("%Y-%m-%d %H:%M:%S")

            status = self.rng.choice(VALID_ORDER_STATUSES, p=[0.72, 0.12, 0.06, 0.05, 0.05])
            pmt = random.choice(VALID_PAYMENT_METHODS)
            fc = random.choice(VALID_FULFILLMENT_CENTERS)
            state = random.choice(["NY", "CA", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "WA", "CO", "MI"])

            orders.append({
                "order_key": order_id,
                "customer_key": cust_id,
                "order_timestamp": order_ts,
                "order_status": status,
                "payment_method": pmt,
                "shipping_region": state,
                "fulfillment_center": fc,
            })

        df = pd.DataFrame(orders)

        # Inject controlled DQ Anomalies
        # 1. Foreign Key Orphans (~35) - Non-existent customer keys
        orphan_idx = self.rng.choice(df.index, size=35, replace=False)
        for idx in orphan_idx:
            df.loc[idx, "customer_key"] = f"CUST-99{random.randint(100, 999):04d}"

        # 2. Invalid timestamps/future dates (~20)
        bad_date_idx = self.rng.choice(df.index, size=20, replace=False)
        for idx in bad_date_idx:
            if random.random() > 0.5:
                df.loc[idx, "order_timestamp"] = "2029-12-31 23:59:59"  # Future date
            else:
                df.loc[idx, "order_timestamp"] = "99-99-9999 INVALID"  # Malformed date string

        # 3. Invalid order status codes (~15)
        bad_status_idx = self.rng.choice(df.index, size=15, replace=False)
        for idx in bad_status_idx:
            df.loc[idx, "order_status"] = random.choice(["UNKNOWN_STATE", "DISPATCH_ERROR", "PENDING_CHECK"])

        return df

    def generate_order_lines(self, df_orders: pd.DataFrame, df_products: pd.DataFrame) -> pd.DataFrame:
        """Generates raw order_lines dataset with intentional errors."""
        order_lines = []
        valid_order_ids = df_orders["order_key"].unique().tolist()
        prod_info = df_products.set_index("product_key")["selling_price"].to_dict()
        valid_prod_ids = list(prod_info.keys())

        line_counter = 1
        lines_per_order = max(1, NUM_ORDER_LINES // len(valid_order_ids))

        for ord_id in valid_order_ids:
            num_items = random.randint(1, lines_per_order + 2)
            chosen_prods = random.sample(valid_prod_ids, min(num_items, len(valid_prod_ids)))

            for prod_id in chosen_prods:
                if line_counter > NUM_ORDER_LINES:
                    break
                line_id = f"LINE-{line_counter:07d}"
                unit_price = prod_info.get(prod_id, 29.99)
                qty = self.rng.choice([1, 2, 3, 4, 5], p=[0.55, 0.25, 0.10, 0.06, 0.04])
                discount = round(random.choice([0.0, 0.0, 0.0, 0.05, 0.10, 0.15, 0.20, 0.25]), 2)

                order_lines.append({
                    "line_key": line_id,
                    "order_key": ord_id,
                    "product_key": prod_id,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "discount_pct": discount,
                })
                line_counter += 1

        df = pd.DataFrame(order_lines)

        # Inject controlled DQ Anomalies
        # 1. Zero/Negative quantities (~45)
        bad_qty_idx = self.rng.choice(df.index, size=45, replace=False)
        for idx in bad_qty_idx:
            df.loc[idx, "quantity"] = random.choice([0, -1, -2, -5])

        # 2. Invalid discounts > 1.0 or < 0 (~30)
        bad_disc_idx = self.rng.choice(df.index, size=30, replace=False)
        for idx in bad_disc_idx:
            df.loc[idx, "discount_pct"] = random.choice([1.50, 2.00, -0.25, 9.99])

        # 3. Missing product references / Orphans (~25)
        orphan_prod_idx = self.rng.choice(df.index, size=25, replace=False)
        for idx in orphan_prod_idx:
            df.loc[idx, "product_key"] = f"PROD-99{random.randint(100, 999):04d}"

        # 4. Duplicate line keys (~12)
        dup_line_idx = self.rng.choice(df.index, size=12, replace=False)
        for idx in dup_line_idx:
            df.loc[idx, "line_key"] = f"LINE-{(idx % 50) + 1:07d}"

        return df

    def generate_returns(self, df_orders: pd.DataFrame, df_lines: pd.DataFrame) -> pd.DataFrame:
        """Generates raw returns dataset with intentional errors."""
        returns = []

        # Find eligible order lines
        merged = df_lines.merge(df_orders[["order_key", "order_timestamp", "order_status"]], on="order_key")
        eligible_lines = merged[merged["order_status"].isin(["Delivered", "Returned"])].copy()

        return_counter = 1
        sample_lines = eligible_lines.sample(n=min(NUM_RETURNS, len(eligible_lines)), random_state=self.seed)

        for _, row in sample_lines.iterrows():
            return_id = f"RET-{return_counter:06d}"
            ord_id = row["order_key"]
            prod_id = row["product_key"]
            purchased_qty = row["quantity"]

            # Return timestamp 1 to 20 days after order timestamp
            try:
                ord_dt = datetime.strptime(str(row["order_timestamp"]), "%Y-%m-%d %H:%M:%S")
            except Exception:
                ord_dt = datetime(2025, 1, 1)

            ret_dt = ord_dt + timedelta(days=random.randint(1, 20), hours=random.randint(1, 12))
            ret_ts = ret_dt.strftime("%Y-%m-%d %H:%M:%S")

            ret_qty = min(purchased_qty, random.randint(1, max(1, purchased_qty)))
            reason = random.choice(VALID_RETURN_REASONS)

            returns.append({
                "return_key": return_id,
                "order_key": ord_id,
                "product_key": prod_id,
                "return_date": ret_ts,
                "return_quantity": ret_qty,
                "return_reason": reason,
            })
            return_counter += 1

        df = pd.DataFrame(returns)

        # Inject controlled DQ Anomalies
        # 1. Return timestamp BEFORE order timestamp (~20)
        bad_date_idx = self.rng.choice(df.index, size=20, replace=False)
        for idx in bad_date_idx:
            df.loc[idx, "return_date"] = "2023-01-01 00:00:00"  # Precedes any order

        # 2. Returned quantity exceeds purchased quantity (~15)
        bad_qty_idx = self.rng.choice(df.index, size=15, replace=False)
        for idx in bad_qty_idx:
            df.loc[idx, "return_quantity"] = 999  # Unrealistic returned qty

        # 3. Invalid returns for non-existent order keys (~30)
        bad_ord_idx = self.rng.choice(df.index, size=30, replace=False)
        for idx in bad_ord_idx:
            df.loc[idx, "order_key"] = f"ORD-99{random.randint(100, 999):04d}"

        return df


if __name__ == "__main__":
    generator = DataGenerator()
    generator.generate_all()
