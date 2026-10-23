import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "./test-utils";
import { ApprovalsPage } from "@/features/approvals/ApprovalsPage";
import { approvalsApi, authApi } from "@/services/api";

vi.mock("@/services/api", () => ({
  approvalsApi: {
    list: vi.fn(),
    get: vi.fn(),
    getEvents: vi.fn(),
    approve: vi.fn(),
    reject: vi.fn(),
    requestRevision: vi.fn(),
  },
  authApi: {
    getMe: vi.fn(),
  },
}));

describe("ApprovalsPage & Human-in-the-Loop Decisions", () => {
  const mockActor = {
    identity: "sre-lead-sarah",
    roles: ["incident_commander"],
    can_approve: true,
    can_request: true,
    can_execute: true,
    can_verify: true,
    can_assess_rollback: true,
  };

  const mockApprovals = [
    {
      id: "appr-1234",
      incident_id: "inc-100",
      version: 1,
      plan_hash: "a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef",
      requested_by: "sre-operator-dan",
      status: "pending" as const,
      requested_at: "2026-10-17T08:10:00Z",
      expires_at: "2026-10-17T09:10:00Z",
      requires_human_approval: true,
      execution_enabled: false,
    },
  ];

  const mockApprovalDetail = {
    ...mockApprovals[0],
    plan_snapshot: {
      incident_summary: "High 5xx error rate",
      planning_basis: "Prometheus alerts and Gemini RCA",
      overall_risk: "LOW",
      requires_human_approval: true,
      execution_enabled: false,
      recommended_actions: [
        {
          title: "Run Connectivity Diagnostic",
          description: "Check downstream TCP reachability without mutating state",
          rationale: "Verify network baseline before manual intervention",
          action_type: "diagnostic",
          risk_level: "LOW",
          supporting_evidence: ["Edge error spike"],
          prerequisites: ["Prometheus reachable"],
          validation_steps: ["Ensure latency < 50ms"],
          rollback_considerations: ["Read-only check, rollback N/A"],
          requires_human_approval: true,
        },
      ],
    },
    decision_reason: null,
    decided_by: null,
    decided_at: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (authApi.getMe as any).mockResolvedValue(mockActor);
    (approvalsApi.list as any).mockResolvedValue(mockApprovals);
    (approvalsApi.get as any).mockResolvedValue(mockApprovalDetail);
    (approvalsApi.getEvents as any).mockResolvedValue([]);
    (approvalsApi.approve as any).mockResolvedValue({ status: "approved" });
    (approvalsApi.reject as any).mockResolvedValue({ status: "rejected" });
  });

  it("renders pending approval requests with plan hash and version", async () => {
    renderWithProviders(<ApprovalsPage />);

    await waitFor(() => {
      expect(screen.getByText("sre-operator-dan")).toBeInTheDocument();
      expect(screen.getByText(/Version 1/i)).toBeInTheDocument();
      expect(screen.getAllByText("PENDING").length).toBeGreaterThan(0);
    });

    const approveBtn = screen.getByRole("button", { name: "Approve" });
    expect(approveBtn).toBeInTheDocument();
  });

  it("opens review modal on clicking approve and displays exact plan snapshot", async () => {
    renderWithProviders(<ApprovalsPage />);

    const approveBtn = await screen.findByRole("button", { name: "Approve" });
    await waitFor(() => expect(approveBtn).not.toBeDisabled());
    await userEvent.click(approveBtn);

    await waitFor(() => {
      expect(screen.getByText("1. Run Connectivity Diagnostic")).toBeInTheDocument();
      expect(screen.getByText(/Check downstream TCP reachability without mutating state/i)).toBeInTheDocument();
    });
  });

  it("validates mandatory rejection reason before submitting rejection", async () => {
    renderWithProviders(<ApprovalsPage />);

    const rejectBtn = await screen.findByRole("button", { name: "Reject" });
    await waitFor(() => expect(rejectBtn).not.toBeDisabled());
    await userEvent.click(rejectBtn);

    await waitFor(() => {
      expect(screen.getByText(/Mandatory Reason for Rejection/i)).toBeInTheDocument();
    });

    // Attempt to submit rejection without entering reason
    const submitRejectBtn = screen.getByRole("button", { name: "Confirm REJECT" });
    await userEvent.click(submitRejectBtn);

    // Mandatory rejection reason validation error
    await waitFor(() => {
      expect(screen.getByText("Rejection reason is required.")).toBeInTheDocument();
    });
    expect(approvalsApi.reject).not.toHaveBeenCalled();
  });
});
