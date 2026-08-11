-- ============================================================
-- OmniMarket Intelligence System (OMIS) - Advanced SQL & Analytical Engine
-- SQL Dialect: SQLite 3.x
-- Advanced Window Functions, CTEs, Self-Joins & Cohort Analytics
-- ============================================================

-- ------------------------------------------------------------
-- 1. Running Total Revenue by Region
-- Window Function: SUM() OVER (PARTITION BY shipping_state ORDER BY order_timestamp)
-- Business Objective: Track cumulative regional revenue progression over time.
-- ------------------------------------------------------------
SELECT 
    o.order_id,
    o.shipping_state,
    o.order_timestamp,
    ROUND(SUM(l.line_total_usd), 2) AS order_revenue_usd,
    ROUND(
        SUM(SUM(l.line_total_usd)) OVER (
            PARTITION BY o.shipping_state 
            ORDER BY o.order_timestamp 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ), 
        2
    ) AS running_regional_revenue_usd
FROM fact_orders o
JOIN fact_order_lines l ON o.order_id = l.order_id
WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
GROUP BY o.order_id, o.shipping_state, o.order_timestamp
ORDER BY o.shipping_state, o.order_timestamp ASC
LIMIT 30;

-- ------------------------------------------------------------
-- 2. Product Ranking within Category using DENSE_RANK()
-- Window Function: DENSE_RANK() OVER (PARTITION BY category_name ORDER BY net_revenue DESC)
-- Business Objective: Identify top revenue generating products within each product category.
-- ------------------------------------------------------------
WITH ProductCategoryRevenue AS (
    SELECT 
        p.category_name,
        p.product_id,
        p.product_name,
        SUM(l.order_qty) AS units_sold,
        ROUND(SUM(l.line_total_usd), 2) AS product_net_revenue_usd
    FROM dim_products p
    JOIN fact_order_lines l ON p.product_id = l.product_id
    JOIN fact_orders o ON l.order_id = o.order_id
    WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
    GROUP BY p.category_name, p.product_id, p.product_name
)
SELECT 
    category_name,
    product_id,
    product_name,
    units_sold,
    product_net_revenue_usd,
    DENSE_RANK() OVER (
        PARTITION BY category_name 
        ORDER BY product_net_revenue_usd DESC
    ) AS category_revenue_rank
FROM ProductCategoryRevenue
ORDER BY category_name, category_revenue_rank ASC;

-- ------------------------------------------------------------
-- 3. Previous-Order Analysis using LAG()
-- Window Function: LAG(order_timestamp) OVER (PARTITION BY customer_id ORDER BY order_timestamp)
-- Business Objective: Calculate days elapsed between consecutive orders per customer.
-- ------------------------------------------------------------
WITH CustomerOrderSequence AS (
    SELECT 
        o.order_id,
        o.customer_id,
        c.full_name,
        o.order_timestamp,
        LAG(o.order_timestamp, 1) OVER (
            PARTITION BY o.customer_id 
            ORDER BY o.order_timestamp
        ) AS previous_order_timestamp,
        ROUND(SUM(l.line_total_usd), 2) AS order_total_usd
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_id = c.customer_id
    JOIN fact_order_lines l ON o.order_id = l.order_id
    WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
    GROUP BY o.order_id, o.customer_id, c.full_name, o.order_timestamp
)
SELECT 
    order_id,
    customer_id,
    full_name,
    order_timestamp,
    previous_order_timestamp,
    ROUND(
        JULIANDAY(order_timestamp) - JULIANDAY(previous_order_timestamp), 
        1
    ) AS days_since_previous_order,
    order_total_usd
FROM CustomerOrderSequence
WHERE previous_order_timestamp IS NOT NULL
ORDER BY customer_id, order_timestamp ASC
LIMIT 30;

-- ------------------------------------------------------------
-- 4. Customer Purchase Frequency & Repeat Purchasing Cadence
-- Business Objective: Compute average days between orders grouped by customer tier.
-- ------------------------------------------------------------
WITH OrderGaps AS (
    SELECT 
        c.account_tier,
        o.customer_id,
        o.order_timestamp,
        LAG(o.order_timestamp) OVER (
            PARTITION BY o.customer_id 
            ORDER BY o.order_timestamp
        ) AS prev_ts
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_id = c.customer_id
    WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
)
SELECT 
    account_tier,
    COUNT(DISTINCT customer_id) AS repeat_customers_count,
    ROUND(AVG(JULIANDAY(order_timestamp) - JULIANDAY(prev_ts)), 1) AS avg_days_between_orders
FROM OrderGaps
WHERE prev_ts IS NOT NULL
GROUP BY account_tier
ORDER BY avg_days_between_orders ASC;

