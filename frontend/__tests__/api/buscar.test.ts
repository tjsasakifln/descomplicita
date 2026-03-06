/**
 * @jest-environment node
 */

// Set poll interval to 0 and timeout short for fast tests.
// These must be set BEFORE importing the route module.
process.env.POLL_INTERVAL_MS = "0";
process.env.POLL_TIMEOUT_MS = "1000";

import { POST } from "@/app/api/buscar/route";
import { NextRequest } from "next/server";

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

/**
 * Helper: mock the 3-step async flow (create job -> poll status -> get result).
 * Returns the job ID used.
 */
function mockAsyncJobFlow(resultData: Record<string, unknown>, jobId = "test-job-1234") {
  mockFetch
    // 1. POST /buscar -> create job
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: jobId, status: "queued" }),
    })
    // 2. GET /buscar/{job_id}/status -> completed
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: jobId, status: "completed" }),
    })
    // 3. GET /buscar/{job_id}/result -> result data
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: jobId, status: "completed", ...resultData }),
    });

  return jobId;
}

function makeRequest(body: Record<string, unknown>) {
  return new NextRequest("http://localhost:3000/api/buscar", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

const validBody = {
  ufs: ["SC"],
  data_inicial: "2026-01-01",
  data_final: "2026-01-07",
};

const mockResult = {
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
};

describe("POST /api/buscar", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // --- Validation tests (no fetch calls needed) ---

  it("should validate missing UFs", async () => {
    const response = await POST(
      makeRequest({ data_inicial: "2026-01-01", data_final: "2026-01-07" })
    );
    const data = await response.json();
    expect(response.status).toBe(400);
    expect(data.message).toBe("Selecione pelo menos um estado");
  });

  it("should validate empty UFs array", async () => {
    const response = await POST(
      makeRequest({ ufs: [], data_inicial: "2026-01-01", data_final: "2026-01-07" })
    );
    const data = await response.json();
    expect(response.status).toBe(400);
    expect(data.message).toBe("Selecione pelo menos um estado");
  });

  it("should validate missing dates", async () => {
    const response = await POST(makeRequest({ ufs: ["SC"] }));
    const data = await response.json();
    expect(response.status).toBe(400);
    expect(data.message).toBe("Período obrigatório");
  });

  it("should handle invalid UFs type", async () => {
    const response = await POST(
      makeRequest({ ufs: "SC", data_inicial: "2026-01-01", data_final: "2026-01-07" })
    );
    const data = await response.json();
    expect(response.status).toBe(400);
    expect(data.message).toBe("Selecione pelo menos um estado");
  });

  // --- Async job flow tests ---

  it("should proxy valid request to backend and return result", async () => {
    mockAsyncJobFlow(mockResult);

    const response = await POST(makeRequest(validBody));
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.resumo).toEqual(mockResult.resumo);
    expect(data.download_id).toBeDefined();
    expect(typeof data.download_id).toBe("string");

    // Verify first fetch was POST to /buscar
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/buscar"),
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })
    );
  });

  it("should handle backend job creation error", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: "Backend error" }),
    });

    const response = await POST(makeRequest(validBody));
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.message).toBe("Backend error");
  });

  it("should handle 429 too many jobs", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 429,
      json: async () => ({ detail: "Muitas buscas simultâneas" }),
    });

    const response = await POST(makeRequest(validBody));
    const data = await response.json();

    expect(response.status).toBe(429);
    expect(data.message).toContain("Muitas buscas");
  });

  it("should handle network errors on job creation", async () => {
    mockFetch.mockRejectedValueOnce(new Error("Network error"));

    const response = await POST(makeRequest(validBody));
    const data = await response.json();

    expect(response.status).toBe(503);
    expect(data.message).toContain("Backend indisponível");
  });

  it("should handle failed job result", async () => {
    const jobId = "test-job-failed";

    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: jobId, status: "queued" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: jobId, status: "failed" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: jobId, status: "failed", error: "PNCP timeout" }),
      });

    const response = await POST(makeRequest(validBody));
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.message).toBe("PNCP timeout");
  });

  it("should save Excel and return download_id", async () => {
    mockAsyncJobFlow(mockResult);

    const response = await POST(makeRequest(validBody));
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.download_id).toBeDefined();
    expect(typeof data.download_id).toBe("string");
    // download_id format: timestamp_uuid
    expect(data.download_id).toMatch(/_/);
  });

  it("should return statistics from result", async () => {
    mockAsyncJobFlow({ ...mockResult, total_raw: 100, total_filtrado: 15 });

    const response = await POST(makeRequest(validBody));
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.total_raw).toBe(100);
    expect(data.total_filtrado).toBe(15);
  });

  it("should use BACKEND_URL from environment", async () => {
    const originalEnv = process.env.BACKEND_URL;
    process.env.BACKEND_URL = "http://custom:9000";

    mockAsyncJobFlow(mockResult);
    await POST(makeRequest(validBody));

    // First call should be to custom backend URL
    expect(mockFetch).toHaveBeenCalledWith(
      "http://custom:9000/buscar",
      expect.any(Object)
    );

    process.env.BACKEND_URL = originalEnv;
  });

  it("should poll status until completed", async () => {
    const jobId = "test-poll-job";

    mockFetch
      // 1. POST /buscar
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: jobId, status: "queued" }),
      })
      // 2. First poll -> still running
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: jobId, status: "running" }),
      })
      // 3. Second poll -> completed
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: jobId, status: "completed" }),
      })
      // 4. GET result
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: jobId, status: "completed", ...mockResult }),
      });

    const response = await POST(makeRequest(validBody));
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.resumo).toEqual(mockResult.resumo);
    // Should have made 4 fetch calls total
    expect(mockFetch).toHaveBeenCalledTimes(4);
  });

  it("should handle no excel gracefully", async () => {
    mockAsyncJobFlow({
      resumo: mockResult.resumo,
      excel_base64: "",
      total_raw: 50,
      total_filtrado: 0,
      filter_stats: null,
    });

    const response = await POST(makeRequest(validBody));
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.download_id).toBeNull();
    expect(data.total_filtrado).toBe(0);
  });
});
