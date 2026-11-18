import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  AlertTriangle,
  SearchCode,
  FileCheck2,
  CheckCircle,
  PlaySquare,
  ClipboardCheck,
  Undo2,
  History,
  Settings,
  ShieldCheck,
  ExternalLink,
  User,
} from "lucide-react";
import type { AuthenticatedActor } from "@/types/auth";

interface SidebarProps {
  actor?: AuthenticatedActor;
  onOpenPersonaModal: () => void;
  openIncidentsCount?: number;
  pendingApprovalsCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  actor,
  onOpenPersonaModal,
  openIncidentsCount,
  pendingApprovalsCount,
}) => {
  const navItems = [
    { name: "Overview", path: "/", icon: LayoutDashboard },
    {
      name: "Incidents",
      path: "/incidents",
      icon: AlertTriangle,
      badge: openIncidentsCount && openIncidentsCount > 0 ? openIncidentsCount : undefined,
      badgeVariant: "critical" as const,
    },
    { name: "Investigations & RCA", path: "/investigations", icon: SearchCode },
    { name: "Remediation Plans", path: "/remediation", icon: FileCheck2 },
    {
      name: "Approvals",
      path: "/approvals",
      icon: CheckCircle,
      badge: pendingApprovalsCount && pendingApprovalsCount > 0 ? pendingApprovalsCount : undefined,
      badgeVariant: "high" as const,
    },
    { name: "Executions", path: "/executions", icon: PlaySquare },
    { name: "Verifications", path: "/verifications", icon: ClipboardCheck },
    { name: "Rollback Readiness", path: "/rollbacks", icon: Undo2 },
    { name: "Audit History", path: "/audit", icon: History },
    { name: "Settings", path: "/settings", icon: Settings },
  ];

  return (
    <aside className="w-64 bg-obsidian-850 border-r border-obsidian-700 flex flex-col h-screen shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-4 border-b border-obsidian-700 flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-copper-500 to-amber-500 flex items-center justify-center text-obsidian-950 font-bold shadow-copper-sm ring-1 ring-copper-400/40 shrink-0">
          <ShieldCheck className="w-5 h-5 text-obsidian-950 stroke-[2.5]" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-base tracking-tight text-obsidian-text">AegisOps</span>
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 bg-copper-400/10 text-copper-400 border border-copper-400/30 rounded font-semibold">
              v0.1
            </span>
          </div>
          <p className="text-[11px] text-obsidian-muted font-medium truncate">
            Agentic SRE Platform
          </p>
        </div>
      </div>

      {/* Nav List */}
      <nav className="flex-1 px-3 py-3.5 space-y-1 overflow-y-auto">
        <div className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-obsidian-muted font-mono">
          Command Center
        </div>
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === "/"}
            className={({ isActive }) =>
              `flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? "bg-copper-400/15 text-copper-400 border border-copper-400/30 font-semibold shadow-obsidian-sm"
                  : "text-obsidian-secondary hover:text-obsidian-text hover:bg-obsidian-750"
              }`
            }
          >
            <div className="flex items-center gap-2.5">
              <item.icon className="w-4 h-4 text-current shrink-0" />
              <span>{item.name}</span>
            </div>
            {item.badge !== undefined && (
              <span
                className={`px-1.5 py-0.2 text-[10px] font-bold font-mono rounded-full ${
                  item.badgeVariant === "critical"
                    ? "bg-rose-500/20 text-status-critical border border-status-critical/30"
                    : "bg-amber-400/20 text-status-warning border border-status-warning/30"
                }`}
              >
                {item.badge}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Observability Tools Integration Links */}
      <div className="px-3 py-2 border-t border-obsidian-700/80">
        <a
          href="http://localhost:3000"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium text-obsidian-muted hover:text-obsidian-text hover:bg-obsidian-750 transition-colors"
        >
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-status-healthy animate-pulse" />
            <span>Grafana Dashboard</span>
          </div>
          <ExternalLink className="w-3.5 h-3.5 text-obsidian-muted" />
        </a>
      </div>

      {/* Persona & Identity Footer */}
      <div className="p-3 border-t border-obsidian-700 bg-obsidian-900/60">
        <button
          onClick={onOpenPersonaModal}
          title="Switch Persona"
          className="w-full flex items-center justify-between p-2 rounded-lg border border-obsidian-700 hover:border-copper-400/50 bg-obsidian-800 transition-all text-left group"
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-7 h-7 rounded-full bg-copper-400/10 border border-copper-400/30 flex items-center justify-center text-copper-400 shrink-0">
              <User className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-obsidian-text truncate group-hover:text-copper-300">
                {actor?.identity || "sre-operator-dan"}
              </p>
              <p className="text-[10px] text-obsidian-muted truncate font-mono">
                {actor?.roles?.join(", ") || "operator"}
              </p>
            </div>
          </div>
          <span className="text-[10px] text-copper-400 font-semibold px-1.5 py-0.5 rounded bg-copper-400/10 border border-copper-400/30 shrink-0 font-mono">
            Switch
          </span>
        </button>
      </div>
    </aside>
  );
};
