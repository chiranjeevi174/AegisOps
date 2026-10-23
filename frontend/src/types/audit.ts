export interface UnifiedAuditEvent {
  id: string;
  category: "approval" | "execution" | "verification" | "rollback";
  event_type: string;
  resource_id: string;
  incident_id?: string | null;
  actor: string;
  previous_status?: string | null;
  new_status?: string | null;
  details: Record<string, any>;
  created_at: string;
}
