"use client";

import { useRef, useEffect } from "react";

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
  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    // Show as modal (provides built-in focus trap and backdrop)
    if (!dialog.open && typeof dialog.showModal === "function") {
      dialog.showModal();
    }

    // Focus the input
    inputRef.current?.focus();

    // Close on Escape (native dialog handles this, but we need to call onCancel)
    function handleCancel(e: Event) {
      e.preventDefault();
      onCancel();
    }

    dialog.addEventListener("cancel", handleCancel);
    return () => dialog.removeEventListener("cancel", handleCancel);
  }, [onCancel]);

  // Close on backdrop click
  function handleBackdropClick(e: React.MouseEvent<HTMLDialogElement>) {
    if (e.target === dialogRef.current) {
      onCancel();
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-50 m-auto p-0 bg-transparent backdrop:bg-black/50 backdrop:animate-fade-in
                 open:animate-fade-in-up max-w-md w-full"
      aria-labelledby="save-search-dialog-title"
      onClick={handleBackdropClick}
    >
      <div className="bg-surface-0 rounded-card shadow-xl w-full p-6">
        <h3 id="save-search-dialog-title" className="text-lg font-semibold text-ink mb-4">Salvar Busca</h3>

        <div className="mb-4">
          <label htmlFor="save-search-name" className="block text-sm font-medium text-ink-secondary mb-2">
            Nome da busca:
          </label>
          <input
            ref={inputRef}
            id="save-search-name"
            type="text"
            value={saveSearchName}
            onChange={(e) => onNameChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && saveSearchName.trim()) {
                e.preventDefault();
                onConfirm();
              }
            }}
            placeholder="Ex: Uniformes Sul do Brasil"
            className="w-full border border-strong rounded-input px-4 py-2.5 text-base
                       bg-surface-0 text-ink
                       focus:outline-none focus:ring-2 focus:ring-brand-blue focus:border-brand-blue
                       transition-colors"
            maxLength={50}
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
    </dialog>
  );
}
