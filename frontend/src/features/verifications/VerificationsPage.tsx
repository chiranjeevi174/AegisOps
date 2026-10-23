import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ClipboardCheck,
  Plus,
  Eye,
  Info,
} from "lucide-react";
import { verificationsApi, executionsApi, authApi } from "@/services/api";
import type {
  VerificationSummary,
  VerificationDetail,
  VerificationOutcome,
} from "@/types/verification";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input, Select } from "@/components/ui/Input";
import { EmptyState, Skeleton, AlertMessage } from "@/components/ui/Feedback";

export const VerificationsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedVerification, setSelectedVerification] = useState<VerificationDetail | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [targetExecId, setTargetExecId] = useState("");
  const [baselineWindow, setBaselineWindow] = useState(15);
  const [followupWindow, setFollowupWindow] = useState(15);
  const [minSamples, setMinSamples] = useState(2);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: actor } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: authApi.getMe,
  });

  const { data: verifications, isLoading } = useQuery({
    queryKey: ["verifications"],
    queryFn: () => verificationsApi.list({ limit: 100 }),
  });

  const { data: executions } = useQuery({
    queryKey: ["executions"],
    queryFn: () => executionsApi.list({ limit: 50 }),
  });

  const { data: events } = useQuery({
    queryKey: ["verifications", selectedVerification?.id, "events"],
    queryFn: () => verificationsApi.getEvents(selectedVerification!.id),
    enabled: !!selectedVerification?.id,
  });

  const createMutation = useMutation({
    mutationFn: () => {
      if (!targetExecId) throw new Error("Please select an execution to verify.");
      return verificationsApi.create(targetExecId, {
        criteria: {
          baseline_window_minutes: Number(baselineWindow),
          followup_window_minutes: Number(followupWindow),
          min_samples_required: Number(minSamples),
          step: "15s",
        },
        idempotency_key: `verify-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      });
    },
    onSuccess: (data) => {
      setErrorMessage(null);
      setIsCreateModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ["verifications"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      setSelectedVerification(data);
      setIsDetailModalOpen(true);
    },
    onError: (err: any) => {
      setErrorMessage(err.message || "Failed to execute post-execution verification");
    },
  });

  const handleInspect = async (v: VerificationSummary) => {
    try {
      const full = await verificationsApi.get(v.id);
      setSelectedVerification(full);
      setIsDetailModalOpen(true);
    } catch (err: any) {
      setErrorMessage(err.message);
    }
  };

  const getOutcomeBadge = (outcome: VerificationOutcome) => {
    switch (outcome) {
      case "diagnostic_verified":
        return <Badge variant="success">DIAGNOSTIC VERIFIED</Badge>;
      case "not_applicable":
        return <Badge variant="default">NOT APPLICABLE (SIMULATION)</Badge>;
      case "inconclusive":
        return <Badge variant="warning">INCONCLUSIVE</Badge>;
      case "failed":
        return <Badge variant="danger">VERIFICATION FAILED</Badge>;
      default:
        return <Badge variant="outline">{outcome}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-tight flex items-center gap-2">
            <ClipboardCheck className="w-5 h-5 text-indigo-400" />
            Post-Execution Evidence Verification
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Statistical comparison between pre-execution baseline and post-execution observation windows.
          </p>
        </div>

        <Button
          variant="primary"
          onClick={() => {
            setErrorMessage(null);
            if (executions && executions.length > 0) {
              setTargetExecId(executions[0].id);
            }
            setIsCreateModalOpen(true);
          }}
          disabled={!actor?.can_verify}
        >
          <Plus className="w-4 h-4" />
          Create Verification
        </Button>
      </div>

      {errorMessage && (
        <AlertMessage type="error" title="Verification Error">
          {errorMessage}
        </AlertMessage>
      )}

      {/* Verifications Table */}
      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm flex items-center gap-2">
            <span>Recorded Verifications</span>
            <span className="text-xs font-mono text-slate-500">
              ({verifications?.length || 0})
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              <Skeleton className="h-10" />
              <Skeleton className="h-10" />
            </div>
          ) : !verifications || verifications.length === 0 ? (
            <EmptyState
              title="No Verifications Recorded"
              description="Click 'Create Verification' above to evaluate post-execution evidence for an existing execution."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/70 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Outcome</th>
                    <th className="py-3 px-4">Execution Mode</th>
                    <th className="py-3 px-4">Operation ID</th>
                    <th className="py-3 px-4">Duration</th>
                    <th className="py-3 px-4">Verifier</th>
                    <th className="py-3 px-4">Created Time</th>
                    <th className="py-3 px-4 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {verifications.map((v) => (
                    <tr key={v.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4 whitespace-nowrap">
                        {getOutcomeBadge(v.outcome)}
                      </td>
                      <td className="py-3 px-4 uppercase font-mono text-slate-300">
                        {v.execution_mode}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-300">{v.operation_id}</td>
                      <td className="py-3 px-4 font-mono text-slate-400">{v.duration_ms} ms</td>
                      <td className="py-3 px-4 text-slate-300">{v.requested_by}</td>
                      <td className="py-3 px-4 text-slate-400">
                        {new Date(v.requested_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleInspect(v)}
                        >
                          <Eye className="w-3.5 h-3.5" />
                          Inspect
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Verification Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Execute Post-Execution Verification"
        description="Verify evidence baseline against follow-up observation window."
        maxWidth="lg"
      >
        <div className="space-y-4 text-xs">
          <Select
            label="Target Remediation Execution *"
            value={targetExecId}
            onChange={(e) => setTargetExecId(e.target.value)}
            options={executions?.map((ex) => ({
              value: ex.id,
              label: `[${ex.mode.toUpperCase()}] ${ex.operation_id} | ${ex.id.slice(0, 8)}...`,
            }))}
          />

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Baseline Window (minutes)"
              type="number"
              min={1}
              max={120}
              value={baselineWindow}
              onChange={(e) => setBaselineWindow(Number(e.target.value))}
            />
            <Input
              label="Follow-up Window (minutes)"
              type="number"
              min={1}
              max={120}
              value={followupWindow}
              onChange={(e) => setFollowupWindow(Number(e.target.value))}
            />
          </div>

          <Input
            label="Minimum Samples Required"
            type="number"
            min={1}
            max={50}
            value={minSamples}
            onChange={(e) => setMinSamples(Number(e.target.value))}
          />

          <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-slate-400">
            <span className="font-semibold text-slate-300 block mb-0.5">Statistical Safety Policy:</span>
            Verification classifies observed directions (e.g. improved, degraded, unchanged) with strict mathematical tolerance (&epsilon; = 0.01).
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setIsCreateModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={() => createMutation.mutate()}
              isLoading={createMutation.isPending}
              disabled={!targetExecId}
            >
              Run Verification
            </Button>
          </div>
        </div>
      </Modal>

      {/* Verification Detail Modal */}
      {selectedVerification && (
        <Modal
          isOpen={isDetailModalOpen}
          onClose={() => setIsDetailModalOpen(false)}
          title={`Verification: ${selectedVerification.outcome.toUpperCase()}`}
          description={`Record ID: ${selectedVerification.id}`}
          maxWidth="xl"
        >
          <div className="space-y-4 text-xs">
            {/* Prominent Truthful Safeguards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 font-semibold block">Remediation Success Confirmed</span>
                <span className="text-rose-400 font-bold text-sm">
                  {selectedVerification.remediation_success_confirmed ? "TRUE" : "FALSE"}
                </span>
                <span className="text-[11px] text-slate-500 block mt-0.5">
                  Diagnostic operations do not modify systems
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 font-semibold block">Human Review Required</span>
                <span className="text-amber-400 font-bold text-sm">
                  {selectedVerification.human_review_required ? "TRUE (Mandatory)" : "FALSE"}
                </span>
                <span className="text-[11px] text-slate-500 block mt-0.5">
                  Final sign-off remains with operator
                </span>
              </div>
            </div>

            {/* Criteria & Windows */}
            <div className="p-3.5 bg-slate-950 rounded-lg border border-slate-800 font-mono space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-500">Baseline Window:</span>
                <span className="text-slate-200">
                  {selectedVerification.verification_criteria.baseline_window_minutes}m
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Follow-up Window:</span>
                <span className="text-slate-200">
                  {selectedVerification.verification_criteria.followup_window_minutes}m
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Query Resolution Step:</span>
                <span className="text-slate-200">
                  {selectedVerification.verification_criteria.step}
                </span>
              </div>
            </div>

            {/* Metric Comparison Data */}
            {selectedVerification.metric_comparison && (
              <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-2">
                <span className="font-semibold text-slate-200 block text-sm">
                  Statistical Metric Comparison:
                </span>
                <pre className="p-3 bg-slate-900 border border-slate-800 rounded text-emerald-300 font-mono text-[11px] overflow-x-auto">
                  {JSON.stringify(selectedVerification.metric_comparison, null, 2)}
                </pre>
              </div>
            )}

            {/* Limitations & Observations */}
            <div className="space-y-2">
              {selectedVerification.limitations?.map((lim, i) => (
                <div key={i} className="p-2.5 rounded bg-slate-950 border border-slate-800 text-slate-400 flex items-start gap-2">
                  <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span>{lim}</span>
                </div>
              ))}
            </div>

            {/* Audit Trail */}
            {events && events.length > 0 && (
              <div className="pt-2 border-t border-slate-800 space-y-2">
                <h4 className="font-semibold text-slate-400 uppercase tracking-wider text-[11px]">
                  Verification Audit Events ({events.length})
                </h4>
                <div className="space-y-1 max-h-36 overflow-y-auto">
                  {events.map((ev) => (
                    <div
                      key={ev.id}
                      className="p-2 rounded bg-slate-950 border border-slate-800 text-[11px] flex items-center justify-between"
                    >
                      <span className="font-semibold text-indigo-400">{ev.event_type}</span>
                      <span className="text-slate-500 font-mono">
                        {new Date(ev.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
};
