import React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?:
    | "default"
    | "primary"
    | "secondary"
    | "critical"
    | "high"
    | "medium"
    | "low"
    | "success"
    | "warning"
    | "info"
    | "danger"
    | "ai"
    | "outline";
  size?: "sm" | "md";
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "default",
  size = "md",
  className = "",
  ...props
}) => {
  const baseClasses =
    "inline-flex items-center font-medium rounded-full tracking-wide transition-colors font-mono select-none";

  const sizeClasses = {
    sm: "px-2 py-0.5 text-[11px]",
    md: "px-2.5 py-0.5 text-xs",
  };

  const variantClasses = {
    default: "bg-obsidian-750 text-obsidian-secondary border border-obsidian-700",
    primary: "bg-copper-400/15 text-copper-400 border border-copper-400/35 font-semibold",
    secondary: "bg-obsidian-800 text-obsidian-text border border-obsidian-700",
    critical: "bg-rose-500/15 text-status-critical border border-status-critical/35 font-semibold",
    high: "bg-amber-400/15 text-status-warning border border-status-warning/35 font-semibold",
    medium: "bg-copper-500/15 text-copper-400 border border-copper-500/35 font-medium",
    low: "bg-status-healthy/15 text-status-healthy border border-status-healthy/35",
    success: "bg-status-healthy/15 text-status-healthy border border-status-healthy/35",
    warning: "bg-amber-400/15 text-status-warning border border-status-warning/35",
    info: "bg-ai-violet/15 text-ai-violet border border-ai-violet/35",
    ai: "bg-ai-violet/15 text-ai-violet border border-ai-violet/35 font-semibold",
    danger: "bg-rose-500/15 text-status-critical border border-status-critical/35 font-semibold",
    outline: "border border-obsidian-700 text-obsidian-secondary bg-transparent",
  };

  return (
    <span
      className={`${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
};
