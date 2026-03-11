"use client";

import { forwardRef } from "react";
import type React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  variant?: "default" | "error";
  inputSize?: "sm" | "md" | "lg";
  label?: string;
  error?: string;
  hint?: string;
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

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { variant, inputSize = "md", label, error, hint, className, id, ...props },
  ref,
) {
  const resolvedVariant = error ? "error" : (variant ?? "default");
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

  return (
    <div className="w-full">
      {label && (
        <label
          htmlFor={inputId}
          className="block text-sm font-medium text-ink mb-1.5"
        >
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={inputId}
        aria-invalid={!!error}
        aria-describedby={
          error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined
        }
        className={`w-full border rounded-input bg-surface-0 text-ink
                    focus:outline-none focus:ring-2 transition-colors
                    disabled:bg-ink-faint disabled:text-ink-muted disabled:cursor-not-allowed
                    placeholder:text-ink-faint
                    ${sizeClasses[inputSize]} ${variantClasses[resolvedVariant]} ${className || ""}`.trim()}
        {...props}
      />
      {error && (
        <p
          id={`${inputId}-error`}
          className="text-sm text-error mt-1.5 font-medium"
          role="alert"
        >
          {error}
        </p>
      )}
      {hint && !error && (
        <p id={`${inputId}-hint`} className="text-sm text-ink-muted mt-1.5">
          {hint}
        </p>
      )}
    </div>
  );
});
