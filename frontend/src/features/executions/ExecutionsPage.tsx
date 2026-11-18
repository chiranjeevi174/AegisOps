import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  PlaySquare,
  Activity,
  Terminal,
  Eye,
} from "lucide-react";
import { executionsApi, approvalsApi, authApi, overviewApi } from "@/services/api";
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
  const [isExecuteDemoModalOpen, setIsExecuteDemoModalOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Form states
  const [selectedApprovalId, setSelectedApprovalId] = useState("");
  const [selectedOpId, setSelectedOpId] = useState("");
  const [recIndex, setRecIndex] = useState(1);
  const [liveConfirmChecked, setLiveConfirmChecked] = useState(false);
  const [demoConfirmChecked, setDemoConfirmChecked] = useState(false);

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

  // Load demo remediation operations
  const { data: demoOperations } = useQuery({
    queryKey: ["execution-operations", "demo"],
    queryFn: executionsApi.getDemoOperations,
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

  // Load system settings for feature flags (live diagnostics)
  const { data: systemSettings } = useQuery({
    queryKey: ["system-settings"],
    queryFn: overviewApi.getSettings,
  });
  const isLiveDiagnosticsEnabled = systemSettings?.live_diagnostics_enabled ?? true;

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
      if (!op) throw new Error("Please select an allowlisted diagnostic operation.");

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
      queryClient.invalidateQueries({ queryKey: ["executions"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      setSelectedExecution(data);
      setIsDetailModalOpen(true);
    },
    onError: (err: any) => {
      setErrorMessage(err.message || "Live diagnostic execution failed");
    },
  });

  // Demo Remediation Mutation
  const executeDemoMutation = useMutation({
    mutationFn: () => {
      const selectedApproval = approvedRequests?.find((a) => a.id === selectedApprovalId);
      if (!selectedApproval) throw new Error("Please select an approved remediation plan.");
      const op = (demoOperations && demoOperations.length > 0)
        ? (demoOperations.find((o) => o.id === selectedOpId) || demoOperations[0])
        : null;
      const opId = op?.id || selectedOpId || "remediate_service_degradation";

      return executionsApi.executeDemo({
        approval_id: selectedApproval.id,
        incident_id: selectedApproval.incident_id,
        operation_id: opId,
        recommendation_index: Number(recIndex),
        idempotency_key: `demo-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        parameters: { service_name: "api-service", target_scenario: "healthy" },
      });
    },
    onSuccess: (data) => {
      setErrorMessage(null);
      setIsExecuteDemoModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ["executions"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      setSelectedExecution(data);
      setIsDetailModalOpen(true);
    },
    onError: (err: any) => {
      setErrorMessage(err.message || "Demo remediation execution failed");
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
    if (!isLiveDiagnosticsEnabled) {
      setErrorMessage("Live diagnostics are disabled in application configuration (LIVE_DIAGNOSTICS_ENABLED=false)");
      return;
    }
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

  const openExecuteDemoModal = () => {
    setErrorMessage(null);
    setDemoConfirmChecked(false);
    if (approvedRequests && approvedRequests.length > 0) {
      setSelectedApprovalId(approvedRequests[0].id);
    }
    if (demoOperations && demoOperations.length > 0) {
      setSelectedOpId(demoOperations[0].id);
    } else {
      setSelectedOpId("remediate_service_degradation");
    }
    setRecIndex(1);
    setIsExecuteDemoModalOpen(true);
  };

  return (
    <div className="space-y-6 text-obsidian-text select-none font-sans">
      <SafetyBanner />

      {/* Header and Action Triggers */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-obsidian-text tracking-tight flex items-center gap-2">
            <PlaySquare className="w-5 h-5 text-copper-400" />
            Controlled Execution Engine
          </h1>
          <p className="text-xs text-obsidian-muted mt-1">
            Execute dry-run simulations, Prometheus live diagnostics, or isolated demo remediations bound to approved plans.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={openSimulateModal}
            disabled={!actor?.can_execute}
          >
            <PlaySquare className="w-4 h-4 text-copper-400" />
            Dry-Run Simulation
          </Button>
          <Button
            variant="secondary"
            onClick={openDiagnoseModal}
            disabled={!actor?.can_execute || !isLiveDiagnosticsEnabled}
            title={
              !isLiveDiagnosticsEnabled
                ? "Live diagnostics are disabled in application configuration (LIVE_DIAGNOSTICS_ENABLED=false)"
                : undefined
            }
          >
            <Activity className="w-4 h-4 text-copper-400" />
            Run Live Diagnostic
            {!isLiveDiagnosticsEnabled && (
              <span className="ml-1 text-[10px] px-1.5 py-0.5 rounded bg-obsidian-900 border border-obsidian-700 text-obsidian-muted font-normal">
                Disabled
              </span>
            )}
          </Button>
          <Button
            variant="primary"
            onClick={openExecuteDemoModal}
            disabled={!actor?.can_execute}
          >
            <PlaySquare className="w-4 h-4 text-obsidian-950" />
            Execute Remediation (Demo)
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
        <h3 className="text-xs font-semibold text-obsidian-muted uppercase tracking-wider font-mono">
          Immutable Allowlisted Operations Registry
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {isLoadingOps ? (
            <Skeleton className="h-32 bg-obsidian-800" />
          ) : (
            operations?.map((op) => (
              <Card key={op.id} className="bg-obsidian-800 border-obsidian-700">
                <CardHeader className="py-3 px-4 flex flex-row items-center justify-between border-b border-obsidian-700">
                  <div className="flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-copper-400" />
                    <CardTitle className="text-xs font-mono">{op.id}</CardTitle>
                  </div>
                  <Badge variant={op.risk_level === "high" ? "high" : "low"}>
                    {op.risk_level.toUpperCase()}
                  </Badge>
                </CardHeader>
                <CardContent className="p-4 space-y-2.5 text-xs">
                  <p className="text-obsidian-text font-medium">{op.name}</p>
                  <p className="text-obsidian-secondary text-[11px] leading-relaxed">{op.description}</p>
                  <div className="flex flex-wrap gap-1.5 pt-1 font-mono text-[10px]">
                    <span className="px-2 py-0.5 rounded bg-obsidian-900 border border-obsidian-700 text-obsidian-muted">
                      Modes: {op.supported_modes?.join(", ") || "simulation, live_diagnostic"}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-obsidian-900 border border-obsidian-700 text-status-healthy font-semibold">
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
      <Card className="bg-obsidian-800 border-obsidian-700">
        <CardHeader className="py-3 px-4 flex flex-row items-center justify-between border-b border-obsidian-700">
          <CardTitle className="text-sm flex items-center gap-2">
            <span>Execution Audit Records</span>
            <span className="text-xs font-mono text-copper-400 font-semibold">
              ({executions?.length || 0})
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoadingExecs ? (
            <div className="p-6 space-y-3">
              <Skeleton className="h-10 bg-obsidian-750" />
              <Skeleton className="h-10 bg-obsidian-750" />
            </div>
          ) : !executions || executions.length === 0 ? (
            <EmptyState
              title="No Executions Recorded"
              description="Click 'Dry-Run Simulation' or 'Run Live Diagnostic' above to trigger an execution."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-obsidian-900 border-b border-obsidian-700 text-obsidian-muted font-semibold uppercase tracking-wider font-mono text-[11px]">
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
                <tbody className="divide-y divide-obsidian-700/60 font-sans">
                  {executions.map((ex) => (
                    <tr key={ex.id} className="hover:bg-obsidian-750/50 transition-colors">
                      <td className="py-3 px-4 whitespace-nowrap">
                        <Badge
                          variant={
                            ex.mode === "demo_execution"
                              ? "warning"
                              : ex.mode === "live_diagnostic"
                              ? "warning"
                              : "default"
                          }
                        >
                          {ex.mode.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <Badge
                          variant={
                            ex.status === "executed"
                              ? "success"
                              : ex.status === "failed"
                              ? "danger"
                              : "default"
                          }
                        >
                          {ex.status.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 font-mono text-copper-300 font-semibold">{ex.operation_id}</td>
                      <td className="py-3 px-4 text-obsidian-secondary max-w-xs truncate">
                        {ex.selected_recommendation_title}
                      </td>
                      <td className="py-3 px-4 font-mono text-obsidian-muted">{ex.duration_ms} ms</td>
                      <td className="py-3 px-4 text-obsidian-text font-mono text-[11px]">{ex.requested_by}</td>
                      <td className="py-3 px-4 text-obsidian-muted font-mono text-[11px]">
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

          <div className="p-3 bg-obsidian-900 border border-obsidian-700 rounded-lg text-xs text-obsidian-secondary">
            <span className="font-semibold text-copper-400 block mb-0.5 font-mono">Safety Guarantee:</span>
            Simulation runs in a synthetic dry-run sandbox. Zero infrastructure commands or mutations are executed.
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-obsidian-700">
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
          <div className="p-3 bg-amber-400/10 border border-status-warning/30 rounded-lg text-xs text-status-warning">
            <span className="font-semibold block mb-0.5 font-mono">Strict Read-Only Verification:</span>
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
              className="mt-1 rounded bg-obsidian-900 border-obsidian-700 text-copper-500 focus:ring-copper-400"
            />
            <label htmlFor="confirm-diagnostic" className="text-xs text-obsidian-secondary cursor-pointer">
              I confirm that this operation is read-only and authorized by the linked approval request.
            </label>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-obsidian-700">
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

      {/* Demo Remediation Modal */}
      <Modal
        isOpen={isExecuteDemoModalOpen}
        onClose={() => setIsExecuteDemoModalOpen(false)}
        title="Execute Remediation (Demo Sandbox)"
        description="Execute an allowlisted remediation action against the isolated demo telemetry service."
        maxWidth="lg"
      >
        <div className="space-y-4">
          <div className="p-3 bg-copper-500/10 border border-copper-500/30 rounded-lg text-xs text-copper-300">
            <span className="font-semibold block mb-0.5 font-mono">Isolated Demo Execution Sandbox:</span>
            Remediation will target the isolated demo simulator (port 8001) to restore healthy telemetry baselines.
            Strict human approval and allowlist parameter validation are fully enforced.
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
            label="Select Remediation Operation *"
            value={selectedOpId}
            onChange={(e) => setSelectedOpId(e.target.value)}
            options={
              demoOperations && demoOperations.length > 0
                ? demoOperations.map((o) => ({
                    value: o.id,
                    label: `${o.name} (${o.id})`,
                  }))
                : [
                    {
                      value: "remediate_service_degradation",
                      label: "Remediate Service Degradation (remediate_service_degradation)",
                    },
                    {
                      value: "restart_demo_service",
                      label: "Restart Demo Service (restart_demo_service)",
                    },
                    {
                      value: "scale_demo_workload",
                      label: "Scale Demo Workload (scale_demo_workload)",
                    },
                  ]
            }
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
              id="confirm-demo-execution"
              checked={demoConfirmChecked}
              onChange={(e) => setDemoConfirmChecked(e.target.checked)}
              className="mt-1 rounded bg-obsidian-900 border-obsidian-700 text-copper-500 focus:ring-copper-400"
            />
            <label htmlFor="confirm-demo-execution" className="text-xs text-obsidian-secondary cursor-pointer">
              I authorize this remediation execution against the isolated demo service under approved plan governance.
            </label>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-obsidian-700">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setIsExecuteDemoModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={() => executeDemoMutation.mutate()}
              isLoading={executeDemoMutation.isPending}
              disabled={!demoConfirmChecked || !selectedApprovalId || !selectedOpId}
            >
              Execute Remediation
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
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3.5 bg-obsidian-900 rounded-lg border border-obsidian-700 font-mono">
              <div>
                <span className="text-obsidian-muted block text-[11px]">Mode</span>
                <span className="text-copper-400 font-bold uppercase">{selectedExecution.mode}</span>
              </div>
              <div>
                <span className="text-obsidian-muted block text-[11px]">Status</span>
                <span className="text-obsidian-text font-bold uppercase">{selectedExecution.status}</span>
              </div>
              <div>
                <span className="text-obsidian-muted block text-[11px]">Duration</span>
                <span className="text-obsidian-text font-bold">{selectedExecution.duration_ms} ms</span>
              </div>
              <div>
                <span className="text-obsidian-muted block text-[11px]">System Changes</span>
                <span className={selectedExecution.system_changes_performed ? "text-status-warning font-bold" : "text-status-healthy font-bold"}>
                  {selectedExecution.system_changes_performed ? "TRUE" : "FALSE"}
                </span>
              </div>
            </div>

            {/* Demo Execution Result */}
            {selectedExecution.execution_result && (
              <div className="p-4 bg-obsidian-900 border border-obsidian-700 rounded-lg space-y-2">
                <span className="font-semibold text-obsidian-text text-sm block font-mono">
                  Demo Execution Result:
                </span>
                <pre className="p-3 bg-obsidian-950 border border-obsidian-700 rounded text-status-healthy font-mono text-[11px] overflow-x-auto">
                  {JSON.stringify(selectedExecution.execution_result, null, 2)}
                </pre>
              </div>
            )}

            {/* Diagnostic Result */}
            {selectedExecution.diagnostic_result && (
              <div className="p-4 bg-obsidian-900 border border-obsidian-700 rounded-lg space-y-2">
                <span className="font-semibold text-obsidian-text text-sm block font-mono">
                  Prometheus Telemetry Result:
                </span>
                <pre className="p-3 bg-obsidian-950 border border-obsidian-700 rounded text-status-healthy font-mono text-[11px] overflow-x-auto">
                  {JSON.stringify(selectedExecution.diagnostic_result, null, 2)}
                </pre>
              </div>
            )}

            {/* Simulation Result */}
            {selectedExecution.simulation_result && (
              <div className="p-4 bg-obsidian-900 border border-obsidian-700 rounded-lg space-y-2">
                <span className="font-semibold text-obsidian-text text-sm block font-mono">
                  Simulation Dry-Run Result:
                </span>
                <pre className="p-3 bg-obsidian-950 border border-obsidian-700 rounded text-copper-300 font-mono text-[11px] overflow-x-auto">
                  {JSON.stringify(selectedExecution.simulation_result, null, 2)}
                </pre>
              </div>
            )}

            {/* Audit Trail */}
            {executionEvents && executionEvents.length > 0 && (
              <div className="pt-2 border-t border-obsidian-700 space-y-2">
                <h4 className="font-semibold text-obsidian-muted uppercase tracking-wider text-[11px] font-mono">
                  Execution Audit Trail ({executionEvents.length} events)
                </h4>
                <div className="space-y-1.5 max-h-40 overflow-y-auto">
                  {executionEvents.map((ev) => (
                    <div
                      key={ev.id}
                      className="p-2 rounded bg-obsidian-900 border border-obsidian-700 text-[11px] flex items-center justify-between"
                    >
                      <div>
                        <span className="font-semibold text-copper-400 font-mono">{ev.event_type}</span>
                        <span className="text-obsidian-secondary ml-2 font-mono">by {ev.actor}</span>
                        <span className="text-obsidian-muted ml-2">
                          ({ev.previous_status || "none"} &rarr; {ev.new_status})
                        </span>
                      </div>
                      <span className="text-obsidian-muted font-mono text-[10px]">
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
