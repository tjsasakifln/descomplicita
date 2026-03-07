import { useState, useEffect, useCallback } from "react";
import type { Setor, ValidationErrors } from "../types";
import { UFS } from "../constants/ufs";
import { DEFAULT_UFS } from "../constants/ufs";

function getDefaultDate(daysAgo: number): string {
  const now = new Date(new Date().toLocaleString("en-US", { timeZone: "America/Sao_Paulo" }));
  now.setDate(now.getDate() - daysAgo);
  return now.toISOString().split("T")[0];
}

export interface UseSearchFormReturn {
  setores: Setor[];
  setorId: string;
  setSetorId: (id: string) => void;
  searchMode: "setor" | "termos";
  setSearchMode: (mode: "setor" | "termos") => void;
  termosArray: string[];
  setTermosArray: React.Dispatch<React.SetStateAction<string[]>>;
  termoInput: string;
  setTermoInput: (val: string) => void;
  ufsSelecionadas: Set<string>;
  toggleUf: (uf: string) => void;
  toggleRegion: (regionUfs: string[]) => void;
  selecionarTodos: () => void;
  limparSelecao: () => void;
  dataInicial: string;
  setDataInicial: (date: string) => void;
  dataFinal: string;
  setDataFinal: (date: string) => void;
  validationErrors: ValidationErrors;
  canSearch: boolean;
  sectorName: string;
  searchLabel: string;
  loadSearchParams: (params: {
    ufs: string[];
    dataInicial: string;
    dataFinal: string;
    searchMode: "setor" | "termos";
    setorId?: string;
    termosBusca?: string;
  }) => void;
}

const FALLBACK_SETORES: Setor[] = [
  { id: "vestuario", name: "Vestuário e Uniformes", description: "" },
  { id: "alimentos", name: "Alimentos e Merenda", description: "" },
  { id: "informatica", name: "Informática e Tecnologia", description: "" },
  { id: "limpeza", name: "Produtos de Limpeza", description: "" },
  { id: "mobiliario", name: "Mobiliário", description: "" },
  { id: "papelaria", name: "Papelaria e Material de Escritório", description: "" },
  { id: "engenharia", name: "Engenharia e Construção", description: "" },
];

export function useSearchForm(onFormChange?: () => void): UseSearchFormReturn {
  const [setores, setSetores] = useState<Setor[]>([]);
  const [setorId, setSetorIdState] = useState("vestuario");
  const [searchMode, setSearchModeState] = useState<"setor" | "termos">("setor");
  const [termosArray, setTermosArray] = useState<string[]>([]);
  const [termoInput, setTermoInput] = useState("");
  const [ufsSelecionadas, setUfsSelecionadas] = useState<Set<string>>(new Set(DEFAULT_UFS));
  const [dataInicial, setDataInicialState] = useState(() => getDefaultDate(7));
  const [dataFinal, setDataFinalState] = useState(() => getDefaultDate(0));
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});

  useEffect(() => {
    fetch("/api/setores")
      .then(res => res.json())
      .then(data => {
        if (data.setores) setSetores(data.setores);
      })
      .catch(() => {
        setSetores(FALLBACK_SETORES);
      });
  }, []);

  const validateForm = useCallback((): ValidationErrors => {
    const errors: ValidationErrors = {};
    if (ufsSelecionadas.size === 0) {
      errors.ufs = "Selecione pelo menos um estado";
    }
    if (dataFinal < dataInicial) {
      errors.date_range = "Data final deve ser maior ou igual à data inicial";
    }
    return errors;
  }, [ufsSelecionadas, dataInicial, dataFinal]);

  const canSearch = Object.keys(validateForm()).length === 0
    && (searchMode === "setor" || termosArray.length > 0);

  useEffect(() => {
    setValidationErrors(validateForm());
  }, [validateForm]);

  const notifyChange = useCallback(() => {
    onFormChange?.();
  }, [onFormChange]);

  const setSetorId = useCallback((id: string) => {
    setSetorIdState(id);
    notifyChange();
  }, [notifyChange]);

  const setSearchMode = useCallback((mode: "setor" | "termos") => {
    setSearchModeState(mode);
    notifyChange();
  }, [notifyChange]);

  const setDataInicial = useCallback((date: string) => {
    setDataInicialState(date);
    notifyChange();
  }, [notifyChange]);

  const setDataFinal = useCallback((date: string) => {
    setDataFinalState(date);
    notifyChange();
  }, [notifyChange]);

  const toggleUf = useCallback((uf: string) => {
    setUfsSelecionadas(prev => {
      const newSet = new Set(prev);
      if (newSet.has(uf)) newSet.delete(uf);
      else newSet.add(uf);
      return newSet;
    });
    notifyChange();
  }, [notifyChange]);

  const toggleRegion = useCallback((regionUfs: string[]) => {
    setUfsSelecionadas(prev => {
      const allSelected = regionUfs.every(uf => prev.has(uf));
      const newSet = new Set(prev);
      if (allSelected) regionUfs.forEach(uf => newSet.delete(uf));
      else regionUfs.forEach(uf => newSet.add(uf));
      return newSet;
    });
    notifyChange();
  }, [notifyChange]);

  const selecionarTodos = useCallback(() => {
    setUfsSelecionadas(new Set(UFS));
    notifyChange();
  }, [notifyChange]);

  const limparSelecao = useCallback(() => {
    setUfsSelecionadas(new Set());
    notifyChange();
  }, [notifyChange]);

  const sectorName = searchMode === "setor"
    ? (setores.find(s => s.id === setorId)?.name || "Licitações")
    : "Licitações";

  const searchLabel = searchMode === "setor"
    ? sectorName
    : termosArray.length > 0
      ? `"${termosArray.join('", "')}"`
      : "Licitações";

  const loadSearchParams = useCallback((params: {
    ufs: string[];
    dataInicial: string;
    dataFinal: string;
    searchMode: "setor" | "termos";
    setorId?: string;
    termosBusca?: string;
  }) => {
    setUfsSelecionadas(new Set(params.ufs));
    setDataInicialState(params.dataInicial);
    setDataFinalState(params.dataFinal);
    setSearchModeState(params.searchMode);
    if (params.searchMode === "setor" && params.setorId) {
      setSetorIdState(params.setorId);
    } else if (params.searchMode === "termos" && params.termosBusca) {
      setTermosArray(params.termosBusca.split(" "));
    }
    notifyChange();
  }, [notifyChange]);

  return {
    setores,
    setorId,
    setSetorId,
    searchMode,
    setSearchMode,
    termosArray,
    setTermosArray,
    termoInput,
    setTermoInput,
    ufsSelecionadas,
    toggleUf,
    toggleRegion,
    selecionarTodos,
    limparSelecao,
    dataInicial,
    setDataInicial,
    dataFinal,
    setDataFinal,
    validationErrors,
    canSearch,
    sectorName,
    searchLabel,
    loadSearchParams,
  };
}
