export type IncidentSeverity = "critical" | "high" | "medium" | "low";
export type IncidentStatus = "open" | "investigating" | "resolved";

export interface Incident {
  id: string;
  title: string;
  description: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  source: string;
  created_at: string;
  alert_fingerprint?: string | null;
  alert_state?: string | null;
  alert_started_at?: string | null;
  alert_updated_at?: string | null;
}

export interface IncidentCreateInput {
  title: string;
  description: string;
  severity: IncidentSeverity;
}

export interface IncidentAnalysisResult {
  incident_id: string;
  title: string;
  severity: IncidentSeverity;
  priority?: string | null;
  requires_escalation?: boolean | null;
  evidence?: Record<string, number | null> | null;
  evidence_collected_at?: string | null;
  investigation?: {
    summary?: string;
    observations?: string[];
    possible_causes?: string[];
    recommended_checks?: string[];
    confidence?: string;
  } | null;
  historical_evidence?: {
    summary?: string;
    metrics_summary?: Record<string, any>;
    evaluation_window?: Record<string, string>;
  } | null;
  rca?: {
    summary?: string;
    hypotheses?: Array<{
      title: string;
      description: string;
      confidence: string;
      supporting_evidence: string[];
      contradicting_evidence: string[];
      missing_evidence: string[];
    }>;
    most_likely_hypothesis?: string;
    root_cause_confirmed?: boolean;
    requires_human_review?: boolean;
  } | null;
  remediation_plan?: {
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
  } | null;
  errors?: Record<string, string | null>;
}
