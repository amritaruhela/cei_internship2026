import axios from 'axios';
import {
  DashboardSummary,
  Alert,
  TrustScoreResponse,
  DriftResult,
  DataQualityMetric,
  ComparisonResult,
  PipelineRun,
  QualityRule,
} from '../types';

const API_BASE = '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const fetchDashboardSummary = async (): Promise<DashboardSummary> => {
  try {
    const res = await api.get('/dashboard/summary');
    return res.data;
  } catch (error) {
    console.warn('Backend unavailable, using rich mock summary data');
    return {
      platform_trust_score: 84.5,
      healthy_sources: 2,
      warning_sources: 1,
      critical_sources: 0,
      total_alerts: 12,
      open_alerts: 5,
      critical_alerts: 1,
      high_alerts: 3,
      pipeline_success_rate: 96.2,
      last_pipeline_run: new Date().toISOString(),
      sources: [
        {
          source_system: 'billing',
          overall_score: 82.4,
          grade: 'B',
          health_status: 'WARNING',
          completeness: 98.5,
          consistency: 82.0,
          accuracy: 85.0,
          freshness: 100.0,
          uniqueness: 97.0,
          drift_stability: 78.0,
          components: {
            completeness: 98.5,
            consistency: 82.0,
            accuracy: 85.0,
            freshness: 100.0,
            uniqueness: 97.0,
            drift_stability: 78.0,
          },
          explanations: [
            'Score reduced by 8.0 pts: 18 GHOST customer_ids detected in Billing with no CRM parent',
            'Score reduced by 5.2 pts: Billing revenue differs from Analytics by 4.2%',
            'Volume drop detected (-22% vs 30-day baseline)',
          ],
        },
        {
          source_system: 'analytics',
          overall_score: 91.0,
          grade: 'A',
          health_status: 'HEALTHY',
          completeness: 95.0,
          consistency: 98.0,
          accuracy: 92.0,
          freshness: 100.0,
          uniqueness: 100.0,
          drift_stability: 95.0,
          components: {
            completeness: 95.0,
            consistency: 98.0,
            accuracy: 92.0,
            freshness: 100.0,
            uniqueness: 100.0,
            drift_stability: 95.0,
          },
          explanations: ['17 rows have NULL total_revenue (completeness violation)'],
        },
        {
          source_system: 'crm',
          overall_score: 93.8,
          grade: 'A',
          health_status: 'HEALTHY',
          completeness: 97.0,
          consistency: 100.0,
          accuracy: 96.0,
          freshness: 100.0,
          uniqueness: 100.0,
          drift_stability: 98.0,
          components: {
            completeness: 97.0,
            consistency: 100.0,
            accuracy: 96.0,
            freshness: 100.0,
            uniqueness: 100.0,
            drift_stability: 98.0,
          },
          explanations: ['3% null email addresses in customer profiles'],
        },
      ],
      recent_alerts: [
        {
          id: '1',
          alert_id: 'ALERT-B003',
          timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
          source: 'billing',
          metric: 'referential_integrity',
          issue_type: 'REFERENTIAL_INTEGRITY_VIOLATION',
          severity: 'HIGH',
          observed_value: '18 ghost records',
          expected_value: '0 ghost records',
          threshold: 0.995,
          description: '18 GHOST customer IDs detected in billing dataset with no parent CRM record',
          status: 'OPEN',
          rule_id: 'DQ-B003',
        },
        {
          id: '2',
          alert_id: 'ALERT-R001',
          timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
          source: 'billing_vs_analytics',
          metric: 'revenue_reconciliation',
          issue_type: 'AGGREGATION_MISMATCH',
          severity: 'CRITICAL',
          observed_value: '4.2% avg diff',
          expected_value: '<5%',
          threshold: 0.05,
          description: 'Daily revenue between Billing and Analytics diverges by 4.2% on average (Max diff: 7.2%)',
          status: 'OPEN',
          rule_id: 'DQ-R001',
        },
        {
          id: '3',
          alert_id: 'ALERT-A001',
          timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
          source: 'analytics',
          metric: 'completeness',
          issue_type: 'COMPLETENESS_VIOLATION',
          severity: 'MEDIUM',
          observed_value: '17 null rows',
          expected_value: '0 null rows',
          threshold: 0.98,
          description: 'Analytics total_revenue field contains 17 null values across historical dates',
          status: 'ACKNOWLEDGED',
          rule_id: 'DQ-A001',
        },
      ],
    };
  }
};

