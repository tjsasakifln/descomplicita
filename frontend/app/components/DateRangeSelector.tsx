"use client";

import type { ValidationErrors } from "../types";

interface DateRangeSelectorProps {
  dataInicial: string;
  dataFinal: string;
  onDataInicialChange: (date: string) => void;
  onDataFinalChange: (date: string) => void;
  validationErrors: ValidationErrors;
}

export function DateRangeSelector({
  dataInicial,
  dataFinal,
  onDataInicialChange,
  onDataFinalChange,
  validationErrors,
}: DateRangeSelectorProps) {
  return (
    <section className="mb-6 animate-fade-in-up stagger-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label htmlFor="data-inicial" className="block text-base font-semibold text-ink mb-2">
            Data inicial:
          </label>
          <input
            id="data-inicial"
            type="date"
            value={dataInicial}
            onChange={e => onDataInicialChange(e.target.value)}
            className="w-full border border-strong rounded-input px-4 py-3 text-base
                       bg-surface-0 text-ink
                       focus:outline-none focus:ring-2 focus:ring-brand-blue focus:border-brand-blue
                       transition-colors"
          />
        </div>
        <div>
          <label htmlFor="data-final" className="block text-base font-semibold text-ink mb-2">
            Data final:
          </label>
          <input
            id="data-final"
            type="date"
            value={dataFinal}
            onChange={e => onDataFinalChange(e.target.value)}
            className="w-full border border-strong rounded-input px-4 py-3 text-base
                       bg-surface-0 text-ink
                       focus:outline-none focus:ring-2 focus:ring-brand-blue focus:border-brand-blue
                       transition-colors"
          />
        </div>
      </div>

      {validationErrors.date_range && (
        <p className="text-sm sm:text-base text-error mt-3 font-medium" role="alert">
          {validationErrors.date_range}
        </p>
      )}
    </section>
  );
}
