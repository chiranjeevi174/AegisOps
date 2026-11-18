import React from "react";
import { Loader2 } from "lucide-react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost" | "outline" | "ai";
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
    "inline-flex items-center justify-center font-medium rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-obsidian-950 focus:ring-copper-400 disabled:opacity-50 disabled:cursor-not-allowed select-none";

  const sizeClasses = {
    sm: "px-3 py-1.5 text-xs gap-1.5",
    md: "px-4 py-2 text-xs font-semibold gap-2",
    lg: "px-5 py-2.5 text-sm font-semibold gap-2.5",
  };

  const variantClasses = {
    primary:
      "bg-copper-400 hover:bg-copper-500 text-obsidian-950 font-semibold shadow-copper-sm active:bg-copper-600 transition-all",
    secondary:
      "bg-obsidian-750 hover:bg-obsidian-700 text-obsidian-text border border-obsidian-700 active:bg-obsidian-800",
    danger:
      "bg-status-critical/90 hover:bg-status-critical text-obsidian-950 font-semibold shadow-sm active:opacity-90",
    ghost:
      "bg-transparent hover:bg-obsidian-750 text-obsidian-secondary hover:text-obsidian-text",
    outline:
      "border border-obsidian-700 hover:border-obsidian-600 hover:bg-obsidian-750 text-obsidian-text active:bg-obsidian-800",
    ai:
      "bg-ai-violet/15 hover:bg-ai-violet/25 text-ai-violet border border-ai-violet/35 font-semibold",
  };

  return (
    <button
      className={`${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && <Loader2 className="w-4 h-4 animate-spin text-current shrink-0" />}
      {children}
    </button>
  );
};
