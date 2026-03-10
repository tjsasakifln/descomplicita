import { NextRequest, NextResponse } from "next/server";
import { getBackendHeaders } from "@/app/lib/backendAuth";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(request: NextRequest) {
  const job_id = request.nextUrl.searchParams.get("job_id");

  if (!job_id) {
    return NextResponse.json(
      { error: "Missing required query parameter: job_id" },
      { status: 400 }
    );
  }

  const headers = await getBackendHeaders();

  let response: Response;
  try {
    response = await fetch(`${BACKEND_URL}/buscar/${job_id}/result`, {
      headers,
    });
  } catch (error) {
    const message = `Backend indisponível em ${BACKEND_URL}: ${error instanceof Error ? error.message : "conexão recusada"}`;
    console.error(`Erro ao conectar com backend em ${BACKEND_URL}:`, error);
    return NextResponse.json({ message }, { status: 503 });
  }

  if (response.status === 404) {
    return NextResponse.json(
      { error: "Job not found" },
      { status: 404 }
    );
  }

  if (!response.ok) {
    return NextResponse.json(
      { error: "Unexpected error from backend" },
      { status: response.status }
    );
  }

  const resultData = await response.json();

  // Job is still running
  if (response.status === 202 || resultData.status === "running" || resultData.status === "pending") {
    return NextResponse.json({ status: "running" }, { status: 202 });
  }

  // Job failed
  if (resultData.status === "failed") {
    return NextResponse.json(
      { message: resultData.error || "Erro no processamento da busca" },
      { status: 500 }
    );
  }

  // Job completed — return result with download_id = job_id
  // Excel is served via streaming from backend /buscar/{job_id}/download
  return NextResponse.json({
    resumo: resultData.resumo,
    download_id: resultData.job_id,
    total_raw: resultData.total_raw || 0,
    total_filtrado: resultData.total_filtrado || 0,
    total_atas: resultData.total_atas || 0,
    total_licitacoes: resultData.total_licitacoes || 0,
    filter_stats: resultData.filter_stats || null,
    sources_used: resultData.sources_used || [],
    source_stats: resultData.source_stats || {},
    dedup_removed: resultData.dedup_removed || 0,
    truncated_combos: resultData.truncated_combos || 0,
  });
}
