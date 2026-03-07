"use client";

import { RegionSelector } from "./RegionSelector";
import { UFS, UF_NAMES } from "../constants/ufs";
import type { ValidationErrors } from "../types";

interface UfSelectorProps {
  ufsSelecionadas: Set<string>;
  onToggleUf: (uf: string) => void;
  onToggleRegion: (regionUfs: string[]) => void;
  onSelecionarTodos: () => void;
  onLimparSelecao: () => void;
  validationErrors: ValidationErrors;
}

export function UfSelector({
  ufsSelecionadas,
  onToggleUf,
  onToggleRegion,
  onSelecionarTodos,
  onLimparSelecao,
  validationErrors,
}: UfSelectorProps) {
  return (
    <section className="mb-6 animate-fade-in-up stagger-2">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 mb-3">
        <label className="text-base sm:text-lg font-semibold text-ink">
          Estados (UFs):
        </label>
        <div className="flex gap-3">
          <button
            onClick={onSelecionarTodos}
            className="text-sm sm:text-base font-medium text-brand-blue hover:text-brand-blue-hover hover:underline transition-colors"
            type="button"
          >
            Selecionar todos
          </button>
          <button
            onClick={onLimparSelecao}
            className="text-sm sm:text-base font-medium text-ink-muted hover:text-ink transition-colors"
            type="button"
          >
            Limpar
          </button>
        </div>
      </div>

      <RegionSelector selected={ufsSelecionadas} onToggleRegion={onToggleRegion} />

      <div role="group" aria-label="Selecionar Unidades Federativas" className="grid grid-cols-5 sm:grid-cols-7 md:grid-cols-9 gap-2">
        {UFS.map(uf => (
          <button
            key={uf}
            onClick={() => onToggleUf(uf)}
            type="button"
            title={UF_NAMES[uf]}
            aria-pressed={ufsSelecionadas.has(uf)}
            className={`px-2 py-2 sm:px-4 rounded-button border text-sm sm:text-base font-medium transition-all duration-200 ${
              ufsSelecionadas.has(uf)
                ? "bg-brand-navy text-white border-brand-navy hover:bg-brand-blue-hover"
                : "bg-surface-0 text-ink-secondary border hover:border-accent hover:text-brand-blue hover:bg-brand-blue-subtle"
            }`}
          >
            {uf}
          </button>
        ))}
      </div>

      <p className="text-sm sm:text-base text-ink-muted mt-2">
        {ufsSelecionadas.size === 1 ? '1 estado selecionado' : `${ufsSelecionadas.size} estados selecionados`}
      </p>

      {validationErrors.ufs && (
        <p className="text-sm sm:text-base text-error mt-2 font-medium" role="alert">
          {validationErrors.ufs}
        </p>
      )}
    </section>
  );
}
