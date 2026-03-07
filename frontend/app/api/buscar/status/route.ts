import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const API_KEY = process.env.BACKEND_API_KEY || "";

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
    response = await fetch(`${BACKEND_URL}/buscar/${job_id}/status`, {
      headers: API_KEY ? { "X-API-Key": API_KEY } : {},
    });
  } catch {
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    );
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

  const data = await response.json();
  return NextResponse.json(data);
}
