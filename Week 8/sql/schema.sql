-- OmniMarket Intelligence System (OMIS) - Relational Database Schema
-- Target Engine: SQLite 3.x
-- Architecture: Star / Snowflake Relational Enterprise Data Model

-- Drop existing tables to ensure clean reproducibility
DROP TABLE IF EXISTS fact_returns;
DROP TABLE IF EXISTS fact_order_lines;
DROP TABLE IF EXISTS fact_orders;
DROP TABLE IF EXISTS dim_products;
DROP TABLE IF EXISTS dim_customers;

-- ============================================================
-- DIMENSION: CUSTOMERS
-- ============================================================
CREATE TABLE dim_customers (
    customer_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    email_address TEXT NOT NULL UNIQUE,
    registration_date TEXT NOT NULL,
    account_tier TEXT NOT NULL CHECK(account_tier IN ('Standard', 'Preferred', 'VIP', 'Enterprise')),
    geo_city TEXT NOT NULL,
    geo_state TEXT NOT NULL,
    signup_channel TEXT NOT NULL,
    is_active INTEGER NOT NULL CHECK(is_active IN (0, 1))
);

-- ============================================================
-- DIMENSION: PRODUCTS
-- ============================================================
CREATE TABLE dim_products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category_name TEXT NOT NULL,
    subcategory_name TEXT NOT NULL,
    brand_tier TEXT NOT NULL,
    unit_cost_usd REAL NOT NULL CHECK(unit_cost_usd > 0),
    list_price_usd REAL NOT NULL CHECK(list_price_usd > 0)
);

-- ============================================================
-- FACT TABLE: ORDERS
-- ============================================================
CREATE TABLE fact_orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    order_timestamp TEXT NOT NULL,
    fulfillment_status TEXT NOT NULL CHECK(fulfillment_status IN ('Delivered', 'Shipped', 'Processing', 'Cancelled', 'Returned')),
    payment_gateway TEXT NOT NULL,
    shipping_state TEXT NOT NULL,
    fulfillment_center TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id) ON DELETE CASCADE
);

-- ============================================================
-- FACT TABLE: ORDER LINES
-- ============================================================
CREATE TABLE fact_order_lines (
    line_item_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    order_qty INTEGER NOT NULL CHECK(order_qty > 0),
    unit_price_usd REAL NOT NULL CHECK(unit_price_usd > 0),
    discount_rate REAL NOT NULL CHECK(discount_rate >= 0.0 AND discount_rate <= 0.50),
    line_total_usd REAL NOT NULL CHECK(line_total_usd >= 0.0),
    FOREIGN KEY (order_id) REFERENCES fact_orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES dim_products(product_id) ON DELETE RESTRICT
);

-- ============================================================
-- FACT TABLE: RETURNS
-- ============================================================
CREATE TABLE fact_returns (
    return_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    return_timestamp TEXT NOT NULL,
    returned_qty INTEGER NOT NULL CHECK(returned_qty > 0),
    return_reason_code TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES fact_orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES dim_products(product_id) ON DELETE RESTRICT
);

-- ============================================================
-- INDEXES FOR QUERY OPTIMIZATION & JOIN ACCELERATION
-- ============================================================
CREATE INDEX idx_orders_customer_id ON fact_orders(customer_id);
CREATE INDEX idx_orders_timestamp ON fact_orders(order_timestamp);
CREATE INDEX idx_orders_status ON fact_orders(fulfillment_status);
CREATE INDEX idx_order_lines_order_id ON fact_order_lines(order_id);
CREATE INDEX idx_order_lines_product_id ON fact_order_lines(product_id);
CREATE INDEX idx_returns_order_id ON fact_returns(order_id);
CREATE INDEX idx_returns_product_id ON fact_returns(product_id);
CREATE INDEX idx_products_category ON dim_products(category_name);
CREATE INDEX idx_customers_tier ON dim_customers(account_tier);
