import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <h1 className="text-6xl font-bold font-display text-brand-navy mb-4">404</h1>
        <h2 className="text-xl font-semibold text-ink mb-2">Página não encontrada</h2>
        <p className="text-ink-muted mb-8">
          A página que você procura não existe ou foi movida.
        </p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-6 py-3 bg-brand-navy text-white
                     rounded-button font-medium hover:bg-brand-blue-hover transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Voltar para a busca
        </Link>
      </div>
    </div>
  );
}
