"use client";

import { forwardRef } from "react";
import type React from "react";

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps
  extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "size"> {
  variant?: "default" | "error";
  selectSize?: "sm" | "md" | "lg";
  label?: string;
  error?: string;
  hint?: string;
  options: SelectOption[];
  placeholder?: string;
}

const sizeClasses = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-3 text-base",
  lg: "px-4 py-3.5 text-lg",
};

const variantClasses = {
  default:
    "border-strong focus:ring-brand-blue focus:border-brand-blue",
  error:
    "border-error focus:ring-error focus:border-error",
};

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  function Select(
    {
      variant,
      selectSize = "md",
      label,
      error,
      hint,
      options,
      placeholder,
      className,
      id,
      ...props
    },
    ref,
  ) {
    const resolvedVariant = error ? "error" : (variant ?? "default");
    const selectId =
      id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={selectId}
            className="block text-sm font-medium text-ink mb-1.5"
          >
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          aria-invalid={!!error}
          aria-describedby={
            error
              ? `${selectId}-error`
              : hint
                ? `${selectId}-hint`
                : undefined
          }
          className={`w-full border rounded-input bg-surface-0 text-ink
                      focus:outline-none focus:ring-2 transition-colors
                      disabled:bg-ink-faint disabled:text-ink-muted disabled:cursor-not-allowed
                      ${sizeClasses[selectSize]} ${variantClasses[resolvedVariant]} ${className || ""}`.trim()}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} disabled={opt.disabled}>
              {opt.label}
            </option>
          ))}
        </select>
        {error && (
          <p
            id={`${selectId}-error`}
            className="text-sm text-error mt-1.5 font-medium"
            role="alert"
          >
            {error}
          </p>
        )}
        {hint && !error && (
          <p id={`${selectId}-hint`} className="text-sm text-ink-muted mt-1.5">
            {hint}
          </p>
        )}
      </div>
    );
  },
);
