"use client";

import type { BuscaResult } from "../types";
import { Button } from "./Button";

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
      <Button
        onClick={onDownload}
        loading={downloadLoading}
        size="lg"
        className="w-full sm:py-4 text-base sm:text-lg font-semibold"
        aria-label={`Baixar Excel com ${result.resumo.total_oportunidades} licitações`}
      >
        {downloadLoading ? (
          "Preparando download..."
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
      </Button>

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
      <Button
        onClick={onSaveSearch}
        disabled={isMaxCapacity}
        type="button"
        variant="secondary"
        className="w-full"
        title={isMaxCapacity ? "Máximo de 10 buscas salvas atingido" : "Salvar esta busca"}
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
        </svg>
        {isMaxCapacity ? "Limite de buscas atingido" : "Salvar Busca"}
      </Button>

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
