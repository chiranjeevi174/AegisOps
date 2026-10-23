export interface SystemOverview {
  total_incidents: number;
  open_incidents: number;
  incidents_by_severity: Record<string, number>;
  incidents_by_status: Record<string, number>;
  pending_approvals: number;
  total_approvals: number;
  total_executions: number;
  executions_by_status: Record<string, number>;
  executions_by_mode: Record<string, number>;
  total_verifications: number;
  verifications_by_outcome: Record<string, number>;
  total_rollback_assessments: number;
  rollback_by_readiness: Record<string, number>;
  service_availability?: number | null;
  service_up?: boolean | null;
  monitoring_available: boolean;
  grafana_url: string;
  incident_creation_trend: Array<{
    timestamp: string;
    date: string;
    severity: string;
  }>;
}

export interface TelemetryPoint {
  timestamp: string;
  value: number;
}

export interface SystemSettings {
  app_name: string;
  environment: string;
  version: string;
  live_diagnostics_enabled: boolean;
  prometheus_url: string;
  grafana_url: string;
  monitoring_available: boolean;
  current_actor: {
    identity: string;
    roles: string[];
    can_approve: boolean;
    can_request: boolean;
    can_execute: boolean;
    can_verify: boolean;
    can_assess_rollback: boolean;
  };
}
