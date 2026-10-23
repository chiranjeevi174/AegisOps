import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  PlaySquare,
  Activity,
  ArrowRight,
  ExternalLink,
} from "lucide-react";
import { overviewApi, incidentsApi } from "@/services/api";
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
} from "recharts";

export const DashboardPage: React.FC = () => {
  const { data: overview, isLoading } = useQuery({
    queryKey: ["overview"],
    queryFn: overviewApi.getOverview,
  });

  const { data: telemetry } = useQuery({
    queryKey: ["overview", "telemetry"],
    queryFn: () => overviewApi.getTelemetry(30),
    refetchInterval: 15000,
  });

  const { data: recentIncidents } = useQuery({
    queryKey: ["incidents", "recent"],
    queryFn: () => incidentsApi.list(5, 0),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-20 w-full" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      </div>
    );
  }

  // Severity colors for pie chart
  const severityData = [
    { name: "Critical", value: overview?.incidents_by_severity?.critical || 0, color: "#f43f5e" },
    { name: "High", value: overview?.incidents_by_severity?.high || 0, color: "#f59e0b" },
    { name: "Medium", value: overview?.incidents_by_severity?.medium || 0, color: "#3b82f6" },
    { name: "Low", value: overview?.incidents_by_severity?.low || 0, color: "#10b981" },
  ].filter((d) => d.value > 0);

  return (
    <div className="space-y-6">
      {/* Top Safety Banner */}
      <SafetyBanner />

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-slate-900/80 border-slate-800">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-400">Open Incidents</p>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-bold text-slate-100">
                  {overview?.open_incidents ?? 0}
                </span>
                <span className="text-xs text-slate-500">
                  of {overview?.total_incidents ?? 0} total
                </span>
              </div>
            </div>
            <div className="p-3 rounded-xl bg-rose-950/50 border border-rose-900/60 text-rose-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900/80 border-slate-800">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-400">Pending Approvals</p>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-bold text-amber-300">
                  {overview?.pending_approvals ?? 0}
                </span>
                <span className="text-xs text-slate-500">
                  {overview?.total_approvals ?? 0} historical
                </span>
              </div>
            </div>
            <div className="p-3 rounded-xl bg-amber-950/50 border border-amber-900/60 text-amber-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900/80 border-slate-800">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-400">Completed Executions</p>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-bold text-indigo-300">
                  {overview?.total_executions ?? 0}
                </span>
                <span className="text-xs text-slate-500">
                  {overview?.total_verifications ?? 0} verified
                </span>
              </div>
            </div>
            <div className="p-3 rounded-xl bg-indigo-950/50 border border-indigo-900/60 text-indigo-400">
              <PlaySquare className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900/80 border-slate-800">
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-400">Service Availability</p>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-bold text-emerald-400">
                  {overview?.service_up ? "100%" : overview?.monitoring_available ? "0%" : "Telemetry N/A"}
                </span>
                <span className="text-xs text-slate-500">
                  {overview?.monitoring_available ? "Prometheus live" : "Prometheus offline"}
                </span>
              </div>
            </div>
            <div className="p-3 rounded-xl bg-emerald-950/50 border border-emerald-900/60 text-emerald-400">
              <Activity className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Service Availability Telemetry Chart */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between py-3">
            <div>
              <CardTitle>Service Availability History (Prometheus)</CardTitle>
              <p className="text-xs text-slate-400 mt-0.5">
                Metric: <code>aegisops_sim_service_up</code> (1.0 = UP, 0.0 = DOWN)
              </p>
            </div>
            <a
              href="http://localhost:3000"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors font-medium"
            >
              <span>View in Grafana</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </CardHeader>
          <CardContent className="p-4">
            {telemetry && telemetry.length > 0 ? (
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={telemetry} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="availabilityGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <XAxis
                      dataKey="timestamp"
                      stroke="#64748b"
                      fontSize={11}
                      tickLine={false}
                    />
                    <YAxis
                      domain={[0, 1.2]}
                      ticks={[0, 0.5, 1.0]}
                      stroke="#64748b"
                      fontSize={11}
                      tickLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0f172a",
                        borderColor: "#334155",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                    />
                    <Area
                      type="stepAfter"
                      dataKey="value"
                      stroke="#10b981"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#availabilityGrad)"
                      name="Availability"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-56 flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-800 rounded-lg">
                <Activity className="w-8 h-8 text-slate-600 mb-2" />
                <p className="text-xs text-slate-400 font-medium">
                  {overview?.monitoring_available
                    ? "Retrieving initial Prometheus samples..."
                    : "Prometheus telemetry unavailable. Ensure local Docker Prometheus is running on port 9090."}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Severity Distribution Pie */}
        <Card>
          <CardHeader className="py-3">
            <CardTitle>Incident Severity Distribution</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            {severityData.length > 0 ? (
              <div className="h-56 flex flex-col items-center justify-center">
                <ResponsiveContainer width="100%" height={160}>
                  <PieChart>
                    <Pie
                      data={severityData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={70}
                      paddingAngle={4}
                    >
                      {severityData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0f172a",
                        borderColor: "#334155",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex flex-wrap justify-center gap-3 mt-2 text-xs">
                  {severityData.map((d) => (
                    <div key={d.name} className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: d.color }} />
                      <span className="text-slate-300">{d.name} ({d.value})</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="h-56 flex items-center justify-center text-xs text-slate-500">
                No incident data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Incidents Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <div>
            <CardTitle>Active & Recent Incidents</CardTitle>
            <p className="text-xs text-slate-400 mt-0.5">
              Live records from PostgreSQL database
            </p>
          </div>
          <Link to="/incidents">
            <Button variant="ghost" size="sm">
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Title</th>
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Source</th>
                  <th className="py-3 px-4">Created</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {recentIncidents && recentIncidents.length > 0 ? (
                  recentIncidents.map((inc) => (
                    <tr key={inc.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4 font-medium text-slate-200">
                        <Link
                          to={`/incidents/${inc.id}`}
                          className="hover:text-indigo-400 transition-colors"
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
                              ? "medium"
                              : "low"
                          }
                        >
                          {inc.status.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-slate-400">{inc.source}</td>
                      <td className="py-3 px-4 text-slate-400">
                        {new Date(inc.created_at).toLocaleString()}
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
                    <td colSpan={6} className="text-center py-8 text-slate-500">
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
  );
};
