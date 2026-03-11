"use client";

import type { Setor } from "../types";
import { Select } from "./Select";
import { Spinner } from "./Spinner";

interface SearchFormProps {
  searchMode: "setor" | "termos";
  onSearchModeChange: (mode: "setor" | "termos") => void;
  setores: Setor[];
  setoresLoading?: boolean;
  setoresFallback?: boolean;
  setorId: string;
  onSetorIdChange: (id: string) => void;
  termosArray: string[];
  onTermosArrayChange: React.Dispatch<React.SetStateAction<string[]>>;
  termoInput: string;
  onTermoInputChange: (val: string) => void;
  onFormChange: () => void;
}

export function SearchForm({
  searchMode,
  onSearchModeChange,
  setores,
  setoresLoading,
  setoresFallback,
  setorId,
  onSetorIdChange,
  termosArray,
  onTermosArrayChange,
  termoInput,
  onTermoInputChange,
  onFormChange,
}: SearchFormProps) {
  return (
    <section className="mb-6 animate-fade-in-up stagger-1">
      <label className="block text-base font-semibold text-ink mb-3">
        Buscar por:
      </label>
      <div className="flex rounded-button border border-strong overflow-hidden mb-4">
        <button
          type="button"
          onClick={() => onSearchModeChange("setor")}
          className={`flex-1 py-2.5 text-sm sm:text-base font-medium transition-all duration-200 ${
            searchMode === "setor"
              ? "bg-brand-navy text-white"
              : "bg-surface-0 text-ink-secondary hover:bg-surface-1"
          }`}
        >
          Setor
        </button>
        <button
          type="button"
          onClick={() => onSearchModeChange("termos")}
          className={`flex-1 py-2.5 text-sm sm:text-base font-medium transition-all duration-200 ${
            searchMode === "termos"
              ? "bg-brand-navy text-white"
              : "bg-surface-0 text-ink-secondary hover:bg-surface-1"
          }`}
        >
          Termos Específicos
        </button>
      </div>

      {searchMode === "setor" && (
        <div className="relative">
          {setoresLoading ? (
            <div className="w-full border border-strong rounded-input px-4 py-3 bg-surface-0 flex items-center gap-2"
                 aria-busy="true" aria-label="Carregando setores">
              <Spinner size="sm" className="text-brand-blue" />
              <span className="text-sm text-ink-muted">Carregando setores...</span>
            </div>
          ) : (
            <>
              <Select
                id="setor"
                value={setorId}
                onChange={e => onSetorIdChange(e.target.value)}
                options={setores.map(s => ({ value: s.id, label: s.name }))}
                hint={setoresFallback ? undefined : undefined}
              />
              {setoresFallback && (
                <p className="text-xs text-ink-warning mt-1.5 flex items-center gap-1" role="status">
                  <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Usando lista de setores em cache (servidor indisponível)
                </p>
              )}
            </>
          )}
        </div>
      )}

      {searchMode === "termos" && (
        <div>
          <div className="border border-strong rounded-input bg-surface-0 px-3 py-2 flex flex-wrap gap-2 items-center
                          focus-within:ring-2 focus-within:ring-brand-blue focus-within:border-brand-blue
                          transition-colors min-h-[48px]">
            {termosArray.map((termo, i) => (
              <span
                key={`${termo}-${i}`}
                className="inline-flex items-center gap-1 bg-brand-blue-subtle text-brand-navy
                           px-2.5 py-1 rounded-full text-sm font-medium border border-brand-blue/20
                           animate-fade-in-up"
              >
                {termo}
                <button
                  type="button"
                  onClick={() => {
                    onTermosArrayChange(prev => prev.filter((_, idx) => idx !== i));
                    onFormChange();
                  }}
                  className="ml-0.5 hover:text-error transition-colors"
                  aria-label={`Remover termo ${termo}`}
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </span>
            ))}
            <input
              id="termos-busca"
              type="text"
              aria-describedby="termos-busca-hint"
              value={termoInput}
              onChange={e => {
                const val = e.target.value;
                if (val.endsWith(",")) {
                  const term = val.slice(0, -1).trim().toLowerCase();
                  if (term && !termosArray.includes(term)) {
                    onTermosArrayChange(prev => [...prev, term]);
                    onFormChange();
                  }
                  onTermoInputChange("");
                } else if (val.endsWith(" ")) {
                  const word = val.trim().toLowerCase();
                  if (word && !termosArray.includes(word)) {
                    onTermosArrayChange(prev => [...prev, word]);
                    onFormChange();
                  }
                  onTermoInputChange("");
                } else {
                  onTermoInputChange(val);
                }
              }}
              onKeyDown={e => {
                if (e.key === "Backspace" && termoInput === "" && termosArray.length > 0) {
                  onTermosArrayChange(prev => prev.slice(0, -1));
                  onFormChange();
                }
                if (e.key === "Enter") {
                  e.preventDefault();
                  const word = termoInput.trim().toLowerCase();
                  if (word && !termosArray.includes(word)) {
                    onTermosArrayChange(prev => [...prev, word]);
                    onFormChange();
                  }
                  onTermoInputChange("");
                }
              }}
              placeholder={termosArray.length === 0 ? "Separe termos por vírgula. Ex: camisa polo, jaleco medico" : "Adicionar mais..."}
              className="flex-1 min-w-[120px] outline-none bg-transparent text-base text-ink
                         placeholder:text-ink-faint py-1"
            />
          </div>
          <p id="termos-busca-hint" className="text-sm text-ink-muted mt-1.5">
            Separe termos por <kbd className="px-1.5 py-0.5 bg-surface-2 rounded text-xs font-mono border">vírgula</kbd> para termos compostos. Ex: camisa polo, jaleco medico.
            {" "}Acentos são opcionais — &quot;licitação&quot; e &quot;licitacao&quot; retornam os mesmos resultados.
            {termosArray.length > 0 && (
              <span className="text-brand-blue font-medium">
                {" "}{termosArray.length} termo{termosArray.length > 1 ? "s" : ""} selecionado{termosArray.length > 1 ? "s" : ""}
              </span>
            )}
          </p>
        </div>
      )}
    </section>
  );
}
