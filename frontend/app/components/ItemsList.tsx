"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Pagination } from "./Pagination";

interface ProcurementItem {
  objeto?: string;
  orgao?: string;
  uf?: string;
  valorTotalEstimado?: number;
  dataPublicacao?: string;
  link?: string;
  tipo?: string;
  [key: string]: unknown;
}

interface ItemsListProps {
  jobId: string;
  totalFiltered: number;
}

export function ItemsList({ jobId, totalFiltered }: ItemsListProps) {
  const [items, setItems] = useState<ProcurementItem[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalItems, setTotalItems] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const pageSize = 20;

  const fetchPage = useCallback(
    async (pageNum: number) => {
      // Abort any in-flight request before starting a new one
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const controller = new AbortController();
      abortControllerRef.current = controller;

      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `/api/buscar/items?job_id=${jobId}&page=${pageNum}&page_size=${pageSize}`,
          { signal: controller.signal }
        );

        if (!res.ok) {
          setError("Erro ao carregar página. Tente novamente.");
          return;
        }

        let data: {
          items?: ProcurementItem[];
          total_pages?: number;
          total_items?: number;
        };
        try {
          data = await res.json();
        } catch {
          setError("Erro ao processar dados do servidor.");
          return;
        }

        setItems(data.items || []);
        setTotalPages(data.total_pages || 0);
        setTotalItems(data.total_items || 0);
        setPage(pageNum);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          // Request was intentionally aborted — do not update error state
          return;
        }
        if (err instanceof TypeError) {
          // TypeError from fetch typically indicates a network failure
          setError(
            "Erro de conexão. Verifique sua internet e tente novamente."
          );
        } else {
          setError("Erro ao carregar página. Tente novamente.");
        }
      } finally {
        setLoading(false);
      }
    },
    [jobId]
  );

  useEffect(() => {
    if (totalFiltered > 0) {
      fetchPage(1);
    }

    // Clean up on unmount
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [totalFiltered, fetchPage]);

  if (totalFiltered === 0) return null;

  return (
    <div className="mt-4">
      <h3 className="text-lg font-semibold font-display text-ink mb-3">
        Licitacoes Encontradas
      </h3>

      {loading ? (
        <div className="py-8 text-center text-ink-muted">Carregando...</div>
      ) : error ? (
        <div className="py-8 text-center space-y-3">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          <button
            onClick={() => fetchPage(page)}
            className="px-4 py-2 text-sm font-medium text-brand-blue hover:text-brand-navy border border-brand-blue/30 rounded-button hover:bg-brand-blue-subtle transition-colors"
          >
            Tentar novamente
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item, idx) => (
            <div
              key={`${page}-${idx}`}
              className="p-4 bg-surface-1 border border-strong rounded-card hover:border-brand-blue/30 transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-ink line-clamp-2">
                    {item.objeto || "Sem descricao"}
                  </p>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-ink-muted">
                    {item.orgao && <span>{item.orgao}</span>}
                    {item.uf && (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-surface-2 font-medium">
                        {item.uf}
                      </span>
                    )}
                    {item.valorTotalEstimado != null &&
                      item.valorTotalEstimado > 0 && (
                        <span className="font-data font-medium text-brand-navy dark:text-brand-blue">
                          R$ {item.valorTotalEstimado.toLocaleString("pt-BR")}
                        </span>
                      )}
                    {item.dataPublicacao && (
                      <span>
                        {new Date(item.dataPublicacao).toLocaleDateString(
                          "pt-BR"
                        )}
                      </span>
                    )}
                  </div>
                </div>
                {item.link && (
                  <a
                    href={item.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-shrink-0 px-3 py-1.5 text-xs font-medium text-brand-blue hover:text-brand-navy border border-brand-blue/30 rounded-button hover:bg-brand-blue-subtle transition-colors"
                  >
                    Ver
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <Pagination
        currentPage={page}
        totalPages={totalPages}
        onPageChange={fetchPage}
        totalItems={totalItems}
        pageSize={pageSize}
      />
    </div>
  );
}
