import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "./test-utils";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { overviewApi, ApiError } from "@/services/api";

vi.mock("@/services/api", () => ({
  overviewApi: {
    getSettings: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

describe("SettingsPage & Non-Sensitive Configuration", () => {
  const mockSettings = {
    app_name: "AegisOps",
    environment: "development",
    version: "1.0.0",
    live_diagnostics_enabled: true,
    prometheus_url: "http://localhost:9090",
    grafana_url: "http://localhost:3000",
    monitoring_available: true,
    current_actor: {
      identity: "sre-operator-dan",
      roles: ["sre_operator"],
      can_approve: true,
      can_request: true,
      can_execute: true,
      can_verify: true,
      can_assess_rollback: true,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders non-sensitive configuration without leaking credentials", async () => {
    (overviewApi.getSettings as any).mockResolvedValue(mockSettings);

    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText("System Settings & Platform Boundaries")).toBeInTheDocument();
      expect(screen.getByText("AegisOps")).toBeInTheDocument();
      expect(screen.getByText("v1.0.0")).toBeInTheDocument();
      expect(screen.getByText("DEVELOPMENT")).toBeInTheDocument();
      expect(screen.getByText("http://localhost:9090")).toBeInTheDocument();
      expect(screen.getByText("http://localhost:3000")).toBeInTheDocument();
      expect(screen.getByText("sre-operator-dan")).toBeInTheDocument();
    });

    // Check security notice
    expect(
      screen.getByText(/Secrets, database connection strings, Gemini API keys, and internal bearer tokens are strictly withheld/i)
    ).toBeInTheDocument();
  });

  it("displays error alert when settings fetch fails", async () => {
    (overviewApi.getSettings as any).mockRejectedValue(new ApiError("Backend connection refused", 503));

    renderWithProviders(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText("Failed to Load Settings")).toBeInTheDocument();
      expect(screen.getByText("Backend connection refused")).toBeInTheDocument();
    });
  });
});
