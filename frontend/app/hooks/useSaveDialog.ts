import { useState, useCallback } from "react";
import type { UseSearchFormReturn } from "./useSearchForm";

interface UseSaveDialogParams {
  form: UseSearchFormReturn;
  saveNewSearch: (name: string, params: any) => any;
  trackEvent: (name: string, props?: Record<string, any>) => void;
  hasResult: boolean;
}

export interface UseSaveDialogReturn {
  showSaveDialog: boolean;
  saveSearchName: string;
  saveError: string | null;
  handleSaveSearch: () => void;
  confirmSaveSearch: () => void;
  cancelSaveDialog: () => void;
  setSaveSearchName: (name: string) => void;
}

export function useSaveDialog({ form, saveNewSearch, trackEvent, hasResult }: UseSaveDialogParams): UseSaveDialogReturn {
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveSearchName, setSaveSearchName] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);

  const handleSaveSearch = useCallback(() => {
    if (!hasResult) return;
    const defaultName = form.searchMode === "setor"
      ? (form.setores.find(s => s.id === form.setorId)?.name || "Busca personalizada")
      : form.termosArray.length > 0
        ? `Busca: "${form.termosArray.join(", ")}"`
        : "Busca personalizada";
    setSaveSearchName(defaultName);
    setSaveError(null);
    setShowSaveDialog(true);
  }, [hasResult, form.searchMode, form.setores, form.setorId, form.termosArray]);

  const confirmSaveSearch = useCallback(() => {
    try {
      saveNewSearch(saveSearchName || "Busca sem nome", {
        ufs: Array.from(form.ufsSelecionadas),
        dataInicial: form.dataInicial,
        dataFinal: form.dataFinal,
        searchMode: form.searchMode,
        setorId: form.searchMode === "setor" ? form.setorId : undefined,
        termosBusca: form.searchMode === "termos" ? form.termosArray.join(" ") : undefined,
      });
      trackEvent("saved_search_created", {
        search_name: saveSearchName,
        search_mode: form.searchMode,
        ufs: Array.from(form.ufsSelecionadas),
        uf_count: form.ufsSelecionadas.size,
      });
      setShowSaveDialog(false);
      setSaveSearchName("");
      setSaveError(null);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Erro ao salvar busca");
    }
  }, [saveNewSearch, saveSearchName, form, trackEvent]);

  const cancelSaveDialog = useCallback(() => {
    setShowSaveDialog(false);
    setSaveSearchName("");
    setSaveError(null);
  }, []);

  return { showSaveDialog, saveSearchName, saveError, handleSaveSearch, confirmSaveSearch, cancelSaveDialog, setSaveSearchName };
}
