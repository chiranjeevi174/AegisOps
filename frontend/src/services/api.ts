import axios, { AxiosError } from "axios";
import type {
  AuthenticatedActor,
  ActorProfile,
} from "@/types/auth";
import type {
  Incident,
  IncidentCreateInput,
  IncidentAnalysisResult,
} from "@/types/incident";
import type {
  Approval,
  ApprovalDetail,
  ApprovalEvent,
  ApproveDecisionInput,
  RejectDecisionInput,
  RevisionDecisionInput,
} from "@/types/approval";
import type {
  AllowlistedOperation,
  Execution,
  ExecutionDetail,
  ExecutionEvent,
  SimulateExecutionInput,
  DiagnoseExecutionInput,
} from "@/types/execution";
import type {
  VerificationSummary,
  VerificationDetail,
  VerificationEvent,
  CreateVerificationInput,
} from "@/types/verification";
import type {
  RollbackAssessmentSummary,
  RollbackAssessmentDetail,
  RollbackEvent,
  CreateRollbackAssessmentInput,
} from "@/types/rollback";
import type { UnifiedAuditEvent } from "@/types/audit";
import type {
  SystemOverview,
  TelemetryPoint,
  SystemSettings,
} from "@/types/overview";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 60000,
});

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp("(^|;\\s*)(" + name + ")=([^;]*)"));
  return match ? decodeURIComponent(match[3]) : null;
}

