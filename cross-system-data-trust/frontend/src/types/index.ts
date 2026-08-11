export interface SourceHealth {
  source_system: string;
  overall_score: number;
  grade: string;
  health_status: 'HEALTHY' | 'WARNING' | 'DEGRADED' | 'CRITICAL';
  completeness?: number;
  consistency?: number;
  accuracy?: number;
  freshness?: number;
  uniqueness?: number;
  drift_stability?: number;
  components?: {
    completeness: number;
    consistency: number;
    accuracy: number;
    freshness: number;
    uniqueness: number;
    drift_stability: number;
  };
  weights?: Record<string, number>;
  explanations?: string[];
}

export interface Alert {
  id: string;
  alert_id: string;
  run_id?: string;
  timestamp: string;
  source: string;
  metric: string;
  issue_type: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  observed_value?: string;
  expected_value?: string;
  threshold?: number;
  description: string;
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED' | 'IGNORED';
  rule_id?: string;
  acknowledged_by?: string;
  acknowledged_at?: string;
  resolution_note?: string;
}

export interface DashboardSummary {
  platform_trust_score: number;
  healthy_sources: number;
  warning_sources: number;
  critical_sources: number;
  total_alerts: number;
  open_alerts: number;
  critical_alerts: number;
  high_alerts: number;
  pipeline_success_rate: number;
  last_pipeline_run?: string;
  sources: SourceHealth[];
  recent_alerts: Alert[];
}

export interface DriftResult {
  id: string;
  run_id?: string;
  drift_type: 'volume' | 'distribution' | 'schema';
  source_system: string;
  column_name?: string;
  is_drifted: boolean;
  drift_score: number;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  baseline_value?: string;
  current_value?: string;
  threshold?: number;
  description?: string;
  details?: Record<string, any>;
  detected_at: string;
}

export interface DataQualityMetric {
  id: string;
  run_id?: string;
  source_system: string;
  total_records: number;
  completeness_score: number;
  uniqueness_score: number;
  validity_score: number;
  referential_integrity_score: number;
  null_count: number;
  duplicate_count: number;
  ghost_customer_count: number;
  null_revenue_count: number;
  inconsistent_count: number;
  computed_at: string;
}

export interface ComparisonResult {
  id: string;
  run_id?: string;
  source_a: string;
  source_b: string;
  comparison_date?: string;
  metric_name: string;
  value_a?: number;
  value_b?: number;
  absolute_difference?: number;
  percentage_difference?: number;
  threshold_status: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'OK';
  computed_at: string;
}

export interface PipelineRun {
  id: string;
  run_id: string;
  pipeline_name: string;
  source?: string;
  scenario?: string;
  status: 'RUNNING' | 'SUCCESS' | 'PARTIAL_SUCCESS' | 'FAILED';
  started_at: string;
  ended_at?: string;
  duration_seconds?: number;
  records_read: number;
  records_written: number;
  records_rejected: number;
  records_quarantined: number;
  error_message?: string;
  stage_summary?: Record<string, any>;
  created_at: string;
}

export interface QualityRule {
  id: string;
  rule_id: string;
  source: string;
  column?: string;
  rule_type: string;
  description?: string;
  threshold?: number;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  enabled: boolean;
  config?: Record<string, any>;
  created_at: string;
}
