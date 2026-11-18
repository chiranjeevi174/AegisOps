import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Undo2,
  Plus,
  Eye,
  Info,
  RotateCcw,
} from "lucide-react";
import { rollbacksApi, executionsApi, authApi } from "@/services/api";
import type {
  RollbackAssessmentSummary,
  RollbackAssessmentDetail,
  RollbackExecutionDetail,
} from "@/types/rollback";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input, Select } from "@/components/ui/Input";
import { SafetyBanner } from "@/components/ui/SafetyBanner";
import { EmptyState, Skeleton, AlertMessage } from "@/components/ui/Feedback";

export const RollbacksPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedAssessment, setSelectedAssessment] = useState<RollbackAssessmentDetail | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [targetExecId, setTargetExecId] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Rollback execution state
  const [isRollbackModalOpen, setIsRollbackModalOpen] = useState(false);
  const [rollbackReason, setRollbackReason] = useState("Restoring telemetry baseline to pre-incident state");
  const [selectedRollbackExecution, setSelectedRollbackExecution] = useState<RollbackExecutionDetail | null>(null);
  const [isRollbackDetailModalOpen, setIsRollbackDetailModalOpen] = useState(false);
  const [rollbackConfirmChecked, setRollbackConfirmChecked] = useState(false);

  const { data: actor } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: authApi.getMe,
  });

  const { data: assessments, isLoading } = useQuery({
    queryKey: ["rollback-assessments"],
    queryFn: () => rollbacksApi.list({ limit: 100 }),
  });

  const { data: rollbackExecutions, isLoading: isLoadingRollbackExecs } = useQuery({
    queryKey: ["rollback-executions"],
    queryFn: () => rollbacksApi.listExecutions({ limit: 50 }),
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

  const executeRollbackMutation = useMutation({
    mutationFn: () => {
      if (!selectedAssessment) throw new Error("No assessment selected");
      return rollbacksApi.executeRollback({
        assessment_id: selectedAssessment.id,
        idempotency_key: `rb-exec-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        reason: rollbackReason,
      });
    },
    onSuccess: (data) => {
      setErrorMessage(null);
      setIsRollbackModalOpen(false);
      setIsDetailModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ["rollback-assessments"] });
      queryClient.invalidateQueries({ queryKey: ["rollback-executions"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      setSelectedRollbackExecution(data);
      setIsRollbackDetailModalOpen(true);
    },
    onError: (err: any) => {
      setErrorMessage(err.message || "Failed to execute rollback");
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

  const handleInspectRollbackExec = async (id: string) => {
    try {
      const full = await rollbacksApi.getExecution(id);
      setSelectedRollbackExecution(full);
      setIsRollbackDetailModalOpen(true);
    } catch (err: any) {
      setErrorMessage(err.message);
    }
  };

  return (
    <div className="space-y-6 text-obsidian-text select-none font-sans">
      <SafetyBanner />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-obsidian-text tracking-tight flex items-center gap-2">
            <Undo2 className="w-5 h-5 text-copper-400" />
            Rollback Readiness & Simulation Planner
          </h1>
          <p className="text-xs text-obsidian-muted mt-1">
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
      <Card className="bg-obsidian-800 border-obsidian-700">
        <CardHeader className="py-3 px-4 border-b border-obsidian-700">
          <CardTitle className="text-sm flex items-center gap-2">
            <span>Rollback Assessment Records</span>
            <span className="text-xs font-mono text-copper-400 font-semibold">
              ({assessments?.length || 0})
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              <Skeleton className="h-10 bg-obsidian-750" />
              <Skeleton className="h-10 bg-obsidian-750" />
            </div>
          ) : !assessments || assessments.length === 0 ? (
            <EmptyState
              title="No Rollback Assessments Recorded"
              description="Click 'Assess Rollback Readiness' above to evaluate an existing execution."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-obsidian-900 border-b border-obsidian-700 text-obsidian-muted font-semibold uppercase tracking-wider font-mono text-[11px]">
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
                <tbody className="divide-y divide-obsidian-700/60 font-sans">
                  {assessments.map((ra) => (
                    <tr key={ra.id} className="hover:bg-obsidian-750/50 transition-colors">
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
                      <td className="py-3 px-4 uppercase font-mono text-copper-300">
                        {ra.applicability}
                      </td>
                      <td className="py-3 px-4 font-mono">
                        <Badge variant={ra.risk_level === "high" ? "high" : "low"}>
                          {ra.risk_level.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 font-mono text-obsidian-text">{ra.operation_id}</td>
                      <td className="py-3 px-4 font-mono text-obsidian-muted">
                        {ra.execution_id.slice(0, 8)}...
                      </td>
                      <td className="py-3 px-4 text-obsidian-text font-mono text-[11px]">{ra.requested_by}</td>
                      <td className="py-3 px-4 text-obsidian-muted font-mono text-[11px]">
                        {new Date(ra.requested_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          variant="secondary"
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

      {/* Rollback Executions History Table */}
      <Card className="bg-obsidian-800 border-obsidian-700">
        <CardHeader className="py-3 px-4 border-b border-obsidian-700">
          <CardTitle className="text-sm flex items-center gap-2">
            <RotateCcw className="w-4 h-4 text-copper-400" />
            <span>Demo Rollback Execution History</span>
            <span className="text-xs font-mono text-copper-400 font-semibold">
              ({rollbackExecutions?.length || 0})
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoadingRollbackExecs ? (
            <div className="p-6 space-y-3">
              <Skeleton className="h-10 bg-obsidian-750" />
            </div>
          ) : !rollbackExecutions || rollbackExecutions.length === 0 ? (
            <EmptyState
              title="No Rollback Executions Recorded"
              description="Assess an executed remediation plan to initiate a demo rollback."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-obsidian-900 border-b border-obsidian-700 text-obsidian-muted font-semibold uppercase tracking-wider font-mono text-[11px]">
                  <tr>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Restored Scenario</th>
                    <th className="py-3 px-4">Operation ID</th>
                    <th className="py-3 px-4">Duration</th>
                    <th className="py-3 px-4">Operator</th>
                    <th className="py-3 px-4">Timestamp</th>
                    <th className="py-3 px-4 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-obsidian-700/60 font-sans">
                  {rollbackExecutions.map((rx) => (
                    <tr key={rx.id} className="hover:bg-obsidian-750/50 transition-colors">
                      <td className="py-3 px-4 whitespace-nowrap">
                        <Badge
                          variant={
                            rx.status === "executed"
                              ? "success"
                              : rx.status === "failed"
                              ? "danger"
                              : "default"
                          }
                        >
                          {rx.status.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 font-mono text-status-warning font-semibold">
                        {rx.restored_scenario || "default"}
                      </td>
                      <td className="py-3 px-4 font-mono text-obsidian-text">{rx.operation_id}</td>
                      <td className="py-3 px-4 font-mono text-obsidian-muted">{rx.duration_ms} ms</td>
                      <td className="py-3 px-4 text-obsidian-text font-mono text-[11px]">{rx.requested_by}</td>
                      <td className="py-3 px-4 text-obsidian-muted font-mono text-[11px]">
                        {new Date(rx.completed_at || rx.started_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleInspectRollbackExec(rx.id)}
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

          <div className="p-3 bg-obsidian-900 border border-obsidian-700 rounded-lg text-obsidian-secondary">
            <span className="font-semibold text-copper-400 block mb-0.5 font-mono">Simulation-Only Scope:</span>
            This assessment evaluates hypothetical reversibility, validates prerequisites, and formulates an advisory restoration simulation. It will not execute rollback actions.
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-obsidian-700">
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
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 p-3.5 bg-obsidian-900 rounded-lg border border-obsidian-700 font-mono text-center">
              <div className="p-2.5 rounded bg-obsidian-850 border border-obsidian-700">
                <span className="text-obsidian-muted block text-[11px]">Rollback Execution</span>
                <span className="text-status-critical font-bold block mt-1">
                  {selectedAssessment.rollback_execution_enabled ? "ENABLED" : "FALSE (DISABLED)"}
                </span>
              </div>
              <div className="p-2.5 rounded bg-obsidian-850 border border-obsidian-700">
                <span className="text-obsidian-muted block text-[11px]">Human Authorization</span>
                <span className="text-status-healthy font-bold block mt-1">
                  {selectedAssessment.human_authorization_required ? "MANDATORY TRUE" : "FALSE"}
                </span>
              </div>
              <div className="p-2.5 rounded bg-obsidian-850 border border-obsidian-700">
                <span className="text-obsidian-muted block text-[11px]">System Changes</span>
                <span className="text-status-healthy font-bold block mt-1">
                  {selectedAssessment.system_changes_performed ? "PERFORMED" : "FALSE (ZERO MUTATION)"}
                </span>
              </div>
            </div>

            {/* Truthful Applicability Notice */}
            <div className="p-3.5 rounded-lg bg-obsidian-900 border border-copper-400/30 text-obsidian-secondary">
              <div className="flex items-center gap-2 font-semibold text-copper-400">
                <Info className="w-4 h-4" />
                <span>Truthful Applicability Assessment</span>
              </div>
              <p className="mt-1 text-obsidian-text">
                Rollback: <strong>{selectedAssessment.applicability.toUpperCase()}</strong>.
                Execution mode was read-only; no infrastructure modifications occurred, so operational risk is minimal ({selectedAssessment.risk_level.toUpperCase()}).
              </p>
            </div>

            {/* Prerequisite Checks */}
            {selectedAssessment.assessment_data?.prerequisites && (
              <div className="space-y-2">
                <h4 className="font-semibold text-obsidian-muted uppercase tracking-wider text-[11px] font-mono">
                  Safety Prerequisite Evaluation
                </h4>
                <div className="space-y-1.5">
                  {selectedAssessment.assessment_data.prerequisites.map((p, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded bg-obsidian-900 border border-obsidian-700 flex items-start justify-between gap-3"
                    >
                      <div>
                        <span className="font-semibold text-obsidian-text block">{p.name}</span>
                        <p className="text-obsidian-muted text-[11px] mt-0.5">{p.details}</p>
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
              <div className="p-4 bg-obsidian-900 border border-obsidian-700 rounded-lg space-y-2">
                <span className="font-semibold text-obsidian-text text-sm block font-mono">
                  Simulation-Only Restoration Planning:
                </span>
                <div className="space-y-1.5 text-obsidian-secondary">
                  <p>
                    <strong className="text-obsidian-text">Target State:</strong> {selectedAssessment.simulation_result.simulated_target_state}
                  </p>
                  <p>
                    <strong className="text-obsidian-text">Risk Summary:</strong> {selectedAssessment.simulation_result.risk_assessment_summary}
                  </p>
                  {selectedAssessment.simulation_result.simulated_actions?.map((act, i) => (
                    <p key={i} className="text-copper-400 font-mono text-[11px]">
                      &bull; {act}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {/* Audit Trail */}
            {events && events.length > 0 && (
              <div className="pt-2 border-t border-obsidian-700 space-y-2">
                <h4 className="font-semibold text-obsidian-muted uppercase tracking-wider text-[11px] font-mono">
                  Assessment Audit Trail ({events.length} events)
                </h4>
                <div className="space-y-1 max-h-36 overflow-y-auto">
                  {events.map((ev) => (
                    <div
                      key={ev.id}
                      className="p-2 rounded bg-obsidian-900 border border-obsidian-700 text-[11px] flex items-center justify-between"
                    >
                      <span className="font-semibold text-copper-400 font-mono">{ev.event_type}</span>
                      <span className="text-obsidian-muted font-mono">
                        {new Date(ev.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action Trigger for Demo Rollback */}
            {selectedAssessment.applicability === "applicable" && (
              <div className="pt-3 border-t border-obsidian-700 flex justify-end">
                <Button
                  variant="danger"
                  onClick={() => {
                    setRollbackConfirmChecked(false);
                    setIsRollbackModalOpen(true);
                  }}
                  disabled={!actor?.can_execute}
                >
                  <Undo2 className="w-4 h-4" />
                  Execute Demo Rollback
                </Button>
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* Rollback Execution Confirmation Modal */}
      <Modal
        isOpen={isRollbackModalOpen}
        onClose={() => setIsRollbackModalOpen(false)}
        title="Execute Demo Rollback"
        description="Restore the pre-incident telemetry scenario on the isolated demo service."
        maxWidth="md"
      >
        <div className="space-y-4 text-xs">
          <div className="p-3 bg-status-critical/10 border border-status-critical/30 rounded-lg text-status-critical">
            <span className="font-semibold block mb-0.5 font-mono">Restoration Action:</span>
            This will revert the demo simulator (port 8001) to its pre-incident snapshot scenario, restoring degraded metrics for post-rollback verification.
          </div>

          <Input
            label="Rollback Reason *"
            value={rollbackReason}
            onChange={(e) => setRollbackReason(e.target.value)}
            placeholder="e.g. Verification complete, restoring degraded baseline"
          />

          <div className="flex items-start gap-2.5 pt-2">
            <input
              type="checkbox"
              id="confirm-rollback-execution"
              checked={rollbackConfirmChecked}
              onChange={(e) => setRollbackConfirmChecked(e.target.checked)}
              className="mt-1 rounded bg-obsidian-900 border-obsidian-700 text-copper-500 focus:ring-copper-400"
            />
            <label htmlFor="confirm-rollback-execution" className="text-xs text-obsidian-secondary cursor-pointer">
              I confirm restoration of the pre-incident telemetry state on the demo service.
            </label>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-obsidian-700">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setIsRollbackModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={() => executeRollbackMutation.mutate()}
              isLoading={executeRollbackMutation.isPending}
              disabled={!rollbackConfirmChecked || !rollbackReason.trim()}
            >
              Confirm & Execute Rollback
            </Button>
          </div>
        </div>
      </Modal>

      {/* Rollback Execution Detail Modal */}
      {selectedRollbackExecution && (
        <Modal
          isOpen={isRollbackDetailModalOpen}
          onClose={() => setIsRollbackDetailModalOpen(false)}
          title={`Rollback Execution: ${selectedRollbackExecution.status.toUpperCase()}`}
          description={`ID: ${selectedRollbackExecution.id}`}
          maxWidth="lg"
        >
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3.5 bg-obsidian-900 rounded-lg border border-obsidian-700 font-mono">
              <div>
                <span className="text-obsidian-muted block text-[11px]">Status</span>
                <span className="text-status-healthy font-bold uppercase">{selectedRollbackExecution.status}</span>
              </div>
              <div>
                <span className="text-obsidian-muted block text-[11px]">Restored Scenario</span>
                <span className="text-status-warning font-bold uppercase">{selectedRollbackExecution.restored_scenario}</span>
              </div>
              <div>
                <span className="text-obsidian-muted block text-[11px]">Duration</span>
                <span className="text-obsidian-text font-bold">{selectedRollbackExecution.duration_ms} ms</span>
              </div>
              <div>
                <span className="text-obsidian-muted block text-[11px]">Operator</span>
                <span className="text-obsidian-text font-bold">{selectedRollbackExecution.requested_by}</span>
              </div>
            </div>

            <div className="p-4 bg-obsidian-900 border border-obsidian-700 rounded-lg space-y-2">
              <span className="font-semibold text-obsidian-text text-sm block font-mono">
                Restored Telemetry State:
              </span>
              <pre className="p-3 bg-obsidian-950 border border-obsidian-700 rounded text-status-warning font-mono text-[11px] overflow-x-auto">
                {JSON.stringify(selectedRollbackExecution.restored_state, null, 2)}
              </pre>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
