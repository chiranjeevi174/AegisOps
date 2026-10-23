import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  CheckCircle,
  History,
  Eye,
} from "lucide-react";
import { approvalsApi, authApi } from "@/services/api";
import type {
  Approval,
  ApprovalDetail,
  ApprovalStatus,
} from "@/types/approval";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { EmptyState, Skeleton, AlertMessage } from "@/components/ui/Feedback";

export const ApprovalsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedApproval, setSelectedApproval] = useState<ApprovalDetail | null>(null);
  const [isDecisionModalOpen, setIsDecisionModalOpen] = useState(false);
  const [decisionType, setDecisionType] = useState<"approve" | "reject" | "revision">("approve");
  const [decisionComment, setDecisionComment] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load current actor to verify permissions
  const { data: actor } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: authApi.getMe,
  });

  // Load approvals
  const { data: approvals, isLoading } = useQuery({
    queryKey: ["approvals"],
    queryFn: () => approvalsApi.list({ limit: 100 }),
  });

  // Load events for selected approval
  const { data: events } = useQuery({
    queryKey: ["approvals", selectedApproval?.id, "events"],
    queryFn: () => approvalsApi.getEvents(selectedApproval!.id),
    enabled: !!selectedApproval?.id,
  });

  // Approve Mutation
  const approveMutation = useMutation({
    mutationFn: () =>
      approvalsApi.approve(selectedApproval!.id, {
        comment: decisionComment.trim() || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      setIsDecisionModalOpen(false);
      setSelectedApproval(null);
      setDecisionComment("");
      setErrorMessage(null);
    },
    onError: (err: any) => {
      setErrorMessage(err.message || "Approval decision failed");
    },
  });

  // Reject Mutation
  const rejectMutation = useMutation({
    mutationFn: () =>
      approvalsApi.reject(selectedApproval!.id, {
        reason: decisionComment.trim(),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      setIsDecisionModalOpen(false);
      setSelectedApproval(null);
      setDecisionComment("");
      setErrorMessage(null);
    },
    onError: (err: any) => {
      setErrorMessage(err.message || "Rejection failed");
    },
  });

  // Revision Mutation
  const revisionMutation = useMutation({
    mutationFn: () =>
      approvalsApi.requestRevision(selectedApproval!.id, {
        reason: decisionComment.trim(),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      setIsDecisionModalOpen(false);
      setSelectedApproval(null);
      setDecisionComment("");
      setErrorMessage(null);
    },
    onError: (err: any) => {
      setErrorMessage(err.message || "Revision request failed");
    },
  });

  const handleOpenDecision = async (app: Approval, type: "approve" | "reject" | "revision") => {
    setErrorMessage(null);
    setDecisionComment("");
    setDecisionType(type);
    try {
      const full = await approvalsApi.get(app.id);
      setSelectedApproval(full);
      setIsDecisionModalOpen(true);
    } catch (err: any) {
      setErrorMessage(err.message || "Could not load approval details");
    }
  };

  const handleExecuteDecision = () => {
    if (decisionType === "approve") {
      approveMutation.mutate();
    } else if (decisionType === "reject") {
      if (!decisionComment.trim()) {
        setErrorMessage("Rejection reason is required.");
        return;
      }
      rejectMutation.mutate();
    } else if (decisionType === "revision") {
      if (!decisionComment.trim()) {
        setErrorMessage("Revision reason is required.");
        return;
      }
      revisionMutation.mutate();
    }
  };

  const filteredApprovals = (approvals || []).filter((app) => {
    if (statusFilter === "all") return true;
    return app.status === statusFilter;
  });

  const getStatusBadge = (status: ApprovalStatus) => {
    switch (status) {
      case "approved":
        return <Badge variant="success">APPROVED</Badge>;
      case "pending":
        return <Badge variant="warning">PENDING</Badge>;
      case "rejected":
        return <Badge variant="danger">REJECTED</Badge>;
      case "revision_requested":
        return <Badge variant="medium">REVISION REQUESTED</Badge>;
      case "expired":
        return <Badge variant="default">EXPIRED</Badge>;
      case "superseded":
        return <Badge variant="default">SUPERSEDED</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-tight flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-indigo-400" />
            Human-in-the-Loop Approval System
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Authoritative approval gating for remediation plans. Approvals authorize controlled planning checks and do not initiate autonomous execution.
          </p>
        </div>

        {/* Status Filter Tabs */}
        <div className="flex flex-wrap gap-1 p-1 bg-slate-900 border border-slate-800 rounded-lg text-xs">
          {["all", "pending", "approved", "rejected", "revision_requested", "expired", "superseded"].map(
            (tab) => (
              <button
                key={tab}
                onClick={() => setStatusFilter(tab)}
                className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
                  statusFilter === tab
                    ? "bg-indigo-600 text-white"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {tab.replace("_", " ").toUpperCase()}
              </button>
            )
          )}
        </div>
      </div>

      {/* Approvals Table */}
      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm flex items-center gap-2">
            <span>Approval Requests</span>
            <span className="text-xs font-mono text-slate-500">
              ({filteredApprovals.length})
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              <Skeleton className="h-10" />
              <Skeleton className="h-10" />
              <Skeleton className="h-10" />
            </div>
          ) : filteredApprovals.length === 0 ? (
            <EmptyState
              title="No Approvals Matching Filter"
              description="No human approval records found matching the current status filter."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/70 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Version & Hash</th>
                    <th className="py-3 px-4">Incident ID</th>
                    <th className="py-3 px-4">Requested By</th>
                    <th className="py-3 px-4">Requested At</th>
                    <th className="py-3 px-4">Decision Metadata</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredApprovals.map((app) => (
                    <tr key={app.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4 whitespace-nowrap">
                        {getStatusBadge(app.status)}
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-200">Version {app.version}</div>
                        <span className="text-[11px] font-mono text-slate-500">
                          {app.plan_hash.slice(0, 16)}...
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-400">
                        <Link
                          to={`/incidents/${app.incident_id}`}
                          className="hover:text-indigo-400 underline decoration-slate-700"
                        >
                          {app.incident_id.slice(0, 8)}...
                        </Link>
                      </td>
                      <td className="py-3 px-4 text-slate-300">{app.requested_by}</td>
                      <td className="py-3 px-4 text-slate-400">
                        {new Date(app.requested_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {app.decided_by ? (
                          <div>
                            <span className="text-slate-300 font-medium">By: {app.decided_by}</span>
                            {app.decision_reason && (
                              <p className="text-[11px] text-slate-500 truncate max-w-xs">
                                &quot;{app.decision_reason}&quot;
                              </p>
                            )}
                          </div>
                        ) : (
                          <span className="text-amber-400/80 font-mono text-[11px]">Pending Decision</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        {app.status === "pending" ? (
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              variant="primary"
                              size="sm"
                              disabled={!actor?.can_approve}
                              onClick={() => handleOpenDecision(app, "approve")}
                            >
                              Approve
                            </Button>
                            <Button
                              variant="danger"
                              size="sm"
                              disabled={!actor?.can_approve}
                              onClick={() => handleOpenDecision(app, "reject")}
                            >
                              Reject
                            </Button>
                            <Button
                              variant="secondary"
                              size="sm"
                              disabled={!actor?.can_approve}
                              onClick={() => handleOpenDecision(app, "revision")}
                            >
                              Revise
                            </Button>
                          </div>
                        ) : (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleOpenDecision(app, "approve")}
                          >
                            <Eye className="w-3.5 h-3.5" />
                            Inspect
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Decision / Inspection Modal */}
      {selectedApproval && (
        <Modal
          isOpen={isDecisionModalOpen}
          onClose={() => setIsDecisionModalOpen(false)}
          title={
            selectedApproval.status === "pending"
              ? `Confirm Decision: ${decisionType.toUpperCase()} (v${selectedApproval.version})`
              : `Approval Record Details (v${selectedApproval.version})`
          }
          description={`Associated with Incident ${selectedApproval.incident_id}`}
          maxWidth="xl"
        >
          <div className="space-y-4">
            {errorMessage && (
              <AlertMessage type="error" title="Decision Blocked">
                {errorMessage}
              </AlertMessage>
            )}

            {/* Plan Snapshot Review */}
            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-3 text-xs">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="font-semibold text-slate-300">Plan Snapshot Hash:</span>
                <span className="font-mono text-indigo-400">{selectedApproval.plan_hash}</span>
              </div>

              <div>
                <span className="text-slate-500 font-semibold block mb-0.5">Planning Basis:</span>
                <p className="text-slate-300">
                  {selectedApproval.plan_snapshot?.planning_basis || "None specified"}
                </p>
              </div>

              <div>
                <span className="text-slate-500 font-semibold block mb-1">
                  Actions Included ({selectedApproval.plan_snapshot?.recommended_actions?.length || 0}):
                </span>
                <div className="space-y-2">
                  {selectedApproval.plan_snapshot?.recommended_actions?.map((act, i) => (
                    <div key={i} className="p-2.5 rounded bg-slate-900 border border-slate-800">
                      <div className="flex items-center justify-between">
                        <strong className="text-slate-200">
                          {i + 1}. {act.title}
                        </strong>
                        <Badge size="sm" variant={act.risk_level === "high" ? "high" : "low"}>
                          {act.risk_level.toUpperCase()}
                        </Badge>
                      </div>
                      <p className="text-slate-400 mt-1">{act.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Decision Input if Pending */}
            {selectedApproval.status === "pending" && (
              <div className="space-y-3 pt-2 border-t border-slate-800">
                <div className="p-3 bg-amber-950/40 border border-amber-900/60 rounded-lg text-xs text-amber-200">
                  <span className="font-semibold block mb-0.5">Formal Sign-off Warning:</span>
                  Approving this plan satisfies safety prerequisites for subsequent simulation or live diagnostic operations. It does not initiate automated mutations.
                </div>

                {decisionType === "approve" ? (
                  <Input
                    label="Optional Approval Comment"
                    placeholder="e.g. Verified downstream dependencies and monitoring"
                    value={decisionComment}
                    onChange={(e) => setDecisionComment(e.target.value)}
                  />
                ) : (
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Mandatory Reason for {decisionType === "reject" ? "Rejection" : "Revision Request"} *
                    </label>
                    <textarea
                      rows={3}
                      required
                      placeholder="Specify reasons, required revisions, or risk factors..."
                      value={decisionComment}
                      onChange={(e) => setDecisionComment(e.target.value)}
                      className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                )}

                <div className="flex justify-end gap-2 pt-2">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => setIsDecisionModalOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="button"
                    variant={decisionType === "reject" ? "danger" : "primary"}
                    onClick={handleExecuteDecision}
                    isLoading={
                      approveMutation.isPending ||
                      rejectMutation.isPending ||
                      revisionMutation.isPending
                    }
                  >
                    Confirm {decisionType.toUpperCase()}
                  </Button>
                </div>
              </div>
            )}

            {/* Audit Event Trail */}
            {events && events.length > 0 && (
              <div className="pt-3 border-t border-slate-800 space-y-2">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <History className="w-3.5 h-3.5" />
                  Decision Audit Trail ({events.length} events)
                </h4>
                <div className="space-y-1.5 max-h-40 overflow-y-auto">
                  {events.map((ev) => (
                    <div
                      key={ev.id}
                      className="p-2 rounded bg-slate-950 border border-slate-800 text-[11px] flex items-center justify-between"
                    >
                      <div>
                        <span className="font-semibold text-indigo-400">{ev.event_type}</span>
                        <span className="text-slate-400 ml-2">by {ev.actor}</span>
                        {ev.reason && (
                          <span className="text-slate-500 ml-2 italic">&quot;{ev.reason}&quot;</span>
                        )}
                      </div>
                      <span className="text-slate-500">
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
