"use client";

import type { ValidationErrors } from "../types";
import { Input } from "./Input";

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
        <Input
          id="data-inicial"
          type="date"
          label="Data inicial:"
          value={dataInicial}
          onChange={e => onDataInicialChange(e.target.value)}
        />
        <Input
          id="data-final"
          type="date"
          label="Data final:"
          value={dataFinal}
          onChange={e => onDataFinalChange(e.target.value)}
        />
      </div>

      {validationErrors.date_range && (
        <p className="text-sm sm:text-base text-error mt-3 font-medium" role="alert">
          {validationErrors.date_range}
        </p>
      )}
    </section>
  );
}
