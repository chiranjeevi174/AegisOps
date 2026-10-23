import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "./test-utils";
import { InvestigationPage } from "@/features/investigation/InvestigationPage";
import { incidentsApi } from "@/services/api";

vi.mock("@/services/api", () => ({
  incidentsApi: {
    list: vi.fn(),
    analyze: vi.fn(),
  },
}));

describe("Investigation & RCA Page", () => {
  const mockIncidents = [
    {
      id: "inc-100",
      title: "Backend API 500 Spike",
      description: "Spike in internal errors",
      severity: "high",
      status: "open",
      source: "prometheus",
      created_at: "2026-10-17T08:00:00Z",
    },
  ];

  const mockAnalysis = {
    incident_id: "inc-100",
    title: "Backend API 500 Spike",
    severity: "high",
    priority: "P1",
    requires_escalation: true,
    evidence: {
      http_requests_total: 1540,
      http_500_errors: 120,
    },
    evidence_collected_at: "2026-10-17T08:05:00Z",
    investigation: {
      summary: "Significant increase in error rate following upstream deployment.",
      observations: ["500 errors concentrated on /checkout endpoint", "Upstream DB pool exhausted"],
      recommended_checks: ["inspect_pool_saturation", "test_connectivity_diagnostic"],
      confidence: "HIGH",
    },
    rca: {
      summary: "Database connection starvation during checkout burst",
      hypotheses: [
        {
          title: "Connection Pool Exhaustion",
          description: "Max connections 50 reached under burst",
          confidence: "HIGH",
          supporting_evidence: ["Active connections reached 50/50"],
          contradicting_evidence: ["Network latency between app and DB is sub-millisecond"],
          missing_evidence: ["PostgreSQL slow query logs"],
        },
      ],
      most_likely_hypothesis: "Connection Pool Exhaustion",
      root_cause_confirmed: false,
      requires_human_review: true,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (incidentsApi.list as any).mockResolvedValue(mockIncidents);
    (incidentsApi.analyze as any).mockResolvedValue(mockAnalysis);
  });

  it("triggers AI investigation and displays structured telemetry vs hypotheses", async () => {
    renderWithProviders(<InvestigationPage />);

    await waitFor(() => {
      expect(screen.getByText(/Backend API 500 Spike/i)).toBeInTheDocument();
    });

    const runBtn = screen.getAllByRole("button", { name: /Execute AI Investigation/i })[0];
    await userEvent.click(runBtn);

    await waitFor(() => {
      expect(incidentsApi.analyze).toHaveBeenCalledWith("inc-100");
    });

    // Check deterministic evidence
    expect(screen.getByText("Observed Platform Evidence (Deterministic Telemetry)")).toBeInTheDocument();
    expect(screen.getByText("http_500_errors")).toBeInTheDocument();
    expect(screen.getByText("120")).toBeInTheDocument();

    // Check hypothesis matrix and unconfirmed safety invariant
    expect(screen.getByText("Root Cause Analysis (AI-Generated Hypotheses)")).toBeInTheDocument();
    expect(screen.getAllByText("Connection Pool Exhaustion").length).toBeGreaterThan(0);
    expect(screen.getByText("Active connections reached 50/50")).toBeInTheDocument();
    expect(screen.getByText("PostgreSQL slow query logs")).toBeInTheDocument();
  });
});