export const fetchAlerts = async (params?: Record<string, any>): Promise<Alert[]> => {
  try {
    const res = await api.get('/alerts', { params });
    return res.data;
  } catch (error) {
    console.warn('Backend unavailable, returning fallback alerts');
    return [
      {
        id: '1',
        alert_id: 'ALERT-B003',
        timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
        source: 'billing',
        metric: 'referential_integrity',
        issue_type: 'REFERENTIAL_INTEGRITY_VIOLATION',
        severity: 'HIGH',
        observed_value: '18 ghost records',
        expected_value: '0 ghost records',
        threshold: 0.995,
        description: '18 GHOST customer IDs detected in billing dataset with no parent CRM record',
        status: 'OPEN',
        rule_id: 'DQ-B003',
      },
      {
        id: '2',
        alert_id: 'ALERT-R001',
        timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
        source: 'billing_vs_analytics',
        metric: 'revenue_reconciliation',
        issue_type: 'AGGREGATION_MISMATCH',
        severity: 'CRITICAL',
        observed_value: '4.2% avg diff',
        expected_value: '<5%',
        threshold: 0.05,
        description: 'Daily revenue between Billing and Analytics diverges by 4.2% on average (Max diff: 7.2%)',
        status: 'OPEN',
        rule_id: 'DQ-R001',
      },
      {
        id: '3',
        alert_id: 'ALERT-V001',
        timestamp: new Date(Date.now() - 1000 * 60 * 180).toISOString(),
        source: 'billing',
        metric: 'tx_count',
        issue_type: 'VOLUME_DRIFT',
        severity: 'HIGH',
        observed_value: '320 tx/day',
        expected_value: '410.5 tx/day',
        threshold: 0.20,
        description: 'Volume drop detected: daily billing transactions dropped by 22% vs 30-day baseline',
        status: 'OPEN',
        rule_id: 'DRIFT-VOL-001',
      },
      {
        id: '4',
        alert_id: 'ALERT-D001',
        timestamp: new Date(Date.now() - 1000 * 60 * 300).toISOString(),
        source: 'billing',
        metric: 'amount',
        issue_type: 'DISTRIBUTION_DRIFT',
        severity: 'CRITICAL',
        observed_value: 'PSI = 0.24',
        expected_value: 'PSI < 0.20',
        threshold: 0.20,
        description: 'Distribution drift in transaction amount: PSI=0.24, KS test p-value < 0.001',
        status: 'ACKNOWLEDGED',
        rule_id: 'DRIFT-DIS-001',
      },
      {
        id: '5',
        alert_id: 'ALERT-S001',
        timestamp: new Date(Date.now() - 1000 * 60 * 420).toISOString(),
        source: 'billing',
        metric: 'discount_code',
        issue_type: 'SCHEMA_DRIFT',
        severity: 'HIGH',
        observed_value: 'new column added',
        expected_value: 'schema unchanged',
        threshold: 0.0,
        description: "New column added to billing schema: 'discount_code' (type: string)",
        status: 'RESOLVED',
        rule_id: 'DRIFT-SCH-001',
      },
    ];
  }
};

export const updateAlertStatus = async (
  alertId: string,
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED' | 'IGNORED',
  note?: string
): Promise<Alert> => {
  const res = await api.patch(`/alerts/${alertId}`, {
    status,
    resolution_note: note,
    acknowledged_by: 'current_user',
  });
  return res.data;
};

export const fetchDriftResults = async (params?: Record<string, any>): Promise<DriftResult[]> => {
  try {
    const res = await api.get('/drift', { params });
    return res.data;
  } catch (error) {
    return [
      {
        id: '1',
        drift_type: 'volume',
        source_system: 'billing',
        column_name: 'tx_count',
        is_drifted: true,
        drift_score: 0.22,
        severity: 'HIGH',
        baseline_value: '410.5 tx/day',
        current_value: '320.0 tx/day',
        threshold: 0.20,
        description: 'Volume drop: billing transactions dropped 22% vs 30-day rolling baseline (z-score: 2.65)',
        details: { z_score: 2.65, pct_change: 0.22, baseline_window_days: 30 },
        detected_at: new Date().toISOString(),
      },
      {
        id: '2',
        drift_type: 'distribution',
        source_system: 'billing',
        column_name: 'amount',
        is_drifted: true,
        drift_score: 0.24,
        severity: 'CRITICAL',
        baseline_value: 'mean=$485.2, p50=$320.1',
        current_value: 'mean=$1455.6, p50=$960.3',
        threshold: 0.20,
        description: 'Distribution drift: PSI = 0.2400 (significant shift), KS p-value = 0.0001',
        details: { psi: 0.24, ks_pvalue: 0.0001, technique: 'PSI + KS-test' },
        detected_at: new Date().toISOString(),
      },
      {
        id: '3',
        drift_type: 'schema',
        source_system: 'billing',
        column_name: 'discount_code',
        is_drifted: true,
        drift_score: 1.0,
        severity: 'HIGH',
        baseline_value: 'column_absent',
        current_value: 'string',
        threshold: 0.0,
        description: "Schema drift: New column added to billing: 'discount_code' (type: string)",
        details: { change_type: 'new_column' },
        detected_at: new Date().toISOString(),
      },
    ];
  }
};

