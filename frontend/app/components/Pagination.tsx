"use client";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  totalItems: number;
  pageSize: number;
}

export function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  totalItems,
  pageSize,
}: PaginationProps) {
  if (totalPages <= 1) return null;

  const startItem = (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  // Generate page numbers to show
  const pages: (number | "...")[] = [];
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (currentPage > 3) pages.push("...");
    for (
      let i = Math.max(2, currentPage - 1);
      i <= Math.min(totalPages - 1, currentPage + 1);
      i++
    ) {
      pages.push(i);
    }
    if (currentPage < totalPages - 2) pages.push("...");
    pages.push(totalPages);
  }

  return (
    <nav
      aria-label="Navegação de páginas"
      className="flex flex-col sm:flex-row items-center justify-between gap-3 mt-4"
    >
      <p className="text-sm text-ink-muted">
        Mostrando {startItem}-{endItem} de {totalItems} itens
      </p>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          className="px-3 py-1.5 text-sm rounded-button border border-strong text-ink-secondary hover:bg-surface-1 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Página anterior"
        >
          Anterior
        </button>
        {pages.map((p, i) =>
          p === "..." ? (
            <span key={`ellipsis-${i}`} className="px-2 text-ink-muted">
              ...
            </span>
          ) : (
            <button
              key={p}
              onClick={() => onPageChange(p)}
              className={`px-3 py-1.5 text-sm rounded-button transition-colors ${
                p === currentPage
                  ? "bg-brand-navy text-white font-semibold"
                  : "border border-strong text-ink-secondary hover:bg-surface-1"
              }`}
              aria-label={`Página ${p}`}
              aria-current={p === currentPage ? "page" : undefined}
            >
              {p}
            </button>
          )
        )}
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          className="px-3 py-1.5 text-sm rounded-button border border-strong text-ink-secondary hover:bg-surface-1 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Próxima página"
        >
          Próxima
        </button>
      </div>
    </nav>
  );
}
