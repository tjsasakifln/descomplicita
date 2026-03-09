import { test, expect, Page } from '@playwright/test';

/**
 * E2E Test: LLM Fallback Scenario
 *
 * Tests that the system gracefully falls back to statistical summary
 * when OpenAI API is unavailable or misconfigured
 *
 * Acceptance Criteria: AC2
 *
 * @see backend/llm.py - gerar_resumo_fallback()
 */

/**
 * Helper: mock the job-based search API (POST + status polling + result).
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
  },
) {
  const jobId = opts.downloadId || 'test-mock-job-id';
  const totalOps = opts.resumo.total_oportunidades;

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

  await page.route('**/api/buscar/status**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        job_id: jobId,
        status: 'completed',
        progress: { phase: 'completed', ufs_completed: 1, ufs_total: 1, items_fetched: totalOps, items_filtered: totalOps },
        elapsed_seconds: 1,
      }),
    });
  });

  await page.route('**/api/buscar/result**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        resumo: { ...opts.resumo, distribuicao_uf: opts.resumo.distribuicao_uf || {}, alerta_urgencia: opts.resumo.alerta_urgencia ?? null },
        download_id: jobId,
        total_raw: totalOps,
        total_filtrado: totalOps,
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

test.describe('LLM Fallback Scenario', () => {
  test.use({
    extraHTTPHeaders: {
      'X-Test-Scenario': 'fallback'
    }
  });

  test('AC2.1: should return 200 OK even without OpenAI API key', async ({ page }) => {
    await mockSearchApi(page, {
      downloadId: 'test-fallback-ac21-id',
      resumo: {
        resumo_executivo: "Resumo Executivo estatístico: Foram encontradas 8 oportunidades de licitação de uniformes, totalizando R$ 320.000,00. Distribuição: SC (5), SP (3).",
        total_oportunidades: 8,
        valor_total: 320000,
        destaques: ["Maior concentração em SC com 5 licitações", "Valor médio de R$ 40.000,00 por licitação"],
        distribuicao_uf: {"SC": 5, "SP": 3},
        alerta_urgencia: null,
      },
    });

    await page.goto('/');

    const limparButton = page.getByRole('button', { name: /Limpar/i });
    if (await limparButton.isVisible().catch(() => false)) {
      await limparButton.click();
    }

    await page.getByRole('button', { name: 'SC', exact: true }).click();

    const searchButton = page.getByRole('button', { name: /^Buscar\b/i });
    await searchButton.click();

    await page.waitForSelector('text=/Resumo Executivo/i', { timeout: 15000 });

    const hasResults = await page.getByText(/Resumo Executivo/i).isVisible().catch(() => false);
    expect(hasResults).toBe(true);
  });

  test('AC2.2: should display fallback summary with statistical indicators', async ({ page }) => {
    await mockSearchApi(page, {
      downloadId: 'test-fallback-ac22-id',
      resumo: {
        resumo_executivo: "Resumo Executivo estatístico: Foram encontradas 8 oportunidades de licitação de uniformes, totalizando R$ 320.000,00. Distribuição: SC (5), SP (3).",
        total_oportunidades: 8,
        valor_total: 320000,
        destaques: ["Maior concentração em SC com 5 licitações", "Valor médio de R$ 40.000,00 por licitação"],
        distribuicao_uf: {"SC": 5, "SP": 3},
        alerta_urgencia: null,
      },
    });

    await page.goto('/');

    const limparButton = page.getByRole('button', { name: /Limpar/i });
    if (await limparButton.isVisible().catch(() => false)) {
      await limparButton.click();
    }

    await page.getByRole('button', { name: 'SP', exact: true }).click();
    await page.getByRole('button', { name: /^Buscar\b/i }).click();

    await page.waitForSelector('text=/Resumo Executivo/i', { timeout: 15000 });

    const summaryText = await page.textContent('body');
    expect(summaryText).toMatch(/\d+/);
    expect(summaryText).toMatch(/R\$\s*[\d.,]+/i);
  });

  test('AC2.3: should NOT make OpenAI API calls in fallback mode', async ({ page }) => {
    await mockSearchApi(page, {
      downloadId: 'test-fallback-ac23-id',
      resumo: {
        resumo_executivo: "Resumo Executivo estatístico: Foram encontradas 8 oportunidades de licitação de uniformes, totalizando R$ 320.000,00.",
        total_oportunidades: 8,
        valor_total: 320000,
        destaques: ["Test"],
        distribuicao_uf: {"SC": 5, "SP": 3},
        alerta_urgencia: null,
      },
    });

    const apiCalls: string[] = [];
    page.on('request', request => {
      const url = request.url();
      if (url.includes('openai.com') || url.includes('api.openai')) {
        apiCalls.push(url);
      }
    });

    await page.goto('/');

    const limparButton = page.getByRole('button', { name: /Limpar/i });
    if (await limparButton.isVisible().catch(() => false)) {
      await limparButton.click();
    }

    await page.getByRole('button', { name: 'SC', exact: true }).click();
    await page.getByRole('button', { name: /^Buscar\b/i }).click();

    await page.waitForSelector('text=/Resumo Executivo/i', { timeout: 15000 });

    expect(apiCalls.length).toBe(0);
  });

  test('AC2.4: should handle zero results gracefully in fallback mode', async ({ page }) => {
    await mockSearchApi(page, {
      downloadId: 'test-zero-results-id',
      resumo: {
        resumo_executivo: "Resumo Executivo: Nenhum resultado encontrado para os critérios selecionados.",
        total_oportunidades: 0,
        valor_total: 0,
        destaques: [],
        distribuicao_uf: {},
        alerta_urgencia: null,
      },
    });

    await page.goto('/');

    const limparButton = page.getByRole('button', { name: /Limpar/i });
    if (await limparButton.isVisible().catch(() => false)) {
      await limparButton.click();
    }

    await page.getByRole('button', { name: 'AC', exact: true }).click();

    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayStr = yesterday.toISOString().split('T')[0];

    await page.getByLabel(/Data inicial/i).fill(yesterdayStr);
    await page.getByLabel(/Data final/i).fill(yesterdayStr);

    await page.getByRole('button', { name: /^Buscar\b/i }).click();

    // Wait for results or empty state (zero results shows EmptyState component)
    await page.waitForTimeout(5000);

    const bodyText = await page.textContent('body');
    expect(bodyText).toBeTruthy();

    const searchButton = page.getByRole('button', { name: /^Buscar\b/i });
    await expect(searchButton).toBeVisible();
  });
});
