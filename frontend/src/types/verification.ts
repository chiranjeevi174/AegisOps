export type VerificationOutcome =
  | "diagnostic_verified"
  | "inconclusive"
  | "failed"
  | "not_applicable";

export interface VerificationSummary {
  id: string;
  execution_id: string;
  incident_id: string;
  approval_id: string;
  operation_id: string;
  execution_mode: string;
  status: string;
  outcome: VerificationOutcome;
  requested_by: string;
  requested_at: string;
  completed_at: string;
  duration_ms: number;
  human_review_required: boolean;
  remediation_success_confirmed: boolean;
}

export interface VerificationDetail extends VerificationSummary {
  approved_plan_hash: string;
  verification_criteria: {
    baseline_window_minutes: number;
    followup_window_minutes: number;
    min_samples_required: number;
    step: string;
  };
  baseline_evidence?: Record<string, any>;
  followup_evidence?: Record<string, any>;
  metric_comparison?: Record<string, any>;
  limitations: string[];
  observations: string[];
  idempotency_key: string;
  started_at: string;
  error_message?: string | null;
  is_replay: boolean;
}

export interface VerificationEvent {
  id: string;
  verification_id: string;
  execution_id: string;
  actor: string;
  event_type: string;
  previous_status?: string | null;
  new_status: string;
  outcome?: string | null;
  details: Record<string, any>;
  created_at: string;
}

export interface CreateVerificationInput {
  criteria?: {
    baseline_window_minutes?: number;
    followup_window_minutes?: number;
    min_samples_required?: number;
    step?: string;
  };
  idempotency_key: string;
}
