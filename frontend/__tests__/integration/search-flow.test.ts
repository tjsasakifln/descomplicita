/**
 * @jest-environment node
 *
 * Integration tests: Frontend-Backend communication via MSW
 *
 * XD-TEST-01 – Tests the full search flow from HTTP call to response handling
 * using Mock Service Worker (msw/node) to intercept fetch requests in the
 * Node.js test environment.
 *
 * Covered scenarios
 * -----------------
 *  Scenario 1  Search with success   (success handlers)
 *  Scenario 2  Search with error     (error / 5xx handlers)
 *  Scenario 3  Polling timeout       (perpetual-processing handlers)
 *  Scenario 4  Download Excel        (binary response + headers)
 *  Scenario 5  Sectors endpoint      (reference data)
 */

import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import {
  successHandlers,
  errorHandlers,
  timeoutHandlers,
} from './mswHandlers';

// ---------------------------------------------------------------------------
// Server lifecycle
// ---------------------------------------------------------------------------

const server = setupServer(...successHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Base URL used by both MSW handlers and test fetch calls. */
const BASE = 'http://localhost';

function post(path: string, body: Record<string, unknown>) {
  return fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

function get(path: string) {
  return fetch(`${BASE}${path}`);
}

const searchBody = {
  ufs: ['SP', 'RJ', 'MG'],
  data_inicial: '2026-03-01',
  data_final: '2026-03-09',
  setor_id: 'vestuario',
};

// ---------------------------------------------------------------------------
// Scenario 1: Successful search flow
// ---------------------------------------------------------------------------

describe('XD-TEST-01 / Scenario 1: Search with success', () => {
  it('creates a search job and returns job_id', async () => {
    const response = await post('/api/buscar', searchBody);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.job_id).toBe('test-job-123');
  });

  it('polls status and receives completed result', async () => {
    const response = await get('/api/buscar/status?job_id=test-job-123');
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.status).toBe('completed');
    expect(data.progress_pct).toBe(100);
    expect(data.ufs_completed).toBe(3);
    expect(data.current_uf).toBeNull();
  });

  it('fetches full result payload after completion', async () => {
    const response = await get('/api/buscar/result?job_id=test-job-123');
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.total_filtrado).toBe(42);
    expect(data.total_raw).toBe(150);
    expect(data.resumo).toContain('Resumo executivo');
    expect(data.ufs_searched).toEqual(['SP', 'RJ', 'MG']);
    expect(data.elapsed_seconds).toBeGreaterThan(0);
  });

  it('fetches page 1 of paginated items', async () => {
    const response = await get(
      '/api/buscar/items?job_id=test-job-123&page=1&page_size=5',
    );
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.items).toHaveLength(5);
    expect(data.total).toBe(42);
    expect(data.page).toBe(1);
    expect(data.total_pages).toBe(9);
    expect(data.items[0].objetoCompra).toContain('Uniforme');
    expect(data.items[0].id).toBe('item-0');
  });

  it('fetches page 2 and returns correctly offset item IDs', async () => {
    const response = await get(
      '/api/buscar/items?job_id=test-job-123&page=2&page_size=5',
    );
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.page).toBe(2);
    // Page 2 with page_size=5 → items starting at index 5
    expect(data.items[0].id).toBe('item-5');
  });
});

// ---------------------------------------------------------------------------
// Scenario 2: Search with backend error
// ---------------------------------------------------------------------------

describe('XD-TEST-01 / Scenario 2: Search with error', () => {
  it('handles backend unavailable (503)', async () => {
    server.use(...errorHandlers);

    const response = await post('/api/buscar', searchBody);
    const data = await response.json();

    expect(response.status).toBe(503);
    expect(data.message).toContain('indisponível');
  });

  it('handles internal server error (500)', async () => {
    server.use(
      http.post(`${BASE}/api/buscar`, () =>
        HttpResponse.json({ message: 'Internal server error' }, { status: 500 }),
      ),
    );

    const response = await post('/api/buscar', searchBody);
    expect(response.status).toBe(500);
  });

  it('handles 404 for unknown job on status endpoint', async () => {
    server.use(
      http.get(`${BASE}/api/buscar/status`, () =>
        HttpResponse.json({ message: 'Job not found' }, { status: 404 }),
      ),
    );

    const response = await get('/api/buscar/status?job_id=does-not-exist');
    const data = await response.json();

    expect(response.status).toBe(404);
    expect(data.message).toBe('Job not found');
  });

  it('handles 404 for unknown job on result endpoint', async () => {
    server.use(
      http.get(`${BASE}/api/buscar/result`, () =>
        HttpResponse.json({ message: 'Job not found' }, { status: 404 }),
      ),
    );

    const response = await get('/api/buscar/result?job_id=does-not-exist');
    expect(response.status).toBe(404);
  });
});

