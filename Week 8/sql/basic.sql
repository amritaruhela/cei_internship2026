-- ============================================================
-- OmniMarket Intelligence System (OMIS) - Basic Analytics Suite
-- SQL Dialect: SQLite 3.x
-- ============================================================

-- ------------------------------------------------------------
-- 1. Revenue by Product Category
-- Business Objective: Determine high-performing product categories by total net revenue,
-- volume sold, and total discount impact.
-- ------------------------------------------------------------
SELECT 
    p.category_name,
    COUNT(DISTINCT l.order_id) AS total_orders_containing_cat,
    SUM(l.order_qty) AS total_units_sold,
    ROUND(SUM(l.order_qty * l.unit_price_usd), 2) AS gross_revenue_usd,
    ROUND(SUM(l.order_qty * l.unit_price_usd * l.discount_rate), 2) AS total_discounts_usd,
    ROUND(SUM(l.line_total_usd), 2) AS net_revenue_usd,
    ROUND(AVG(l.unit_price_usd), 2) AS avg_item_price_usd
FROM fact_order_lines l
JOIN dim_products p ON l.product_id = p.product_id
JOIN fact_orders o ON l.order_id = o.order_id
WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
GROUP BY p.category_name
ORDER BY net_revenue_usd DESC;

-- ------------------------------------------------------------
-- 2. Top Customers by Lifetime Purchase Value
-- Business Objective: Identify top 15 highest-value customers by net monetary contribution.
-- ------------------------------------------------------------
SELECT 
    c.customer_id,
    c.full_name,
    c.account_tier,
    c.geo_state,
    COUNT(DISTINCT o.order_id) AS completed_orders_count,
    ROUND(SUM(l.line_total_usd), 2) AS lifetime_net_spend_usd,
    ROUND(AVG(l.line_total_usd), 2) AS avg_line_item_spend_usd
FROM dim_customers c
JOIN fact_orders o ON c.customer_id = o.customer_id
JOIN fact_order_lines l ON o.order_id = l.order_id
WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
GROUP BY c.customer_id, c.full_name, c.account_tier, c.geo_state
ORDER BY lifetime_net_spend_usd DESC
LIMIT 15;

-- ------------------------------------------------------------
-- 3. Monthly Order and Revenue Trends
-- Business Objective: Track monthly volume trajectory, gross revenue, net revenue, and AOV.
-- ------------------------------------------------------------
SELECT 
    STRFTIME('%Y-%m', o.order_timestamp) AS order_month,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT o.customer_id) AS active_unique_customers,
    SUM(l.order_qty) AS units_shipped,
    ROUND(SUM(l.order_qty * l.unit_price_usd), 2) AS gross_revenue_usd,
    ROUND(SUM(l.line_total_usd), 2) AS net_revenue_usd,
    ROUND(SUM(l.line_total_usd) / COUNT(DISTINCT o.order_id), 2) AS average_order_value_usd
FROM fact_orders o
JOIN fact_order_lines l ON o.order_id = l.order_id
WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
GROUP BY STRFTIME('%Y-%m', o.order_timestamp)
ORDER BY order_month ASC;
