-- ============================================================
-- Cross-System Reconciliation Views
-- Reconciles recognized billing revenue against daily analytics aggregates
-- ============================================================

CREATE OR REPLACE VIEW v_daily_revenue_reconciliation AS
WITH billing_daily AS (
    SELECT
        CAST(transaction_date AS DATE) AS date,
        SUM(amount) AS billing_revenue,
        COUNT(DISTINCT customer_id) AS billing_customers,
        COUNT(transaction_id) AS billing_tx_count
    FROM silver_billing
    WHERE status = 'completed'
    GROUP BY CAST(transaction_date AS DATE)
),
analytics_daily AS (
    SELECT
        CAST(date AS DATE) AS date,
        total_revenue AS analytics_revenue,
        total_customers AS analytics_customers
    FROM silver_analytics
)
SELECT
    COALESCE(b.date, a.date) AS date,
    COALESCE(b.billing_revenue, 0) AS billing_revenue,
    COALESCE(a.analytics_revenue, 0) AS analytics_revenue,
    ABS(COALESCE(b.billing_revenue, 0) - COALESCE(a.analytics_revenue, 0)) AS absolute_difference,
    CASE 
        WHEN COALESCE(a.analytics_revenue, 0) > 0 THEN
            ABS(COALESCE(b.billing_revenue, 0) - COALESCE(a.analytics_revenue, 0)) / a.analytics_revenue
        ELSE 0 
    END AS percentage_difference,
    b.billing_customers,
    a.analytics_customers,
    ABS(COALESCE(b.billing_customers, 0) - COALESCE(a.analytics_customers, 0)) AS customer_diff,
    CASE
        WHEN (
            CASE WHEN COALESCE(a.analytics_revenue, 0) > 0 THEN
                ABS(COALESCE(b.billing_revenue, 0) - COALESCE(a.analytics_revenue, 0)) / a.analytics_revenue
            ELSE 0 END
        ) > 0.10 THEN 'CRITICAL'
        WHEN (
            CASE WHEN COALESCE(a.analytics_revenue, 0) > 0 THEN
                ABS(COALESCE(b.billing_revenue, 0) - COALESCE(a.analytics_revenue, 0)) / a.analytics_revenue
            ELSE 0 END
        ) > 0.05 THEN 'HIGH'
        WHEN (
            CASE WHEN COALESCE(a.analytics_revenue, 0) > 0 THEN
                ABS(COALESCE(b.billing_revenue, 0) - COALESCE(a.analytics_revenue, 0)) / a.analytics_revenue
            ELSE 0 END
        ) > 0.02 THEN 'MEDIUM'
        ELSE 'OK'
    END AS threshold_status
FROM billing_daily b
FULL OUTER JOIN analytics_daily a ON b.date = a.date
ORDER BY date DESC;
