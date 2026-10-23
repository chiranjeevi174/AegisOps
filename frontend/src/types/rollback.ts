export type RollbackReadinessStatus =
  | "ready"
  | "blocked"
  | "not_applicable"
  | "failed";

export interface RollbackAssessmentSummary {
  id: string;
  execution_id: string;
  incident_id: string;
  approval_id: string;
  operation_id: string;
  execution_mode: string;
  status: string;
  readiness_status: RollbackReadinessStatus;
  applicability: string;
  risk_level: string;
  requested_by: string;
  requested_at: string;
  completed_at: string;
  duration_ms: number;
  human_authorization_required: boolean;
  rollback_execution_enabled: boolean;
  system_changes_performed: boolean;
}

export interface RollbackAssessmentDetail extends RollbackAssessmentSummary {
  approved_plan_hash: string;
  assessment_data: {
    prerequisites?: Array<{
      name: string;
      description?: string;
      details: string;
      satisfied: boolean;
    }>;
    [key: string]: any;
  };
  simulation_result?: {
    simulation_mode?: string;
    simulated_target_state?: string;
    risk_assessment_summary?: string;
    simulated_actions?: string[];
    notes?: string[];
    can_safely_simulate?: boolean;
    simulated_at?: string;
  } | null;
  limitations: string[];
  observations: string[];
  idempotency_key: string;
  started_at: string;
  error_message?: string | null;
  is_replay: boolean;
}

export interface RollbackEvent {
  id: string;
  assessment_id: string;
  execution_id: string;
  actor: string;
  event_type: string;
  previous_status?: string | null;
  new_status: string;
  readiness_status?: string | null;
  details: Record<string, any>;
  created_at: string;
}

export interface CreateRollbackAssessmentInput {
  idempotency_key: string;
}
