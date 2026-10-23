import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  SearchCode,
  Sparkles,
  Eye,
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
    queryFn: () => null, // populated by analyze mutation or cache
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-tight flex items-center gap-2">
            <SearchCode className="w-5 h-5 text-indigo-400" />
            Investigations & Root Cause Analysis
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Gemini-powered telemetry investigation, evidence verification, and multi-hypothesis root cause deduction.
          </p>
        </div>

        {/* Incident Selector */}
        <div className="w-full sm:w-72">
          <Select
            value={selectedIncidentId}
            onChange={(e) => setSelectedIncidentId(e.target.value)}
            disabled={isLoadingIncidents || analyzeMutation.isPending}
            options={incidents?.map((inc) => ({
              value: inc.id,
              label: `[${inc.severity.toUpperCase()}] ${inc.title.slice(0, 30)}...`,
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
        <Card className="bg-slate-900/60 border-slate-800 p-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <Badge variant={selectedIncident.severity}>
                  {selectedIncident.severity.toUpperCase()}
                </Badge>
                <h3 className="text-sm font-semibold text-slate-200">
                  {selectedIncident.title}
                </h3>
              </div>
              <p className="text-xs text-slate-400 mt-1 font-mono">
                Incident ID: {selectedIncident.id}
              </p>
            </div>
            <Button
              variant="primary"
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
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
              <Eye className="w-4 h-4 text-emerald-400" />
              <span>Observed Platform Evidence (Deterministic Telemetry)</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="p-4 bg-slate-900/90 border-slate-800">
                <span className="text-xs text-slate-400 block font-medium">Triage Priority</span>
                <span className="text-lg font-bold text-indigo-300 font-mono mt-1 block">
                  {analysis.priority || "P2"}
                </span>
                <span className="text-[11px] text-slate-500 block mt-1">
                  Escalation Required: {analysis.requires_escalation ? "YES" : "NO"}
                </span>
              </Card>

              <Card className="p-4 bg-slate-900/90 border-slate-800">
                <span className="text-xs text-slate-400 block font-medium">Telemetry Timestamp</span>
                <span className="text-xs font-mono text-slate-200 mt-1 block truncate">
                  {analysis.evidence_collected_at || "Live snapshot"}
                </span>
                <span className="text-[11px] text-emerald-400 block mt-1">
                  Verified Prometheus metrics captured
                </span>
              </Card>

              <Card className="p-4 bg-slate-900/90 border-slate-800">
                <span className="text-xs text-slate-400 block font-medium">Human Review Flag</span>
                <span className="text-sm font-semibold text-amber-300 mt-1 block">
                  Mandatory Operator Sign-off
                </span>
                <span className="text-[11px] text-slate-500 block mt-1">
                  Autonomous mutations prohibited
                </span>
              </Card>
            </div>

            {analysis.evidence && (
              <Card>
                <CardHeader className="py-2.5 px-4 bg-slate-950/40">
                  <CardTitle className="text-xs">Raw Prometheus Metrics</CardTitle>
                </CardHeader>
                <CardContent className="p-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
                    {Object.entries(analysis.evidence).map(([key, val]) => (
                      <div key={key} className="p-2.5 rounded bg-slate-950 border border-slate-800">
                        <span className="text-slate-500 text-[11px] block truncate">{key}</span>
                        <span className="text-slate-200 font-bold text-sm">{String(val ?? "null")}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Section 2: AI Investigation Summary */}
          {analysis.investigation && (
            <Card>
              <CardHeader className="py-3 px-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <SearchCode className="w-4 h-4 text-indigo-400" />
                    Agentic Investigation Observations
                  </CardTitle>
                  <Badge variant="info">
                    Confidence: {analysis.investigation.confidence || "MEDIUM"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-4 space-y-4 text-xs">
                <p className="text-slate-300 leading-relaxed bg-slate-950/60 p-3.5 rounded-lg border border-slate-800">
                  {analysis.investigation.summary}
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-lg">
                    <span className="font-semibold text-slate-300 block mb-2">
                      Key Telemetry Observations
                    </span>
                    <ul className="list-disc list-inside text-slate-400 space-y-1">
                      {analysis.investigation.observations?.map((obs: string, idx: number) => (
                        <li key={idx}>{obs}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-lg">
                    <span className="font-semibold text-slate-300 block mb-2">
                      Recommended Diagnostic Checks
                    </span>
                    <ul className="list-disc list-inside text-slate-400 space-y-1">
                      {analysis.investigation.recommended_checks?.map((chk: string, idx: number) => (
                        <li key={idx}>{chk}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Section 3: Root Cause Hypotheses (Distinguishing Hypotheses vs Truth) */}
          {analysis.rca && (
            <Card>
              <CardHeader className="py-3 px-4 flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    Root Cause Analysis (AI-Generated Hypotheses)
                  </CardTitle>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Hypotheses are analytical suggestions and must not be treated as confirmed without verification.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={analysis.rca.root_cause_confirmed ? "success" : "high"}>
                    Root Cause Confirmed: {analysis.rca.root_cause_confirmed ? "True" : "False"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-4 space-y-4">
                <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 text-xs text-slate-300">
                  <span className="text-slate-500 font-semibold block mb-0.5">RCA Summary:</span>
                  {analysis.rca.summary}
                </div>

                {analysis.rca.most_likely_hypothesis && (
                  <div className="p-3 bg-indigo-950/40 border border-indigo-800/60 rounded-lg text-xs">
                    <span className="text-indigo-400 font-semibold uppercase tracking-wider text-[11px] block">
                      Most Likely Hypothesis
                    </span>
                    <p className="text-slate-200 font-medium mt-1">
                      {analysis.rca.most_likely_hypothesis}
                    </p>
                  </div>
                )}

                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Evaluated Hypotheses Matrix
                  </h4>
                  {analysis.rca.hypotheses?.map((hypo, idx: number) => (
                    <div
                      key={idx}
                      className="p-4 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-2.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-200 text-sm">{hypo.title}</span>
                        <Badge variant="outline">Confidence: {hypo.confidence}</Badge>
                      </div>
                      <p className="text-slate-400">{hypo.description}</p>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 pt-1">
                        <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                          <span className="text-emerald-400 font-semibold block mb-1">
                            Supporting Evidence ({hypo.supporting_evidence?.length || 0})
                          </span>
                          <ul className="list-disc list-inside text-slate-400 space-y-0.5">
                            {hypo.supporting_evidence?.map((item: string, i: number) => (
                              <li key={i}>{item}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                          <span className="text-rose-400 font-semibold block mb-1">
                            Contradicting Evidence ({hypo.contradicting_evidence?.length || 0})
                          </span>
                          <ul className="list-disc list-inside text-slate-400 space-y-0.5">
                            {hypo.contradicting_evidence?.map((item: string, i: number) => (
                              <li key={i}>{item}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                          <span className="text-amber-400 font-semibold block mb-1">
                            Missing Evidence ({hypo.missing_evidence?.length || 0})
                          </span>
                          <ul className="list-disc list-inside text-slate-400 space-y-0.5">
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
              variant="primary"
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
