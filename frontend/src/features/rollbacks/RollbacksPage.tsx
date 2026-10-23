import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Undo2,
  Plus,
  Eye,
  Info,
} from "lucide-react";
import { rollbacksApi, executionsApi, authApi } from "@/services/api";
import type {
  RollbackAssessmentSummary,
  RollbackAssessmentDetail,
} from "@/types/rollback";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Input";
import { SafetyBanner } from "@/components/ui/SafetyBanner";
import { EmptyState, Skeleton, AlertMessage } from "@/components/ui/Feedback";

export const RollbacksPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedAssessment, setSelectedAssessment] = useState<RollbackAssessmentDetail | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [targetExecId, setTargetExecId] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: actor } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: authApi.getMe,
  });

  const { data: assessments, isLoading } = useQuery({
    queryKey: ["rollback-assessments"],
    queryFn: () => rollbacksApi.list({ limit: 100 }),
  });

  const { data: executions } = useQuery({
    queryKey: ["executions"],
    queryFn: () => executionsApi.list({ limit: 50 }),
  });

  const { data: events } = useQuery({
    queryKey: ["rollback-assessments", selectedAssessment?.id, "events"],
    queryFn: () => rollbacksApi.getEvents(selectedAssessment!.id),
    enabled: !!selectedAssessment?.id,
  });

  const createMutation = useMutation({
    mutationFn: () => {
      if (!targetExecId) throw new Error("Please select an execution to assess.");
      return rollbacksApi.create(targetExecId, {
        idempotency_key: `rollback-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      });
    },
    onSuccess: (data) => {
      setErrorMessage(null);
      setIsCreateModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ["rollback-assessments"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      setSelectedAssessment(data);
      setIsDetailModalOpen(true);
    },
    onError: (err: any) => {
      setErrorMessage(err.message || "Failed to assess rollback readiness");
    },
  });

  const handleInspect = async (ra: RollbackAssessmentSummary) => {
    try {
      const full = await rollbacksApi.get(ra.id);
      setSelectedAssessment(full);
      setIsDetailModalOpen(true);
    } catch (err: any) {
      setErrorMessage(err.message);
    }
  };

  return (
    <div className="space-y-6">
      <SafetyBanner />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-tight flex items-center gap-2">
            <Undo2 className="w-5 h-5 text-indigo-400" />
            Rollback Readiness & Simulation Planner
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Pre-flight reversibility evaluation, prerequisite validation, and hypothetical restoration simulation.
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
          disabled={!actor?.can_assess_rollback}
        >
          <Plus className="w-4 h-4" />
          Assess Rollback Readiness
        </Button>
      </div>

      {errorMessage && (
        <AlertMessage type="error" title="Rollback Evaluation Error">
          {errorMessage}
        </AlertMessage>
      )}

      {/* Assessments History Table */}
      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm flex items-center gap-2">
            <span>Rollback Assessment Records</span>
            <span className="text-xs font-mono text-slate-500">
              ({assessments?.length || 0})
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              <Skeleton className="h-10" />
              <Skeleton className="h-10" />
            </div>
          ) : !assessments || assessments.length === 0 ? (
            <EmptyState
              title="No Rollback Assessments Recorded"
              description="Click 'Assess Rollback Readiness' above to evaluate an existing execution."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/70 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Readiness Status</th>
                    <th className="py-3 px-4">Applicability</th>
                    <th className="py-3 px-4">Risk Level</th>
                    <th className="py-3 px-4">Operation ID</th>
                    <th className="py-3 px-4">Execution UUID</th>
                    <th className="py-3 px-4">Assessor</th>
                    <th className="py-3 px-4">Timestamp</th>
                    <th className="py-3 px-4 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {assessments.map((ra) => (
                    <tr key={ra.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4 whitespace-nowrap">
                        <Badge
                          variant={
                            ra.readiness_status === "ready"
                              ? "success"
                              : ra.readiness_status === "not_applicable"
                              ? "default"
                              : "danger"
                          }
                        >
                          {ra.readiness_status.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 uppercase font-mono text-slate-300">
                        {ra.applicability}
                      </td>
                      <td className="py-3 px-4 font-mono">
                        <Badge variant={ra.risk_level === "high" ? "high" : "low"}>
                          {ra.risk_level.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-300">{ra.operation_id}</td>
                      <td className="py-3 px-4 font-mono text-slate-500">
                        {ra.execution_id.slice(0, 8)}...
                      </td>
                      <td className="py-3 px-4 text-slate-300">{ra.requested_by}</td>
                      <td className="py-3 px-4 text-slate-400">
                        {new Date(ra.requested_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleInspect(ra)}
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

      {/* Create Assessment Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Evaluate Rollback Readiness"
        description="Deterministic pre-flight assessment and hypothetical restoration planning."
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

          <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-slate-400">
            <span className="font-semibold text-slate-300 block mb-0.5">Simulation-Only Scope:</span>
            This assessment evaluates hypothetical reversibility, validates prerequisites, and formulates an advisory restoration simulation. It will not execute rollback actions.
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
              Run Assessment
            </Button>
          </div>
        </div>
      </Modal>

      {/* Assessment Detail Modal */}
      {selectedAssessment && (
        <Modal
          isOpen={isDetailModalOpen}
          onClose={() => setIsDetailModalOpen(false)}
          title={`Rollback Readiness: ${selectedAssessment.readiness_status.toUpperCase()}`}
          description={`Record ID: ${selectedAssessment.id}`}
          maxWidth="xl"
        >
          <div className="space-y-4 text-xs">
            {/* Safety Invariants Display */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 p-3.5 bg-slate-950 rounded-lg border border-slate-800 font-mono text-center">
              <div className="p-2 rounded bg-slate-900 border border-slate-800">
                <span className="text-slate-500 block text-[11px]">Rollback Execution</span>
                <span className="text-rose-400 font-bold block mt-1">
                  {selectedAssessment.rollback_execution_enabled ? "ENABLED" : "FALSE (DISABLED)"}
                </span>
              </div>
              <div className="p-2 rounded bg-slate-900 border border-slate-800">
                <span className="text-slate-500 block text-[11px]">Human Authorization</span>
                <span className="text-emerald-400 font-bold block mt-1">
                  {selectedAssessment.human_authorization_required ? "MANDATORY TRUE" : "FALSE"}
                </span>
              </div>
              <div className="p-2 rounded bg-slate-900 border border-slate-800">
                <span className="text-slate-500 block text-[11px]">System Changes</span>
                <span className="text-emerald-400 font-bold block mt-1">
                  {selectedAssessment.system_changes_performed ? "PERFORMED" : "FALSE (ZERO MUTATION)"}
                </span>
              </div>
            </div>

            {/* Truthful Applicability Notice */}
            <div className="p-3.5 rounded-lg bg-indigo-950/40 border border-indigo-900/60 text-indigo-200">
              <div className="flex items-center gap-2 font-semibold">
                <Info className="w-4 h-4 text-indigo-400" />
                <span>Truthful Applicability Assessment</span>
              </div>
              <p className="mt-1 text-slate-300">
                Rollback: <strong>{selectedAssessment.applicability.toUpperCase()}</strong>.
                Execution mode was read-only; no infrastructure modifications occurred, so operational risk is minimal ({selectedAssessment.risk_level.toUpperCase()}).
              </p>
            </div>

            {/* Prerequisite Checks */}
            {selectedAssessment.assessment_data?.prerequisites && (
              <div className="space-y-2">
                <h4 className="font-semibold text-slate-300 uppercase tracking-wider text-[11px]">
                  Safety Prerequisite Evaluation
                </h4>
                <div className="space-y-1.5">
                  {selectedAssessment.assessment_data.prerequisites.map((p, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded bg-slate-950 border border-slate-800 flex items-start justify-between gap-3"
                    >
                      <div>
                        <span className="font-semibold text-slate-200 block">{p.name}</span>
                        <p className="text-slate-400 text-[11px] mt-0.5">{p.details}</p>
                      </div>
                      <Badge size="sm" variant={p.satisfied ? "success" : "default"}>
                        {p.satisfied ? "PASS" : "INFO/BLOCKED"}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Simulation-Only Result */}
            {selectedAssessment.simulation_result && (
              <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-2">
                <span className="font-semibold text-slate-200 text-sm block">
                  Simulation-Only Restoration Planning:
                </span>
                <div className="space-y-1.5 text-slate-300">
                  <p>
                    <strong>Target State:</strong> {selectedAssessment.simulation_result.simulated_target_state}
                  </p>
                  <p>
                    <strong>Risk Summary:</strong> {selectedAssessment.simulation_result.risk_assessment_summary}
                  </p>
                  {selectedAssessment.simulation_result.simulated_actions?.map((act, i) => (
                    <p key={i} className="text-indigo-300 font-mono text-[11px]">
                      &bull; {act}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {/* Audit Trail */}
            {events && events.length > 0 && (
              <div className="pt-2 border-t border-slate-800 space-y-2">
                <h4 className="font-semibold text-slate-400 uppercase tracking-wider text-[11px]">
                  Assessment Audit Trail ({events.length} events)
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
