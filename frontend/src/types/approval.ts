export type ApprovalStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "revision_requested"
  | "expired"
  | "superseded";

export interface Approval {
  id: string;
  incident_id: string;
  status: ApprovalStatus;
  version: number;
  plan_hash: string;
  requested_by: string;
  requested_at: string;
  expires_at: string;
  decided_by?: string | null;
  decided_at?: string | null;
  decision_reason?: string | null;
  requires_human_approval: boolean;
  execution_enabled: boolean;
}

export interface ApprovalDetail extends Approval {
  plan_snapshot: {
    incident_summary?: string;
    planning_basis?: string;
    recommended_actions?: Array<{
      title: string;
      description: string;
      rationale: string;
      supporting_evidence: string[];
      prerequisites: string[];
      risk_level: string;
      action_type: string;
      validation_steps: string[];
      rollback_considerations: string[];
      requires_human_approval: boolean;
    }>;
    missing_information?: string[];
    overall_risk?: string;
    requires_human_approval?: boolean;
    execution_enabled?: boolean;
  };
}

export interface ApprovalEvent {
  id: string;
  approval_id: string;
  incident_id: string;
  actor: string;
  event_type: string;
  previous_status?: string | null;
  new_status: string;
  reason?: string | null;
  plan_hash: string;
  created_at: string;
}

export interface ApproveDecisionInput {
  comment?: string;
}

export interface RejectDecisionInput {
  reason: string;
}

export interface RevisionDecisionInput {
  reason: string;
}
