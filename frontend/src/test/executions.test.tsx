import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "./test-utils";
import { ExecutionsPage } from "@/features/executions/ExecutionsPage";
import { executionsApi, approvalsApi, authApi } from "@/services/api";

vi.mock("@/services/api", () => ({
  executionsApi: {
    getOperations: vi.fn(),
    list: vi.fn(),
    get: vi.fn(),
    getEvents: vi.fn(),
    simulate: vi.fn(),
    diagnose: vi.fn(),
  },
  approvalsApi: {
    list: vi.fn(),
  },
  authApi: {
    getMe: vi.fn(),
  },
}));

describe("ExecutionsPage & Diagnostic Boundaries", () => {
  const mockActor = {
    identity: "sre-operator-dan",
    roles: ["sre_operator"],
    can_approve: true,
    can_request: true,
    can_execute: true,
    can_verify: true,
    can_assess_rollback: true,
  };

  const mockOperations = [
    {
      id: "test_connectivity_diagnostic",
      name: "Test Connectivity Diagnostic",
      description: "Restricted read-only network probe to verify downstream connectivity",
      allowed_in_simulation: true,
      allowed_in_live_diagnostic: true,
      supported_modes: ["simulation", "live_diagnostic"],
      is_read_only: true,
      mutates_infrastructure: false,
      risk_level: "low" as const,
      required_permission: "operator",
      max_simulated_duration_ms: 1000,
      real_execution_supported: false,
      live_diagnostic_supported: true,
      parameters_schema: {},
    },
    {
      id: "read_service_metrics",
      name: "Read Service Metrics",
      description: "Sample Prometheus runtime gauges and counters",
      allowed_in_simulation: true,
      allowed_in_live_diagnostic: true,
      supported_modes: ["simulation", "live_diagnostic"],
      is_read_only: true,
      mutates_infrastructure: false,
      risk_level: "low" as const,
      required_permission: "operator",
      max_simulated_duration_ms: 1000,
      real_execution_supported: false,
      live_diagnostic_supported: true,
      parameters_schema: {},
    },
  ];

  const mockApprovedApprovals = [
    {
      id: "appr-valid-1",
      incident_id: "inc-100",
      version: 1,
      plan_hash: "hash1234567890abcdef",
      requested_by: "sre-operator-dan",
      status: "approved" as const,
      requested_at: "2026-10-17T08:10:00Z",
      expires_at: "2026-10-17T09:10:00Z",
      requires_human_approval: true,
      execution_enabled: false,
    },
  ];

  const mockExecutions = [
    {
      id: "exec-999",
      incident_id: "inc-100",
      approval_id: "appr-valid-1",
      approved_plan_hash: "hash123",
      approved_plan_version: 1,
      selected_recommendation_index: 0,
      selected_recommendation_title: "Connectivity Check",
      operation_id: "test_connectivity_diagnostic",
      parameters: {},
      requested_by: "sre-operator-dan",
      mode: "live_diagnostic" as const,
      status: "completed" as const,
      idempotency_key: "idem-123",
      requested_at: "2026-10-17T08:15:00Z",
      started_at: "2026-10-17T08:15:01Z",
      completed_at: "2026-10-17T08:15:02Z",
      duration_ms: 120,
      is_replay: false,
      actual_infrastructure_access: false,
      system_changes_performed: false,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    (authApi.getMe as any).mockResolvedValue(mockActor);
    (executionsApi.getOperations as any).mockResolvedValue(mockOperations);
    (approvalsApi.list as any).mockResolvedValue(mockApprovedApprovals);
    (executionsApi.list as any).mockResolvedValue(mockExecutions);
    (executionsApi.get as any).mockResolvedValue({
      ...mockExecutions[0],
      diagnostic_result: {
        summary: "Connectivity check passed with 0 packet loss",
        stdout_excerpt: "PING upstream.service (10.0.0.5): 56 data bytes\n0% packet loss",
      },
    });
    (executionsApi.getEvents as any).mockResolvedValue([]);
    (executionsApi.simulate as any).mockResolvedValue({ id: "exec-sim-1" });
    (executionsApi.diagnose as any).mockResolvedValue({ id: "exec-diag-1" });
  });

  it("renders operations registry and execution history", async () => {
    renderWithProviders(<ExecutionsPage />);

    await waitFor(() => {
      expect(screen.getAllByText("test_connectivity_diagnostic").length).toBeGreaterThan(0);
      expect(screen.getByText("read_service_metrics")).toBeInTheDocument();
      expect(screen.getByText("LIVE_DIAGNOSTIC")).toBeInTheDocument();
    });

    expect(screen.getByText("Immutable Allowlisted Operations Registry")).toBeInTheDocument();
  });

  it("requires confirmation dialog before live diagnostic execution", async () => {
    renderWithProviders(<ExecutionsPage />);

    await waitFor(() => {
      expect(screen.getByText("Run Live Diagnostic")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Run Live Diagnostic"));

    expect(screen.getByText("Execute Read-Only Live Diagnostic")).toBeInTheDocument();
    expect(screen.getByText(/Strict Read-Only Verification/i)).toBeInTheDocument();
  });
});
