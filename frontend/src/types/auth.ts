export interface AuthenticatedActor {
  identity: string;
  roles: string[];
  can_approve: boolean;
  can_request: boolean;
  can_execute: boolean;
  can_verify: boolean;
  can_assess_rollback: boolean;
  csrf_token?: string | null;
  dev_persona_switching_enabled?: boolean;
}

export interface ActorProfile {
  identity: string;
  roles: string[];
}
