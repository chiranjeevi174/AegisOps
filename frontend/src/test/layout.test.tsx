import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "./test-utils";
import { AppLayout } from "@/components/layout/AppLayout";
import { authApi, overviewApi } from "@/services/api";

vi.mock("@/services/api", () => ({
  authApi: {
    getMe: vi.fn(),
    loginSession: vi.fn(),
    logout: vi.fn(),
    getActors: vi.fn(),
  },
  overviewApi: {
    getOverview: vi.fn(),
  },
}));

describe("AppLayout & Navigation", () => {
  const mockActor = {
    identity: "sre-operator-dan",
    roles: ["sre_operator"],
    can_approve: true,
    can_request: true,
    can_execute: true,
    can_verify: true,
    can_assess_rollback: true,
  };

  const mockOverview = {
    total_incidents: 5,
    open_incidents: 2,
    pending_approvals: 1,
    monitoring_available: true,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (authApi.getMe as any).mockResolvedValue(mockActor);
    (authApi.getActors as any).mockResolvedValue([
      mockActor,
      {
        identity: "readonly-auditor",
        roles: ["auditor"],
        can_approve: false,
        can_request: false,
        can_execute: false,
        can_verify: false,
        can_assess_rollback: false,
      },
    ]);
    (overviewApi.getOverview as any).mockResolvedValue(mockOverview);
  });

  it("renders navigation links and operator branding", async () => {
    renderWithProviders(<AppLayout />, { initialEntries: ["/"] });

    expect(screen.getByText("AegisOps")).toBeInTheDocument();
    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("Incidents")).toBeInTheDocument();
    expect(screen.getByText("Investigations & RCA")).toBeInTheDocument();
    expect(screen.getByText("Approvals")).toBeInTheDocument();
    expect(screen.getByText("Executions")).toBeInTheDocument();
    expect(screen.getByText("Verifications")).toBeInTheDocument();
    expect(screen.getByText("Rollback Readiness")).toBeInTheDocument();
    expect(screen.getByText("Audit History")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("sre-operator-dan")).toBeInTheDocument();
    });
  });

  it("opens persona switcher modal on clicking operator profile", async () => {
    renderWithProviders(<AppLayout />, { initialEntries: ["/"] });

    await waitFor(() => {
      expect(screen.getByText("sre-operator-dan")).toBeInTheDocument();
    });

    const switcherBtn = screen.getByTitle("Switch Persona");
    await userEvent.click(switcherBtn);

    expect(screen.getByText("Operator Persona & Authentication")).toBeInTheDocument();
    expect(screen.getByText("Configured Development Personas")).toBeInTheDocument();
  });
});
