import { test, expect, Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/**
 * E2E Test: Accessibility Quality Gate (v2-story-1.0, Tasks 19-21)
 *
 * Runs axe-core automated accessibility audit on the search form page
 * across all 5 themes: Light, Paperwhite, Sépia, Dim, Dark.
 *
 * Verifies WCAG 2.1 AA compliance for:
 * - Color contrast (text, controls, badges)
 * - ARIA roles and labels
 * - Keyboard navigation
 * - Focus management
 */

const THEMES = ['light', 'paperwhite', 'sepia', 'dim', 'dark'] as const;

/**
 * Set theme via localStorage before page loads.
 * ThemeProvider reads from localStorage on mount.
 */
async function setTheme(page: Page, theme: string) {
  await page.evaluate((t) => {
    localStorage.setItem('descomplicita-theme', t);
  }, theme);
  await page.reload();
  await page.waitForLoadState('domcontentloaded');
  // Wait for theme to be applied (ThemeProvider sets mounted=true after applyTheme)
  await page.waitForTimeout(300);
}

test.describe('Accessibility: axe-core audit per theme', () => {
  for (const theme of THEMES) {
    test(`${theme} theme passes axe-core WCAG 2.1 AA`, async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('domcontentloaded');

      // Apply theme
      await setTheme(page, theme);

      // Run axe-core audit
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .exclude('[data-testid="analytics-noscript"]') // Exclude hidden analytics
        .analyze();

      // Report violations with helpful details
      const violations = results.violations.map(v => ({
        id: v.id,
        impact: v.impact,
        description: v.description,
        nodes: v.nodes.length,
        help: v.helpUrl,
      }));

      if (violations.length > 0) {
        console.log(`\n[${theme}] axe violations:`, JSON.stringify(violations, null, 2));
      }

      expect(
        results.violations,
        `Theme "${theme}" has ${results.violations.length} axe violation(s):\n` +
        results.violations.map(v => `  - ${v.id} (${v.impact}): ${v.description} [${v.nodes.length} node(s)]`).join('\n')
      ).toHaveLength(0);
    });
  }
});

test.describe('Accessibility: keyboard navigation', () => {
  test('Tab key navigates through all interactive elements', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Tab through page — verify focus reaches main form elements
    await page.keyboard.press('Tab'); // skip-link or first focusable

    // Should be able to tab through several elements without getting stuck
    const focusedElements: string[] = [];
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab');
      const tag = await page.evaluate(() => {
        const el = document.activeElement;
        return el ? `${el.tagName.toLowerCase()}${el.getAttribute('type') ? `[type=${el.getAttribute('type')}]` : ''}` : 'none';
      });
      focusedElements.push(tag);
    }

    // Verify we reached interactive elements (buttons, inputs, selects)
    const interactiveFound = focusedElements.some(
      el => el.startsWith('button') || el.startsWith('input') || el.startsWith('select') || el.startsWith('a')
    );
    expect(interactiveFound).toBe(true);
  });
});
