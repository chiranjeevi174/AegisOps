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
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col h-screen shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800/80 flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center text-white shadow-md shadow-indigo-950/60 ring-1 ring-indigo-400/40">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-base tracking-tight text-white">AegisOps</span>
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 bg-indigo-950 text-indigo-300 border border-indigo-800 rounded font-semibold">
              v0.1
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-medium truncate max-w-[150px]">
            Agentic SRE Platform
          </p>
        </div>
      </div>

      {/* Nav List */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === "/"}
            className={({ isActive }) =>
              `flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? "bg-indigo-600/15 text-indigo-300 border border-indigo-600/30"
                  : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60"
              }`
            }
          >
            <div className="flex items-center gap-2.5">
              <item.icon className="w-4 h-4 text-current" />
              <span>{item.name}</span>
            </div>
            {item.badge !== undefined && (
              <span
                className={`px-1.5 py-0.2 text-[10px] font-bold rounded-full ${
                  item.badgeVariant === "critical"
                    ? "bg-rose-900 text-rose-200"
                    : "bg-amber-900 text-amber-200"
                }`}
              >
                {item.badge}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Observability Tools Integration Links */}
      <div className="px-3 py-2 border-t border-slate-800/80">
        <a
          href="http://localhost:3000"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-100 hover:bg-slate-800/50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Grafana Dashboard</span>
          </div>
          <ExternalLink className="w-3.5 h-3.5 text-slate-500" />
        </a>
      </div>

      {/* Persona & Identity Footer */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/60">
        <button
          onClick={onOpenPersonaModal}
          title="Switch Persona"
          className="w-full flex items-center justify-between p-2 rounded-lg border border-slate-800 hover:border-slate-700 bg-slate-900/60 transition-all text-left group"
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-7 h-7 rounded-full bg-indigo-950 border border-indigo-800 flex items-center justify-center text-indigo-300 shrink-0">
              <User className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-slate-200 truncate group-hover:text-white">
                {actor?.identity || "sre-operator-dan"}
              </p>
              <p className="text-[10px] text-slate-400 truncate">
                {actor?.roles?.join(", ") || "operator"}
              </p>
            </div>
          </div>
          <span className="text-[10px] text-indigo-400 font-semibold px-1.5 py-0.5 rounded bg-indigo-950 border border-indigo-900 shrink-0">
            Switch
          </span>
        </button>
      </div>
    </aside>
  );
};
