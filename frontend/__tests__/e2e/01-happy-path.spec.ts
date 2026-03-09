import { test, expect, Page } from '@playwright/test';

/**
 * E2E Test: Happy Path User Journey
 *
 * Tests the complete user flow from landing page to Excel download
 * following the manual test scenario from docs/INTEGRATION.md
 *
 * Acceptance Criteria: AC1
 *
 * @see docs/INTEGRATION.md - Manual End-to-End Testing section
 */

/**
 * Helper: mock the job-based search API (POST /api/buscar + polling endpoints).
 * Sets up route mocks for the three endpoints the frontend uses:
 *   1. POST /api/buscar        → { job_id }
 *   2. GET  /api/buscar/status  → { status: 'completed', ... }
 *   3. GET  /api/buscar/result  → BuscaResult
 */
async function mockSearchApi(
  page: Page,
  opts: {
    resumo: {
      resumo_executivo: string;
      total_oportunidades: number;
      valor_total: number;
      destaques: string[];
      distribuicao_uf?: Record<string, number>;
      alerta_urgencia?: string | null;
    };
    downloadId?: string;
    totalRaw?: number;
    totalFiltrado?: number;
  },
) {
  const jobId = opts.downloadId || 'test-mock-job-id';
  const totalOps = opts.resumo.total_oportunidades;

  // Mock POST /api/buscar → return job_id
  await page.route('**/api/buscar', async route => {
    if (route.request().method() !== 'POST') {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ job_id: jobId }),
    });
  });

  // Mock GET /api/buscar/status → return completed immediately
  await page.route('**/api/buscar/status**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        job_id: jobId,
        status: 'completed',
        progress: {
          phase: 'completed',
          ufs_completed: 2,
          ufs_total: 2,
          items_fetched: totalOps,
          items_filtered: totalOps,
        },
        elapsed_seconds: 1,
      }),
    });
  });

  // Mock GET /api/buscar/result → return full BuscaResult
  await page.route('**/api/buscar/result**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        resumo: {
          ...opts.resumo,
          distribuicao_uf: opts.resumo.distribuicao_uf || {},
          alerta_urgencia: opts.resumo.alerta_urgencia ?? null,
        },
        download_id: jobId,
        total_raw: opts.totalRaw ?? totalOps,
        total_filtrado: opts.totalFiltrado ?? totalOps,
        total_atas: 0,
        total_licitacoes: totalOps,
        filter_stats: null,
        sources_used: ['pncp'],
        source_stats: {},
        dedup_removed: 0,
        truncated_combos: 0,
      }),
    });
  });
}

