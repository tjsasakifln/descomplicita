"use client";

import type { BuscaResult } from "../types";
import { Spinner } from "./Spinner";

interface SearchActionsProps {
  result: BuscaResult;
  rawCount: number;
  sectorName: string;
  downloadLoading: boolean;
  downloadError: string | null;
  isMaxCapacity: boolean;
  onDownload: () => void;
  onDownloadCsv?: () => void;
  onSaveSearch: () => void;
}

export function SearchActions({
  result,
  rawCount,
  sectorName,
  downloadLoading,
  downloadError,
  isMaxCapacity,
  onDownload,
  onDownloadCsv,
  onSaveSearch,
}: SearchActionsProps) {
  return (
    <>
      {/* Download Button */}
      <button
        onClick={onDownload}
        disabled={downloadLoading}
        aria-label={`Baixar Excel com ${result.resumo.total_oportunidades} licitações`}
        className="w-full bg-brand-navy text-white py-3 sm:py-4 rounded-button text-base sm:text-lg font-semibold
                   hover:bg-brand-blue-hover active:bg-brand-blue
                   disabled:bg-ink-faint disabled:text-ink-muted disabled:cursor-not-allowed
                   transition-all duration-200
                   flex items-center justify-center gap-3"
      >
        {downloadLoading ? (
          <>
            <Spinner size="md" />
            Preparando download...
          </>
        ) : (
          <>
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Baixar Excel ({result.export_limited
              ? `${(result.excel_item_limit ?? 10000).toLocaleString("pt-BR")} de ${result.resumo.total_oportunidades.toLocaleString("pt-BR")}`
              : result.resumo.total_oportunidades.toLocaleString("pt-BR")
            } licitações)
          </>
        )}
      </button>

      {/* Export limit message + CSV download (v3-story-2.2) */}
      {result.export_limited && onDownloadCsv && (
        <div className="p-3 sm:p-4 bg-warning-subtle border border-warning/20 rounded-card" role="status">
          <p className="text-sm font-medium text-warning-fg mb-2">
            Exportação Excel limitada a {(result.excel_item_limit ?? 10000).toLocaleString("pt-BR")} itens.
          </p>
          <button
            onClick={onDownloadCsv}
            disabled={downloadLoading}
            className="text-sm text-brand-navy font-medium underline hover:text-brand-blue-hover
                       disabled:text-ink-muted disabled:no-underline disabled:cursor-not-allowed"
          >
            Baixar CSV completo ({result.resumo.total_oportunidades.toLocaleString("pt-BR")} licitações)
          </button>
        </div>
      )}

      {/* Save Search Button */}
      <button
        onClick={onSaveSearch}
        disabled={isMaxCapacity}
        type="button"
        className="w-full bg-surface-0 text-brand-navy py-2.5 sm:py-3 rounded-button text-sm sm:text-base font-medium
                   border border-brand-navy hover:bg-brand-blue-subtle
                   disabled:bg-surface-0 disabled:text-ink-muted disabled:border-ink-faint disabled:cursor-not-allowed
                   transition-all duration-200 flex items-center justify-center gap-2"
        title={isMaxCapacity ? "Máximo de 10 buscas salvas atingido" : "Salvar esta busca"}
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
        </svg>
        {isMaxCapacity ? "Limite de buscas atingido" : "Salvar Busca"}
      </button>

      {/* Download Error */}
      {downloadError && (
        <div className="p-4 sm:p-5 bg-error-subtle border border-error/20 rounded-card" role="alert">
          <p className="text-sm sm:text-base font-medium text-error">{downloadError}</p>
        </div>
      )}

      {/* Stats */}
      <div className="text-xs sm:text-sm text-ink-muted text-center">
        {rawCount > 0 && (
          <p>
            Encontradas {result.resumo.total_oportunidades} de {rawCount.toLocaleString("pt-BR")} licitações
            ({((result.resumo.total_oportunidades / rawCount) * 100).toFixed(1)}% do setor {sectorName.toLowerCase()})
          </p>
        )}
      </div>
    </>
  );
}
