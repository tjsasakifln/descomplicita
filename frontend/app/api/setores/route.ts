import { NextResponse } from "next/server";

export async function GET() {
  try {
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    const apiKey = process.env.BACKEND_API_KEY || "";

    const response = await fetch(`${backendUrl}/setores`, {
      headers: apiKey ? { "X-API-Key": apiKey } : {},
    });

    if (!response.ok) {
      return NextResponse.json(
        { message: "Erro ao buscar setores" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Erro ao buscar setores:", error);
    return NextResponse.json(
      { message: "Backend indisponível" },
      { status: 503 }
    );
  }
}
