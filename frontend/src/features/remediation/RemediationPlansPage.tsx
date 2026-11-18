import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  FileCheck2,
  Lock,
  CheckCircle2,
  ShieldAlert,
  Hash,
} from "lucide-react";
import { approvalsApi } from "@/services/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { SafetyBanner } from "@/components/ui/SafetyBanner";
import { EmptyState, Skeleton } from "@/components/ui/Feedback";

export const RemediationPlansPage: React.FC = () => {
  const [selectedApprovalId, setSelectedApprovalId] = useState<string>("");

  const { data: approvals, isLoading: isLoadingApprovals } = useQuery({
    queryKey: ["approvals"],
    queryFn: () => approvalsApi.list({ limit: 50 }),
  });

  // Select first approval by default
  React.useEffect(() => {
    if (approvals && approvals.length > 0 && !selectedApprovalId) {
      setSelectedApprovalId(approvals[0].id);
    }
  }, [approvals, selectedApprovalId]);

  const { data: approvalDetail, isLoading: isLoadingDetail } = useQuery({
    queryKey: ["approvals", selectedApprovalId],
    queryFn: () => approvalsApi.get(selectedApprovalId),
    enabled: !!selectedApprovalId,
  });

  const plan = approvalDetail?.plan_snapshot;

  return (
    <div className="space-y-6 text-obsidian-text select-none font-sans">
      {/* Top Safety Banner */}
      <SafetyBanner />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-obsidian-text tracking-tight flex items-center gap-2">
            <FileCheck2 className="w-5 h-5 text-copper-400" />
            Remediation Plans (Advisory Only)
          </h1>
          <p className="text-xs text-obsidian-muted mt-1">
            Safety-validated remediation actions generated from RCA findings. All plans require formal operator approval.
          </p>
        </div>

        {approvals && approvals.length > 0 && (
          <div className="w-full sm:w-80">
            <select
              value={selectedApprovalId}
              onChange={(e) => setSelectedApprovalId(e.target.value)}
              className="w-full px-3 py-2 bg-obsidian-900 border border-obsidian-700 rounded-lg text-xs text-obsidian-text focus:outline-none focus:ring-1 focus:ring-copper-400 focus:border-copper-400 font-mono transition-colors"
            >
              {approvals.map((app) => (
                <option key={app.id} value={app.id} className="bg-obsidian-900 text-obsidian-text">
                  v{app.version} | Status: {app.status.toUpperCase()} | {app.requested_by}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {isLoadingApprovals || isLoadingDetail ? (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full bg-obsidian-800" />
          <Skeleton className="h-48 w-full bg-obsidian-800" />
        </div>
      ) : !approvalDetail || !plan ? (
        <EmptyState
          title="No Remediation Plans Found"
          description="Create an incident and submit an approval request to generate and inspect remediation plans."
          action={
            <Link to="/incidents">
              <Button variant="primary">Go to Incidents</Button>
            </Link>
          }
        />
      ) : (
        <div className="space-y-6">
          {/* Plan Header Card */}
          <Card className="bg-obsidian-800 border-obsidian-700">
            <CardHeader className="py-4 border-b border-obsidian-700">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <Badge variant={approvalDetail.status === "approved" ? "success" : "high"}>
                      {approvalDetail.status.toUpperCase()}
                    </Badge>
                    <CardTitle>Plan Version {approvalDetail.version}</CardTitle>
                    <span className="text-xs font-mono text-copper-300 flex items-center gap-1">
                      <Hash className="w-3 h-3 text-copper-400" />
                      {approvalDetail.plan_hash.slice(0, 16)}...
                    </span>
                  </div>
                  <p className="text-xs text-obsidian-muted mt-1">
                    Requested by <strong className="text-copper-300 font-mono">{approvalDetail.requested_by}</strong> on{" "}
                    {new Date(approvalDetail.requested_at).toLocaleString()}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <Link to="/approvals">
                    <Button variant="secondary" size="sm">
                      Inspect Decision & Audit
                    </Button>
                  </Link>
                  <Link to="/executions">
                    <Button variant="primary" size="sm">
                      Execution Sandbox
                    </Button>
                  </Link>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 p-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="p-3 bg-obsidian-900 rounded-lg border border-obsidian-700">
                  <span className="text-obsidian-muted font-semibold block mb-1 font-mono text-[11px]">
                    Incident Summary:
                  </span>
                  <p className="text-obsidian-text">{plan.incident_summary}</p>
                </div>
                <div className="p-3 bg-obsidian-900 rounded-lg border border-obsidian-700">
                  <span className="text-obsidian-muted font-semibold block mb-1 font-mono text-[11px]">
                    Planning Basis (RCA):
                  </span>
                  <p className="text-obsidian-text">{plan.planning_basis}</p>
                </div>
              </div>

              {/* Immutable Safety Properties */}
              <div className="flex flex-wrap gap-2 text-xs pt-1">
                <div className="px-3 py-1.5 rounded-lg bg-status-healthy/10 border border-status-healthy/30 text-status-healthy flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Human Approval Required: <strong>TRUE (Mandatory)</strong></span>
                </div>
                <div className="px-3 py-1.5 rounded-lg bg-rose-500/10 border border-status-critical/30 text-status-critical flex items-center gap-2">
                  <Lock className="w-3.5 h-3.5" />
                  <span>Execution Enabled: <strong>FALSE (Advisory Only)</strong></span>
                </div>
                <div className="px-3 py-1.5 rounded-lg bg-copper-400/10 border border-copper-400/30 text-copper-300 flex items-center gap-2">
                  <ShieldAlert className="w-3.5 h-3.5 text-copper-400" />
                  <span>Overall Risk Level: <strong>{(plan.overall_risk || "low").toUpperCase()}</strong></span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Recommended Actions List */}
          <div className="space-y-4">
            <h3 className="text-xs font-semibold text-obsidian-muted uppercase tracking-wider font-mono">
              Recommended Remediation Actions ({plan.recommended_actions?.length || 0})
            </h3>

            {plan.recommended_actions?.map((action, idx) => (
              <Card key={idx} className="bg-obsidian-800 border-obsidian-700">
                <CardHeader className="py-3 px-5 flex flex-row items-center justify-between border-b border-obsidian-700">
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-full bg-obsidian-900 border border-copper-400/40 flex items-center justify-center text-xs font-bold text-copper-400 font-mono">
                      {idx + 1}
                    </span>
                    <div>
                      <CardTitle className="text-sm">{action.title}</CardTitle>
                      <span className="text-[11px] text-obsidian-muted capitalize font-mono">
                        Type: {action.action_type.replace(/_/g, " ")}
                      </span>
                    </div>
                  </div>
                  <Badge variant={action.risk_level === "high" ? "high" : "low"}>
                    Risk: {action.risk_level.toUpperCase()}
                  </Badge>
                </CardHeader>
                <CardContent className="p-5 space-y-4 text-xs">
                  <div>
                    <span className="text-obsidian-muted font-semibold block mb-0.5 font-mono text-[11px]">Description:</span>
                    <p className="text-obsidian-text">{action.description}</p>
                  </div>

                  <div className="p-3 bg-obsidian-900 rounded-lg border border-obsidian-700">
                    <span className="text-copper-400 font-semibold block mb-0.5 font-mono text-[11px]">Rationale:</span>
                    <p className="text-obsidian-secondary">{action.rationale}</p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div className="p-3 rounded-lg bg-obsidian-900/60 border border-obsidian-700">
                      <span className="text-obsidian-muted font-semibold block mb-1 font-mono text-[11px]">
                        Supporting Evidence ({action.supporting_evidence?.length || 0})
                      </span>
                      <ul className="list-disc list-inside text-obsidian-secondary space-y-0.5 text-[11px]">
                        {action.supporting_evidence?.map((e, i) => (
                          <li key={i}>{e}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="p-3 rounded-lg bg-obsidian-900/60 border border-obsidian-700">
                      <span className="text-obsidian-muted font-semibold block mb-1 font-mono text-[11px]">
                        Validation Steps
                      </span>
                      <ul className="list-disc list-inside text-obsidian-secondary space-y-0.5 text-[11px]">
                        {action.validation_steps?.map((step, i) => (
                          <li key={i}>{step}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="p-3 rounded-lg bg-obsidian-900/60 border border-obsidian-700">
                      <span className="text-obsidian-muted font-semibold block mb-1 font-mono text-[11px]">
                        Rollback Considerations
                      </span>
                      <ul className="list-disc list-inside text-obsidian-secondary space-y-0.5 text-[11px]">
                        {action.rollback_considerations?.map((rc, i) => (
                          <li key={i}>{rc}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
