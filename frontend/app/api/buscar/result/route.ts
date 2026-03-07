import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { writeFile } from "fs/promises";
import { join } from "path";
import { tmpdir } from "os";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const DOWNLOAD_TTL_MS = parseInt(process.env.DOWNLOAD_TTL_MS || String(60 * 60 * 1000), 10);

export async function GET(request: NextRequest) {
  const job_id = request.nextUrl.searchParams.get("job_id");

  if (!job_id) {
    return NextResponse.json(
      { error: "Missing required query parameter: job_id" },
      { status: 400 }
    );
  }

  let response: Response;
  try {
    response = await fetch(`${BACKEND_URL}/buscar/${job_id}/result`);
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

  // Job completed — save Excel and return response
  let downloadId: string | null = null;
  if (resultData.excel_base64) {
    downloadId = `${Date.now()}_${randomUUID()}`;
    const buffer = Buffer.from(resultData.excel_base64, "base64");
    const tmpDir = tmpdir();
    const filePath = join(tmpDir, `bidiq_${downloadId}.xlsx`);

    try {
      await writeFile(filePath, buffer);
      console.log(`Excel saved to: ${filePath}`);

      setTimeout(async () => {
        try {
          const { unlink } = await import("fs/promises");
          await unlink(filePath);
          console.log(`Cleaned up expired download: ${downloadId}`);
        } catch (error) {
          console.error(`Failed to clean up ${downloadId}:`, error);
        }
      }, DOWNLOAD_TTL_MS);
    } catch (error) {
      console.error("Failed to save Excel to filesystem:", error);
      downloadId = null;
    }
  }

  return NextResponse.json({
    resumo: resultData.resumo,
    download_id: downloadId,
    total_raw: resultData.total_raw || 0,
    total_filtrado: resultData.total_filtrado || 0,
    total_atas: resultData.total_atas || 0,
    total_licitacoes: resultData.total_licitacoes || 0,
    filter_stats: resultData.filter_stats || null,
    sources_used: resultData.sources_used || [],
    source_stats: resultData.source_stats || {},
    dedup_removed: resultData.dedup_removed || 0,
  });
}