apiClient.interceptors.request.use((config) => {
  const method = (config.method || "").toUpperCase();
  if (["POST", "PUT", "DELETE", "PATCH"].includes(method)) {
    const csrfToken = getCookie("aegisops_csrf");
    if (csrfToken && !config.headers["X-CSRF-Token"]) {
      config.headers["X-CSRF-Token"] = csrfToken;
    }
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const status = error.response?.status || 500;
    let detail = (error.response?.data as any)?.detail || error.message || "An unexpected error occurred";
    if (error.code === "ECONNABORTED" || error.message?.toLowerCase().includes("timeout")) {
      detail = "The request timed out. The multi-agent AI workflow requires additional processing time for Gemini RCA deduction and telemetry snapshots; please retry.";
    }
    return Promise.reject(new ApiError(detail, status, error.response?.data));
  }
);

// --- Auth Endpoints ---
export const authApi = {
  getMe: async (): Promise<AuthenticatedActor> => {
    const { data } = await apiClient.get<AuthenticatedActor>("/auth/me");
    return data;
  },
  getCsrf: async (): Promise<{ csrf_token: string }> => {
    const { data } = await apiClient.get<{ csrf_token: string }>("/auth/csrf");
    return data;
  },
  getActors: async (): Promise<ActorProfile[]> => {
    const { data } = await apiClient.get<ActorProfile[]>("/auth/actors");
    return data;
  },
  loginSession: async (payload: { token?: string; identity?: string }): Promise<AuthenticatedActor> => {
    const { data } = await apiClient.post<AuthenticatedActor>("/auth/session", payload);
    return data;
  },
  logout: async (): Promise<{ status: string }> => {
    const { data } = await apiClient.post<{ status: string }>("/auth/logout");
    return data;
  },
};

// --- Overview & Settings ---
export const overviewApi = {
  getOverview: async (): Promise<SystemOverview> => {
    const { data } = await apiClient.get<SystemOverview>("/overview");
    return data;
  },
  getTelemetry: async (windowMinutes: number = 30): Promise<TelemetryPoint[]> => {
    const { data } = await apiClient.get<TelemetryPoint[]>("/overview/telemetry", {
      params: { window_minutes: windowMinutes },
    });
    return data;
  },
  getSettings: async (): Promise<SystemSettings> => {
    const { data } = await apiClient.get<SystemSettings>("/system/settings");
    return data;
  },
};

// --- Incidents Endpoints ---
export const incidentsApi = {
  list: async (limit: number = 50, offset: number = 0): Promise<Incident[]> => {
    const { data } = await apiClient.get<Incident[]>("/incidents", {
      params: { limit, offset },
    });
    return data;
  },
  get: async (id: string): Promise<Incident> => {
    const { data } = await apiClient.get<Incident>(`/incidents/${id}`);
    return data;
  },
  create: async (payload: IncidentCreateInput): Promise<Incident> => {
    const { data } = await apiClient.post<Incident>("/incidents", payload);
    return data;
  },
  analyze: async (id: string): Promise<IncidentAnalysisResult> => {
    const { data } = await apiClient.post<IncidentAnalysisResult>(
      `/incidents/${id}/analyze`,
      {},
      { timeout: 120000 }
    );
    return data;
  },
  createApproval: async (id: string): Promise<Approval> => {
    const { data } = await apiClient.post<Approval>(
      `/incidents/${id}/approvals`,
      {},
      { timeout: 120000 }
    );
    return data;
  },
};

// --- Approvals Endpoints ---
export const approvalsApi = {
  list: async (params?: { incident_id?: string; status?: string; limit?: number; offset?: number }): Promise<Approval[]> => {
    const { data } = await apiClient.get<Approval[]>("/approvals", { params });
    return data;
  },
  get: async (id: string): Promise<ApprovalDetail> => {
    const { data } = await apiClient.get<ApprovalDetail>(`/approvals/${id}`);
    return data;
  },
  getEvents: async (id: string): Promise<ApprovalEvent[]> => {
    const { data } = await apiClient.get<ApprovalEvent[]>(`/approvals/${id}/events`);
    return data;
  },
  approve: async (id: string, payload: ApproveDecisionInput): Promise<any> => {
    const { data } = await apiClient.post(`/approvals/${id}/approve`, payload);
    return data;
  },
  reject: async (id: string, payload: RejectDecisionInput): Promise<any> => {
    const { data } = await apiClient.post(`/approvals/${id}/reject`, payload);
    return data;
  },
  requestRevision: async (id: string, payload: RevisionDecisionInput): Promise<any> => {
    const { data } = await apiClient.post(`/approvals/${id}/request-revision`, payload);
    return data;
  },
};

// --- Executions Endpoints ---
export const executionsApi = {
  getOperations: async (): Promise<AllowlistedOperation[]> => {
    const { data } = await apiClient.get<AllowlistedOperation[]>("/execution-operations");
    return data;
  },
  list: async (params?: { incident_id?: string; approval_id?: string; status?: string; limit?: number; offset?: number }): Promise<Execution[]> => {
    const { data } = await apiClient.get<Execution[]>("/executions", { params });
    return data;
  },
  get: async (id: string): Promise<ExecutionDetail> => {
    const { data } = await apiClient.get<ExecutionDetail>(`/executions/${id}`);
    return data;
  },
  getEvents: async (id: string): Promise<ExecutionEvent[]> => {
    const { data } = await apiClient.get<ExecutionEvent[]>(`/executions/${id}/events`);
    return data;
  },
  simulate: async (payload: SimulateExecutionInput): Promise<ExecutionDetail> => {
    const { data } = await apiClient.post<ExecutionDetail>(
      "/executions/simulate",
      payload,
      { timeout: 60000 }
    );
    return data;
  },
  diagnose: async (payload: DiagnoseExecutionInput): Promise<ExecutionDetail> => {
    const { data } = await apiClient.post<ExecutionDetail>(
      "/executions/diagnose",
      payload,
      { timeout: 60000 }
    );
    return data;
  },
};

// --- Verifications Endpoints ---
export const verificationsApi = {
  list: async (params?: { execution_id?: string; incident_id?: string; limit?: number; offset?: number }): Promise<VerificationSummary[]> => {
    const { data } = await apiClient.get<VerificationSummary[]>("/verifications", { params });
    return data;
  },
  get: async (id: string): Promise<VerificationDetail> => {
    const { data } = await apiClient.get<VerificationDetail>(`/verifications/${id}`);
    return data;
  },
  getEvents: async (id: string): Promise<VerificationEvent[]> => {
    const { data } = await apiClient.get<VerificationEvent[]>(`/verifications/${id}/events`);
    return data;
  },
  create: async (executionId: string, payload: CreateVerificationInput): Promise<VerificationDetail> => {
    const { data } = await apiClient.post<VerificationDetail>(`/executions/${executionId}/verifications`, payload);
    return data;
  },
};

// --- Rollback Assessments Endpoints ---
export const rollbacksApi = {
  list: async (params?: { execution_id?: string; incident_id?: string; limit?: number; offset?: number }): Promise<RollbackAssessmentSummary[]> => {
    const { data } = await apiClient.get<RollbackAssessmentSummary[]>("/rollback-assessments", { params });
    return data;
  },
  get: async (id: string): Promise<RollbackAssessmentDetail> => {
    const { data } = await apiClient.get<RollbackAssessmentDetail>(`/rollback-assessments/${id}`);
    return data;
  },
  getEvents: async (id: string): Promise<RollbackEvent[]> => {
    const { data } = await apiClient.get<RollbackEvent[]>(`/rollback-assessments/${id}/events`);
    return data;
  },
  create: async (executionId: string, payload: CreateRollbackAssessmentInput): Promise<RollbackAssessmentDetail> => {
    const { data } = await apiClient.post<RollbackAssessmentDetail>(`/executions/${executionId}/rollback-assessments`, payload);
    return data;
  },
};

// --- Audit History Endpoints ---
export const auditApi = {
  getEvents: async (params?: { category?: string; limit?: number; offset?: number }): Promise<UnifiedAuditEvent[]> => {
    const { data } = await apiClient.get<UnifiedAuditEvent[]>("/audit/events", { params });
    return data;
  },
};
