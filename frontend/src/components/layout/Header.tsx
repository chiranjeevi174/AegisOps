import React from "react";
import { Activity, Shield, Server, RefreshCw } from "lucide-react";
import type { AuthenticatedActor } from "@/types/auth";

interface HeaderProps {
  actor?: AuthenticatedActor;
  monitoringAvailable?: boolean;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  actor,
  monitoringAvailable = false,
  onRefresh,
  isRefreshing = false,
}) => {
  return (
    <header className="h-14 border-b border-slate-800 bg-slate-900/60 backdrop-blur-md px-6 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-400">Environment:</span>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
            development
          </span>
        </div>
        <span className="text-slate-700">|</span>
        <div className="flex items-center gap-2 text-xs">
          <Server className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400">API Status:</span>
          <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Healthy
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Monitoring availability indicator */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800/80 border border-slate-700 text-xs">
          <Activity
            className={`w-3.5 h-3.5 ${
              monitoringAvailable ? "text-emerald-400" : "text-amber-400"
            }`}
          />
          <span className="text-slate-300">Prometheus:</span>
          <span
            className={`font-semibold ${
              monitoringAvailable ? "text-emerald-400" : "text-amber-400"
            }`}
          >
            {monitoringAvailable ? "Live Connected" : "Local Standby"}
          </span>
        </div>

        {/* Current Operator & Role */}
        {actor && (
          <div className="flex items-center gap-2 px-3 py-1 bg-indigo-950/40 border border-indigo-900/60 rounded-full text-xs">
            <Shield className="w-3.5 h-3.5 text-indigo-400" />
            <span className="text-indigo-200 font-medium">{actor.identity}</span>
            <span className="text-slate-600">/</span>
            <span className="text-indigo-400 font-mono text-[11px]">
              {actor.roles.slice(0, 2).join("+")}
              {actor.roles.length > 2 ? `+${actor.roles.length - 2}` : ""}
            </span>
          </div>
        )}

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-1.5 rounded-lg border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
            title="Refresh Data"
            aria-label="Refresh Data"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-indigo-400" : ""}`}
            />
          </button>
        )}
      </div>
    </header>
  );
};
