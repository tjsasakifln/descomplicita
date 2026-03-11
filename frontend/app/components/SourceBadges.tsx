"use client";

import { useState } from "react";
import type { SourceStats } from "../types";

const SOURCE_LABELS: Record<string, string> = {
  pncp: "PNCP",
  comprasgov: "Compras.gov",
  transparencia: "Transparencia",
  querido_diario: "Diarios Oficiais",
  tce_rj: "TCE-RJ",
};

interface SourceBadgesProps {
  sources: string[];
  stats: Record<string, SourceStats>;
  dedupRemoved: number;
  truncatedCombos?: number;
}

export function SourceBadges({ sources, stats, dedupRemoved, truncatedCombos = 0 }: SourceBadgesProps) {
  const [expanded, setExpanded] = useState(false);

  if (!sources || sources.length === 0) return null;

  const allSourceNames = Object.keys(stats);

  return (
    <div className="mt-4 sm:mt-6">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        className="flex items-center gap-2 text-sm font-medium text-ink-secondary hover:text-ink transition-colors"
      >
        <svg className="w-4 h-4 text-brand-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
        <span>{allSourceNames.length} fonte{allSourceNames.length !== 1 ? "s" : ""} consultada{allSourceNames.length !== 1 ? "s" : ""}</span>
        <svg className={`w-3.5 h-3.5 transition-transform ${expanded ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Inline badge summary */}
      <div className="flex flex-wrap gap-2 mt-2">
        {allSourceNames.map(name => {
          const stat = stats[name];
          const label = SOURCE_LABELS[name] || name;
          const statusColor =
            stat.status === "success" && stat.total_fetched > 0
              ? "bg-status-success-bg text-status-success-text border-status-success"
              : stat.status === "success" && stat.total_fetched === 0
                ? "bg-status-warning-bg text-status-warning-text border-status-warning"
                : "bg-status-error-bg text-status-error-text border-status-error";

          return (
            <span
              key={name}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full border ${statusColor}`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${
                stat.status === "success" && stat.total_fetched > 0
                  ? "bg-status-success-dot"
                  : stat.status === "success" && stat.total_fetched === 0
                    ? "bg-status-warning-dot"
                    : "bg-status-error-dot"
              }`} />
              {label}: {stat.total_fetched}
            </span>
          );
        })}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="mt-3 p-3 bg-surface-0 rounded-card border text-sm animate-fade-in-up">
          <div className="space-y-2">
            {allSourceNames.map(name => {
              const stat = stats[name];
              const label = SOURCE_LABELS[name] || name;
              return (
                <div key={name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${
                      stat.status === "success" && stat.total_fetched > 0
                        ? "bg-status-success-dot"
                        : stat.status === "success" && stat.total_fetched === 0
                          ? "bg-status-warning-dot"
                          : "bg-status-error-dot"
                    }`} />
                    <span className="font-medium text-ink">{label}</span>
                  </div>
                  <div className="flex items-center gap-3 text-ink-muted">
                    <span>{stat.total_fetched} encontradas</span>
                    {stat.after_dedup !== stat.total_fetched && (
                      <span className="text-xs">({stat.after_dedup} apos dedup)</span>
                    )}
                    <span className="text-xs tabular-nums font-data">{stat.elapsed_ms}ms</span>
                  </div>
                </div>
              );
            })}
          </div>
          {dedupRemoved > 0 && (
            <p className="mt-2 pt-2 border-t text-xs text-ink-muted">
              {dedupRemoved} registro{dedupRemoved !== 1 ? "s" : ""} duplicado{dedupRemoved !== 1 ? "s" : ""} removido{dedupRemoved !== 1 ? "s" : ""}
            </p>
          )}
          {truncatedCombos > 0 && (
            <p className="mt-2 pt-2 border-t text-xs" style={{ color: 'var(--ink-warning)' }}>
              Resultados parciais: {truncatedCombos} combinac{truncatedCombos !== 1 ? "oes" : "ao"} UF/modalidade foram limitadas para evitar timeout. Para resultados completos, reduza o numero de estados.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default SourceBadges;
