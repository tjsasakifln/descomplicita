"use client";

import type React from "react";
import { Spinner } from "./Spinner";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  children: React.ReactNode;
}

const variantClasses = {
  primary: "bg-brand-navy text-white hover:bg-brand-blue-hover active:bg-brand-blue",
  secondary: "bg-surface-0 text-brand-navy border border-brand-navy hover:bg-brand-blue-subtle",
  ghost: "bg-transparent text-ink-secondary hover:bg-surface-1",
  danger: "bg-error text-white hover:opacity-90",
};

const sizeClasses = {
  sm: "py-1.5 px-3 text-sm",
  md: "py-2.5 px-4 text-base",
  lg: "py-3 px-6 text-lg",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  children,
  disabled,
  className,
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`rounded-button font-medium transition-all duration-200 min-h-[44px] flex items-center justify-center gap-2 ${sizeClasses[size]} ${variantClasses[variant]} disabled:bg-ink-faint disabled:text-ink-muted disabled:cursor-not-allowed ${className || ""}`.trim()}
    >
      {loading && <Spinner size="sm" />}
      {children}
    </button>
  );
}
