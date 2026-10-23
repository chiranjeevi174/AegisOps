import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  PlaySquare,
  Activity,
  Terminal,
  Eye,
} from "lucide-react";
import { executionsApi, approvalsApi, authApi } from "@/services/api";
import type {
  Execution,
  ExecutionDetail,
} from "@/types/execution";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input, Select } from "@/components/ui/Input";
import { SafetyBanner } from "@/components/ui/SafetyBanner";
import { EmptyState, Skeleton, AlertMessage } from "@/components/ui/Feedback";

export const ExecutionsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedExecution, setSelectedExecution] = useState<ExecutionDetail | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isSimulateModalOpen, setIsSimulateModalOpen] = useState(false);
  const [isDiagnoseModalOpen, setIsDiagnoseModalOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Form states
  const [selectedApprovalId, setSelectedApprovalId] = useState("");
  const [selectedOpId, setSelectedOpId] = useState("");
  const [recIndex, setRecIndex] = useState(1);
  const [liveConfirmChecked, setLiveConfirmChecked] = useState(false);

  // Load current user profile
  const { data: actor } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: authApi.getMe,
  });

  // Load allowlisted operation registry
  const { data: operations, isLoading: isLoadingOps } = useQuery({
    queryKey: ["execution-operations"],
    queryFn: executionsApi.getOperations,
  });

  // Load executions history
  const { data: executions, isLoading: isLoadingExecs } = useQuery({
    queryKey: ["executions"],
    queryFn: () => executionsApi.list({ limit: 100 }),
  });

  // Load approved approvals for dropdown
  const { data: approvedRequests } = useQuery({
    queryKey: ["approvals", { status: "approved" }],
    queryFn: () => approvalsApi.list({ status: "approved", limit: 50 }),
  });

  // Load execution events when inspecting
  const { data: executionEvents } = useQuery({
    queryKey: ["executions", selectedExecution?.id, "events"],
    queryFn: () => executionsApi.getEvents(selectedExecution!.id),
    enabled: !!selectedExecution?.id,
  });

  // Simulation Mutation
  const simulateMutation = useMutation({
    mutationFn: () => {
      const selectedApproval = approvedRequests?.find((a) => a.id === selectedApprovalId);
      if (!selectedApproval) throw new Error("Please select an approved remediation plan.");
      const op = operations?.find((o) => o.id === selectedOpId);
      if (!op) throw new Error("Please select an allowlisted operation.");

      return executionsApi.simulate({
        approval_id: selectedApproval.id,
        incident_id: selectedApproval.incident_id,
        operation_id: op.id,
        recommendation_index: Number(recIndex),
        idempotency_key: `sim-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        parameters: {},
      });
    },
    onSuccess: (data) => {
      setErrorMessage(null);
      setIsSimulateModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ["executions"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      setSelectedExecution(data);
      setIsDetailModalOpen(true);
    },
    onError: (err: any) => {
      setErrorMessage(err.message || "Simulation failed");
    },
  });

  // Live Diagnostic Mutation
  const diagnoseMutation = useMutation({
    mutationFn: () => {
      const selectedApproval = approvedRequests?.find((a) => a.id === selectedApprovalId);
      if (!selectedApproval) throw new Error("Please select an approved remediation plan.");
      const op = operations?.find((o) => o.id === selectedOpId);
      if (!op) throw new Error("Please select an allowlisted operation.");

      return executionsApi.diagnose({
        approval_id: selectedApproval.id,
        incident_id: selectedApproval.incident_id,
        operation_id: op.id,
        recommendation_index: Number(recIndex),
        idempotency_key: `diag-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        parameters: {},
      });
    },
    onSuccess: (data) => {
      setErrorMessage(null);
      setIsDiagnoseModalOpen(false);
      setLiveConfirmChecked(false);
      queryClient.invalidateQueries({ queryKey: ["executions"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      setSelectedExecution(data);
      setIsDetailModalOpen(true);
    },
    onError: (err: any) => {
      setErrorMessage(err.message || "Live diagnostic execution failed");
    },
  });

  const handleInspect = async (exec: Execution) => {
    try {
      const detail = await executionsApi.get(exec.id);
      setSelectedExecution(detail);
      setIsDetailModalOpen(true);
    } catch (err: any) {
      setErrorMessage(err.message);
    }
  };

  // Set default values when opening modal
  const openSimulateModal = () => {
    setErrorMessage(null);
    if (approvedRequests && approvedRequests.length > 0) {
      setSelectedApprovalId(approvedRequests[0].id);
    }
    if (operations && operations.length > 0) {
      setSelectedOpId(operations[0].id);
    }
    setRecIndex(1);
    setIsSimulateModalOpen(true);
  };

  const openDiagnoseModal = () => {
    setErrorMessage(null);
    setLiveConfirmChecked(false);
    if (approvedRequests && approvedRequests.length > 0) {
      setSelectedApprovalId(approvedRequests[0].id);
    }
    if (operations && operations.length > 0) {
      const liveOp = operations.find((o) => o.live_diagnostic_supported) || operations[0];
      setSelectedOpId(liveOp.id);
    }
    setRecIndex(1);
    setIsDiagnoseModalOpen(true);
  };

  return (
    <div className="space-y-6">
      <SafetyBanner />

      {/* Header and Action Triggers */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-tight flex items-center gap-2">
            <PlaySquare className="w-5 h-5 text-indigo-400" />
            Controlled Execution Engine
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Execute dry-run simulations or restricted read-only Prometheus live diagnostics bound to approved plans.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={openSimulateModal}
            disabled={!actor?.can_execute}
          >
            <PlaySquare className="w-4 h-4 text-indigo-400" />
            Dry-Run Simulation
          </Button>
          <Button
            variant="primary"
            onClick={openDiagnoseModal}
            disabled={!actor?.can_execute}
          >
            <Activity className="w-4 h-4 text-emerald-400" />
            Run Live Diagnostic
          </Button>
        </div>
      </div>

      {errorMessage && (
        <AlertMessage type="error" title="Execution Error">
          {errorMessage}
        </AlertMessage>
      )}

      {/* Operation Registry Cards */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Immutable Allowlisted Operations Registry
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {isLoadingOps ? (
            <Skeleton className="h-32" />
          ) : (
            operations?.map((op) => (
              <Card key={op.id} className="bg-slate-900 border-slate-800">
                <CardHeader className="py-3 px-4 flex flex-row items-center justify-between border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-indigo-400" />
                    <CardTitle className="text-xs font-mono">{op.id}</CardTitle>
                  </div>
                  <Badge variant={op.risk_level === "high" ? "high" : "low"}>
                    {op.risk_level.toUpperCase()}
                  </Badge>
                </CardHeader>
                <CardContent className="p-4 space-y-2.5 text-xs">
                  <p className="text-slate-300 font-medium">{op.name}</p>
                  <p className="text-slate-400 text-[11px] leading-relaxed">{op.description}</p>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    <span className="text-[10px] px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-400">
                      Modes: {op.supported_modes?.join(", ") || "simulation, live_diagnostic"}
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-emerald-400">
                      Read-Only: {op.is_read_only ? "YES" : "NO"}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>

      {/* Execution History Table */}
      <Card>
        <CardHeader className="py-3 px-4 flex flex-row items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <span>Execution Audit Records</span>
            <span className="text-xs font-mono text-slate-500">
              ({executions?.length || 0})
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoadingExecs ? (
            <div className="p-6 space-y-3">
              <Skeleton className="h-10" />
              <Skeleton className="h-10" />
            </div>
          ) : !executions || executions.length === 0 ? (
            <EmptyState
              title="No Executions Recorded"
              description="Click 'Dry-Run Simulation' or 'Run Live Diagnostic' above to trigger an execution."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/70 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Mode</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Operation ID</th>
                    <th className="py-3 px-4">Recommendation</th>
                    <th className="py-3 px-4">Duration</th>
                    <th className="py-3 px-4">Operator</th>
                    <th className="py-3 px-4">Timestamp</th>
                    <th className="py-3 px-4 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {executions.map((ex) => (
                    <tr key={ex.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4 whitespace-nowrap">
                        <Badge variant={ex.mode === "live_diagnostic" ? "warning" : "info"}>
                          {ex.mode.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <Badge variant={ex.status === "failed" ? "danger" : "default"}>
                          {ex.status.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-300">{ex.operation_id}</td>
                      <td className="py-3 px-4 text-slate-300 max-w-xs truncate">
                        {ex.selected_recommendation_title}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-400">{ex.duration_ms} ms</td>
                      <td className="py-3 px-4 text-slate-300">{ex.requested_by}</td>
                      <td className="py-3 px-4 text-slate-400">
                        {new Date(ex.started_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleInspect(ex)}
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

      {/* Simulation Modal */}
      <Modal
        isOpen={isSimulateModalOpen}
        onClose={() => setIsSimulateModalOpen(false)}
        title="Execute Dry-Run Simulation"
        description="Simulate execution of an allowlisted operation bound to an approved plan."
        maxWidth="lg"
      >
        <div className="space-y-4">
          <Select
            label="Select Approved Remediation Plan *"
            value={selectedApprovalId}
            onChange={(e) => setSelectedApprovalId(e.target.value)}
            options={approvedRequests?.map((a) => ({
              value: a.id,
              label: `Version ${a.version} | Hash: ${a.plan_hash.slice(0, 12)}... | Incident: ${a.incident_id.slice(0, 8)}...`,
            }))}
          />

          <Select
            label="Select Allowlisted Operation *"
            value={selectedOpId}
            onChange={(e) => setSelectedOpId(e.target.value)}
            options={operations?.map((o) => ({
              value: o.id,
              label: `${o.name} (${o.id})`,
            }))}
          />

          <Input
            label="Recommendation Index (1-based)"
            type="number"
            min={1}
            max={5}
            value={recIndex}
            onChange={(e) => setRecIndex(Number(e.target.value))}
          />

          <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-400">
            <span className="font-semibold text-slate-300 block mb-0.5">Safety Guarantee:</span>
            Simulation runs in a synthetic dry-run sandbox. Zero infrastructure commands or mutations are executed.
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setIsSimulateModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={() => simulateMutation.mutate()}
              isLoading={simulateMutation.isPending}
              disabled={!selectedApprovalId || !selectedOpId}
            >
              Execute Simulation
            </Button>
          </div>
        </div>
      </Modal>

      {/* Live Diagnostic Modal */}
      <Modal
        isOpen={isDiagnoseModalOpen}
        onClose={() => setIsDiagnoseModalOpen(false)}
        title="Execute Read-Only Live Diagnostic"
        description="Query live Prometheus telemetry bound to an approved remediation plan."
        maxWidth="lg"
      >
        <div className="space-y-4">
          <div className="p-3 bg-amber-950/40 border border-amber-900/60 rounded-lg text-xs text-amber-200">
            <span className="font-semibold block mb-0.5">Strict Read-Only Verification:</span>
            Live diagnostic execution queries Prometheus metric endpoints. No server restarts, configuration modifications, or command-line mutations will occur.
          </div>

          <Select
            label="Select Approved Remediation Plan *"
            value={selectedApprovalId}
            onChange={(e) => setSelectedApprovalId(e.target.value)}
            options={approvedRequests?.map((a) => ({
              value: a.id,
              label: `Version ${a.version} | Hash: ${a.plan_hash.slice(0, 12)}... | Incident: ${a.incident_id.slice(0, 8)}...`,
            }))}
          />

          <Select
            label="Select Diagnostic Operation *"
            value={selectedOpId}
            onChange={(e) => setSelectedOpId(e.target.value)}
            options={operations
              ?.filter((o) => o.live_diagnostic_supported)
              .map((o) => ({
                value: o.id,
                label: `${o.name} (${o.id})`,
              }))}
          />

          <Input
            label="Recommendation Index (1-based)"
            type="number"
            min={1}
            max={5}
            value={recIndex}
            onChange={(e) => setRecIndex(Number(e.target.value))}
          />

          <div className="flex items-start gap-2.5 pt-2">
            <input
              type="checkbox"
              id="confirm-diagnostic"
              checked={liveConfirmChecked}
              onChange={(e) => setLiveConfirmChecked(e.target.checked)}
              className="mt-1 rounded bg-slate-950 border-slate-800 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="confirm-diagnostic" className="text-xs text-slate-300">
              I confirm that this operation is read-only and authorized by the linked approval request.
            </label>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setIsDiagnoseModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={() => diagnoseMutation.mutate()}
              isLoading={diagnoseMutation.isPending}
              disabled={!liveConfirmChecked || !selectedApprovalId || !selectedOpId}
            >
              Execute Diagnostic
            </Button>
          </div>
        </div>
      </Modal>

      {/* Execution Inspection Modal */}
      {selectedExecution && (
        <Modal
          isOpen={isDetailModalOpen}
          onClose={() => setIsDetailModalOpen(false)}
          title={`Execution Result: ${selectedExecution.operation_id}`}
          description={`ID: ${selectedExecution.id}`}
          maxWidth="xl"
        >
          <div className="space-y-4 text-xs">
            {/* Summary Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3.5 bg-slate-950 rounded-lg border border-slate-800 font-mono">
              <div>
                <span className="text-slate-500 block text-[11px]">Mode</span>
                <span className="text-indigo-300 font-bold uppercase">{selectedExecution.mode}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[11px]">Status</span>
                <span className="text-slate-200 font-bold uppercase">{selectedExecution.status}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[11px]">Duration</span>
                <span className="text-slate-200 font-bold">{selectedExecution.duration_ms} ms</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[11px]">System Changes</span>
                <span className="text-emerald-400 font-bold">FALSE</span>
              </div>
            </div>

            {/* Diagnostic Result */}
            {selectedExecution.diagnostic_result && (
              <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-2">
                <span className="font-semibold text-slate-200 text-sm block">
                  Prometheus Telemetry Result:
                </span>
                <pre className="p-3 bg-slate-900 border border-slate-800 rounded text-emerald-300 font-mono text-[11px] overflow-x-auto">
                  {JSON.stringify(selectedExecution.diagnostic_result, null, 2)}
                </pre>
              </div>
            )}

            {/* Simulation Result */}
            {selectedExecution.simulation_result && (
              <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-2">
                <span className="font-semibold text-slate-200 text-sm block">
                  Simulation Dry-Run Result:
                </span>
                <pre className="p-3 bg-slate-900 border border-slate-800 rounded text-indigo-300 font-mono text-[11px] overflow-x-auto">
                  {JSON.stringify(selectedExecution.simulation_result, null, 2)}
                </pre>
              </div>
            )}

            {/* Audit Trail */}
            {executionEvents && executionEvents.length > 0 && (
              <div className="pt-2 border-t border-slate-800 space-y-2">
                <h4 className="font-semibold text-slate-400 uppercase tracking-wider text-[11px]">
                  Execution Audit Trail ({executionEvents.length} events)
                </h4>
                <div className="space-y-1.5 max-h-40 overflow-y-auto">
                  {executionEvents.map((ev) => (
                    <div
                      key={ev.id}
                      className="p-2 rounded bg-slate-950 border border-slate-800 text-[11px] flex items-center justify-between"
                    >
                      <div>
                        <span className="font-semibold text-indigo-400">{ev.event_type}</span>
                        <span className="text-slate-400 ml-2">by {ev.actor}</span>
                        <span className="text-slate-500 ml-2">
                          ({ev.previous_status || "none"} &rarr; {ev.new_status})
                        </span>
                      </div>
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
