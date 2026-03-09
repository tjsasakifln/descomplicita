/**
 * MSW (Mock Service Worker) request handlers for integration tests.
 *
 * Handlers use `http://localhost` as the base URL because msw/node intercepts
 * fetch calls made in the Node.js test environment and matches against
 * fully-qualified URLs.
 *
 * Organised into named handler sets so individual test suites can swap them
 * in/out with `server.use(...)` + `server.resetHandlers()`.
 */
import { http, HttpResponse } from 'msw';

const BASE = 'http://localhost';

// ---------------------------------------------------------------------------
// Successful search flow
// ---------------------------------------------------------------------------
export const successHandlers = [
  // POST /api/buscar → creates a job and returns its ID
  http.post(`${BASE}/api/buscar`, () => {
    return HttpResponse.json({ job_id: 'test-job-123' });
  }),

  // GET /api/buscar/status → immediately reports completion
  http.get(`${BASE}/api/buscar/status`, ({ request }) => {
    const url = new URL(request.url);
    void url.searchParams.get('job_id'); // referenced in real implementation
    return HttpResponse.json({
      status: 'completed',
      phase: 'done',
      ufs_completed: 3,
      total_ufs: 3,
      progress_pct: 100,
      current_uf: null,
    });
  }),

  // GET /api/buscar/result → full result payload
  http.get(`${BASE}/api/buscar/result`, () => {
    return HttpResponse.json({
      resumo: '<div>Resumo executivo de teste</div>',
      total_raw: 150,
      total_filtrado: 42,
      elapsed_seconds: 12.5,
      ufs_searched: ['SP', 'RJ', 'MG'],
    });
  }),

  // GET /api/buscar/items → paginated item list
  http.get(`${BASE}/api/buscar/items`, ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') ?? '1', 10);
    const pageSize = parseInt(url.searchParams.get('page_size') ?? '5', 10);
    return HttpResponse.json({
      items: Array.from({ length: pageSize }, (_, i) => ({
        id: `item-${(page - 1) * pageSize + i}`,
        objetoCompra: `Uniforme escolar lote ${i + 1}`,
        nomeOrgao: `Prefeitura ${i + 1}`,
        uf: 'SP',
        valorTotalEstimado: 100_000 + i * 10_000,
        dataAberturaProposta: '2026-03-15T10:00:00',
      })),
      total: 42,
      page,
      page_size: pageSize,
      total_pages: Math.ceil(42 / pageSize),
    });
  }),

  // GET /api/download → streams an Excel-like binary blob
  http.get(`${BASE}/api/download`, () => {
    const buffer = new ArrayBuffer(1024);
    return new HttpResponse(buffer, {
      headers: {
        'Content-Type':
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'Content-Disposition': 'attachment; filename="licitacoes.xlsx"',
      },
    });
  }),

  // GET /api/setores → list of available sectors
  http.get(`${BASE}/api/setores`, () => {
    return HttpResponse.json([
      { id: 'vestuario', nome: 'Vestuário e Uniformes' },
      { id: 'informatica', nome: 'Informática e TI' },
    ]);
  }),
];

// ---------------------------------------------------------------------------
// Backend error handlers (replace POST /api/buscar with a 503)
// ---------------------------------------------------------------------------
export const errorHandlers = [
  http.post(`${BASE}/api/buscar`, () => {
    return HttpResponse.json(
      { message: 'Backend indisponível' },
      { status: 503 },
    );
  }),
];

// ---------------------------------------------------------------------------
// Handlers that simulate a job stuck in "processing" state (polling timeout)
// ---------------------------------------------------------------------------
export const timeoutHandlers = [
  http.post(`${BASE}/api/buscar`, () => {
    return HttpResponse.json({ job_id: 'test-job-timeout' });
  }),

  http.get(`${BASE}/api/buscar/status`, () => {
    return HttpResponse.json({
      status: 'processing',
      phase: 'searching',
      ufs_completed: 1,
      total_ufs: 3,
      progress_pct: 33,
      current_uf: 'RJ',
    });
  }),
];