// ---------------------------------------------------------------------------
// Scenario 3: Polling timeout / stuck jobs
// ---------------------------------------------------------------------------

describe('XD-TEST-01 / Scenario 3: Polling timeout', () => {
  it('handles a job that stays in processing state', async () => {
    server.use(...timeoutHandlers);

    // Step 1 – create job
    const createResponse = await post('/api/buscar', searchBody);
    const createData = await createResponse.json();

    expect(createResponse.status).toBe(200);
    expect(createData.job_id).toBe('test-job-timeout');

    // Step 2 – poll status (should remain "processing")
    const statusResponse = await get(
      `/api/buscar/status?job_id=${createData.job_id}`,
    );
    const statusData = await statusResponse.json();

    expect(statusResponse.status).toBe(200);
    expect(statusData.status).toBe('processing');
    expect(statusData.progress_pct).toBe(33);
    expect(statusData.current_uf).toBe('RJ');
  });

  it('handles a job that transitions to failed state', async () => {
    server.use(
      http.post(`${BASE}/api/buscar`, () =>
        HttpResponse.json({ job_id: 'test-job-failed' }),
      ),
      http.get(`${BASE}/api/buscar/status`, () =>
        HttpResponse.json({
          status: 'failed',
          phase: 'error',
          error: 'PNCP API timeout after 300s',
          ufs_completed: 1,
          total_ufs: 3,
          progress_pct: 33,
          current_uf: null,
        }),
      ),
    );

    const statusResponse = await get('/api/buscar/status?job_id=test-job-failed');
    const statusData = await statusResponse.json();

    expect(statusResponse.status).toBe(200);
    expect(statusData.status).toBe('failed');
    expect(statusData.error).toContain('timeout');
  });

  it('handles job not yet started (queued status)', async () => {
    server.use(
      http.post(`${BASE}/api/buscar`, () =>
        HttpResponse.json({ job_id: 'test-job-queued' }),
      ),
      http.get(`${BASE}/api/buscar/status`, () =>
        HttpResponse.json({
          status: 'queued',
          phase: 'waiting',
          ufs_completed: 0,
          total_ufs: 3,
          progress_pct: 0,
          current_uf: null,
        }),
      ),
    );

    const statusResponse = await get('/api/buscar/status?job_id=test-job-queued');
    const statusData = await statusResponse.json();

    expect(statusData.status).toBe('queued');
    expect(statusData.progress_pct).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// Scenario 4: Download Excel
// ---------------------------------------------------------------------------

describe('XD-TEST-01 / Scenario 4: Download Excel', () => {
  it('downloads Excel file with correct content-type and disposition headers', async () => {
    const response = await get('/api/download?job_id=test-job-123');

    expect(response.status).toBe(200);
    expect(response.headers.get('Content-Type')).toContain('spreadsheetml');
    expect(response.headers.get('Content-Disposition')).toContain(
      'licitacoes.xlsx',
    );
  });

  it('returns a non-empty binary buffer', async () => {
    const response = await get('/api/download?job_id=test-job-123');
    const buffer = await response.arrayBuffer();

    expect(buffer.byteLength).toBeGreaterThan(0);
  });

  it('handles download request for a non-existent job (404)', async () => {
    server.use(
      http.get(`${BASE}/api/download`, () =>
        HttpResponse.json({ message: 'Job not found' }, { status: 404 }),
      ),
    );

    const response = await get('/api/download?job_id=non-existent');
    const data = await response.json();

    expect(response.status).toBe(404);
    expect(data.message).toBe('Job not found');
  });

  it('handles download failure (500)', async () => {
    server.use(
      http.get(`${BASE}/api/download`, () =>
        HttpResponse.json(
          { message: 'Failed to generate Excel' },
          { status: 500 },
        ),
      ),
    );

    const response = await get('/api/download?job_id=test-job-123');
    expect(response.status).toBe(500);
  });
});

// ---------------------------------------------------------------------------
// Scenario 5: Sectors (reference data)
// ---------------------------------------------------------------------------

describe('XD-TEST-01 / Scenario 5: Sectors endpoint', () => {
  it('lists available sectors', async () => {
    const response = await get('/api/setores');
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(Array.isArray(data)).toBe(true);
    expect(data).toHaveLength(2);
    expect(data[0]).toMatchObject({ id: 'vestuario', nome: expect.any(String) });
    expect(data[1]).toMatchObject({
      id: 'informatica',
      nome: expect.any(String),
    });
  });

  it('returns sector objects with required fields', async () => {
    const response = await get('/api/setores');
    const data = await response.json();

    for (const sector of data) {
      expect(sector).toHaveProperty('id');
      expect(sector).toHaveProperty('nome');
      expect(typeof sector.id).toBe('string');
      expect(typeof sector.nome).toBe('string');
    }
  });
});