-- ------------------------------------------------------------
-- 5. Customer Churn-Risk / Inactivity Identification
-- Business Objective: Identify active customers with no completed purchases in the last 120 days.
-- ------------------------------------------------------------
WITH MaxSystemDate AS (
    SELECT MAX(order_timestamp) AS max_dt FROM fact_orders
),
CustomerLastOrder AS (
    SELECT 
        c.customer_id,
        c.full_name,
        c.email_address,
        c.account_tier,
        MAX(o.order_timestamp) AS last_order_timestamp,
        SUM(l.line_total_usd) AS historical_spend
    FROM dim_customers c
    JOIN fact_orders o ON c.customer_id = o.customer_id
    JOIN fact_order_lines l ON o.order_id = l.order_id
    WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
    GROUP BY c.customer_id, c.full_name, c.email_address, c.account_tier
)
SELECT 
    clo.customer_id,
    clo.full_name,
    clo.email_address,
    clo.account_tier,
    clo.last_order_timestamp,
    ROUND(JULIANDAY(msd.max_dt) - JULIANDAY(clo.last_order_timestamp), 0) AS days_since_last_order,
    ROUND(clo.historical_spend, 2) AS lifetime_historical_spend_usd,
    CASE 
        WHEN JULIANDAY(msd.max_dt) - JULIANDAY(clo.last_order_timestamp) > 180 THEN 'High Churn Risk'
        WHEN JULIANDAY(msd.max_dt) - JULIANDAY(clo.last_order_timestamp) > 90 THEN 'Moderate Risk'
        ELSE 'Active'
    END AS churn_risk_segment
FROM CustomerLastOrder clo, MaxSystemDate msd
WHERE JULIANDAY(msd.max_dt) - JULIANDAY(clo.last_order_timestamp) > 90
ORDER BY days_since_last_order DESC
LIMIT 25;

-- ------------------------------------------------------------
-- 6. Monthly Customer RFM Segmentation using CTEs
-- Business Objective: Segment customers dynamically based on Recency, Frequency, and Monetary metrics.
-- ------------------------------------------------------------
WITH AnchorDate AS (
    SELECT MAX(order_timestamp) AS anchor_ts FROM fact_orders
),
CustomerRFM AS (
    SELECT 
        c.customer_id,
        c.full_name,
        ROUND(JULIANDAY(a.anchor_ts) - JULIANDAY(MAX(o.order_timestamp)), 0) AS recency_days,
        COUNT(DISTINCT o.order_id) AS frequency_count,
        ROUND(SUM(l.line_total_usd), 2) AS monetary_usd
    FROM dim_customers c
    JOIN fact_orders o ON c.customer_id = o.customer_id
    JOIN fact_order_lines l ON o.order_id = l.order_id
    CROSS JOIN AnchorDate a
    WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
    GROUP BY c.customer_id, c.full_name, a.anchor_ts
)
SELECT 
    customer_id,
    full_name,
    recency_days,
    frequency_count,
    monetary_usd,
    CASE 
        WHEN monetary_usd >= 1000 AND frequency_count >= 4 AND recency_days <= 60 THEN 'VIP Champion'
        WHEN monetary_usd >= 500 AND frequency_count >= 2 AND recency_days <= 90 THEN 'High Value Loyalist'
        WHEN recency_days <= 60 THEN 'Active Regular'
        WHEN recency_days > 120 THEN 'At Risk / Lapsed'
        ELSE 'Occasional Buyer'
    END AS rfm_segment
FROM CustomerRFM
ORDER BY monetary_usd DESC
LIMIT 30;

-- ------------------------------------------------------------
-- 7. NTILE Customer Spend Quartile Segmentation
-- Window Function: NTILE(4) OVER (ORDER BY lifetime_spend DESC)
-- Business Objective: Divide customer base into 4 equal spend quartiles for targeted marketing.
-- ------------------------------------------------------------
WITH CustomerSpend AS (
    SELECT 
        c.customer_id,
        c.full_name,
        c.account_tier,
        ROUND(SUM(l.line_total_usd), 2) AS total_spend_usd
    FROM dim_customers c
    JOIN fact_orders o ON c.customer_id = o.customer_id
    JOIN fact_order_lines l ON o.order_id = l.order_id
    WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
    GROUP BY c.customer_id, c.full_name, c.account_tier
)
SELECT 
    customer_id,
    full_name,
    account_tier,
    total_spend_usd,
    NTILE(4) OVER (ORDER BY total_spend_usd DESC) AS spend_quartile,
    CASE NTILE(4) OVER (ORDER BY total_spend_usd DESC)
        WHEN 1 THEN 'Top 25% (Q1 - High Spend)'
        WHEN 2 THEN '25%-50% (Q2 - Upper Mid)'
        WHEN 3 THEN '50%-75% (Q3 - Lower Mid)'
        WHEN 4 THEN '75%-100% (Q4 - Low Spend)'
    END AS quartile_label
