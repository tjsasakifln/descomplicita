import { APP_VERSION } from "../../lib/version";

interface FooterProps {
  currentPage?: "termos";
}

export function Footer({ currentPage }: FooterProps) {
  return (
    <footer className="border-t mt-12 py-6 text-xs text-ink-muted">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-2">
        <span>DescompLicita &mdash; Licitações e Contratos de Forma Descomplicada</span>
        <nav aria-label="Links do rodapé" className="flex items-center gap-4">
          <a href="mailto:contato@descomplicita.com.br" className="hover:text-ink transition-colors">Contato</a>
          <a
            href="/termos"
            className="hover:text-ink transition-colors"
            {...(currentPage === "termos" ? { "aria-current": "page" as const } : {})}
          >
            Termos de Uso
          </a>
          <span className="tabular-nums font-data">{APP_VERSION}</span>
        </nav>
      </div>
    </footer>
  );
}
