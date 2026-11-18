import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  AlertOctagon,
  CheckCircle2,
  PlaySquare,
  Activity,
  ArrowRight,
  ExternalLink,
  ShieldCheck,
  RefreshCw,
  Clock,
  Sparkles,
  SearchCode,
  FileCheck2,
  History,
  Layers,
  Zap,
} from "lucide-react";
import {
  overviewApi,
  incidentsApi,
  approvalsApi,
  auditApi,
} from "@/services/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { SafetyBanner } from "@/components/ui/SafetyBanner";
import { Skeleton } from "@/components/ui/Feedback";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  CartesianGrid,
} from "recharts";

export const DashboardPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [telemetryWindow, setTelemetryWindow] = useState<number>(30);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date>(new Date());

  const {
    data: overview,
    isLoading: isLoadingOverview,
    isRefetching: isRefetchingOverview,
    refetch: refetchOverview,
  } = useQuery({
    queryKey: ["overview"],
    queryFn: overviewApi.getOverview,
    staleTime: 30000,
  });

  const {
    data: telemetry,
    isLoading: isLoadingTelemetry,
    refetch: refetchTelemetry,
  } = useQuery({
    queryKey: ["overview", "telemetry", telemetryWindow],
    queryFn: () => overviewApi.getTelemetry(telemetryWindow),
    refetchInterval: 15000,
  });

  const {
    data: recentIncidents,
    refetch: refetchIncidents,
  } = useQuery({
    queryKey: ["incidents", "recent"],
    queryFn: () => incidentsApi.list(6, 0),
  });

  const {
    data: pendingApprovalsList,
    refetch: refetchApprovals,
  } = useQuery({
    queryKey: ["approvals", { status: "pending", limit: 5 }],
    queryFn: () => approvalsApi.list({ status: "pending", limit: 5 }),
  });

  const {
    data: recentAuditEvents,
    refetch: refetchAudit,
  } = useQuery({
    queryKey: ["audit", "recent-events"],
    queryFn: () => auditApi.getEvents({ limit: 6 }),
  });

  const handleManualRefresh = async () => {
    await Promise.all([
      refetchOverview(),
      refetchTelemetry(),
      refetchIncidents(),
      refetchApprovals(),
      refetchAudit(),
    ]);
    queryClient.invalidateQueries();
    setLastRefreshedAt(new Date());
  };

  if (isLoadingOverview) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-16 w-full bg-obsidian-800" />
        <Skeleton className="h-24 w-full bg-obsidian-800" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28 bg-obsidian-800" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="lg:col-span-2 h-72 bg-obsidian-800" />
          <Skeleton className="h-72 bg-obsidian-800" />
        </div>
      </div>
    );
  }

  // Incident severity distribution data
  const criticalCount = overview?.incidents_by_severity?.critical || 0;
  const highCount = overview?.incidents_by_severity?.high || 0;
  const mediumCount = overview?.incidents_by_severity?.medium || 0;
  const lowCount = overview?.incidents_by_severity?.low || 0;

  const severityData = [
    { name: "Critical", value: criticalCount, color: "#FB7185" }, // Coral
    { name: "High", value: highCount, color: "#FBBF24" },        // Warning Amber
    { name: "Medium", value: mediumCount, color: "#E58A2B" },     // Copper
    { name: "Low", value: lowCount, color: "#4ADE80" },          // Healthy Green
  ].filter((d) => d.value > 0);

  // Status breakdown
  const statusOpen = overview?.incidents_by_status?.open || 0;
  const statusInvestigating = overview?.incidents_by_status?.investigating || 0;
  const statusMitigated = overview?.incidents_by_status?.mitigated || 0;
  const statusResolved = overview?.incidents_by_status?.resolved || 0;

  // Executions completed
  const executionsCompleted = overview?.executions_by_status?.completed ?? overview?.total_executions ?? 0;
  const totalVerifications = overview?.total_verifications ?? 0;

  // Service availability representation
  const isServiceUp = overview?.service_up;
  const monitoringLive = overview?.monitoring_available;

  return (
    <div className="space-y-6 select-none font-sans text-obsidian-text">
      {/* 4.1 Command Center Header */}
      <div className="bg-obsidian-850 border border-obsidian-700 rounded-xl p-5 shadow-obsidian-md relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="w-2.5 h-2.5 rounded-full bg-copper-400 animate-ping" />
              <h1 className="text-xl font-bold tracking-tight text-obsidian-text">
                Operations Command Center
              </h1>
              <span className="text-[10px] font-mono uppercase bg-copper-400/10 text-copper-400 border border-copper-400/30 px-2 py-0.5 rounded font-semibold tracking-wider">
                Active Sentinel
              </span>
            </div>
            <p className="text-xs text-obsidian-muted mt-1 max-w-2xl">
              Autonomous observability stream, deterministic safety guardrails, and human-in-the-loop incident response orchestration.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Environment Indicator */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-obsidian-900 border border-obsidian-700 text-xs">
              <Layers className="w-3.5 h-3.5 text-copper-400" />
              <span className="text-obsidian-muted">Env:</span>
              <span className="font-mono text-copper-300 font-semibold uppercase text-[11px]">
                development
              </span>
            </div>

            {/* Freshness / Last Updated */}
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-obsidian-900 border border-obsidian-700 text-xs text-obsidian-muted">
              <Clock className="w-3.5 h-3.5 text-obsidian-muted" />
              <span>Updated:</span>
              <span className="font-mono text-obsidian-secondary text-[11px]">
                {lastRefreshedAt.toLocaleTimeString()}
              </span>
            </div>

            {/* Refresh Action */}
            <Button
              variant="secondary"
              size="sm"
              onClick={handleManualRefresh}
              isLoading={isRefetchingOverview}
              title="Refresh All Operations Data"
            >
              <RefreshCw className="w-3.5 h-3.5 text-copper-400" />
              <span>Refresh</span>
            </Button>
          </div>
        </div>
      </div>

      {/* 4.2 Operational Health & Safety Banner */}
      <SafetyBanner />

      {/* 4.3 KPI Cards Section (6 Metrics) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5">
        {/* KPI 1: Open Incidents */}
        <Card className="hover:border-obsidian-600 transition-all hover:shadow-obsidian-md bg-obsidian-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between text-obsidian-muted">
              <span className="text-[11px] font-semibold uppercase tracking-wider font-mono">Open Incidents</span>
              <div className="p-2 rounded-lg bg-rose-500/10 text-status-critical border border-status-critical/20">
                <AlertTriangle className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-obsidian-text">
                {overview?.open_incidents ?? 0}
              </span>
              <span className="text-[11px] text-obsidian-muted">
                of {overview?.total_incidents ?? 0} total
              </span>
            </div>
            <div className="mt-2 pt-2 border-t border-obsidian-700/60 flex items-center justify-between text-[11px]">
              <span className="text-obsidian-muted">Triage Status:</span>
              <span className={overview?.open_incidents && overview.open_incidents > 0 ? "text-status-warning font-medium" : "text-status-healthy font-medium"}>
                {overview?.open_incidents && overview.open_incidents > 0 ? "Attention Required" : "All Clear"}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* KPI 2: Critical Incidents */}
        <Card className="hover:border-obsidian-600 transition-all hover:shadow-obsidian-md bg-obsidian-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between text-obsidian-muted">
              <span className="text-[11px] font-semibold uppercase tracking-wider font-mono">Critical (P1)</span>
              <div className="p-2 rounded-lg bg-rose-500/15 text-status-critical border border-status-critical/30">
                <AlertOctagon className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className={`text-2xl font-bold font-mono ${criticalCount > 0 ? "text-status-critical" : "text-obsidian-text"}`}>
                {criticalCount}
              </span>
              <span className="text-[11px] text-obsidian-muted">
                {criticalCount > 0 ? "immediate priority" : "none active"}
              </span>
            </div>
            <div className="mt-2 pt-2 border-t border-obsidian-700/60 flex items-center justify-between text-[11px]">
              <span className="text-obsidian-muted">Severity SLA:</span>
              <span className={criticalCount > 0 ? "text-status-critical font-medium" : "text-status-healthy font-medium"}>
                {criticalCount > 0 ? "< 15m Target" : "Guarded"}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* KPI 3: Pending Approvals */}
        <Card className="hover:border-obsidian-600 transition-all hover:shadow-obsidian-md bg-obsidian-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between text-obsidian-muted">
              <span className="text-[11px] font-semibold uppercase tracking-wider font-mono">Pending Approvals</span>
              <div className="p-2 rounded-lg bg-amber-400/10 text-status-warning border border-status-warning/20">
                <CheckCircle2 className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-status-warning">
                {overview?.pending_approvals ?? 0}
              </span>
              <span className="text-[11px] text-obsidian-muted">
                of {overview?.total_approvals ?? 0} historical
              </span>
            </div>
            <div className="mt-2 pt-2 border-t border-obsidian-700/60 flex items-center justify-between text-[11px]">
              <span className="text-obsidian-muted">Human Gate:</span>
              <span className="text-copper-400 font-medium">Mandatory Review</span>
            </div>
          </CardContent>
        </Card>

        {/* KPI 4: Completed Executions */}
        <Card className="hover:border-obsidian-600 transition-all hover:shadow-obsidian-md bg-obsidian-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between text-obsidian-muted">
              <span className="text-[11px] font-semibold uppercase tracking-wider font-mono">Completed Runs</span>
              <div className="p-2 rounded-lg bg-copper-400/10 text-copper-400 border border-copper-400/20">
                <PlaySquare className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-copper-300">
                {executionsCompleted}
              </span>
              <span className="text-[11px] text-obsidian-muted">
                of {overview?.total_executions ?? 0} total
              </span>
            </div>
            <div className="mt-2 pt-2 border-t border-obsidian-700/60 flex items-center justify-between text-[11px]">
              <span className="text-obsidian-muted">Execution Mode:</span>
              <span className="text-copper-400 font-mono text-[10px]">Sim / Read-Only</span>
            </div>
          </CardContent>
        </Card>

        {/* KPI 5: Verified Executions */}
        <Card className="hover:border-obsidian-600 transition-all hover:shadow-obsidian-md bg-obsidian-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between text-obsidian-muted">
              <span className="text-[11px] font-semibold uppercase tracking-wider font-mono">Verifications</span>
              <div className="p-2 rounded-lg bg-status-healthy/10 text-status-healthy border border-status-healthy/20">
                <ShieldCheck className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-status-healthy">
                {totalVerifications}
              </span>
              <span className="text-[11px] text-obsidian-muted">
                verified runs
              </span>
            </div>
            <div className="mt-2 pt-2 border-t border-obsidian-700/60 flex items-center justify-between text-[11px]">
              <span className="text-obsidian-muted">Post-Flight:</span>
              <span className="text-status-healthy font-medium">Statistical Checks</span>
            </div>
          </CardContent>
        </Card>

        {/* KPI 6: Service Availability / Telemetry */}
        <Card className="hover:border-obsidian-600 transition-all hover:shadow-obsidian-md bg-obsidian-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between text-obsidian-muted">
              <span className="text-[11px] font-semibold uppercase tracking-wider font-mono">Service Availability</span>
              <div className={`p-2 rounded-lg border ${
                monitoringLive && isServiceUp
                  ? "bg-status-healthy/10 text-status-healthy border-status-healthy/20"
                  : monitoringLive
                  ? "bg-rose-500/10 text-status-critical border-status-critical/20"
                  : "bg-amber-400/10 text-status-warning border-status-warning/20"
              }`}>
                <Activity className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className={`text-2xl font-bold font-mono ${
                monitoringLive && isServiceUp
                  ? "text-status-healthy"
                  : monitoringLive
                  ? "text-status-critical"
                  : "text-status-warning text-lg"
              }`}>
                {isServiceUp ? "100%" : monitoringLive ? "0%" : "Telemetry N/A"}
              </span>
            </div>
            <div className="mt-2 pt-2 border-t border-obsidian-700/60 flex items-center justify-between text-[11px]">
              <span className="text-obsidian-muted">Metrics Probe:</span>
              <span className={`font-mono text-[10px] font-medium ${monitoringLive ? "text-status-healthy" : "text-status-warning"}`}>
                {monitoringLive ? "Prometheus Live" : "Offline / Standby"}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Row 2: Telemetry Monitoring (2 Cols) + Incident Intelligence & Severity Distribution (1 Col) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 4.4 Service Health and Telemetry Monitoring */}
        <Card className="lg:col-span-2 bg-obsidian-800 border-obsidian-700">
          <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 py-3.5">
            <div>
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-copper-400" />
                <CardTitle>Service Availability & Runtime Telemetry</CardTitle>
                <span className="text-[10px] font-mono text-obsidian-muted bg-obsidian-900 border border-obsidian-700 px-2 py-0.5 rounded">
                  aegisops_sim_service_up
                </span>
              </div>
              <p className="text-xs text-obsidian-muted mt-0.5">
                Target service status: 1.0 = UP, 0.0 = DOWN sampled via Prometheus engine
              </p>
            </div>

            <div className="flex items-center gap-3">
              {/* Window Selector */}
              <div className="flex items-center bg-obsidian-900 border border-obsidian-700 rounded-lg p-0.5 text-xs font-mono">
                {[15, 30, 60].map((mins) => (
                  <button
                    key={mins}
                    onClick={() => setTelemetryWindow(mins)}
                    className={`px-2.5 py-1 rounded text-[11px] font-medium transition-all ${
                      telemetryWindow === mins
                        ? "bg-copper-400 text-obsidian-950 font-bold shadow-copper-sm"
                        : "text-obsidian-muted hover:text-obsidian-text"
                    }`}
                  >
                    {mins}m
                  </button>
                ))}
              </div>

              {/* Grafana Dashboard link */}
              <a
                href={overview?.grafana_url || "http://localhost:3000"}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-copper-400 hover:text-copper-300 transition-colors font-medium px-2.5 py-1 rounded bg-copper-400/10 border border-copper-400/20"
              >
                <span>Grafana</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </CardHeader>

          <CardContent className="p-4">
            {isLoadingTelemetry ? (
              <div className="h-64 flex items-center justify-center">
                <Skeleton className="h-56 w-full bg-obsidian-750" />
              </div>
            ) : telemetry && telemetry.length > 0 ? (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={telemetry} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="copperAvailabilityGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#E58A2B" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#E58A2B" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="#40372D" strokeDasharray="3 3" opacity={0.4} />
                    <XAxis
                      dataKey="timestamp"
                      stroke="#817565"
                      fontSize={10}
                      tickLine={false}
                      fontFamily="JetBrains Mono, monospace"
                    />
                    <YAxis
                      domain={[0, 1.2]}
                      ticks={[0, 0.5, 1.0]}
                      stroke="#817565"
                      fontSize={10}
                      tickLine={false}
                      fontFamily="JetBrains Mono, monospace"
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#26211B",
                        borderColor: "#40372D",
                        borderRadius: "8px",
                        fontSize: "12px",
                        color: "#F5F0E8",
                        boxShadow: "0 4px 14px 0 rgba(0, 0, 0, 0.6)",
                      }}
                      labelStyle={{ color: "#E58A2B", fontFamily: "JetBrains Mono, monospace" }}
                    />
                    <Area
                      type="stepAfter"
                      dataKey="value"
                      stroke="#E58A2B"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#copperAvailabilityGrad)"
                      name="Availability"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-64 flex flex-col items-center justify-center text-center p-6 border border-dashed border-obsidian-700 rounded-lg bg-obsidian-900/40">
                <Activity className="w-8 h-8 text-obsidian-muted mb-2" />
                <p className="text-xs text-obsidian-secondary font-medium">
                  {overview?.monitoring_available
                    ? "Connecting to Prometheus metrics stream..."
                    : "Prometheus telemetry unavailable. Ensure local Docker Prometheus is running on port 9090."}
                </p>
                <p className="text-[11px] text-obsidian-muted mt-1 max-w-md">
                  AegisOps strictly presents honest telemetry: no synthetic data or fabricated charts are substituted when the metric server is offline.
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 4.5 Incident Intelligence & Severity Distribution */}
        <Card className="bg-obsidian-800 border-obsidian-700">
          <CardHeader className="py-3.5">
            <div className="flex items-center justify-between">
              <CardTitle>Incident Severity & Triage</CardTitle>
              <Badge variant="outline" size="sm">
                {overview?.total_incidents ?? 0} Recorded
              </Badge>
            </div>
            <p className="text-xs text-obsidian-muted mt-0.5">
              Active cluster severity classification
            </p>
          </CardHeader>
          <CardContent className="p-4">
            {severityData.length > 0 ? (
              <div className="flex flex-col items-center justify-center">
                <div className="h-44 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={severityData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={72}
                        paddingAngle={5}
                      >
                        {severityData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} stroke="#191714" strokeWidth={2} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#26211B",
                          borderColor: "#40372D",
                          borderRadius: "8px",
                          fontSize: "12px",
                          color: "#F5F0E8",
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                {/* Legend Chips */}
                <div className="grid grid-cols-2 gap-2 w-full mt-3 pt-3 border-t border-obsidian-700 text-xs">
                  <div className="flex items-center justify-between p-1.5 rounded bg-obsidian-900 border border-obsidian-700">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-status-critical" />
                      <span className="text-obsidian-secondary text-[11px]">Critical</span>
                    </div>
                    <span className="font-mono font-bold text-status-critical text-xs">{criticalCount}</span>
                  </div>

                  <div className="flex items-center justify-between p-1.5 rounded bg-obsidian-900 border border-obsidian-700">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-status-warning" />
                      <span className="text-obsidian-secondary text-[11px]">High</span>
                    </div>
                    <span className="font-mono font-bold text-status-warning text-xs">{highCount}</span>
                  </div>

                  <div className="flex items-center justify-between p-1.5 rounded bg-obsidian-900 border border-obsidian-700">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-copper-400" />
                      <span className="text-obsidian-secondary text-[11px]">Medium</span>
                    </div>
                    <span className="font-mono font-bold text-copper-400 text-xs">{mediumCount}</span>
                  </div>

                  <div className="flex items-center justify-between p-1.5 rounded bg-obsidian-900 border border-obsidian-700">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-status-healthy" />
                      <span className="text-obsidian-secondary text-[11px]">Low</span>
                    </div>
                    <span className="font-mono font-bold text-status-healthy text-xs">{lowCount}</span>
                  </div>
                </div>

                {/* Status distribution mini bar */}
                <div className="w-full mt-3 pt-3 border-t border-obsidian-700">
                  <div className="flex items-center justify-between text-[11px] text-obsidian-muted mb-1.5">
                    <span>Lifecycle:</span>
                    <span className="font-mono">
                      {statusOpen} open / {statusInvestigating} investigating / {statusMitigated + statusResolved} resolved
                    </span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-obsidian-900 overflow-hidden flex">
                    <div
                      style={{ width: `${(statusOpen / Math.max(1, overview?.total_incidents || 1)) * 100}%` }}
                      className="bg-status-critical"
                      title={`Open: ${statusOpen}`}
                    />
                    <div
                      style={{ width: `${(statusInvestigating / Math.max(1, overview?.total_incidents || 1)) * 100}%` }}
                      className="bg-ai-violet"
                      title={`Investigating: ${statusInvestigating}`}
                    />
                    <div
                      style={{ width: `${((statusMitigated + statusResolved) / Math.max(1, overview?.total_incidents || 1)) * 100}%` }}
                      className="bg-status-healthy"
                      title={`Resolved/Mitigated: ${statusMitigated + statusResolved}`}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-56 flex items-center justify-center text-xs text-obsidian-muted">
                No incident distribution records available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Row 3: 4.6 Agent Investigation & RCA Activity (1/2) + 4.7 Remediation & Approval Overview (1/2) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 4.6 Agent Investigation and RCA Activity */}
        <Card className="bg-obsidian-800 border-obsidian-700">
          <CardHeader className="flex flex-row items-center justify-between py-3.5 border-b border-obsidian-700">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-ai-violet/15 text-ai-violet border border-ai-violet/30">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <CardTitle>AI Agent Investigation & RCA Engine</CardTitle>
                <p className="text-xs text-obsidian-muted mt-0.5">
                  LangGraph multi-agent diagnostic deduction & Gemini hypothesis formulation
                </p>
              </div>
            </div>
            <Link to="/investigations">
              <Button variant="ghost" size="sm">
                <span>Investigations</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="p-4 space-y-3.5">
            <div className="p-3 rounded-lg bg-obsidian-900 border border-ai-violet/25 flex items-start gap-3">
              <SearchCode className="w-4 h-4 text-ai-violet mt-0.5 shrink-0" />
              <div className="text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-obsidian-text">Autonomous Investigation Pipeline</span>
                  <Badge variant="ai" size="sm">AI ADVISORY</Badge>
                </div>
                <p className="text-obsidian-secondary mt-1">
                  Agentic workflow collects deterministic Prometheus time-series snapshots and synthesizes candidate root cause hypotheses.
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-obsidian-muted">
                  <span className="px-2 py-0.5 rounded bg-obsidian-800 border border-obsidian-700 text-ai-violet font-mono">
                    Deterministic Evidence First
                  </span>
                  <span className="text-obsidian-700">•</span>
                  <span className="px-2 py-0.5 rounded bg-obsidian-800 border border-obsidian-700 text-status-warning font-mono">
                    Hypotheses Require Human Confirmation
                  </span>
                </div>
              </div>
            </div>

            {/* Recent active investigations representation */}
            <div className="space-y-2">
              <div className="text-[11px] font-semibold text-obsidian-muted uppercase tracking-wider font-mono">
                Recent Triage Activity
              </div>
              {recentIncidents && recentIncidents.length > 0 ? (
                recentIncidents.slice(0, 3).map((inc) => (
                  <div
                    key={inc.id}
                    className="p-2.5 rounded-lg bg-obsidian-900/70 border border-obsidian-700 flex items-center justify-between text-xs hover:border-copper-400/40 transition-colors"
                  >
                    <div className="min-w-0 pr-3">
                      <div className="flex items-center gap-2">
                        <Badge variant={inc.severity} size="sm">
                          {inc.severity.toUpperCase()}
                        </Badge>
                        <span className="font-medium text-obsidian-text truncate max-w-xs">
                          {inc.title}
                        </span>
                      </div>
                      <p className="text-[11px] text-obsidian-muted mt-0.5 truncate">
                        Source: {inc.source} • Created: {new Date(inc.created_at).toLocaleTimeString()}
                      </p>
                    </div>
                    <Link to={`/incidents/${inc.id}`}>
                      <Button variant="secondary" size="sm">
                        RCA View
                      </Button>
                    </Link>
                  </div>
                ))
              ) : (
                <p className="text-xs text-obsidian-muted py-2">No active incident investigations</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* 4.7 Remediation and Approval Overview */}
        <Card className="bg-obsidian-800 border-obsidian-700">
          <CardHeader className="flex flex-row items-center justify-between py-3.5 border-b border-obsidian-700">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-amber-400/10 text-status-warning border border-status-warning/20">
                <FileCheck2 className="w-4 h-4" />
              </div>
              <div>
                <CardTitle>Remediation & Human Approvals</CardTitle>
                <p className="text-xs text-obsidian-muted mt-0.5">
                  Cryptographic SHA-256 integrity plans & separation of duties
                </p>
              </div>
            </div>
            <Link to="/approvals">
              <Button variant="ghost" size="sm">
                <span>Approval Queue</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="p-4 space-y-3.5">
            {/* Safety policy notice */}
            <div className="p-3 rounded-lg bg-obsidian-900 border border-amber-400/30 flex items-start gap-3">
              <ShieldCheck className="w-4 h-4 text-status-warning mt-0.5 shrink-0" />
              <div className="text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-obsidian-text">Approval Gate Enforced</span>
                  <Badge variant="high" size="sm">MANDATORY</Badge>
                </div>
                <p className="text-obsidian-secondary mt-1">
                  Remediation actions cannot execute without signed human consent. Plans are bound to immutable plan hashes to detect tampering.
                </p>
              </div>
            </div>

            {/* Pending Approvals Queue list */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-[11px] font-semibold text-obsidian-muted uppercase tracking-wider font-mono">
                <span>Pending Approval Queue</span>
                <span className="text-copper-400">{pendingApprovalsList?.length ?? 0} Awaiting Action</span>
              </div>

              {pendingApprovalsList && pendingApprovalsList.length > 0 ? (
                pendingApprovalsList.map((appr) => (
                  <div
                    key={appr.id}
                    className="p-2.5 rounded-lg bg-obsidian-900/70 border border-obsidian-700 flex items-center justify-between text-xs hover:border-copper-400/40 transition-colors"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <Badge variant="high" size="sm">PENDING</Badge>
                        <span className="font-mono text-xs text-obsidian-text">
                          Plan v{appr.version}
                        </span>
                        <span className="text-obsidian-muted font-mono text-[10px]">
                          [{appr.plan_hash ? `${appr.plan_hash.slice(0, 8)}...` : "NO_HASH"}]
                        </span>
                      </div>
                      <p className="text-[11px] text-obsidian-muted mt-0.5">
                        Requested by: <span className="text-copper-300 font-mono">{appr.requested_by}</span>
                      </p>
                    </div>
                    <Link to="/approvals">
                      <Button variant="primary" size="sm">
                        Review
                      </Button>
                    </Link>
                  </div>
                ))
              ) : (
                <div className="p-4 rounded-lg bg-obsidian-900/40 border border-dashed border-obsidian-700 text-center text-xs text-obsidian-muted">
                  <CheckCircle2 className="w-5 h-5 text-status-healthy mx-auto mb-1 opacity-80" />
                  No pending remediation plans awaiting operator approval.
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Row 4: 4.8 Recent Operational Activity (Audit Log) (1/3) + Active & Recent Incidents (2/3) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 4.8 Recent Operational Activity */}
        <Card className="bg-obsidian-800 border-obsidian-700">
          <CardHeader className="flex flex-row items-center justify-between py-3.5 border-b border-obsidian-700">
            <div className="flex items-center gap-2">
              <History className="w-4 h-4 text-copper-400" />
              <CardTitle>Operational Audit Stream</CardTitle>
            </div>
            <Link to="/audit">
              <Button variant="ghost" size="sm">
                <span>View All</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="p-4">
            {recentAuditEvents && recentAuditEvents.length > 0 ? (
              <div className="space-y-3">
                {recentAuditEvents.map((ev) => (
                  <div
                    key={ev.id}
                    className="flex items-start gap-2.5 p-2 rounded-lg bg-obsidian-900/60 border border-obsidian-700 text-xs"
                  >
                    <div className="p-1 rounded bg-obsidian-800 border border-obsidian-700 mt-0.5 text-copper-400 shrink-0">
                      <Zap className="w-3 h-3" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-semibold text-obsidian-text truncate font-mono text-[11px]">
                          {ev.event_type}
                        </span>
                        <span className="text-[10px] text-obsidian-muted shrink-0 font-mono">
                          {new Date(ev.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-1 text-[11px] text-obsidian-muted">
                        <span className="text-copper-300 font-mono">{ev.actor}</span>
                        <span>•</span>
                        <Badge
                          variant={
                            ev.category === "approval"
                              ? "high"
                              : ev.category === "execution"
                              ? "primary"
                              : ev.category === "verification"
                              ? "low"
                              : "secondary"
                          }
                          size="sm"
                        >
                          {ev.category.toUpperCase()}
                        </Badge>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-8 text-center text-xs text-obsidian-muted">
                No recent audit records available.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Active & Recent Incidents Table */}
        <Card className="lg:col-span-2 bg-obsidian-800 border-obsidian-700">
          <CardHeader className="flex flex-row items-center justify-between py-3.5 border-b border-obsidian-700">
            <div>
              <CardTitle>Active & Recent Production Incidents</CardTitle>
              <p className="text-xs text-obsidian-muted mt-0.5">
                Live alert ingestion and PostgreSQL incident datastore
              </p>
            </div>
            <Link to="/incidents">
              <Button variant="ghost" size="sm">
                <span>All Incidents</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-obsidian-900 border-b border-obsidian-700 text-obsidian-muted font-semibold uppercase tracking-wider font-mono text-[11px]">
                  <tr>
                    <th className="py-3 px-4">Incident Title</th>
                    <th className="py-3 px-4">Severity</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Source</th>
                    <th className="py-3 px-4">Created</th>
                    <th className="py-3 px-4 text-right">Inspect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-obsidian-700/60 font-sans">
                  {recentIncidents && recentIncidents.length > 0 ? (
                    recentIncidents.map((inc) => (
                      <tr key={inc.id} className="hover:bg-obsidian-750/50 transition-colors">
                        <td className="py-3 px-4 font-medium text-obsidian-text">
                          <Link
                            to={`/incidents/${inc.id}`}
                            className="hover:text-copper-400 transition-colors font-medium"
                          >
                            {inc.title}
                          </Link>
                        </td>
                        <td className="py-3 px-4">
                          <Badge variant={inc.severity}>{inc.severity.toUpperCase()}</Badge>
                        </td>
                        <td className="py-3 px-4">
                          <Badge
                            variant={
                              inc.status === "open"
                                ? "high"
                                : inc.status === "investigating"
                                ? "info"
                                : "low"
                            }
                          >
                            {inc.status.toUpperCase()}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 text-obsidian-muted font-mono text-[11px]">{inc.source}</td>
                        <td className="py-3 px-4 text-obsidian-muted font-mono text-[11px]">
                          {new Date(inc.created_at).toLocaleString([], {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <Link to={`/incidents/${inc.id}`}>
                            <Button variant="secondary" size="sm">
                              Inspect
                            </Button>
                          </Link>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="text-center py-8 text-obsidian-muted">
                        No incident records found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
