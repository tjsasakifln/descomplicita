import { test, expect } from '@playwright/test';

/**
 * E2E Test: Form Validation Errors
 *
 * Tests client-side validation prevents invalid searches
 * and displays appropriate error messages
 *
 * Acceptance Criteria: AC3
 *
 * @see frontend/app/hooks/useSearchForm.ts - Form validation logic
 */
test.describe('Form Validation Errors', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('AC3.1: should show error when no UFs are selected', async ({ page }) => {
    const limparButton = page.getByRole('button', { name: /Limpar/i });
    const limparVisible = await limparButton.isVisible().catch(() => false);

    if (limparVisible) {
      await limparButton.click();
    }

    const errorMessage = page.getByText(/Selecione pelo menos um estado/i);
    await expect(errorMessage).toBeVisible();

    const searchButton = page.getByRole('button', { name: /^Buscar\b/i });
    await expect(searchButton).toBeDisabled();
  });

  test('AC3.2: should show error when data_final is before data_inicial', async ({ page }) => {
    // Select at least one UF to avoid UF validation error
    await page.getByRole('button', { name: 'SP', exact: true }).click();

    // Set data_final before data_inicial
    const today = new Date();
    const pastDate = new Date(today);
    pastDate.setDate(today.getDate() - 10);

    const todayStr = today.toISOString().split('T')[0];
    const pastStr = pastDate.toISOString().split('T')[0];

    await page.getByLabel(/Data inicial/i).fill(todayStr);
    await page.getByLabel(/Data final/i).fill(pastStr);

    // Trigger validation
    await page.getByLabel(/Data final/i).blur();
    await page.waitForTimeout(500);

    // Verify error message appears
    const errorMessage = page.getByText(/Data final deve ser maior ou igual/i);
    await expect(errorMessage).toBeVisible();

    // Verify search button is disabled
    const searchButton = page.getByRole('button', { name: /^Buscar\b/i });
    await expect(searchButton).toBeDisabled();
  });

  test('AC3.3: should show error when data_final is before data_inicial (different scenario)', async ({ page }) => {
    // Select at least one UF
    await page.getByRole('button', { name: 'RJ', exact: true }).click();

    // Set data_final < data_inicial
    const today = new Date();
    const pastDate = new Date(today);
    pastDate.setDate(today.getDate() - 7);

    const todayStr = today.toISOString().split('T')[0];
    const pastStr = pastDate.toISOString().split('T')[0];

    await page.getByLabel(/Data inicial/i).fill(todayStr);
    await page.getByLabel(/Data final/i).fill(pastStr);

    // Trigger validation
    await page.getByLabel(/Data final/i).blur();
    await page.waitForTimeout(500);

    // Verify error message appears
    const errorMessage = page.getByText(/Data final deve ser maior ou igual/i);
    await expect(errorMessage).toBeVisible();

    // Verify search button is disabled
    const searchButton = page.getByRole('button', { name: /^Buscar\b/i });
    await expect(searchButton).toBeDisabled();
  });

  test('AC3.4: should clear errors when valid input is provided', async ({ page }) => {
    // Create error state first (no UFs selected)
    const limparButton = page.getByRole('button', { name: /Limpar/i });
    const limparVisible = await limparButton.isVisible().catch(() => false);

    if (limparVisible) {
      await limparButton.click();
    }

    // Verify error exists
    const errorMessage = page.getByText(/Selecione pelo menos um estado/i);
    await expect(errorMessage).toBeVisible();

    // Fix the error by selecting a UF
    await page.getByRole('button', { name: 'SP', exact: true }).click();

    // Verify error is cleared
    await expect(errorMessage).not.toBeVisible();

    // Verify search button is enabled
    const searchButton = page.getByRole('button', { name: /^Buscar\b/i });
    await expect(searchButton).toBeEnabled();
  });

  test('AC3.5: should show multiple validation errors simultaneously', async ({ page }) => {
    // Clear UF selection
    const limparButton = page.getByRole('button', { name: /Limpar/i });
    const limparVisible = await limparButton.isVisible().catch(() => false);

    if (limparVisible) {
      await limparButton.click();
    }

    // Set invalid date range (final before initial)
    const today = new Date();
    const pastDate = new Date(today);
    pastDate.setDate(today.getDate() - 10);

    const todayStr = today.toISOString().split('T')[0];
    const pastStr = pastDate.toISOString().split('T')[0];

    await page.getByLabel(/Data inicial/i).fill(todayStr);
    await page.getByLabel(/Data final/i).fill(pastStr);
    await page.getByLabel(/Data final/i).blur();
    await page.waitForTimeout(500);

    // Should show both UF error and date range error
    const ufError = page.getByText(/Selecione pelo menos um estado/i);
    const dateError = page.getByText(/Data final deve ser maior ou igual/i);

    await expect(ufError).toBeVisible();
    await expect(dateError).toBeVisible();

    // Search button should remain disabled
    const searchButton = page.getByRole('button', { name: /^Buscar\b/i });
    await expect(searchButton).toBeDisabled();
  });

  test('AC3.6: should validate on form submission attempt', async ({ page }) => {
    // Clear UFs
    const limparButton = page.getByRole('button', { name: /Limpar/i });
    const limparVisible = await limparButton.isVisible().catch(() => false);

    if (limparVisible) {
      await limparButton.click();
    }

    // Try to submit (button should be disabled)
    const searchButton = page.getByRole('button', { name: /^Buscar\b/i });

    // Button should be disabled
    await expect(searchButton).toBeDisabled();

    // Verify error message is shown to guide user
    const errorMessage = page.getByText(/Selecione pelo menos um estado/i);
    await expect(errorMessage).toBeVisible();
  });

  test('AC3.7: should handle edge case of valid date range', async ({ page }) => {
    // Select UF
    await page.getByRole('button', { name: 'SC', exact: true }).click();

    // Set a valid date range (7 days)
    const today = new Date();
    const futureDate = new Date(today);
    futureDate.setDate(today.getDate() + 7);

    const todayStr = today.toISOString().split('T')[0];
    const futureStr = futureDate.toISOString().split('T')[0];

    await page.getByLabel(/Data inicial/i).fill(todayStr);
    await page.getByLabel(/Data final/i).fill(futureStr);
    await page.getByLabel(/Data final/i).blur();
    await page.waitForTimeout(500);

    // Should NOT show error
    const errorMessage = page.getByText(/Data final deve ser maior ou igual/i);
    await expect(errorMessage).not.toBeVisible();

    // Search button should be enabled
    const searchButton = page.getByRole('button', { name: /^Buscar\b/i });
    await expect(searchButton).toBeEnabled();
  });
});
