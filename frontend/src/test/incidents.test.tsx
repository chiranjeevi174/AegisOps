import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "./test-utils";
import { IncidentsPage } from "@/features/incidents/IncidentsPage";
import { incidentsApi } from "@/services/api";

vi.mock("@/services/api", () => ({
  incidentsApi: {
    list: vi.fn(),
    create: vi.fn(),
  },
}));

describe("IncidentsPage", () => {
  const mockIncidents = [
    {
      id: "inc-1111-2222-3333-4444",
      title: "Service High Error Rate Ingress 5xx",
      description: "HTTP 500 error spike detected on edge proxies",
      severity: "critical",
      status: "open",
      source: "prometheus_alertmanager",
      created_at: "2026-10-17T08:00:00Z",
      alert_fingerprint: "fp-12345",
      alert_state: "firing",
    },
    {
      id: "inc-5555-6666-7777-8888",
      title: "Elevated Database Query Latency",
      description: "P99 latency exceeding 450ms threshold",
      severity: "medium",
      status: "investigating",
      source: "prometheus_alertmanager",
      created_at: "2026-10-17T07:30:00Z",
      alert_fingerprint: "fp-67890",
      alert_state: "firing",
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    (incidentsApi.list as any).mockResolvedValue(mockIncidents);
  });

  it("renders incident list from backend API", async () => {
    renderWithProviders(<IncidentsPage />);

    await waitFor(() => {
      expect(screen.getByText("Service High Error Rate Ingress 5xx")).toBeInTheDocument();
      expect(screen.getByText("Elevated Database Query Latency")).toBeInTheDocument();
    });

    expect(screen.getByText("CRITICAL")).toBeInTheDocument();
    expect(screen.getByText("MEDIUM")).toBeInTheDocument();
  });

  it("filters incidents by search term", async () => {
    renderWithProviders(<IncidentsPage />);

    await waitFor(() => {
      expect(screen.getByText("Service High Error Rate Ingress 5xx")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Search title/i);
    await userEvent.type(searchInput, "Database");

    expect(screen.getByText("Elevated Database Query Latency")).toBeInTheDocument();
    expect(screen.queryByText("Service High Error Rate Ingress 5xx")).not.toBeInTheDocument();
  });

  it("shows empty state when no incidents match filter", async () => {
    renderWithProviders(<IncidentsPage />);

    await waitFor(() => {
      expect(screen.getByText("Service High Error Rate Ingress 5xx")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Search title/i);
    await userEvent.type(searchInput, "NonexistentSpikePattern");

    expect(screen.getByText("No Incidents Match Filter")).toBeInTheDocument();
  });
});
