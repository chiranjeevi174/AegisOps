import React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, className = "", id, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={inputId} className="block text-xs font-medium text-obsidian-secondary">
            {label}
          </label>
        )}
        <input
          id={inputId}
          ref={ref}
          className={`w-full px-3.5 py-2 bg-obsidian-900 border rounded-lg text-xs text-obsidian-text placeholder-obsidian-muted focus:outline-none focus:ring-1 focus:ring-copper-400 focus:border-copper-400 transition-all disabled:opacity-50 ${
            error ? "border-status-critical focus:ring-status-critical focus:border-status-critical" : "border-obsidian-700"
          } ${className}`}
          {...props}
        />
        {error && <p className="text-xs text-status-critical font-medium">{error}</p>}
        {helperText && !error && <p className="text-xs text-obsidian-muted">{helperText}</p>}
      </div>
    );
  }
);
Input.displayName = "Input";

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options?: Array<{ value: string; label: string }>;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, children, className = "", id, ...props }, ref) => {
    const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={selectId} className="block text-xs font-medium text-obsidian-secondary">
            {label}
          </label>
        )}
        <select
          id={selectId}
          ref={ref}
          className={`w-full px-3.5 py-2 bg-obsidian-900 border rounded-lg text-xs text-obsidian-text focus:outline-none focus:ring-1 focus:ring-copper-400 focus:border-copper-400 transition-all disabled:opacity-50 ${
            error ? "border-status-critical" : "border-obsidian-700"
          } ${className}`}
          {...props}
        >
          {options
            ? options.map((opt) => (
                <option key={opt.value} value={opt.value} className="bg-obsidian-900 text-obsidian-text">
                  {opt.label}
                </option>
              ))
            : children}
        </select>
        {error && <p className="text-xs text-status-critical font-medium">{error}</p>}
      </div>
    );
  }
);
Select.displayName = "Select";
