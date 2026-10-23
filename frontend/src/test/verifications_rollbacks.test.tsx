import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "./test-utils";
import { VerificationsPage } from "@/features/verifications/VerificationsPage";
import { RollbacksPage } from "@/features/rollbacks/RollbacksPage";
import { verificationsApi, rollbacksApi, executionsApi, authApi } from "@/services/api";

vi.mock("@/services/api", () => ({
  verificationsApi: {
    list: vi.fn(),
    get: vi.fn(),
    getEvents: vi.fn(),
    create: vi.fn(),
  },
  rollbacksApi: {
    list: vi.fn(),
    get: vi.fn(),
    getEvents: vi.fn(),
    create: vi.fn(),
  },
  executionsApi: {
    list: vi.fn(),
  },
  authApi: {
    getMe: vi.fn(),
  },
}));

describe("VerificationsPage & Outcome Truthfulness", () => {
  const mockActor = {
    identity: "sre-operator-dan",
    roles: ["sre_operator"],
    can_approve: true,
    can_request: true,
    can_execute: true,
    can_verify: true,
    can_assess_rollback: true,
  };

  const mockVerifications = [
    {
      id: "verif-101",
      execution_id: "exec-999",
      incident_id: "inc-100",
      approval_id: "appr-1",
      operation_id: "test_connectivity_diagnostic",
      execution_mode: "live_diagnostic",
      status: "completed",
      outcome: "diagnostic_verified" as const,
      requested_by: "sre-operator-dan",
      requested_at: "2026-10-17T08:20:00Z",
      completed_at: "2026-10-17T08:20:02Z",
      duration_ms: 200,
      remediation_success_confirmed: false,
      human_review_required: true,
    },
  ];

  const mockVerificationDetail = {
    ...mockVerifications[0],
    approved_plan_hash: "hash123",
    verification_criteria: {
      baseline_window_minutes: 10,
      followup_window_minutes: 5,
      min_samples_required: 5,
      step: "30s",
    },
    baseline_telemetry: {
      metric_name: "http_requests_total",
      metric_units: "req/s",
      mean_value: 100.5,
      sample_count: 12,
    },
    followup_telemetry: {
      metric_name: "http_requests_total",
      metric_units: "req/s",
      mean_value: 102.1,
      sample_count: 6,
    },
    statistical_comparison: {
      absolute_change: 1.6,
      relative_change: 0.0159,
      observed_direction: "steady",
      sample_counts: { baseline: 12, followup: 6 },
    },
    evidence_sufficiency: "sufficient",
    temporal_coverage: "100%",
    missing_measurements: [],
    operator_notes: "Diagnostic probe telemetry confirmed operational reachability.",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (authApi.getMe as any).mockResolvedValue(mockActor);
    (verificationsApi.list as any).mockResolvedValue(mockVerifications);
    (verificationsApi.get as any).mockResolvedValue(mockVerificationDetail);
    (verificationsApi.getEvents as any).mockResolvedValue([]);
    (executionsApi.list as any).mockResolvedValue([]);
  });

  it("displays verification outcome and enforces remediation success is not falsely claimed", async () => {
    renderWithProviders(<VerificationsPage />);

    await waitFor(() => {
      expect(screen.getByText("DIAGNOSTIC VERIFIED")).toBeInTheDocument();
      expect(screen.getByText("Inspect")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Inspect"));

    await waitFor(() => {
      expect(screen.getByText("Verification: DIAGNOSTIC_VERIFIED")).toBeInTheDocument();
      expect(screen.getByText("Remediation Success Confirmed")).toBeInTheDocument();
      expect(screen.getByText("FALSE")).toBeInTheDocument();
      expect(screen.getByText("Human Review Required")).toBeInTheDocument();
      expect(screen.getByText(/TRUE/)).toBeInTheDocument();
    });
  });
});

describe("RollbacksPage & Simulation Guardrails", () => {
  const mockActor = {
    identity: "sre-operator-dan",
    roles: ["sre_operator"],
    can_approve: true,
    can_request: true,
    can_execute: true,
    can_verify: true,
    can_assess_rollback: true,
  };

  const mockAssessments = [
    {
      id: "rb-202",
      execution_id: "exec-999",
      incident_id: "inc-100",
      approval_id: "appr-1",
      operation_id: "test_connectivity_diagnostic",
      execution_mode: "live_diagnostic",
      status: "completed",
      readiness_status: "not_applicable" as const,
      applicability: "not_applicable",
      risk_level: "low",
      requested_by: "sre-operator-dan",
      requested_at: "2026-10-17T08:25:00Z",
      completed_at: "2026-10-17T08:25:02Z",
      duration_ms: 150,
      rollback_execution_enabled: false,
      human_authorization_required: true,
      system_changes_performed: false,
    },
  ];

  const mockAssessmentDetail = {
    ...mockAssessments[0],
    approved_plan_hash: "hash123",
    assessment_data: {
      prerequisites: [{ name: "Target reachable", details: "OK", satisfied: true }],
    },
    simulation_result: {
      simulated_target_state: "Baseline steady state (zero rollback required)",
      risk_assessment_summary: "No infrastructure-changing remediation occurred. Diagnostic was read-only.",
    },
    limitations: ["Rollback execution is completely disabled in AegisOps core"],
    observations: [],
    idempotency_key: "idem-123",
    started_at: "2026-10-17T08:25:01Z",
    is_replay: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (authApi.getMe as any).mockResolvedValue(mockActor);
    (rollbacksApi.list as any).mockResolvedValue(mockAssessments);
    (rollbacksApi.get as any).mockResolvedValue(mockAssessmentDetail);
    (rollbacksApi.getEvents as any).mockResolvedValue([]);
    (executionsApi.list as any).mockResolvedValue([]);
  });

  it("displays rollback not-applicable state and safety invariants", async () => {
    renderWithProviders(<RollbacksPage />);

    await waitFor(() => {
      expect(screen.getByText("NOT_APPLICABLE")).toBeInTheDocument();
      expect(screen.getByText("Inspect")).toBeInTheDocument();
    });

    // Invariants in safety banner
    expect(screen.getByText(/Human Approval:/i)).toBeInTheDocument();
    expect(screen.getByText(/Auto Execution:/i)).toBeInTheDocument();

    await userEvent.click(screen.getByText("Inspect"));

    await waitFor(() => {
      expect(screen.getByText("Rollback Readiness: NOT_APPLICABLE")).toBeInTheDocument();
      expect(screen.getByText(/Baseline steady state/i)).toBeInTheDocument();
    });
  });
});
