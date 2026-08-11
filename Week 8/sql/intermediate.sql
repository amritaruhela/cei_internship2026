-- ============================================================
-- OmniMarket Intelligence System (OMIS) - Intermediate Analytics Suite
-- SQL Dialect: SQLite 3.x
-- ============================================================

-- ------------------------------------------------------------
-- 4. Customers with Orders but No Completed Purchase (Friction Analysis)
-- Business Objective: Identify customer accounts with order activity but ZERO completed
-- purchases (all orders cancelled or returned), signaling onboarding friction or cart abandonment.
-- ------------------------------------------------------------
SELECT 
    c.customer_id,
    c.full_name,
    c.email_address,
    c.account_tier,
    c.registration_date,
    COUNT(o.order_id) AS total_attempted_orders,
    SUM(CASE WHEN o.fulfillment_status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled_orders,
    SUM(CASE WHEN o.fulfillment_status = 'Returned' THEN 1 ELSE 0 END) AS returned_orders
FROM dim_customers c
JOIN fact_orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.full_name, c.email_address, c.account_tier, c.registration_date
HAVING SUM(CASE WHEN o.fulfillment_status IN ('Delivered', 'Shipped') THEN 1 ELSE 0 END) = 0
ORDER BY total_attempted_orders DESC;

-- ------------------------------------------------------------
-- 5. Products with Unusually High Return Quantities
-- Business Objective: Identify top products suffering from high physical return counts
-- and return rates (>10% return-to-sales ratio) to investigate quality control defects.
-- ------------------------------------------------------------
SELECT 
    p.product_id,
    p.product_name,
    p.category_name,
    p.brand_tier,
    COALESCE(SUM(l.order_qty), 0) AS total_units_ordered,
    COALESCE(SUM(r.returned_qty), 0) AS total_units_returned,
    ROUND(
        (CAST(COALESCE(SUM(r.returned_qty), 0) AS REAL) / NULLIF(SUM(l.order_qty), 0)) * 100.0, 
        2
    ) AS return_rate_percentage
FROM dim_products p
JOIN fact_order_lines l ON p.product_id = l.product_id
LEFT JOIN fact_returns r ON l.order_id = r.order_id AND l.product_id = r.product_id
GROUP BY p.product_id, p.product_name, p.category_name, p.brand_tier
HAVING total_units_returned > 0 AND return_rate_percentage >= 5.0
ORDER BY total_units_returned DESC, return_rate_percentage DESC;

-- ------------------------------------------------------------
-- 6. Return Rate and Refund Value Impact by Product Category
-- Business Objective: Compute category-level return percentages and financial impact.
-- ------------------------------------------------------------
SELECT 
    p.category_name,
    SUM(l.order_qty) AS gross_units_ordered,
    COALESCE(SUM(r.returned_qty), 0) AS units_returned,
    ROUND(
        (CAST(COALESCE(SUM(r.returned_qty), 0) AS REAL) / SUM(l.order_qty)) * 100.0, 
        2
    ) AS category_return_rate_pct,
    ROUND(SUM(l.line_total_usd), 2) AS gross_category_revenue_usd,
    ROUND(COALESCE(SUM(r.returned_qty * l.unit_price_usd * (1 - l.discount_rate)), 0), 2) AS estimated_refund_value_usd
FROM dim_products p
JOIN fact_order_lines l ON p.product_id = l.product_id
LEFT JOIN fact_returns r ON l.order_id = r.order_id AND l.product_id = r.product_id
GROUP BY p.category_name
ORDER BY category_return_rate_pct DESC;

-- ------------------------------------------------------------
-- 7. Average Order Value (AOV) and Frequency by Customer Segment (Tier)
-- Business Objective: Validate tier monetization strategies across Standard, Preferred, VIP, and Enterprise.
-- ------------------------------------------------------------
SELECT 
    c.account_tier,
    COUNT(DISTINCT c.customer_id) AS total_tier_customers,
    COUNT(DISTINCT o.order_id) AS total_tier_orders,
    ROUND(CAST(COUNT(DISTINCT o.order_id) AS REAL) / COUNT(DISTINCT c.customer_id), 2) AS avg_orders_per_customer,
    ROUND(SUM(l.line_total_usd), 2) AS total_tier_net_revenue_usd,
    ROUND(SUM(l.line_total_usd) / COUNT(DISTINCT o.order_id), 2) AS average_order_value_aov_usd
FROM dim_customers c
JOIN fact_orders o ON c.customer_id = o.customer_id
JOIN fact_order_lines l ON o.order_id = l.order_id
WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
GROUP BY c.account_tier
ORDER BY average_order_value_aov_usd DESC;

-- ------------------------------------------------------------
-- 8. Regional Revenue Contribution & Percentage Share
-- Business Objective: Analyze revenue distribution by state/region and evaluate percentage market share.
-- ------------------------------------------------------------
WITH RegionalTotals AS (
    SELECT 
        o.shipping_state,
        COUNT(DISTINCT o.order_id) AS regional_orders,
        SUM(l.line_total_usd) AS regional_net_revenue
    FROM fact_orders o
    JOIN fact_order_lines l ON o.order_id = l.order_id
    WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
    GROUP BY o.shipping_state
),
OverallTotal AS (
    SELECT SUM(regional_net_revenue) AS grand_total_revenue FROM RegionalTotals
)
SELECT 
    r.shipping_state,
    r.regional_orders,
    ROUND(r.regional_net_revenue, 2) AS regional_net_revenue_usd,
    ROUND((r.regional_net_revenue / o.grand_total_revenue) * 100.0, 2) AS revenue_share_percentage
FROM RegionalTotals r, OverallTotal o
ORDER BY regional_net_revenue_usd DESC;
