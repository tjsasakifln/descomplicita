import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { writeFile } from "fs/promises";
import { join } from "path";
import { tmpdir } from "os";

const DOWNLOAD_TTL_MS = parseInt(process.env.DOWNLOAD_TTL_MS || String(60 * 60 * 1000), 10); // 1 hour

function getPollIntervalMs(): number {
  return parseInt(process.env.POLL_INTERVAL_MS || "2000", 10);
}

function getPollTimeoutMs(): number {
  return parseInt(process.env.POLL_TIMEOUT_MS || String(10 * 60 * 1000), 10);
}

function sleep(ms: number): Promise<void> {
  if (ms <= 0) return Promise.resolve();
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { ufs, data_inicial, data_final, setor_id, termos_busca } = body;

    // Validações
    if (!ufs || !Array.isArray(ufs) || ufs.length === 0) {
      return NextResponse.json(
        { message: "Selecione pelo menos um estado" },
        { status: 400 }
      );
    }

    if (!data_inicial || !data_final) {
      return NextResponse.json(
        { message: "Período obrigatório" },
        { status: 400 }
      );
    }

    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

    // Step 1: Create async job
    let jobResponse: Response;
    try {
      jobResponse = await fetch(`${backendUrl}/buscar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ufs,
          data_inicial,
          data_final,
          setor_id: setor_id || "vestuario",
          termos_busca: termos_busca || undefined,
        }),
      });
    } catch (error) {
      const message = `Backend indisponível em ${backendUrl}: ${error instanceof Error ? error.message : "conexão recusada"}`;
      console.error(`Erro ao conectar com backend em ${backendUrl}:`, error);
      return NextResponse.json({ message }, { status: 503 });
    }

    if (!jobResponse.ok) {
      const error = await jobResponse.json().catch(() => ({}));
      return NextResponse.json(
        { message: error.detail || "Erro no backend" },
        { status: jobResponse.status }
      );
    }

    const jobData = await jobResponse.json();
    const jobId: string = jobData.job_id;

    // Step 2: Poll for completion
    const deadline = Date.now() + getPollTimeoutMs();
    let jobDone = false;

    while (Date.now() < deadline) {
      await sleep(getPollIntervalMs());

      let statusResponse: Response;
      try {
        statusResponse = await fetch(`${backendUrl}/buscar/${jobId}/status`);
      } catch {
        continue;
      }

      if (!statusResponse.ok) {
        continue;
      }

      const statusData = await statusResponse.json();

      if (statusData.status === "completed" || statusData.status === "failed") {
        jobDone = true;
        break;
      }
    }

    // Step 3: Fetch result
    let resultResponse: Response;
    try {
      resultResponse = await fetch(`${backendUrl}/buscar/${jobId}/result`);
    } catch (error) {
      console.error("Erro ao buscar resultado do job:", error);
      return NextResponse.json(
        { message: "Erro ao obter resultado da busca" },
        { status: 503 }
      );
    }

    const resultData = await resultResponse.json();

    if (resultData.status === "failed") {
      return NextResponse.json(
        { message: resultData.error || "Erro no processamento da busca" },
        { status: 500 }
      );
    }

    if (resultData.status !== "completed") {
      return NextResponse.json(
        { message: "A consulta excedeu o tempo limite. Tente com menos estados ou um período menor." },
        { status: 504 }
      );
    }

    // Step 4: Save Excel and return response
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
      filter_stats: resultData.filter_stats || null,
    });

  } catch (error) {
    console.error("Erro na busca:", error);
    return NextResponse.json(
      { message: "Erro interno do servidor" },
      { status: 500 }
    );
  }
}