test.describe('Happy Path User Journey', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('/');

    // Clear default UF selections (SC, PR, RS are selected by default)
    // This ensures tests start from a clean state
    const limparButton = page.getByRole('button', { name: /Limpar/i });
    if (await limparButton.isVisible().catch(() => false)) {
      await limparButton.click();
    }
  });

  test('AC1.1: should load homepage with all expected UI elements', async ({ page }) => {
    // Verify page title contains the brand name
    await expect(page).toHaveTitle(/DescompLicita/i);

    // Verify main heading
    const heading = page.getByRole('heading', { name: /Busca de Licitações/i });
    await expect(heading).toBeVisible();

    // Verify UF selection section
    const ufSection = page.getByText(/Estados \(UFs\)/i);
    await expect(ufSection).toBeVisible();

    // Verify at least 27 state buttons are present
    const ufButtons = page.getByRole('button').filter({ hasText: /^[A-Z]{2}$/ });
    await expect(ufButtons).toHaveCount(27);

    // Verify date range inputs
    const dataInicial = page.getByLabel(/Data Inicial/i);
    const dataFinal = page.getByLabel(/Data Final/i);
    await expect(dataInicial).toBeVisible();
    await expect(dataFinal).toBeVisible();

    // Verify search button
    const searchButton = page.getByRole('button', { name: /^Buscar\b/i });
    await expect(searchButton).toBeVisible();
  });

  test('AC1.2: should select multiple UFs and update selection counter', async ({ page }) => {
    // Select SP
    await page.getByRole('button', { name: 'SP', exact: true }).click();
    await expect(page.getByText(/1 estado selecionado/i)).toBeVisible();

    // Select RJ
    await page.getByRole('button', { name: 'RJ', exact: true }).click();
    await expect(page.getByText(/2 estados selecionados/i)).toBeVisible();

    // Verify selected states are highlighted
    const spButton = page.getByRole('button', { name: 'SP', exact: true });
    await expect(spButton).toHaveClass(/bg-brand-navy/);

    const rjButton = page.getByRole('button', { name: 'RJ', exact: true });
    await expect(rjButton).toHaveClass(/bg-brand-navy/);
  });

  test('AC1.3: should have default 7-day date range', async ({ page }) => {
    const dataInicial = page.getByLabel(/Data Inicial/i);
    const dataFinal = page.getByLabel(/Data Final/i);

    const dataInicialValue = await dataInicial.inputValue();
    const dataFinalValue = await dataFinal.inputValue();

    // Verify both dates are filled
    expect(dataInicialValue).not.toBe('');
    expect(dataFinalValue).not.toBe('');

    // Verify dates are valid YYYY-MM-DD format
    expect(dataInicialValue).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(dataFinalValue).toMatch(/^\d{4}-\d{2}-\d{2}$/);

    // Verify date range is approximately 7 days
    const inicial = new Date(dataInicialValue);
    const final = new Date(dataFinalValue);
    const diffDays = Math.round((final.getTime() - inicial.getTime()) / (1000 * 60 * 60 * 24));

    expect(diffDays).toBeGreaterThanOrEqual(6);
    expect(diffDays).toBeLessThanOrEqual(8); // Allow some tolerance
  });

  test('AC1.4: should submit search and display results', async ({ page }) => {
    // Mock job-based search API
    await mockSearchApi(page, {
      downloadId: 'test-happy-path-ac14-id',
      resumo: {
        resumo_executivo: 'Resumo Executivo: Encontradas 15 licitações de uniformes em SC e PR, totalizando R$ 750.000,00. As oportunidades incluem uniformes escolares, fardamento militar e roupas profissionais para diversos órgãos públicos.',
        total_oportunidades: 15,
        valor_total: 750000,
        destaques: [
          'Destaque para licitação de uniformes escolares em Curitiba no valor de R$ 120.000,00',
          'Oportunidade de fardamento militar em Florianópolis com prazo de entrega de 45 dias'
        ],
        distribuicao_uf: { SC: 8, PR: 7 },
        alerta_urgencia: null,
      },
    });

    // Select 2 UFs (smaller scope for faster test)
    await page.getByRole('button', { name: 'SC', exact: true }).click();
    await page.getByRole('button', { name: 'PR', exact: true }).click();

    // Wait for search button to be enabled
    const searchButton = page.getByRole('button', { name: /^Buscar\b/i });
    await expect(searchButton).toBeEnabled();

    // Click search button
    await searchButton.click();

    // Wait for results (mock responds instantly via polling)
    await page.waitForSelector('text=/Resumo Executivo/i', {
      timeout: 15000
    });

    // Verify results are displayed
    await expect(page.getByText(/Resumo Executivo/i)).toBeVisible();
  });

  test('AC1.5: should display executive summary with statistics', async ({ page }) => {
    // Mock job-based search API with clear statistics
    await mockSearchApi(page, {
      downloadId: 'test-happy-path-ac15-id',
      resumo: {
        resumo_executivo: 'Resumo Executivo: Encontradas 23 licitações de uniformes em SP e RJ, totalizando R$ 1.250.000,00. Predominam uniformes escolares (65%) e fardamento para segurança pública (35%).',
        total_oportunidades: 23,
        valor_total: 1250000,
        destaques: [
          'Maior licitação: Uniformes escolares para rede municipal de São Paulo - R$ 450.000,00',
          'Prazo urgente: Fardamento para Polícia Civil do Rio de Janeiro - abertura em 7 dias',
          'Oportunidade diferenciada: Uniformes hospitalares com tecido antimicrobiano'
        ],
        distribuicao_uf: { SP: 15, RJ: 8 },
        alerta_urgencia: 'Atenção: 3 licitações com abertura nos próximos 5 dias úteis',
      },
    });

    // Select UFs with higher probability of results
    await page.getByRole('button', { name: 'SP', exact: true }).click();
    await page.getByRole('button', { name: 'RJ', exact: true }).click();

    // Submit search
    await page.getByRole('button', { name: /^Buscar\b/i }).click();

    // Wait for results (should be fast with mock)
    await page.waitForSelector('text=/Resumo Executivo/i', {
      timeout: 15000
    });

    // Verify executive summary section
    await expect(page.getByText(/Resumo Executivo/i)).toBeVisible();

    // Verify statistics are displayed (total_oportunidades shown as number + label)
    const statsNumber = page.locator('text=/^23$/').first();
    await expect(statsNumber).toBeVisible();
    await expect(page.getByText('oportunidades', { exact: true }).first()).toBeVisible();

    // Verify valor_total is formatted as currency
    const valorSection = page.locator('text=/R\\$\\s*1[\\.\\s]250[\\.\\s]000/i').first();
    await expect(valorSection).toBeVisible();
  });

  test('AC1.6: should enable download button and serve Excel file', async ({ page }) => {
    // Mock job-based search API
    await mockSearchApi(page, {
      downloadId: 'test-happy-path-ac16-id',
      resumo: {
        resumo_executivo: 'Resumo Executivo: Encontradas 12 licitações de uniformes em SC, totalizando R$ 680.000,00.',
        total_oportunidades: 12,
        valor_total: 680000,
        destaques: [
          'Uniformes escolares para municípios de Santa Catarina',
          'Fardamento para segurança pública estadual'
        ],
        distribuicao_uf: { SC: 12 },
        alerta_urgencia: null,
      },
    });

    // Mock download endpoint (GET /api/download?id=...)
    await page.route('**/api/download**', async (route) => {
      const content = Buffer.from('PK\x05\x06' + '\x00'.repeat(18), 'binary');
      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          'Content-Disposition': 'attachment; filename=licitacoes_test-happy-path-ac16-id.xlsx',
          'Content-Length': content.length.toString(),
        },
        body: content,
      });
    });

    // Select UFs
    await page.getByRole('button', { name: 'SC', exact: true }).click();

    // Submit search
    await page.getByRole('button', { name: /^Buscar\b/i }).click();

    // Wait for results (should be fast with mock)
    await page.waitForSelector('text=/Resumo Executivo/i', {
      timeout: 15000
    });

    // Verify download button exists
    const downloadButton = page.getByRole('button', { name: /Baixar Excel/i });
    await expect(downloadButton).toBeVisible();
    await expect(downloadButton).toBeEnabled();

    // Track download requests
    const downloadRequests: { method: string; url: string }[] = [];
    page.on('request', request => {
      if (request.url().includes('/api/download')) {
        downloadRequests.push({ method: request.method(), url: request.url() });
      }
    });

    // Click download button - triggers blob download
    await downloadButton.click();

    // Wait for download request to complete
    await page.waitForTimeout(2000);

    // Verify GET request was made for the download
    const getRequests = downloadRequests.filter(r => r.method === 'GET');
    expect(getRequests.length).toBeGreaterThanOrEqual(1);

    // Verify no download error is shown on the page
    const errorElement = page.locator('text=/Erro no download/i');
    await expect(errorElement).not.toBeVisible();
  });

  test('AC1.7: should complete full E2E journey in under 60 seconds', async ({ page }) => {
    // Mock job-based search API for fast execution
    await mockSearchApi(page, {
      downloadId: 'test-happy-path-ac17-id',
      resumo: {
        resumo_executivo: 'Resumo Executivo: Encontradas 18 licitações de uniformes em SC, totalizando R$ 890.000,00. Performance test concluído com sucesso.',
        total_oportunidades: 18,
        valor_total: 890000,
        destaques: [
          'Sistema respondeu em tempo adequado',
          'Teste de performance bem-sucedido'
        ],
        distribuicao_uf: { SC: 18 },
        alerta_urgencia: null,
      },
    });

    const startTime = Date.now();

    // Full user journey
    await page.getByRole('button', { name: 'SC', exact: true }).click();
    await page.getByRole('button', { name: /^Buscar\b/i }).click();
    await page.waitForSelector('text=/Resumo Executivo/i', {
      timeout: 15000
    });

    const elapsed = Date.now() - startTime;

    // Verify journey completed within timeout (should be much faster with mock)
    expect(elapsed).toBeLessThan(60000); // 60 seconds

    // Additional verification that results are displayed
    await expect(page.getByText(/Resumo Executivo/i)).toBeVisible();
  });
});
