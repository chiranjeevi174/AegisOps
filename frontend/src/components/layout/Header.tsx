import React from "react";
import { Activity, Shield, Server, RefreshCw, Layers } from "lucide-react";
import type { AuthenticatedActor } from "@/types/auth";

interface HeaderProps {
  actor?: AuthenticatedActor;
  monitoringAvailable?: boolean;
  onRefresh?: () => void;
  isRefreshing?: boolean;
  onOpenPersonaModal?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  actor,
  monitoringAvailable = false,
  onRefresh,
  isRefreshing = false,
  onOpenPersonaModal,
}) => {
  return (
    <header className="h-14 border-b border-obsidian-700 bg-obsidian-900/90 backdrop-blur-md px-6 flex items-center justify-between shrink-0 select-none z-10">
      {/* Left: Environment & System Status */}
      <div className="flex items-center gap-4">
        {/* Environment Badge */}
        <div className="flex items-center gap-2">
          <Layers className="w-3.5 h-3.5 text-copper-400" />
          <span className="text-xs font-semibold text-obsidian-muted uppercase tracking-wider">Env:</span>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-obsidian-800 border border-obsidian-700 text-copper-300 font-medium">
            development
          </span>
        </div>

        <span className="text-obsidian-700">|</span>

        {/* API Backend Health */}
        <div className="flex items-center gap-2 text-xs">
          <Server className="w-3.5 h-3.5 text-obsidian-muted" />
          <span className="text-obsidian-muted">API:</span>
          <span className="flex items-center gap-1.5 text-status-healthy font-medium font-mono text-[11px]">
            <span className="w-1.5 h-1.5 rounded-full bg-status-healthy animate-pulse" />
            Healthy
          </span>
        </div>

        <span className="text-obsidian-700 hidden sm:inline">|</span>

        {/* Prometheus Telemetry Live Status */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-obsidian-800/80 border border-obsidian-700 text-xs">
          <Activity
            className={`w-3.5 h-3.5 ${
              monitoringAvailable ? "text-status-healthy" : "text-status-warning"
            }`}
          />
          <span className="text-obsidian-muted">Telemetry:</span>
          <span
            className={`font-mono text-[11px] font-semibold ${
              monitoringAvailable ? "text-status-healthy" : "text-status-warning"
            }`}
          >
            {monitoringAvailable ? "Prometheus Live" : "Local Standby"}
          </span>
        </div>
      </div>

      {/* Right: Operator Identity & Refresh */}
      <div className="flex items-center gap-3">
        {/* Current Operator & Role */}
        {actor && (
          <button
            onClick={onOpenPersonaModal}
            title="Switch Operator Persona"
            className="flex items-center gap-2 px-3 py-1 bg-obsidian-800 border border-copper-400/30 hover:border-copper-400/70 rounded-lg text-xs shadow-obsidian-sm transition-all cursor-pointer"
          >
            <Shield className="w-3.5 h-3.5 text-copper-400" />
            <span className="text-obsidian-text font-medium">{actor.identity}</span>
            <span className="text-obsidian-700">/</span>
            <span className="text-copper-400 font-mono text-[11px] font-semibold">
              {actor.roles.slice(0, 2).join("+")}
              {actor.roles.length > 2 ? `+${actor.roles.length - 2}` : ""}
            </span>
          </button>
        )}

        {/* Manual Refresh Trigger */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-1.5 rounded-lg border border-obsidian-700 bg-obsidian-800 hover:bg-obsidian-750 text-obsidian-muted hover:text-copper-400 transition-all focus:outline-none focus:ring-1 focus:ring-copper-400"
            title="Refresh Data"
            aria-label="Refresh Data"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-copper-400" : ""}`}
            />
          </button>
        )}
      </div>
    </header>
  );
};
