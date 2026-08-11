-- ============================================================
-- Seed Quality Rules Data
-- ============================================================

INSERT INTO quality_rules (id, rule_id, source, column_name, rule_type, description, threshold, severity, enabled)
VALUES
  (gen_random_uuid()::text, 'DQ-B001', 'billing', 'amount', 'completeness', 'Billing transaction amount must not be null', 0.98, 'HIGH', true),
  (gen_random_uuid()::text, 'DQ-B002', 'billing', 'transaction_id', 'uniqueness', 'Transaction IDs must be unique', 0.999, 'CRITICAL', true),
  (gen_random_uuid()::text, 'DQ-B003', 'billing', 'customer_id', 'referential', 'Billing customer_id must exist in CRM (GHOST IDs flag violation)', 0.995, 'HIGH', true),
  (gen_random_uuid()::text, 'DQ-A001', 'analytics', 'total_revenue', 'completeness', 'Analytics daily total revenue must not be null', 0.98, 'MEDIUM', true),
  (gen_random_uuid()::text, 'DQ-A002', 'analytics', 'date', 'uniqueness', 'Analytics dates must be unique (1 row per day)', 1.0, 'HIGH', true),
  (gen_random_uuid()::text, 'DQ-C001', 'crm', 'customer_id', 'uniqueness', 'CRM customer_id must be unique', 1.0, 'CRITICAL', true),
  (gen_random_uuid()::text, 'DQ-C002', 'crm', 'email', 'completeness', 'CRM customer email completeness', 0.95, 'MEDIUM', true),
  (gen_random_uuid()::text, 'DQ-R001', 'reconciliation', 'revenue', 'reconciliation', 'Daily revenue variance between Billing and Analytics must be < 5%', 0.05, 'CRITICAL', true)
ON CONFLICT (rule_id) DO UPDATE SET
  description = EXCLUDED.description,
  threshold = EXCLUDED.threshold,
  severity = EXCLUDED.severity,
  updated_at = CURRENT_TIMESTAMP;
