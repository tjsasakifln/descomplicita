import type { Setor } from "../types";

/**
 * Fallback sectors used when the /api/setores endpoint is unavailable.
 * UXD-017: Centralized in config for easy maintenance.
 */
export const FALLBACK_SETORES: Setor[] = [
  { id: "vestuario", name: "Vestuário e Uniformes", description: "" },
  { id: "alimentos", name: "Alimentos e Merenda", description: "" },
  { id: "informatica", name: "Informática e Tecnologia", description: "" },
  { id: "limpeza", name: "Produtos de Limpeza", description: "" },
  { id: "mobiliario", name: "Mobiliário", description: "" },
  { id: "papelaria", name: "Papelaria e Material de Escritório", description: "" },
  { id: "engenharia", name: "Engenharia e Construção", description: "" },
];
