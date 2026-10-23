import React from "react";
import { ShieldAlert, Lock, CheckCircle2, AlertOctagon } from "lucide-react";

export const SafetyBanner: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
  if (compact) {
    return (
      <div className="bg-indigo-950/40 border border-indigo-900/60 rounded-lg px-3 py-1.5 flex items-center justify-between text-xs text-indigo-300">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-3.5 h-3.5 text-indigo-400" />
          <span className="font-semibold text-indigo-200">Safety Invariants Active:</span>
          <span>Zero Autonomous Mutations</span>
          <span className="text-slate-600">|</span>
          <span>Human Approval Required</span>
        </div>
        <span className="text-indigo-400 font-mono text-[11px] bg-indigo-900/40 px-2 py-0.5 rounded">
          READ_ONLY_GUARD
        </span>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-indigo-800/40 rounded-xl p-4 shadow-sm">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-indigo-900/40 text-indigo-400 border border-indigo-800/50 mt-0.5">
            <Lock className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-slate-100">
                AegisOps Controlled Remediation Boundaries
              </h4>
              <span className="text-[10px] font-mono uppercase bg-emerald-950 text-emerald-400 border border-emerald-800 px-1.5 py-0.5 rounded font-semibold">
                Guards Enforced
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Strict deterministic safety policy active. AI planning is advisory; live diagnostics are read-only Prometheus telemetry queries.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-slate-300">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Human Approval: <strong className="text-emerald-400">Mandatory</strong></span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-slate-300">
            <AlertOctagon className="w-3.5 h-3.5 text-amber-400" />
            <span>Auto Execution: <strong className="text-amber-400">Disabled</strong></span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-slate-300">
            <Lock className="w-3.5 h-3.5 text-cyan-400" />
            <span>Rollback Mode: <strong className="text-cyan-400">Simulation Only</strong></span>
          </div>
        </div>
      </div>
    </div>
  );
};
