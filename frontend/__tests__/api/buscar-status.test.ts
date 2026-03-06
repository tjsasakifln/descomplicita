/**
 * @jest-environment node
 */

import { GET } from "@/app/api/buscar/status/route";
import { NextRequest } from "next/server";

const mockFetch = jest.fn();
global.fetch = mockFetch;

function makeRequest(jobId?: string) {
  const url = jobId
    ? `http://localhost:3000/api/buscar/status?job_id=${jobId}`
    : "http://localhost:3000/api/buscar/status";
  return new NextRequest(url);
}

describe("GET /api/buscar/status", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should return 400 when job_id is missing", async () => {
    const response = await GET(makeRequest());
    expect(response.status).toBe(400);
  });

  it("should proxy status from backend", async () => {
    const statusData = {
      job_id: "test-123",
      status: "running",
      progress: {
        phase: "fetching",
        ufs_completed: 2,
        ufs_total: 5,
        items_fetched: 342,
        items_filtered: 0,
      },
      created_at: "2026-03-06T10:00:00Z",
      elapsed_seconds: 12,
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => statusData,
    });

    const response = await GET(makeRequest("test-123"));
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.progress.phase).toBe("fetching");
    expect(data.progress.ufs_completed).toBe(2);
    expect(data.progress.items_fetched).toBe(342);
  });

  it("should return 404 when job not found", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Job not found" }),
    });

    const response = await GET(makeRequest("nonexistent"));
    expect(response.status).toBe(404);
  });

  it("should return 503 when backend is down", async () => {
    mockFetch.mockRejectedValueOnce(new Error("Connection refused"));

    const response = await GET(makeRequest("test-123"));
    expect(response.status).toBe(503);
  });
});