FROM CustomerSpend
ORDER BY total_spend_usd DESC
LIMIT 30;

-- ------------------------------------------------------------
-- 8. Month-over-Month (MoM) Revenue Growth Comparison using LAG()
-- Window Function: LAG(net_revenue) OVER (ORDER BY order_month)
-- Business Objective: Calculate exact dollar and percentage monthly growth trends.
-- ------------------------------------------------------------
WITH MonthlyRevenue AS (
    SELECT 
        STRFTIME('%Y-%m', o.order_timestamp) AS order_month,
        ROUND(SUM(l.line_total_usd), 2) AS net_revenue_usd
    FROM fact_orders o
    JOIN fact_order_lines l ON o.order_id = l.order_id
    WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
    GROUP BY STRFTIME('%Y-%m', o.order_timestamp)
)
SELECT 
    order_month,
    net_revenue_usd,
    LAG(net_revenue_usd, 1) OVER (ORDER BY order_month) AS prev_month_revenue_usd,
    ROUND(
        net_revenue_usd - LAG(net_revenue_usd, 1) OVER (ORDER BY order_month), 
        2
    ) AS mom_growth_usd,
    ROUND(
        ( (net_revenue_usd - LAG(net_revenue_usd, 1) OVER (ORDER BY order_month)) / 
          LAG(net_revenue_usd, 1) OVER (ORDER BY order_month) ) * 100.0, 
        2
    ) AS mom_growth_percentage
FROM MonthlyRevenue
ORDER BY order_month ASC;

-- ------------------------------------------------------------
-- 9. First and Most Recent Product Purchased per Customer
-- Window Functions: FIRST_VALUE() and LAST_VALUE()
-- Business Objective: Understand customer product adoption journeys over time.
-- ------------------------------------------------------------
WITH DetailedOrders AS (
    SELECT 
        o.customer_id,
        c.full_name,
        p.product_name,
        p.category_name,
        o.order_timestamp,
        ROW_NUMBER() OVER (PARTITION BY o.customer_id ORDER BY o.order_timestamp ASC) AS asc_seq,
        ROW_NUMBER() OVER (PARTITION BY o.customer_id ORDER BY o.order_timestamp DESC) AS desc_seq
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_id = c.customer_id
    JOIN fact_order_lines l ON o.order_id = l.order_id
    JOIN dim_products p ON l.product_id = p.product_id
    WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
),
FirstPurchase AS (
    SELECT customer_id, full_name, product_name AS first_product, category_name AS first_category, order_timestamp AS first_order_ts
    FROM DetailedOrders WHERE asc_seq = 1
),
LatestPurchase AS (
    SELECT customer_id, product_name AS latest_product, category_name AS latest_category, order_timestamp AS latest_order_ts
    FROM DetailedOrders WHERE desc_seq = 1
)
SELECT 
    fp.customer_id,
    fp.full_name,
    fp.first_product,
    fp.first_category,
    fp.first_order_ts,
    lp.latest_product,
    lp.latest_category,
    lp.latest_order_ts
FROM FirstPurchase fp
JOIN LatestPurchase lp ON fp.customer_id = lp.customer_id
ORDER BY fp.first_order_ts ASC
LIMIT 25;

-- ------------------------------------------------------------
-- 10. Cumulative Customer Revenue Contribution & Pareto 80/20 Rule Analysis
-- Window Function: SUM() OVER (ORDER BY total_spend DESC)
-- Business Objective: Determine if top 20% of customers generate 80% of total revenue.
-- ------------------------------------------------------------
WITH CustomerSpend AS (
    SELECT 
        c.customer_id,
        c.full_name,
        SUM(l.line_total_usd) AS customer_spend
    FROM dim_customers c
    JOIN fact_orders o ON c.customer_id = o.customer_id
    JOIN fact_order_lines l ON o.order_id = l.order_id
    WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
    GROUP BY c.customer_id, c.full_name
),
TotalRevenue AS (
    SELECT SUM(customer_spend) AS grand_total FROM CustomerSpend
),
CumulativeSpend AS (
    SELECT 
        cs.customer_id,
        cs.full_name,
        cs.customer_spend,
        SUM(cs.customer_spend) OVER (ORDER BY cs.customer_spend DESC) AS cumulative_spend,
        tr.grand_total,
        ROW_NUMBER() OVER (ORDER BY cs.customer_spend DESC) AS customer_rank,
        (SELECT COUNT(*) FROM CustomerSpend) AS total_customer_count
    FROM CustomerSpend cs, TotalRevenue tr
)
SELECT 
    customer_id,
    full_name,
    ROUND(customer_spend, 2) AS customer_spend_usd,
    ROUND(cumulative_spend, 2) AS cumulative_spend_usd,
    ROUND((cumulative_spend / grand_total) * 100.0, 2) AS cumulative_revenue_pct,
    ROUND((CAST(customer_rank AS REAL) / total_customer_count) * 100.0, 2) AS customer_percentile
