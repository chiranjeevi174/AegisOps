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
    "inline-flex items-center font-medium rounded-full tracking-wide transition-colors";

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-2.5 py-1 text-xs",
  };

  const variantClasses = {
    default: "bg-slate-800 text-slate-300 border border-slate-700",
    primary: "bg-indigo-950 text-indigo-300 border border-indigo-800",
    secondary: "bg-slate-800 text-slate-200 border border-slate-700",
    critical: "bg-rose-950/80 text-rose-300 border border-rose-800 font-semibold",
    high: "bg-amber-950/80 text-amber-300 border border-amber-800 font-medium",
    medium: "bg-blue-950/80 text-blue-300 border border-blue-800",
    low: "bg-emerald-950/80 text-emerald-300 border border-emerald-800",
    success: "bg-emerald-950/80 text-emerald-300 border border-emerald-800",
    warning: "bg-amber-950/80 text-amber-300 border border-amber-800",
    info: "bg-cyan-950/80 text-cyan-300 border border-cyan-800",
    danger: "bg-rose-950/80 text-rose-300 border border-rose-800",
    outline: "border border-slate-700 text-slate-300 bg-transparent",
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