export const fetchQualityMetrics = async (): Promise<DataQualityMetric[]> => {
  try {
    const res = await api.get('/quality');
    return res.data;
  } catch (error) {
    return [
      {
        id: 'q1',
        source_system: 'billing',
        total_records: 11915,
        completeness_score: 0.998,
        uniqueness_score: 0.999,
        validity_score: 0.995,
        referential_integrity_score: 0.985,
        null_count: 12,
        duplicate_count: 5,
        ghost_customer_count: 18,
        null_revenue_count: 0,
        inconsistent_count: 0,
        computed_at: new Date().toISOString(),
      },
      {
        id: 'q2',
        source_system: 'analytics',
        total_records: 913,
        completeness_score: 0.981,
        uniqueness_score: 1.0,
        validity_score: 0.997,
        referential_integrity_score: 1.0,
        null_count: 17,
        duplicate_count: 0,
        ghost_customer_count: 0,
        null_revenue_count: 17,
        inconsistent_count: 2,
        computed_at: new Date().toISOString(),
      },
      {
        id: 'q3',
        source_system: 'crm',
        total_records: 10500,
        completeness_score: 0.972,
        uniqueness_score: 1.0,
        validity_score: 0.981,
        referential_integrity_score: 1.0,
        null_count: 315,
        duplicate_count: 0,
        ghost_customer_count: 0,
        null_revenue_count: 0,
        inconsistent_count: 0,
        computed_at: new Date().toISOString(),
      },
    ];
  }
};

export const fetchComparisons = async (): Promise<ComparisonResult[]> => {
  try {
    const res = await api.get('/comparisons');
    return res.data;
  } catch (error) {
    const dates = [];
    const baseTime = Date.now() - 1000 * 60 * 60 * 24 * 14;
    for (let i = 0; i < 14; i++) {
      const dt = new Date(baseTime + 1000 * 60 * 60 * 24 * i).toISOString();
      const valA = 7500 + Math.random() * 2000;
      const valB = valA * (1 + (Math.random() * 0.08 - 0.03));
      const diff = Math.abs(valA - valB);
      const pct = diff / valB;
      dates.push({
        id: `c-${i}`,
        source_a: 'billing',
        source_b: 'analytics',
        comparison_date: dt,
        metric_name: 'daily_revenue',
        value_a: Math.round(valA),
        value_b: Math.round(valB),
        absolute_difference: Math.round(diff),
        percentage_difference: Math.round(pct * 1000) / 1000,
        threshold_status: pct > 0.05 ? 'HIGH' : 'OK',
        computed_at: dt,
      });
    }
    return dates as ComparisonResult[];
  }
};

export const fetchPipelineRuns = async (): Promise<PipelineRun[]> => {
  try {
    const res = await api.get('/pipelines/runs');
    return res.data;
  } catch (error) {
    return [
      {
        id: 'pr-1',
        run_id: 'RUN-2024-06-30-001',
        pipeline_name: 'full_pipeline_mixed',
        scenario: 'mixed',
        status: 'SUCCESS',
        started_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
        ended_at: new Date(Date.now() - 1000 * 60 * 58).toISOString(),
        duration_seconds: 118.5,
        records_read: 23328,
        records_written: 23200,
        records_rejected: 128,
        records_quarantined: 35,
        stage_summary: {
          bronze: { sources: 3, records: 23328 },
          silver: { clean: 23200, quarantined: 35 },
          gold: { quality_metrics: 3, comparisons: 913 },
          drift: { total_checks: 8, drifted: 3 },
        },
        created_at: new Date().toISOString(),
      },
    ];
  }
};

export const triggerPipeline = async (scenario: string = 'healthy') => {
  const res = await api.post('/pipelines/trigger', { scenario });
  return res.data;
};

export const fetchRules = async (): Promise<QualityRule[]> => {
  try {
    const res = await api.get('/rules');
    return res.data;
  } catch (error) {
    return [
      {
        id: 'r1',
        rule_id: 'DQ-B001',
        source: 'billing',
        column: 'amount',
        rule_type: 'completeness',
        description: 'Billing amount must not be null',
        threshold: 0.98,
        severity: 'HIGH',
        enabled: true,
        created_at: new Date().toISOString(),
      },
      {
        id: 'r2',
        rule_id: 'DQ-B003',
        source: 'billing',
        column: 'customer_id',
        rule_type: 'referential_integrity',
        description: 'Customer IDs must exist in CRM (GHOST records are violations)',
        threshold: 0.995,
        severity: 'HIGH',
        enabled: true,
        created_at: new Date().toISOString(),
      },
      {
        id: 'r3',
        rule_id: 'DQ-R001',
        source: 'reconciliation',
        column: 'revenue',
        rule_type: 'reconciliation',
        description: 'Daily revenue between Billing and Analytics must not deviate > 5%',
        threshold: 0.05,
        severity: 'CRITICAL',
        enabled: true,
        created_at: new Date().toISOString(),
      },
    ];
  }
};
