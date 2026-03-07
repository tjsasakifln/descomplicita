"use client";

interface SaveSearchDialogProps {
  saveSearchName: string;
  onNameChange: (name: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
  saveError: string | null;
}

export function SaveSearchDialog({
  saveSearchName,
  onNameChange,
  onConfirm,
  onCancel,
  saveError,
}: SaveSearchDialogProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-label="Salvar Busca"
    >
      <div className="bg-surface-0 rounded-card shadow-xl max-w-md w-full p-6 animate-fade-in-up">
        <h3 className="text-lg font-semibold text-ink mb-4">Salvar Busca</h3>

        <div className="mb-4">
          <label htmlFor="save-search-name" className="block text-sm font-medium text-ink-secondary mb-2">
            Nome da busca:
          </label>
          <input
            id="save-search-name"
            type="text"
            value={saveSearchName}
            onChange={(e) => onNameChange(e.target.value)}
            placeholder="Ex: Uniformes Sul do Brasil"
            className="w-full border border-strong rounded-input px-4 py-2.5 text-base
                       bg-surface-0 text-ink
                       focus:outline-none focus:ring-2 focus:ring-brand-blue focus:border-brand-blue
                       transition-colors"
            maxLength={50}
            autoFocus
          />
          <p className="text-xs text-ink-muted mt-1">
            {saveSearchName.length}/50 caracteres
          </p>
        </div>

        {saveError && (
          <div className="mb-4 p-3 bg-error-subtle border border-error/20 rounded text-sm text-error" role="alert">
            {saveError}
          </div>
        )}

        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            type="button"
            className="px-4 py-2 text-sm font-medium text-ink-secondary hover:text-ink
                       hover:bg-surface-1 rounded-button transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={!saveSearchName.trim()}
            type="button"
            className="px-4 py-2 text-sm font-medium text-white bg-brand-navy
                       hover:bg-brand-blue-hover rounded-button transition-colors
                       disabled:bg-ink-faint disabled:cursor-not-allowed"
          >
            Salvar
          </button>
        </div>
      </div>
    </div>
  );
}
