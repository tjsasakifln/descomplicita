import { test, expect, Page } from '@playwright/test';

/**
 * E2E Test: Error Handling Scenarios
 *
 * Tests system behavior under various failure conditions:
 * - PNCP API timeout
 * - Backend unavailable
 * - Excel download failures
 *
 * Acceptance Criteria: AC4
 *
 * @see frontend/app/error.tsx - Error boundary
 * @see frontend/app/api/ - API route error handling
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

test.describe('Error Handling Scenarios', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');

    const limparButton = page.getByRole('button', { name: /Limpar/i });
    if (await limparButton.isVisible().catch(() => false)) {
      await limparButton.click();
    }
  });

  test('AC4.1: should show user-friendly error on PNCP API timeout', async ({ page }) => {
    await page.getByRole('button', { name: 'SP', exact: true }).click();

    // Intercept API call and abort to simulate timeout
    await page.route('**/api/buscar', async route => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      await route.abort('timedout');
    });

    const searchButton = page.getByRole('button', { name: /^Buscar\b/i });
    await searchButton.click();

    // Wait for error alert to appear (uses role="alert" + bg-error-subtle in page.tsx)
    const errorAlert = page.locator('.bg-error-subtle[role="alert"]');
    await expect(errorAlert).toBeVisible({ timeout: 15000 });

    // Verify page is still functional
    await expect(searchButton).toBeVisible();
    await expect(searchButton).toBeEnabled();
  });

  test('AC4.2: should display error boundary on backend unavailable', async ({ page }) => {
    await page.route('**/api/buscar', async route => {
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Backend unavailable' }),
      });
    });

    await page.getByRole('button', { name: 'RJ', exact: true }).click();
    const searchButton = page.getByRole('button', { name: /^Buscar\b/i });
    await searchButton.click();

    // Wait for error message
    const errorMessage = page.getByText(/erro|falha|indisponível|unavailable/i);
    await expect(errorMessage).toBeVisible({ timeout: 15000 });

    await expect(searchButton).toBeVisible();
  });

  test('AC4.3: should handle Excel download 404 gracefully', async ({ page }) => {
    await page.getByRole('button', { name: 'SC', exact: true }).click();

    // Mock successful search via job-based polling
    await mockSearchApi(page, {
      downloadId: 'test-download-id',
      resumo: {
        resumo_executivo: 'Resumo Executivo: Encontradas 5 licitações de uniformes',
        total_oportunidades: 5,
        valor_total: 100000,
        destaques: ['Test'],
        distribuicao_uf: { SC: 5 },
        alerta_urgencia: null,
      },
    });

    const searchButton = page.getByRole('button', { name: /^Buscar\b/i });
    await searchButton.click();

    await expect(page.getByText(/Resumo Executivo/i)).toBeVisible({ timeout: 15000 });

    // Now mock 404 on download
    await page.route('**/api/download**', async route => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Excel file not found or expired' }),
      });
    });

    // Try to download
    const downloadButton = page.getByRole('button', { name: /Baixar Excel/i });
    await downloadButton.click();

    // Should show error message about download failure
    const errorMessage = page.getByText(/erro.*download|arquivo.*encontrado|expirad|nova busca/i);
    await expect(errorMessage).toBeVisible({ timeout: 15000 });
  });

  test('AC4.4: should recover from error and allow new search', async ({ page }) => {
    // Cause an error first
    await page.route('**/api/buscar', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Internal server error' }),
      });
    });

    await page.getByRole('button', { name: 'SP', exact: true }).click();
    const searchButton = page.getByRole('button', { name: /^Buscar\b/i });
    await searchButton.click();

    // Wait for error
    const errorAlert = page.locator('.bg-error-subtle[role="alert"]');
    await expect(errorAlert).toBeVisible({ timeout: 15000 });

    // Remove the route to allow normal requests
    await page.unroute('**/api/buscar');

    // Change selection and try again
    await page.getByRole('button', { name: 'RJ', exact: true }).click();

    // Should be able to submit again
    await expect(searchButton).toBeEnabled();
  });

  test('AC4.5: should show loading state during long operations', async ({ page }) => {
    await page.getByRole('button', { name: 'SP', exact: true }).click();

    // Delay the POST response to keep loading state visible
    await page.route('**/api/buscar', async route => {
      if (route.request().method() !== 'POST') {
        await route.continue();
        return;
      }
      await new Promise(resolve => setTimeout(resolve, 3000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ job_id: 'test-loading-id' }),
      });
    });

    const searchButton = page.getByRole('button', { name: /^Buscar\b/i });
    await searchButton.click();

    // Verify search button shows loading state ("Buscando...")
    await expect(page.getByRole('button', { name: 'Buscando...' })).toBeVisible({ timeout: 2000 });
  });

  test('AC4.6: should handle network errors gracefully', async ({ page }) => {
    await page.route('**/api/buscar', async route => {
      await route.abort('connectionrefused');
    });

    await page.getByRole('button', { name: 'SC', exact: true }).click();
    const searchButton = page.getByRole('button', { name: /^Buscar\b/i });
    await searchButton.click();

    // Should show error (verify the alert div appears)
    const errorAlert = page.locator('.bg-error-subtle[role="alert"]');
    await expect(errorAlert).toBeVisible({ timeout: 15000 });

    await page.unroute('**/api/buscar');

    // Should be able to retry
    await expect(searchButton).toBeEnabled();
  });

  test('AC4.7: should not leak sensitive errors to user', async ({ page }) => {
    await page.route('**/api/buscar', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Database connection failed at 127.0.0.1:5432',
          stack: 'Error: connection timeout\n  at DB.connect (db.js:42)',
          secret: 'sk-this-should-not-be-shown',
        }),
      });
    });

    await page.getByRole('button', { name: 'SP', exact: true }).click();
    await page.getByRole('button', { name: /^Buscar\b/i }).click();

    // Wait for error to appear
    const errorAlert = page.locator('.bg-error-subtle[role="alert"]');
    await expect(errorAlert).toBeVisible({ timeout: 15000 });

    // Get all page text
    const pageText = await page.textContent('body');

    // Should NOT contain sensitive information
    expect(pageText).not.toContain('127.0.0.1');
    expect(pageText).not.toContain('5432');
    expect(pageText).not.toContain('sk-');
    expect(pageText).not.toContain('DB.connect');
    expect(pageText).not.toContain('db.js:42');

    // Should contain user-friendly generic error
    expect(pageText).toMatch(/erro|falha|problema/i);
  });
});
