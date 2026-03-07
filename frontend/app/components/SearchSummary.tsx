"use client";

import type { BuscaResult } from "../types";
import { SourceBadges } from "./SourceBadges";

interface SearchSummaryProps {
  result: BuscaResult;
}

export function SearchSummary({ result }: SearchSummaryProps) {
  return (
    <div className="p-4 sm:p-6 bg-brand-blue-subtle border border-accent rounded-card">
      <p className="text-base sm:text-lg leading-relaxed text-ink">
        {result.resumo.resumo_executivo}
      </p>

      <div className="flex flex-col sm:flex-row flex-wrap gap-4 sm:gap-8 mt-4 sm:mt-6">
        <div>
          <span className="text-3xl sm:text-4xl font-bold font-data tabular-nums text-brand-navy dark:text-brand-blue">
            {result.resumo.total_oportunidades}
          </span>
          <span className="text-sm sm:text-base text-ink-secondary block mt-1">oportunidades</span>
          {(result.total_atas > 0 || result.total_licitacoes > 0) && (
            <div className="flex flex-wrap gap-2 mt-2">
              {result.total_licitacoes > 0 && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-800 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800">
                  {result.total_licitacoes} Licitações
                </span>
              )}
              {result.total_atas > 0 && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-purple-100 text-purple-800 border border-purple-200 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-800">
                  {result.total_atas} Atas RP
                </span>
              )}
            </div>
          )}
        </div>
        <div>
          <span className="text-3xl sm:text-4xl font-bold font-data tabular-nums text-brand-navy dark:text-brand-blue">
            R$ {result.resumo.valor_total.toLocaleString("pt-BR")}
          </span>
          <span className="text-sm sm:text-base text-ink-secondary block mt-1">valor total</span>
        </div>
      </div>

      {result.resumo.alerta_urgencia && (
        <div className="mt-4 sm:mt-6 p-3 sm:p-4 bg-warning-subtle border border-warning/20 rounded-card" role="alert">
          <p className="text-sm sm:text-base font-medium text-warning">
            <span aria-hidden="true">Atenção: </span>
            {result.resumo.alerta_urgencia}
          </p>
        </div>
      )}

      {result.resumo.destaques.length > 0 && (
        <div className="mt-4 sm:mt-6">
          <h3 className="text-base sm:text-lg font-semibold font-display text-ink mb-2 sm:mb-3">Destaques:</h3>
          <ul className="list-disc list-inside text-sm sm:text-base space-y-2 text-ink-secondary">
            {result.resumo.destaques.map((d, i) => (
              <li key={i} className="animate-fade-in-up" style={{ animationDelay: `${i * 60}ms` }}>{d}</li>
            ))}
          </ul>
        </div>
      )}

      {result.sources_used && result.sources_used.length > 0 && (
        <SourceBadges
          sources={result.sources_used}
          stats={result.source_stats}
          dedupRemoved={result.dedup_removed}
          truncatedCombos={result.truncated_combos}
        />
      )}
    </div>
  );
}
