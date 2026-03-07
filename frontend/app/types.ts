/**
 * Type definitions for Descomplicita
 */

// Re-export UFS and UF from canonical source (TD-021)
export { UFS, type UF } from "./constants/ufs";

/** Search parameters for multi-source API */
export interface SearchParams {
  ufs: string[];
  data_inicial: string; // YYYY-MM-DD format
  data_final: string;   // YYYY-MM-DD format
  setor_id: string;     // Sector ID (e.g., "vestuario")
}

/** Available procurement sector */
export interface Setor {
  id: string;
  name: string;
  description: string;
}

/** Executive summary from GPT-4.1-nano */
export interface Resumo {
  resumo_executivo: string;
  total_oportunidades: number;
  valor_total: number;
  destaques: string[];
  distribuicao_uf: Record<string, number>;
  alerta_urgencia: string | null;
}

/** Breakdown of filter rejection reasons */
export interface FilterStats {
  rejeitadas_uf: number;
  rejeitadas_valor: number;
  rejeitadas_keyword: number;
  rejeitadas_prazo: number;
  rejeitadas_outros: number;
}

/** Per-source statistics from orchestrated multi-source search */
export interface SourceStats {
  total_fetched: number;
  after_dedup: number;
  elapsed_ms: number;
  status: "success" | "error" | "timeout";
  error_message: string | null;
}

/** API response from POST /api/buscar */
export interface BuscaResult {
  resumo: Resumo;
  download_id: string;
  total_raw: number;
  total_filtrado: number;
  total_atas: number;
  total_licitacoes: number;
  filter_stats: FilterStats | null;
  sources_used: string[];
  source_stats: Record<string, SourceStats>;
  dedup_removed: number;
  truncated_combos: number;
}

/** Form validation errors */
export interface ValidationErrors {
  ufs?: string;
  data_inicial?: string;
  data_final?: string;
  date_range?: string;
}

/** Search phase from backend job status */
export type SearchPhase =
  | "idle"
  | "queued"
  | "fetching"
  | "filtering"
  | "summarizing"
  | "generating_excel"
  | "completed"
  | "failed";

/** Real-time search progress from backend polling */
export interface SearchProgress {
  phase: SearchPhase;
  ufs_completed: number;
  ufs_total: number;
  items_fetched: number;
  items_filtered: number;
  elapsed_seconds: number;
}

/** Backend job status response */
export interface JobStatusResponse {
  job_id: string;
  status: string;
  progress: {
    phase: string;
    ufs_completed: number;
    ufs_total: number;
    items_fetched: number;
    items_filtered: number;
  };
  created_at: string;
  elapsed_seconds: number;
}
