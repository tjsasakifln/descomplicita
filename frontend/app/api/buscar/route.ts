import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { ufs, data_inicial, data_final, setor_id, termos_busca } = body;

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
    const apiKey = process.env.BACKEND_API_KEY || "";

    let jobResponse: Response;
    try {
      jobResponse = await fetch(`${backendUrl}/buscar`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(apiKey && { "X-API-Key": apiKey }),
        },
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
    return NextResponse.json({ job_id: jobData.job_id });
  } catch (error) {
    console.error("Erro na busca:", error);
    return NextResponse.json(
      { message: "Erro interno do servidor" },
      { status: 500 }
    );
  }
}