FROM CumulativeSpend
ORDER BY customer_spend DESC
LIMIT 30;

-- ------------------------------------------------------------
-- 11. Customer Cohort Retention Analysis Matrix
-- Business Objective: Group customers by signup month and calculate active retention count in Months 0, 1, 2, 3+.
-- ------------------------------------------------------------
WITH CustomerCohorts AS (
    SELECT 
        customer_id,
        STRFTIME('%Y-%m', registration_date) AS cohort_month
    FROM dim_customers
),
OrderActivity AS (
    SELECT DISTINCT
        o.customer_id,
        STRFTIME('%Y-%m', o.order_timestamp) AS activity_month
    FROM fact_orders o
    WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
),
CohortActivity AS (
    SELECT 
        c.cohort_month,
        a.activity_month,
        COUNT(DISTINCT c.customer_id) AS active_users,
        ( (CAST(STRFTIME('%Y', a.activity_month || '-01') AS INT) - CAST(STRFTIME('%Y', c.cohort_month || '-01') AS INT)) * 12 +
          (CAST(STRFTIME('%m', a.activity_month || '-01') AS INT) - CAST(STRFTIME('%m', c.cohort_month || '-01') AS INT))
        ) AS month_number
    FROM CustomerCohorts c
    JOIN OrderActivity a ON c.customer_id = a.customer_id
    WHERE a.activity_month >= c.cohort_month
    GROUP BY c.cohort_month, a.activity_month
),
CohortSizes AS (
    SELECT cohort_month, COUNT(customer_id) AS cohort_size
    FROM CustomerCohorts
    GROUP BY cohort_month
)
SELECT 
    cs.cohort_month,
    cs.cohort_size,
    SUM(CASE WHEN ca.month_number = 0 THEN ca.active_users ELSE 0 END) AS month_0_active,
    SUM(CASE WHEN ca.month_number = 1 THEN ca.active_users ELSE 0 END) AS month_1_active,
    SUM(CASE WHEN ca.month_number = 2 THEN ca.active_users ELSE 0 END) AS month_2_active,
    SUM(CASE WHEN ca.month_number >= 3 THEN ca.active_users ELSE 0 END) AS month_3_plus_active,
    ROUND( (CAST(SUM(CASE WHEN ca.month_number = 1 THEN ca.active_users ELSE 0 END) AS REAL) / cs.cohort_size) * 100.0, 1) AS month_1_retention_pct
FROM CohortSizes cs
LEFT JOIN CohortActivity ca ON cs.cohort_month = ca.cohort_month
GROUP BY cs.cohort_month, cs.cohort_size
ORDER BY cs.cohort_month ASC;

-- ------------------------------------------------------------
-- 12. Product Basket / Co-Purchase Self-Join Analysis
-- Self-Join: fact_order_lines l1 JOIN fact_order_lines l2 ON l1.order_id = l2.order_id AND l1.product_id < l2.product_id
-- Business Objective: Identify product pairs frequently purchased together in the same order.
-- ------------------------------------------------------------
SELECT 
    p1.product_name AS product_a,
    p1.category_name AS category_a,
    p2.product_name AS product_b,
    p2.category_name AS category_b,
    COUNT(DISTINCT l1.order_id) AS times_co_purchased,
    ROUND(SUM(l1.line_total_usd + l2.line_total_usd), 2) AS combined_co_purchase_revenue_usd
FROM fact_order_lines l1
JOIN fact_order_lines l2 ON l1.order_id = l2.order_id AND l1.product_id < l2.product_id
JOIN dim_products p1 ON l1.product_id = p1.product_id
JOIN dim_products p2 ON l2.product_id = p2.product_id
JOIN fact_orders o ON l1.order_id = o.order_id
WHERE o.fulfillment_status IN ('Delivered', 'Shipped')
GROUP BY p1.product_name, p1.category_name, p2.product_name, p2.category_name
HAVING times_co_purchased >= 2
ORDER BY times_co_purchased DESC, combined_co_purchase_revenue_usd DESC
LIMIT 20;
