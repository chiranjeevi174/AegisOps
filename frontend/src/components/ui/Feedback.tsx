import React from "react";
import { FolderOpen } from "lucide-react";

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon = <FolderOpen className="w-10 h-10 text-obsidian-muted" />,
  title,
  description,
  action,
}) => (
  <div className="flex flex-col items-center justify-center p-8 text-center bg-obsidian-800/50 border border-obsidian-700/80 rounded-xl my-4 text-obsidian-text">
    <div className="p-3 bg-obsidian-750/70 border border-obsidian-700 rounded-full mb-3 text-copper-400">
      {icon}
    </div>
    <h3 className="text-sm font-semibold text-obsidian-text">{title}</h3>
    {description && (
      <p className="text-xs text-obsidian-secondary max-w-sm mt-1">{description}</p>
    )}
    {action && <div className="mt-4">{action}</div>}
  </div>
);

export const Skeleton: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className = "",
  ...props
}) => (
  <div
    className={`animate-pulse bg-obsidian-750/70 border border-obsidian-700/40 rounded ${className}`}
    {...props}
  />
);

export interface AlertMessageProps {
  type?: "info" | "success" | "warning" | "error";
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export const AlertMessage: React.FC<AlertMessageProps> = ({
  type = "info",
  title,
  children,
  className = "",
}) => {
  const typeStyles = {
    info: "bg-ai-violet/10 border-ai-violet/30 text-ai-violet",
    success: "bg-status-healthy/10 border-status-healthy/30 text-status-healthy",
    warning: "bg-amber-400/10 border-status-warning/30 text-status-warning",
    error: "bg-rose-500/10 border-status-critical/30 text-status-critical",
  };

  return (
    <div
      className={`border rounded-lg p-3.5 text-xs ${typeStyles[type]} ${className}`}
      role="alert"
    >
      {title && <h5 className="font-semibold mb-1 text-sm">{title}</h5>}
      <div className="text-obsidian-secondary">{children}</div>
    </div>
  );
};
