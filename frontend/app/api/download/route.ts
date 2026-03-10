import { NextRequest, NextResponse } from "next/server";
import { getBackendHeaders } from "@/lib/backendAuth";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const id = searchParams.get("id");

  if (!id) {
    return NextResponse.json(
      { message: "ID obrigatório" },
      { status: 400 }
    );
  }

  const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
  const headers = await getBackendHeaders();

  // Proxy the download request to the backend streaming endpoint
  let response: Response;
  try {
    response = await fetch(`${backendUrl}/buscar/${id}/download`, {
      headers,
    });
  } catch (error) {
    console.error(`Download proxy error for ${id}:`, error);
    return NextResponse.json(
      { message: "Backend indisponível. Tente novamente." },
      { status: 503 }
    );
  }

  if (!response.ok) {
    if (response.status === 404 || response.status === 409) {
      return NextResponse.json(
        { message: "Download expirado ou inválido. Faça uma nova busca para gerar o Excel." },
        { status: 404 }
      );
    }
    return NextResponse.json(
      { message: "Erro ao baixar arquivo." },
      { status: response.status }
    );
  }

  // Stream the binary response through
  const contentType = response.headers.get("content-type") ||
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  const contentDisposition = response.headers.get("content-disposition") ||
    `attachment; filename="descomplicita_${new Date().toISOString().split("T")[0]}.xlsx"`;

  const buffer = await response.arrayBuffer();
  const uint8Array = new Uint8Array(buffer);

  console.log(`Download served: ${id} (${uint8Array.length} bytes)`);

  return new NextResponse(uint8Array, {
    headers: {
      "Content-Type": contentType,
      "Content-Disposition": contentDisposition,
    }
  });
}
