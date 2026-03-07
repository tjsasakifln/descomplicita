"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Application error:", error);
  }, [error]);

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{ background: "var(--canvas, #f7f8fa)", color: "var(--ink, #1e2d3b)" }}
    >
      <div
        className="max-w-md w-full shadow-lg rounded-lg p-8 text-center"
        style={{ background: "var(--surface-0, #ffffff)", borderRadius: "var(--radius-card, 8px)" }}
      >
        <div className="mb-6">
          <svg
            className="mx-auto h-16 w-16"
            style={{ color: "var(--error, #dc2626)" }}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>

        <h1
          className="text-2xl font-bold mb-2"
          style={{ color: "var(--ink, #1e2d3b)" }}
        >
          Ops! Algo deu errado
        </h1>

        <p
          className="mb-6"
          style={{ color: "var(--ink-secondary, #3d5975)" }}
        >
          Ocorreu um erro inesperado. Por favor, tente novamente.
        </p>

        {error.message && (
          <div
            className="mb-6 p-4 rounded-md text-left"
            style={{ background: "var(--surface-1, #f7f8fa)" }}
          >
            <p
              className="text-sm font-mono break-words"
              style={{ color: "var(--ink-secondary, #3d5975)" }}
            >
              {error.message}
            </p>
          </div>
        )}

        <button
          onClick={reset}
          className="w-full font-medium py-3 px-6 rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2"
          style={{
            background: "var(--brand-navy, #0a1e3f)",
            color: "#ffffff",
            borderRadius: "var(--radius-button, 6px)",
          }}
        >
          Tentar novamente
        </button>

        <p
          className="mt-4 text-sm"
          style={{ color: "var(--ink-muted, #5a6a7a)" }}
        >
          Se o problema persistir, entre em contato com o suporte.
        </p>
      </div>
    </div>
  );
}
