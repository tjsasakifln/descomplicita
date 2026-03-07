/**
 * @jest-environment node
 */

import { GET } from "@/app/api/buscar/result/route";
import { NextRequest } from "next/server";

const mockFetch = jest.fn();
global.fetch = mockFetch;

function makeRequest(jobId?: string) {
  const url = jobId
    ? `http://localhost:3000/api/buscar/result?job_id=${jobId}`
    : "http://localhost:3000/api/buscar/result";
  return new NextRequest(url);
}

const mockResult = {
  status: "completed",
  resumo: {
    resumo_executivo: "Test summary",
    total_oportunidades: 5,
    valor_total: 100000,
    destaques: ["Test"],
    alerta_urgencia: null,
  },
  excel_base64: Buffer.from("test").toString("base64"),
  total_raw: 10,
  total_filtrado: 5,
  filter_stats: null,
  sources_used: ["pncp", "comprasgov"],
  source_stats: {
    pncp: { total_fetched: 8, after_dedup: 7, elapsed_ms: 1200, status: "success", error_message: null },
    comprasgov: { total_fetched: 3, after_dedup: 3, elapsed_ms: 800, status: "success", error_message: null },
  },
  dedup_removed: 1,
};

describe("GET /api/buscar/result", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should return 400 when job_id is missing", async () => {
    const response = await GET(makeRequest());
    expect(response.status).toBe(400);
  });

  it("should return completed result with download_id", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ ...mockResult, job_id: "test-123" }),
    });

    const response = await GET(makeRequest("test-123"));
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.resumo).toEqual(mockResult.resumo);
    expect(data.download_id).toBeDefined();
    expect(typeof data.download_id).toBe("string");
    expect(data.total_raw).toBe(10);
    expect(data.total_filtrado).toBe(5);
    expect(data.sources_used).toEqual(["pncp", "comprasgov"]);
    expect(data.source_stats.pncp.total_fetched).toBe(8);
    expect(data.dedup_removed).toBe(1);
  });

  it("should return 202 when job is still running", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 202,
      json: async () => ({ status: "running" }),
    });

    const response = await GET(makeRequest("test-123"));
    const data = await response.json();

    expect(response.status).toBe(202);
    expect(data.status).toBe("running");
  });

  it("should return 500 when job failed", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ status: "failed", error: "PNCP timeout" }),
    });

    const response = await GET(makeRequest("test-123"));
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.message).toBe("PNCP timeout");
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

  it("should handle result without excel_base64", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        ...mockResult,
        job_id: "test-123",
        excel_base64: "",
      }),
    });

    const response = await GET(makeRequest("test-123"));
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.download_id).toBe("test-123");
  });
});
