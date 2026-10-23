import React from "react";
import { Loader2 } from "lucide-react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost" | "outline";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = "primary",
  size = "md",
  isLoading = false,
  disabled,
  className = "",
  ...props
}) => {
  const baseClasses =
    "inline-flex items-center justify-center font-medium rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-950 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed select-none";

  const sizeClasses = {
    sm: "px-3 py-1.5 text-xs gap-1.5",
    md: "px-4 py-2 text-sm gap-2",
    lg: "px-5 py-2.5 text-base gap-2.5",
  };

  const variantClasses = {
    primary:
      "bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm shadow-indigo-950/50 active:bg-indigo-700",
    secondary:
      "bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700 active:bg-slate-800",
    danger:
      "bg-rose-600 hover:bg-rose-500 text-white shadow-sm shadow-rose-950/50 active:bg-rose-700",
    ghost:
      "bg-transparent hover:bg-slate-800/60 text-slate-300 hover:text-white",
    outline:
      "border border-slate-700 hover:bg-slate-800 text-slate-200 active:bg-slate-900",
  };

  return (
    <button
      className={`${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && <Loader2 className="w-4 h-4 animate-spin text-current" />}
      {children}
    </button>
  );
};
