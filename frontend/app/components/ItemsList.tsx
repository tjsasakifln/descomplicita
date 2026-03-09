"use client";

import { useState, useEffect, useCallback } from "react";
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
  const pageSize = 20;

  const fetchPage = useCallback(
    async (pageNum: number) => {
      setLoading(true);
      try {
        const res = await fetch(
          `/api/buscar/items?job_id=${jobId}&page=${pageNum}&page_size=${pageSize}`
        );
        if (res.ok) {
          const data = await res.json();
          setItems(data.items || []);
          setTotalPages(data.total_pages || 0);
          setTotalItems(data.total_items || 0);
          setPage(pageNum);
        }
      } catch {
        // silently fail
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
  }, [totalFiltered, fetchPage]);

  if (totalFiltered === 0) return null;

  return (
    <div className="mt-4">
      <h3 className="text-lg font-semibold font-display text-ink mb-3">
        Licitacoes Encontradas
      </h3>

      {loading ? (
        <div className="py-8 text-center text-ink-muted">Carregando...</div>
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
