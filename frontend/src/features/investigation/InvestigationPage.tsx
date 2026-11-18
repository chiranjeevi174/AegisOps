import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  SearchCode,
  Sparkles,
  Eye,
  CheckCircle2,
} from "lucide-react";
import { incidentsApi } from "@/services/api";
import type { IncidentAnalysisResult } from "@/types/incident";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Input";
import { EmptyState, AlertMessage } from "@/components/ui/Feedback";

export const InvestigationPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedIncidentId, setSelectedIncidentId] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Load all incidents for selector
  const { data: incidents, isLoading: isLoadingIncidents } = useQuery({
    queryKey: ["incidents"],
    queryFn: () => incidentsApi.list(100, 0),
  });

  // Default to first incident if none selected
  React.useEffect(() => {
    if (incidents && incidents.length > 0 && !selectedIncidentId) {
      setSelectedIncidentId(incidents[0].id);
    }
  }, [incidents, selectedIncidentId]);

  // Read analysis from query cache
  const { data: analysis } = useQuery<IncidentAnalysisResult | null>({
    queryKey: ["incidents", selectedIncidentId, "analysis"],
    queryFn: () => null,
    enabled: !!selectedIncidentId,
  });

  const analyzeMutation = useMutation({
    mutationFn: () => incidentsApi.analyze(selectedIncidentId),
    onMutate: () => {
      setErrorMsg(null);
    },
    onSuccess: (data) => {
      setErrorMsg(null);
      queryClient.setQueryData(["incidents", selectedIncidentId, "analysis"], data);
    },
    onError: (err: any) => {
      setErrorMsg(err.message || "Failed to trigger AI investigation workflow");
    },
  });

  const selectedIncident = incidents?.find((i) => i.id === selectedIncidentId);

  return (
    <div className="space-y-6 text-obsidian-text select-none font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-obsidian-text tracking-tight flex items-center gap-2">
            <SearchCode className="w-5 h-5 text-ai-violet" />
            Investigations & Root Cause Analysis
          </h1>
          <p className="text-xs text-obsidian-muted mt-1">
            Gemini-powered telemetry investigation, evidence verification, and multi-hypothesis root cause deduction.
          </p>
        </div>

        {/* Incident Selector */}
        <div className="w-full sm:w-80">
          <Select
            value={selectedIncidentId}
            onChange={(e) => setSelectedIncidentId(e.target.value)}
            disabled={isLoadingIncidents || analyzeMutation.isPending}
            options={incidents?.map((inc) => ({
              value: inc.id,
              label: `[${inc.severity.toUpperCase()}] ${inc.title.slice(0, 32)}...`,
            }))}
          />
        </div>
      </div>

      {errorMsg && (
        <AlertMessage type="error" title="Workflow Error">
          {errorMsg}
        </AlertMessage>
      )}

      {selectedIncident && (
        <Card className="bg-obsidian-800 border-obsidian-700 p-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <Badge variant={selectedIncident.severity}>
                  {selectedIncident.severity.toUpperCase()}
                </Badge>
                <h3 className="text-sm font-semibold text-obsidian-text">
                  {selectedIncident.title}
                </h3>
              </div>
              <p className="text-xs text-obsidian-muted mt-1 font-mono text-[11px]">
                Incident ID: {selectedIncident.id}
              </p>
            </div>
            <Button
              variant="ai"
              size="sm"
              onClick={() => analyzeMutation.mutate()}
              isLoading={analyzeMutation.isPending}
            >
              <Sparkles className="w-3.5 h-3.5" />
              {analyzeMutation.isPending
                ? "Running Investigation..."
                : analysis
                ? "Re-Run AI Investigation"
                : "Execute AI Investigation"}
            </Button>
          </div>
        </Card>
      )}

      {/* Analysis Content */}
      {analysis ? (
        <div className="space-y-6">
          {/* Section 1: Strictly Observed Evidence */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-obsidian-text">
              <Eye className="w-4 h-4 text-status-healthy" />
              <span>Observed Platform Evidence (Deterministic Telemetry)</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="p-4 bg-obsidian-800 border-obsidian-700">
                <span className="text-xs text-obsidian-muted block font-medium font-mono">Triage Priority</span>
                <span className="text-lg font-bold text-copper-400 font-mono mt-1 block">
                  {analysis.priority || "P2"}
                </span>
                <span className="text-[11px] text-obsidian-muted block mt-1">
                  Escalation Required: <strong className="text-obsidian-text">{analysis.requires_escalation ? "YES" : "NO"}</strong>
                </span>
              </Card>

              <Card className="p-4 bg-obsidian-800 border-obsidian-700">
                <span className="text-xs text-obsidian-muted block font-medium font-mono">Telemetry Timestamp</span>
                <span className="text-xs font-mono text-copper-300 mt-1 block truncate">
                  {analysis.evidence_collected_at || "Live snapshot"}
                </span>
                <span className="text-[11px] text-status-healthy block mt-1 flex items-center gap-1 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Verified Prometheus metrics captured
                </span>
              </Card>

              <Card className="p-4 bg-obsidian-800 border-obsidian-700">
                <span className="text-xs text-obsidian-muted block font-medium font-mono">Human Review Flag</span>
                <span className="text-sm font-semibold text-status-warning mt-1 block">
                  Mandatory Operator Sign-off
                </span>
                <span className="text-[11px] text-obsidian-muted block mt-1">
                  Autonomous mutations prohibited
                </span>
              </Card>
            </div>

            {analysis.evidence && (
              <Card className="bg-obsidian-800 border-obsidian-700">
                <CardHeader className="py-2.5 px-4 bg-obsidian-900/60 border-b border-obsidian-700">
                  <CardTitle className="text-xs font-mono text-obsidian-secondary uppercase tracking-wider">Raw Prometheus Metrics</CardTitle>
                </CardHeader>
                <CardContent className="p-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
                    {Object.entries(analysis.evidence).map(([key, val]) => (
                      <div key={key} className="p-2.5 rounded bg-obsidian-900 border border-obsidian-700">
                        <span className="text-obsidian-muted text-[11px] block truncate">{key}</span>
                        <span className="text-obsidian-text font-bold text-sm">{String(val ?? "null")}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Section 2: AI Investigation Summary */}
          {analysis.investigation && (
            <Card className="bg-obsidian-800 border-obsidian-700">
              <CardHeader className="py-3 px-4 border-b border-obsidian-700">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <SearchCode className="w-4 h-4 text-ai-violet" />
                    Agentic Investigation Observations
                  </CardTitle>
                  <Badge variant="ai">
                    Confidence: {analysis.investigation.confidence || "MEDIUM"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-4 space-y-4 text-xs">
                <p className="text-obsidian-secondary leading-relaxed bg-obsidian-900 p-3.5 rounded-lg border border-obsidian-700 font-mono">
                  {analysis.investigation.summary}
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-3 bg-obsidian-900 border border-obsidian-700 rounded-lg">
                    <span className="font-semibold text-obsidian-text block mb-2 font-mono text-[11px]">
                      Key Telemetry Observations
                    </span>
                    <ul className="list-disc list-inside text-obsidian-secondary space-y-1 text-[11px]">
                      {analysis.investigation.observations?.map((obs: string, idx: number) => (
                        <li key={idx}>{obs}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-3 bg-obsidian-900 border border-obsidian-700 rounded-lg">
                    <span className="font-semibold text-copper-400 block mb-2 font-mono text-[11px]">
                      Recommended Diagnostic Checks
                    </span>
                    <ul className="list-disc list-inside text-obsidian-secondary space-y-1 text-[11px] font-mono">
                      {analysis.investigation.recommended_checks?.map((chk: string, idx: number) => (
                        <li key={idx}>{chk}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Section 3: Root Cause Hypotheses */}
          {analysis.rca && (
            <Card className="bg-obsidian-800 border-obsidian-700">
              <CardHeader className="py-3.5 px-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-obsidian-700">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-ai-violet" />
                    Root Cause Analysis (AI-Generated Hypotheses)
                  </CardTitle>
                  <p className="text-[11px] text-obsidian-muted mt-0.5">
                    Hypotheses are analytical suggestions and must not be treated as confirmed without verification.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={analysis.rca.root_cause_confirmed ? "success" : "warning"}>
                    Root Cause Confirmed: {analysis.rca.root_cause_confirmed ? "True" : "False"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-4 space-y-4">
                <div className="p-3.5 bg-obsidian-900 rounded-lg border border-obsidian-700 text-xs text-obsidian-secondary">
                  <span className="text-obsidian-muted font-semibold block mb-0.5 font-mono text-[11px]">RCA Summary:</span>
                  {analysis.rca.summary}
                </div>

                {analysis.rca.most_likely_hypothesis && (
                  <div className="p-3.5 bg-ai-violet/10 border border-ai-violet/30 rounded-lg text-xs">
                    <span className="text-ai-violet font-semibold uppercase tracking-wider text-[11px] block font-mono">
                      Most Likely Hypothesis
                    </span>
                    <p className="text-obsidian-text font-medium mt-1">
                      {analysis.rca.most_likely_hypothesis}
                    </p>
                  </div>
                )}

                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-obsidian-muted uppercase tracking-wider font-mono">
                    Evaluated Hypotheses Matrix
                  </h4>
                  {analysis.rca.hypotheses?.map((hypo, idx: number) => (
                    <div
                      key={idx}
                      className="p-4 rounded-lg bg-obsidian-900 border border-obsidian-700 text-xs space-y-2.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-obsidian-text text-sm">{hypo.title}</span>
                        <Badge variant="outline">Confidence: {hypo.confidence}</Badge>
                      </div>
                      <p className="text-obsidian-secondary">{hypo.description}</p>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 pt-1">
                        <div className="p-2.5 rounded bg-obsidian-850 border border-obsidian-700">
                          <span className="text-status-healthy font-semibold block mb-1 font-mono text-[11px]">
                            Supporting Evidence ({hypo.supporting_evidence?.length || 0})
                          </span>
                          <ul className="list-disc list-inside text-obsidian-secondary space-y-0.5 text-[11px]">
                            {hypo.supporting_evidence?.map((item: string, i: number) => (
                              <li key={i}>{item}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="p-2.5 rounded bg-obsidian-850 border border-obsidian-700">
                          <span className="text-status-critical font-semibold block mb-1 font-mono text-[11px]">
                            Contradicting Evidence ({hypo.contradicting_evidence?.length || 0})
                          </span>
                          <ul className="list-disc list-inside text-obsidian-secondary space-y-0.5 text-[11px]">
                            {hypo.contradicting_evidence?.map((item: string, i: number) => (
                              <li key={i}>{item}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="p-2.5 rounded bg-obsidian-850 border border-obsidian-700">
                          <span className="text-status-warning font-semibold block mb-1 font-mono text-[11px]">
                            Missing Evidence ({hypo.missing_evidence?.length || 0})
                          </span>
                          <ul className="list-disc list-inside text-obsidian-secondary space-y-0.5 text-[11px]">
                            {hypo.missing_evidence?.map((item: string, i: number) => (
                              <li key={i}>{item}</li>
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
          title={
            analyzeMutation.isPending
              ? "Running Multi-Agent Investigation"
              : "No Investigation Cached For This Incident"
          }
          description={
            analyzeMutation.isPending
              ? "Executing LangGraph multi-agent workflow: Triage -> Prometheus Metric Snapshot -> Historical Telemetry Window -> Gemini RCA & Safety-Validated Remediation Plan. Please wait..."
              : "Click below to run the LangGraph workflow: Triage -> Prometheus Snapshot -> Historical Evidence -> Gemini RCA."
          }
          action={
            <Button
              variant="ai"
              onClick={() => analyzeMutation.mutate()}
              isLoading={analyzeMutation.isPending}
            >
              <Sparkles className="w-4 h-4" />
              {analyzeMutation.isPending ? "Investigating..." : "Execute AI Investigation"}
            </Button>
          }
        />
      )}
    </div>
  );
};
