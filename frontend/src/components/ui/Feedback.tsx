import React from "react";
import { FolderOpen } from "lucide-react";

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon = <FolderOpen className="w-10 h-10 text-slate-500" />,
  title,
  description,
  action,
}) => (
  <div className="flex flex-col items-center justify-center p-8 text-center bg-slate-900/40 border border-slate-800/80 rounded-xl my-4">
    <div className="p-3 bg-slate-800/60 rounded-full mb-3">{icon}</div>
    <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
    {description && (
      <p className="text-xs text-slate-400 max-w-sm mt-1">{description}</p>
    )}
    {action && <div className="mt-4">{action}</div>}
  </div>
);

export const Skeleton: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className = "",
  ...props
}) => (
  <div
    className={`animate-pulse bg-slate-800/70 rounded ${className}`}
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
    info: "bg-blue-950/50 border-blue-800/60 text-blue-200",
    success: "bg-emerald-950/50 border-emerald-800/60 text-emerald-200",
    warning: "bg-amber-950/50 border-amber-800/60 text-amber-200",
    error: "bg-rose-950/50 border-rose-800/60 text-rose-200",
  };

  return (
    <div
      className={`border rounded-lg p-3.5 text-xs ${typeStyles[type]} ${className}`}
      role="alert"
    >
      {title && <h5 className="font-semibold mb-1 text-sm">{title}</h5>}
      <div>{children}</div>
    </div>
  );
};
