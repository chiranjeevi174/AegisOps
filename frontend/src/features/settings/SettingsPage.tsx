import React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Settings,
  Server,
  Activity,
  ExternalLink,
  ShieldCheck,
  UserCheck,
  CheckCircle2,
  XCircle,
  Cpu,
} from "lucide-react";
import { overviewApi } from "@/services/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Skeleton, AlertMessage } from "@/components/ui/Feedback";

export const SettingsPage: React.FC = () => {
  const { data: settings, isLoading, error } = useQuery({
    queryKey: ["settings"],
    queryFn: () => overviewApi.getSettings(),
  });

  return (
    <div className="space-y-6 text-obsidian-text select-none font-sans">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-obsidian-text flex items-center gap-2">
          <Settings className="w-6 h-6 text-copper-400" />
          System Settings & Platform Boundaries
        </h1>
        <p className="text-sm text-obsidian-muted mt-1">
          Non-sensitive runtime operational configuration, observability endpoints, and operator authorization matrix.
        </p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Skeleton className="h-64 rounded-xl bg-obsidian-800" />
          <Skeleton className="h-64 rounded-xl bg-obsidian-800" />
          <Skeleton className="h-64 rounded-xl bg-obsidian-800" />
          <Skeleton className="h-64 rounded-xl bg-obsidian-800" />
        </div>
      ) : error || !settings ? (
        <AlertMessage
          type="error"
          title="Failed to Load Settings"
        >
          {error ? (error as Error).message : "No settings received from backend"}
        </AlertMessage>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Card 1: Platform & Environment */}
          <Card className="bg-obsidian-800 border-obsidian-700">
            <CardHeader className="flex flex-row items-center justify-between border-b border-obsidian-700">
              <div>
                <CardTitle>Core Platform Configuration</CardTitle>
                <CardDescription>Runtime environment and version information</CardDescription>
              </div>
              <Server className="w-5 h-5 text-copper-400" />
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between py-2 border-b border-obsidian-700">
                  <span className="text-obsidian-muted">Application Name</span>
                  <span className="font-semibold text-obsidian-text font-mono">{settings.app_name}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-obsidian-700">
                  <span className="text-obsidian-muted">Platform Version</span>
                  <Badge variant="outline">v{settings.version}</Badge>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-obsidian-700">
                  <span className="text-obsidian-muted">Environment</span>
                  <Badge variant={settings.environment === "development" ? "warning" : "info"}>
                    {settings.environment.toUpperCase()}
                  </Badge>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-obsidian-muted">Backend API Status</span>
                  <span className="flex items-center gap-1.5 text-status-healthy font-medium font-mono text-xs">
                    <CheckCircle2 className="w-4 h-4" /> Connected (FastAPI)
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Card 2: Observability & Telemetry */}
          <Card className="bg-obsidian-800 border-obsidian-700">
            <CardHeader className="flex flex-row items-center justify-between border-b border-obsidian-700">
              <div>
                <CardTitle>Observability Infrastructure</CardTitle>
                <CardDescription>Connected metrics providers and dashboard integrations</CardDescription>
              </div>
              <Activity className="w-5 h-5 text-copper-400" />
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between py-2 border-b border-obsidian-700">
                  <span className="text-obsidian-muted">Prometheus Telemetry</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-copper-300">{settings.prometheus_url}</span>
                    <Badge variant={settings.monitoring_available ? "success" : "default"}>
                      {settings.monitoring_available ? "Active" : "Unreachable"}
                    </Badge>
                  </div>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-obsidian-700">
                  <span className="text-obsidian-muted">Grafana Dashboards</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-copper-300">{settings.grafana_url}</span>
                    <a
                      href={settings.grafana_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-copper-400 hover:text-copper-300 font-medium px-2 py-0.5 rounded bg-copper-400/10 border border-copper-400/20"
                    >
                      Open <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-obsidian-muted">Prometheus Proxy Security</span>
                  <span className="text-xs text-obsidian-secondary font-mono">Strictly Scoped / No Arbitrary Queries</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Card 3: Safety Guardrails & Capabilities */}
          <Card className="bg-obsidian-800 border-obsidian-700">
            <CardHeader className="flex flex-row items-center justify-between border-b border-obsidian-700">
              <div>
                <CardTitle>Remediation Guardrails</CardTitle>
                <CardDescription>Deterministic safety bounds enforced by backend core</CardDescription>
              </div>
              <ShieldCheck className="w-5 h-5 text-copper-400" />
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between py-2 border-b border-obsidian-700">
                  <span className="text-obsidian-muted">Live Diagnostic Operations</span>
                  <Badge variant={settings.live_diagnostics_enabled ? "warning" : "default"}>
                    {settings.live_diagnostics_enabled ? "Restricted Allowed" : "Disabled"}
                  </Badge>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-obsidian-700">
                  <span className="text-obsidian-muted">Infrastructure Mutation</span>
                  <span className="flex items-center gap-1.5 text-status-critical font-medium text-xs font-mono">
                    <XCircle className="w-4 h-4" /> Strictly Disabled
                  </span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-obsidian-700">
                  <span className="text-obsidian-muted">Autonomous Shell / SSH Execution</span>
                  <span className="flex items-center gap-1.5 text-status-critical font-medium text-xs font-mono">
                    <XCircle className="w-4 h-4" /> Disabled
                  </span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-obsidian-muted">Human-in-the-Loop Requirement</span>
                  <span className="flex items-center gap-1.5 text-status-healthy font-medium text-xs font-mono">
                    <CheckCircle2 className="w-4 h-4" /> Mandatory on All Plans
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Card 4: Current Operator Permissions */}
          <Card className="bg-obsidian-800 border-obsidian-700">
            <CardHeader className="flex flex-row items-center justify-between border-b border-obsidian-700">
              <div>
                <CardTitle>Operator Authorization Matrix</CardTitle>
                <CardDescription>Privileges granted to currently authenticated persona</CardDescription>
              </div>
              <UserCheck className="w-5 h-5 text-copper-400" />
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between py-2 border-b border-obsidian-700">
                  <span className="text-obsidian-muted">Active Identity</span>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-obsidian-text font-mono">{settings.current_actor.identity}</span>
                    {settings.current_actor.roles.map((r) => (
                      <Badge key={r} variant="ai">{r}</Badge>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-1 font-mono text-xs">
                  <div className="flex items-center justify-between p-2 rounded bg-obsidian-900 border border-obsidian-700">
                    <span className="text-[11px] text-obsidian-secondary">Request Approvals</span>
                    {settings.current_actor.can_request ? (
                      <CheckCircle2 className="w-4 h-4 text-status-healthy" />
                    ) : (
                      <XCircle className="w-4 h-4 text-obsidian-muted" />
                    )}
                  </div>
                  <div className="flex items-center justify-between p-2 rounded bg-obsidian-900 border border-obsidian-700">
                    <span className="text-[11px] text-obsidian-secondary">Decide Approvals</span>
                    {settings.current_actor.can_approve ? (
                      <CheckCircle2 className="w-4 h-4 text-status-healthy" />
                    ) : (
                      <XCircle className="w-4 h-4 text-obsidian-muted" />
                    )}
                  </div>
                  <div className="flex items-center justify-between p-2 rounded bg-obsidian-900 border border-obsidian-700">
                    <span className="text-[11px] text-obsidian-secondary">Execute Diagnostics</span>
                    {settings.current_actor.can_execute ? (
                      <CheckCircle2 className="w-4 h-4 text-status-healthy" />
                    ) : (
                      <XCircle className="w-4 h-4 text-obsidian-muted" />
                    )}
                  </div>
                  <div className="flex items-center justify-between p-2 rounded bg-obsidian-900 border border-obsidian-700">
                    <span className="text-[11px] text-obsidian-secondary">Run Verifications</span>
                    {settings.current_actor.can_verify ? (
                      <CheckCircle2 className="w-4 h-4 text-status-healthy" />
                    ) : (
                      <XCircle className="w-4 h-4 text-obsidian-muted" />
                    )}
                  </div>
                  <div className="flex items-center justify-between p-2 rounded bg-obsidian-900 border border-obsidian-700 col-span-2">
                    <span className="text-[11px] text-obsidian-secondary">Assess Rollback Readiness</span>
                    {settings.current_actor.can_assess_rollback ? (
                      <CheckCircle2 className="w-4 h-4 text-status-healthy" />
                    ) : (
                      <XCircle className="w-4 h-4 text-obsidian-muted" />
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Security Footnote */}
      <div className="p-4 rounded-xl border border-obsidian-700 bg-obsidian-850 text-xs text-obsidian-secondary flex items-start gap-3">
        <Cpu className="w-4 h-4 text-copper-400 mt-0.5 shrink-0" />
        <div>
          <span className="font-semibold text-obsidian-text">Security Architecture Notice: </span>
          Runtime parameters are read directly from backend verified configuration. Secrets, database connection strings,
          Gemini API keys, and internal bearer tokens are strictly withheld by the FastAPI backend and never delivered to the client bundle.
        </div>
      </div>
    </div>
  );
};
