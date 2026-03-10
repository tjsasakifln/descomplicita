import { NextRequest, NextResponse } from "next/server";
import { getBackendHeaders } from "@/app/lib/backendAuth";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(request: NextRequest) {
  const job_id = request.nextUrl.searchParams.get("job_id");
  const page = request.nextUrl.searchParams.get("page") ?? "1";
  const page_size = request.nextUrl.searchParams.get("page_size") ?? "20";

  if (!job_id) {
    return NextResponse.json({ error: "Missing job_id" }, { status: 400 });
  }

  const headers = await getBackendHeaders();
  try {
    const response = await fetch(
      `${BACKEND_URL}/buscar/${job_id}/items?page=${page}&page_size=${page_size}`,
      { headers }
    );
    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to fetch items" },
        { status: response.status }
      );
    }
    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    );
  }
}
