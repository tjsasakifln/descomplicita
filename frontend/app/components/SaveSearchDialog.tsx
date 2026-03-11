"use client";

import { useRef, useEffect } from "react";
import { Button } from "./Button";
import { Input } from "./Input";

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
          <Input
            ref={inputRef}
            id="save-search-name"
            label="Nome da busca:"
            value={saveSearchName}
            onChange={(e) => onNameChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && saveSearchName.trim()) {
                e.preventDefault();
                onConfirm();
              }
            }}
            placeholder="Ex: Uniformes Sul do Brasil"
            maxLength={50}
            hint={`${saveSearchName.length}/50 caracteres`}
            error={saveError ?? undefined}
          />
        </div>

        <div className="flex gap-3 justify-end">
          <Button onClick={onCancel} type="button" variant="ghost" size="sm">
            Cancelar
          </Button>
          <Button onClick={onConfirm} disabled={!saveSearchName.trim()} type="button" size="sm">
            Salvar
          </Button>
        </div>
      </div>
    </dialog>
  );
}
