import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Sparkles,
  FileCheck2,
  Activity,
  AlertCircle,
} from "lucide-react";
import {
  incidentsApi,
  approvalsApi,
  executionsApi,
  verificationsApi,
  rollbacksApi,
} from "@/services/api";
import type { IncidentAnalysisResult } from "@/types/incident";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { SafetyBanner } from "@/components/ui/SafetyBanner";
import { AlertMessage, Skeleton, EmptyState } from "@/components/ui/Feedback";

export const IncidentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<
    "overview" | "investigation" | "remediation" | "approvals" | "executions" | "verifications" | "rollbacks"
  >("overview");
  const [actionError, setActionError] = useState<string | null>(null);

  // Load Incident
  const {
    data: incident,
    isLoading: isLoadingIncident,
    isError: isIncidentError,
  } = useQuery({
    queryKey: ["incidents", id],
    queryFn: () => incidentsApi.get(id!),
    enabled: !!id,
  });

  // Load Approvals for this incident
  const { data: approvals } = useQuery({
    queryKey: ["approvals", { incident_id: id }],
    queryFn: () => approvalsApi.list({ incident_id: id }),
    enabled: !!id,
  });

  // Load Executions for this incident
  const { data: executions } = useQuery({
    queryKey: ["executions", { incident_id: id }],
    queryFn: () => executionsApi.list({ incident_id: id }),
    enabled: !!id,
  });

  // Load Verifications for this incident
  const { data: verifications } = useQuery({
    queryKey: ["verifications", { incident_id: id }],
    queryFn: () => verificationsApi.list({ incident_id: id }),
    enabled: !!id,
  });

  // Load Rollback Assessments for this incident
  const { data: rollbackAssessments } = useQuery({
    queryKey: ["rollback-assessments", { incident_id: id }],
    queryFn: () => rollbacksApi.list({ incident_id: id }),
    enabled: !!id,
  });

  // Explicit AI workflow trigger mutation
  const analyzeMutation = useMutation({
    mutationFn: () => incidentsApi.analyze(id!),
    onSuccess: (data) => {
      setActionError(null);
      queryClient.setQueryData(["incidents", id, "analysis"], data);
      setActiveTab("investigation");
    },
    onError: (err: any) => {
      setActionError(err.message || "Failed to execute AI investigation workflow");
    },
  });

  // Read latest cached analysis or retrieve from approval if available
  const { data: liveAnalysis } = useQuery<IncidentAnalysisResult | null>({
    queryKey: ["incidents", id, "analysis"],
    queryFn: () => null, // populated by analyzeMutation or transient state
    enabled: false,
  });

  // Create Approval Request mutation
  const createApprovalMutation = useMutation({
    mutationFn: () => incidentsApi.createApproval(id!),
    onSuccess: () => {
      setActionError(null);
      queryClient.invalidateQueries({ queryKey: ["approvals", { incident_id: id }] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      setActiveTab("approvals");
    },
    onError: (err: any) => {
      setActionError(err.message || "Failed to create approval request");
    },
  });

  if (isLoadingIncident) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (isIncidentError || !incident) {
    return (
      <div className="p-8 text-center">
        <AlertCircle className="w-10 h-10 text-rose-500 mx-auto mb-2" />
        <h2 className="text-base font-semibold text-slate-200">Incident Not Found</h2>
        <p className="text-xs text-slate-400 mt-1">The requested incident ID does not exist in PostgreSQL.</p>
        <Link to="/incidents" className="mt-4 inline-block">
          <Button variant="secondary" size="sm">
            <ArrowLeft className="w-4 h-4" /> Back to Incidents
          </Button>
        </Link>
      </div>
    );
  }

  // Derive latest plan snapshot from the most recent approval if available
  const latestApproval = approvals && approvals.length > 0 ? approvals[0] : null;

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Action Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link to="/incidents">
            <button className="p-2 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors">
              <ArrowLeft className="w-4 h-4" />
            </button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <Badge variant={incident.severity}>{incident.severity.toUpperCase()}</Badge>
              <h1 className="text-lg font-bold text-slate-100">{incident.title}</h1>
              <Badge
                variant={
                  incident.status === "open"
                    ? "high"
                    : incident.status === "investigating"
                    ? "medium"
                    : "low"
                }
              >
                {incident.status.toUpperCase()}
              </Badge>
            </div>
            <p className="text-xs font-mono text-slate-500 mt-0.5">UUID: {incident.id}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => analyzeMutation.mutate()}
            isLoading={analyzeMutation.isPending}
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            Run AI Investigation & RCA
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => createApprovalMutation.mutate()}
            isLoading={createApprovalMutation.isPending}
          >
            <FileCheck2 className="w-3.5 h-3.5" />
            Create Approval Request
          </Button>
        </div>
      </div>

      {actionError && (
        <AlertMessage type="error" title="Workflow Action Error">
          {actionError}
        </AlertMessage>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 text-xs font-medium space-x-1 overflow-x-auto">
        {(
          [
            { id: "overview", label: "Incident Overview" },
            { id: "investigation", label: "AI Investigation & RCA" },
            { id: "remediation", label: "Remediation Plan" },
            { id: "approvals", label: `Approvals (${approvals?.length || 0})` },
            { id: "executions", label: `Executions (${executions?.length || 0})` },
            { id: "verifications", label: `Verifications (${verifications?.length || 0})` },
            { id: "rollbacks", label: `Rollbacks (${rollbackAssessments?.length || 0})` },
          ] as const
        ).map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 border-b-2 transition-colors whitespace-nowrap ${
              activeTab === tab.id
                ? "border-indigo-500 text-indigo-300 font-semibold"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab: Overview */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-2 space-y-6">
            <CardHeader className="py-4">
              <CardTitle>Description & Context</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-slate-300 leading-relaxed bg-slate-950/60 p-4 rounded-lg border border-slate-800 font-mono text-xs">
                {incident.description}
              </p>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2">
                <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800">
                  <span className="text-[11px] text-slate-500 block">Source</span>
                  <span className="text-xs font-medium text-slate-200 uppercase mt-0.5 block">
                    {incident.source}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800">
                  <span className="text-[11px] text-slate-500 block">Created At</span>
                  <span className="text-xs font-medium text-slate-200 mt-0.5 block">
                    {new Date(incident.created_at).toLocaleString()}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800">
                  <span className="text-[11px] text-slate-500 block">Alert State</span>
                  <span className="text-xs font-medium text-slate-200 mt-0.5 block">
                    {incident.alert_state || "Manual Entry"}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Alert Context Sidebar */}
          <Card>
            <CardHeader className="py-4">
              <CardTitle>Alertmanager Metadata</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div>
                <span className="text-slate-500 block">Fingerprint:</span>
                <span className="font-mono text-slate-300 break-all">
                  {incident.alert_fingerprint || "None (Manually reported)"}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Alert Started:</span>
                <span className="text-slate-300">
                  {incident.alert_started_at
                    ? new Date(incident.alert_started_at).toLocaleString()
                    : "Not specified"}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Last Alert Update:</span>
                <span className="text-slate-300">
                  {incident.alert_updated_at
                    ? new Date(incident.alert_updated_at).toLocaleString()
                    : "Not specified"}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab: Investigation & RCA */}
      {activeTab === "investigation" && (
        <div className="space-y-6">
          {liveAnalysis ? (
            <div className="space-y-6">
              {/* Triage & Evidence Snapshot */}
              <Card>
                <CardHeader className="py-3">
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-emerald-400" />
                    Observed Metric Telemetry & Triage Evidence
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="p-3 rounded bg-slate-950 border border-slate-800">
                      <span className="text-slate-500 block">Calculated Priority:</span>
                      <strong className="text-sm text-indigo-300 font-mono">
                        {liveAnalysis.priority || "P2"}
                      </strong>
                    </div>
                    <div className="p-3 rounded bg-slate-950 border border-slate-800">
                      <span className="text-slate-500 block">Escalation Required:</span>
                      <strong className="text-sm text-slate-200">
                        {liveAnalysis.requires_escalation ? "YES" : "NO"}
                      </strong>
                    </div>
                    <div className="p-3 rounded bg-slate-950 border border-slate-800">
                      <span className="text-slate-500 block">Evidence Collected At:</span>
                      <span className="text-xs text-slate-300 font-mono">
                        {liveAnalysis.evidence_collected_at || "Live snapshot"}
                      </span>
                    </div>
                  </div>

                  {liveAnalysis.evidence && (
                    <div className="mt-3">
                      <h5 className="text-xs font-semibold text-slate-400 mb-2">Metrics Snapshot:</h5>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-xs">
                        {Object.entries(liveAnalysis.evidence).map(([key, val]) => (
                          <div key={key} className="p-2 rounded bg-slate-950/70 border border-slate-800">
                            <span className="text-slate-500 block truncate">{key}</span>
                            <span className="text-slate-200 font-bold">{String(val ?? "null")}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* RCA Findings */}
              {liveAnalysis.rca && (
                <Card>
                  <CardHeader className="py-3 flex flex-row items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-indigo-400" />
                      Root Cause Analysis (AI Hypotheses)
                    </CardTitle>
                    <Badge variant="warning">
                      Root Cause Confirmed: {liveAnalysis.rca.root_cause_confirmed ? "True" : "False"}
                    </Badge>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-xs text-slate-300 bg-slate-950/50 p-3 rounded border border-slate-800">
                      {liveAnalysis.rca.summary}
                    </p>

                    <div className="space-y-3">
                      {liveAnalysis.rca.hypotheses?.map((hypo: any, idx: number) => (
                        <div
                          key={idx}
                          className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-2 text-xs"
                        >
                          <div className="flex items-center justify-between">
                            <h4 className="font-semibold text-slate-200 text-sm">{hypo.title}</h4>
                            <Badge variant="info">Confidence: {hypo.confidence}</Badge>
                          </div>
                          <p className="text-slate-400">{hypo.description}</p>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 pt-2">
                            <div className="p-2 rounded bg-slate-900 border border-slate-800">
                              <span className="text-emerald-400 font-semibold block mb-1">
                                Supporting Evidence
                              </span>
                              <ul className="list-disc list-inside text-slate-400 space-y-0.5">
                                {hypo.supporting_evidence?.map((e: string, i: number) => (
                                  <li key={i}>{e}</li>
                                ))}
                              </ul>
                            </div>
                            <div className="p-2 rounded bg-slate-900 border border-slate-800">
                              <span className="text-rose-400 font-semibold block mb-1">
                                Contradicting Evidence
                              </span>
                              <ul className="list-disc list-inside text-slate-400 space-y-0.5">
                                {hypo.contradicting_evidence?.map((e: string, i: number) => (
                                  <li key={i}>{e}</li>
                                ))}
                              </ul>
                            </div>
                            <div className="p-2 rounded bg-slate-900 border border-slate-800">
                              <span className="text-amber-400 font-semibold block mb-1">
                                Missing Evidence
                              </span>
                              <ul className="list-disc list-inside text-slate-400 space-y-0.5">
                                {hypo.missing_evidence?.map((e: string, i: number) => (
                                  <li key={i}>{e}</li>
                                ))}
                              </ul>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <EmptyState
              title="No AI Analysis Performed Yet"
              description="To perform root cause analysis and telemetry investigation, trigger the agentic workflow explicitly."
              action={
                <Button
                  variant="primary"
                  onClick={() => analyzeMutation.mutate()}
                  isLoading={analyzeMutation.isPending}
                >
                  <Sparkles className="w-4 h-4" />
                  Run AI Investigation & RCA
                </Button>
              }
            />
          )}
        </div>
      )}

      {/* Tab: Remediation Plan */}
      {activeTab === "remediation" && (
        <div className="space-y-6">
          <SafetyBanner compact />

          {latestApproval ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-slate-100">
                    Latest Approved / Proposed Plan (v{latestApproval.version})
                  </h3>
                  <p className="text-xs font-mono text-slate-500">
                    Hash: {latestApproval.plan_hash}
                  </p>
                </div>
                <Badge variant={latestApproval.status === "approved" ? "success" : "high"}>
                  {latestApproval.status.toUpperCase()}
                </Badge>
              </div>

              <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
                <p className="text-xs text-slate-300">
                  Remediation plans in AegisOps are strictly advisory. Actions require explicit operator authorization and binding to an approved plan.
                </p>
                <div className="flex gap-2">
                  <Link to="/approvals">
                    <Button variant="secondary" size="sm">
                      Inspect in Approvals
                    </Button>
                  </Link>
                  <Link to="/executions">
                    <Button variant="primary" size="sm">
                      Go to Executions Engine
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          ) : (
            <EmptyState
              title="No Remediation Plan Bound"
              description="Click 'Create Approval Request' to generate and evaluate a safety-validated remediation plan for this incident."
              action={
                <Button
                  variant="primary"
                  onClick={() => createApprovalMutation.mutate()}
                  isLoading={createApprovalMutation.isPending}
                >
                  <FileCheck2 className="w-4 h-4" />
                  Create Approval Request
                </Button>
              }
            />
          )}
        </div>
      )}

      {/* Tab: Approvals */}
      {activeTab === "approvals" && (
        <div className="space-y-4">
          {approvals && approvals.length > 0 ? (
            <div className="space-y-3">
              {approvals.map((app) => (
                <div
                  key={app.id}
                  className="p-4 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <strong className="text-slate-200">Approval Version {app.version}</strong>
                      <Badge variant={app.status === "approved" ? "success" : "high"}>
                        {app.status.toUpperCase()}
                      </Badge>
                    </div>
                    <p className="text-slate-400 font-mono text-[11px]">ID: {app.id}</p>
                    <p className="text-slate-500 text-[11px]">
                      Requested by {app.requested_by} at {new Date(app.requested_at).toLocaleString()}
                    </p>
                  </div>
                  <Link to="/approvals">
                    <Button variant="secondary" size="sm">
                      Manage Decision
                    </Button>
                  </Link>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No Approvals Recorded"
              description="No human approval requests have been submitted for this incident."
              action={
                <Button
                  variant="primary"
                  onClick={() => createApprovalMutation.mutate()}
                  isLoading={createApprovalMutation.isPending}
                >
                  Create Approval Request
                </Button>
              }
            />
          )}
        </div>
      )}

      {/* Tab: Executions */}
      {activeTab === "executions" && (
        <div className="space-y-4">
          {executions && executions.length > 0 ? (
            <div className="space-y-3">
              {executions.map((ex) => (
                <div
                  key={ex.id}
                  className="p-4 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Badge variant={ex.mode === "live_diagnostic" ? "warning" : "info"}>
                        {ex.mode.toUpperCase()}
                      </Badge>
                      <strong className="text-slate-200">{ex.operation_id}</strong>
                      <Badge variant="outline">{ex.status.toUpperCase()}</Badge>
                    </div>
                    <p className="text-slate-400 font-mono text-[11px]">Execution UUID: {ex.id}</p>
                    <p className="text-slate-500 text-[11px]">
                      Duration: {ex.duration_ms} ms | Started: {new Date(ex.started_at).toLocaleString()}
                    </p>
                  </div>
                  <Link to="/executions">
                    <Button variant="secondary" size="sm">
                      View Executions
                    </Button>
                  </Link>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No Executions Found"
              description="No simulation or read-only diagnostic runs have been performed for this incident."
              action={
                <Link to="/executions">
                  <Button variant="primary">Go to Executions</Button>
                </Link>
              }
            />
          )}
        </div>
      )}

      {/* Tab: Verifications */}
      {activeTab === "verifications" && (
        <div className="space-y-4">
          {verifications && verifications.length > 0 ? (
            <div className="space-y-3">
              {verifications.map((v) => (
                <div
                  key={v.id}
                  className="p-4 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between text-xs"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <Badge variant="info">{v.outcome.toUpperCase()}</Badge>
                      <strong className="text-slate-200">Operation: {v.operation_id}</strong>
                    </div>
                    <p className="text-slate-400 font-mono text-[11px] mt-1">Verification ID: {v.id}</p>
                  </div>
                  <Link to="/verifications">
                    <Button variant="secondary" size="sm">
                      View Verification
                    </Button>
                  </Link>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No Post-Execution Verifications"
              description="No statistical verification checks recorded for this incident's executions."
            />
          )}
        </div>
      )}

      {/* Tab: Rollbacks */}
      {activeTab === "rollbacks" && (
        <div className="space-y-4">
          {rollbackAssessments && rollbackAssessments.length > 0 ? (
            <div className="space-y-3">
              {rollbackAssessments.map((rb) => (
                <div
                  key={rb.id}
                  className="p-4 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between text-xs"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <Badge variant="default">{rb.readiness_status.toUpperCase()}</Badge>
                      <strong className="text-slate-200">Applicability: {rb.applicability}</strong>
                      <span className="text-slate-500 font-mono">Risk: {rb.risk_level.toUpperCase()}</span>
                    </div>
                    <p className="text-slate-400 font-mono text-[11px] mt-1">Assessment ID: {rb.id}</p>
                  </div>
                  <Link to="/rollbacks">
                    <Button variant="secondary" size="sm">
                      Inspect Assessment
                    </Button>
                  </Link>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No Rollback Assessments"
              description="No rollback readiness evaluations recorded for this incident."
            />
          )}
        </div>
      )}
    </div>
  );
};
