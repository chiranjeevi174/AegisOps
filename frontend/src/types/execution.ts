export type ExecutionMode = "simulation" | "live_diagnostic";
export type ExecutionStatus =
  | "requested"
  | "running"
  | "simulated"
  | "diagnosed"
  | "completed"
  | "failed"
  | "rejected"
  | "timed_out";

export interface AllowlistedOperation {
  id: string;
  name: string;
  description: string;
  risk_level: "low" | "medium" | "high";
  required_permission: string;
  max_simulated_duration_ms: number;
  real_execution_supported: boolean;
  live_diagnostic_supported: boolean;
  supported_modes: string[];
  is_read_only: boolean;
  parameters_schema: Record<string, any>;
}

export interface Execution {
  id: string;
  incident_id: string;
  approval_id: string;
  approved_plan_hash: string;
  approved_plan_version: number;
  selected_recommendation_index: number;
  selected_recommendation_title: string;
  operation_id: string;
  parameters: Record<string, any>;
  requested_by: string;
  mode: ExecutionMode;
  status: ExecutionStatus;
  idempotency_key: string;
  requested_at: string;
  started_at: string;
  completed_at: string;
  duration_ms: number;
  is_replay: boolean;
  actual_infrastructure_access: boolean;
  system_changes_performed: boolean;
}

export interface ExecutionDetail extends Execution {
  simulation_result?: Record<string, any> | null;
  diagnostic_result?: Record<string, any> | null;
}

export interface ExecutionEvent {
  id: string;
  execution_id: string;
  incident_id: string;
  approval_id: string;
  actor: string;
  event_type: string;
  previous_status?: string | null;
  new_status: string;
  operation_id: string;
  approved_plan_hash: string;
  details: Record<string, any>;
  created_at: string;
}

export interface SimulateExecutionInput {
  approval_id: string;
  incident_id: string;
  operation_id: string;
  recommendation_index: number;
  parameters?: Record<string, any>;
  idempotency_key: string;
}

export interface DiagnoseExecutionInput {
  approval_id: string;
  incident_id: string;
  operation_id: string;
  recommendation_index: number;
  parameters?: Record<string, any>;
  idempotency_key: string;
}
