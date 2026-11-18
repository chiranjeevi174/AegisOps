import React from "react";
import { ShieldCheck, Lock, CheckCircle2, AlertOctagon, Terminal, ShieldAlert } from "lucide-react";

export const SafetyBanner: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
  if (compact) {
    return (
      <div className="bg-obsidian-800/90 border border-copper-400/30 rounded-lg px-3.5 py-2 flex items-center justify-between text-xs text-obsidian-secondary shadow-obsidian-sm">
        <div className="flex items-center gap-2.5">
          <ShieldAlert className="w-4 h-4 text-copper-400" />
          <span className="font-semibold text-obsidian-text">Safety Invariants Active:</span>
          <span>Zero Autonomous Mutations</span>
          <span className="text-obsidian-muted">|</span>
          <span>Human Approval Required</span>
        </div>
        <span className="text-copper-400 font-mono text-[11px] bg-copper-400/10 border border-copper-400/30 px-2 py-0.5 rounded font-semibold">
          READ_ONLY_GUARD
        </span>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-r from-obsidian-800 via-obsidian-850 to-obsidian-800 border border-obsidian-700 rounded-xl p-4 shadow-obsidian-md relative overflow-hidden">
      {/* Subtle decorative copper top line */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-copper-400/60 to-transparent" />

      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="p-2.5 rounded-lg bg-copper-400/10 text-copper-400 border border-copper-400/30 mt-0.5 shrink-0 shadow-copper-sm">
            <Lock className="w-4 h-4" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="text-sm font-semibold text-obsidian-text tracking-tight">
                AegisOps Controlled Remediation Boundaries
              </h4>
              <span className="text-[10px] font-mono uppercase bg-status-healthy/15 text-status-healthy border border-status-healthy/30 px-2 py-0.5 rounded font-semibold tracking-wider">
                Safety Guards: Enforced
              </span>
            </div>
            <p className="text-xs text-obsidian-muted mt-0.5">
              Strict deterministic safety policy active. AI planning is strictly advisory; live diagnostics are restricted to read-only Prometheus telemetry queries.
            </p>
          </div>
        </div>

        {/* Status Indicators Grid */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-obsidian-900 border border-obsidian-700 text-obsidian-secondary">
            <CheckCircle2 className="w-3.5 h-3.5 text-status-healthy shrink-0" />
            <span>Human Approval: <strong className="text-status-healthy font-semibold">Mandatory</strong></span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-obsidian-900 border border-obsidian-700 text-obsidian-secondary">
            <AlertOctagon className="w-3.5 h-3.5 text-status-warning shrink-0" />
            <span>Auto Execution: <strong className="text-status-warning font-semibold">Disabled</strong></span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-obsidian-900 border border-obsidian-700 text-obsidian-secondary">
            <ShieldCheck className="w-3.5 h-3.5 text-status-neutral shrink-0" />
            <span>Rollback Mode: <strong className="text-status-neutral font-semibold">Simulation Only</strong></span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-obsidian-900 border border-obsidian-700 text-obsidian-secondary">
            <Terminal className="w-3.5 h-3.5 text-copper-400 shrink-0" />
            <span>Live Diagnostics: <strong className="text-copper-400 font-semibold">Restricted Read-Only</strong></span>
          </div>
        </div>
      </div>
    </div>
  );
};
