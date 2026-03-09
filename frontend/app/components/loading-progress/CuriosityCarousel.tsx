import type { Curiosidade, CuriosidadeCategoria } from "../carouselData";
import { CATEGORIA_CONFIG } from "../carouselData";

const CATEGORIA_ICON_SVG_PATHS: Record<string, string> = {
  scale: "M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l3 9a5.002 5.002 0 006.001 0M18 7l-3 9m3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3",
  target: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
  chart: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  bulb: "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z",
};

function CategoriaIcon({ icon, className }: { icon: string; className?: string }) {
  const path = CATEGORIA_ICON_SVG_PATHS[icon];
  if (!path) return null;
  return (
    <svg className={className || "w-4 h-4"} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d={path} />
    </svg>
  );
}

interface CuriosityCarouselProps {
  curiosidade: Curiosidade;
  isFading: boolean;
}

export function CuriosityCarousel({ curiosidade, isFading }: CuriosityCarouselProps) {
  const categoriaConfig = CATEGORIA_CONFIG[curiosidade.categoria];

  return (
    <div
      className={`p-4 rounded-card border transition-all duration-300 ${categoriaConfig.bgClass} ${isFading ? "opacity-0" : "opacity-100"}`}
    >
      <div className="flex items-start gap-3">
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${categoriaConfig.iconBgClass}`}>
          <CategoriaIcon icon={categoriaConfig.icon} className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <p className="text-sm font-medium text-ink-muted">{categoriaConfig.header}</p>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${categoriaConfig.iconBgClass} ${categoriaConfig.iconTextClass}`}>
              {categoriaConfig.label}
            </span>
          </div>
          <p className="text-base text-ink leading-relaxed">{curiosidade.texto}</p>
          <p className="text-xs text-ink-muted mt-2">Fonte: {curiosidade.fonte}</p>
        </div>
      </div>
    </div>
  );
}
