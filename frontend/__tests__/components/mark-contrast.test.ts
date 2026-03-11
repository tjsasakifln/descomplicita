/**
 * TD-UX-021: Contrast ratio validation for <mark> element across all 5 themes.
 * Validates WCAG AA minimum 4.5:1 contrast ratio for text on highlight background.
 *
 * mark uses: background-color: var(--brand-blue-subtle), color: var(--ink)
 */

function sRGBtoLinear(c: number): number {
  const s = c / 255;
  return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
}

function relativeLuminance(hex: string): number {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return 0.2126 * sRGBtoLinear(r) + 0.7152 * sRGBtoLinear(g) + 0.0722 * sRGBtoLinear(b);
}

function contrastRatio(fg: string, bg: string): number {
  const l1 = relativeLuminance(fg);
  const l2 = relativeLuminance(bg);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Composites an rgba color over a solid background.
 * rgba format: { r, g, b, a } where a is 0-1
 */
function compositeOver(
  fg: { r: number; g: number; b: number; a: number },
  bgHex: string
): string {
  const bgR = parseInt(bgHex.slice(1, 3), 16);
  const bgG = parseInt(bgHex.slice(3, 5), 16);
  const bgB = parseInt(bgHex.slice(5, 7), 16);
  const r = Math.round(fg.r * fg.a + bgR * (1 - fg.a));
  const g = Math.round(fg.g * fg.a + bgG * (1 - fg.a));
  const b = Math.round(fg.b * fg.a + bgB * (1 - fg.a));
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

// Theme values for mark: ink (text color) and brand-blue-subtle (background)
// For dark themes, brand-blue-subtle is rgba — composite over canvas
const themes: Record<string, { ink: string; markBg: string }> = {
  light: {
    ink: '#1e2d3b',
    markBg: '#e8f0ff', // --brand-blue-subtle
  },
  paperwhite: {
    ink: '#1e2d3b', // inherits from :root
    markBg: '#e8f0ff', // inherits from :root
  },
  sepia: {
    ink: '#2c1810',
    markBg: '#e8e0d4', // sepia overrides --brand-blue-subtle
  },
  dim: {
    ink: '#e8eaed', // inherits from .dark
    // rgba(17, 109, 255, 0.12) over #2A2A2E
    markBg: compositeOver({ r: 17, g: 109, b: 255, a: 0.12 }, '#2A2A2E'),
  },
  dark: {
    ink: '#e8eaed', // from .dark
    // rgba(17, 109, 255, 0.12) over #121212
    markBg: compositeOver({ r: 17, g: 109, b: 255, a: 0.12 }, '#121212'),
  },
};

describe('WCAG AA contrast validation: <mark> element (TD-UX-021)', () => {
  for (const [theme, { ink, markBg }] of Object.entries(themes)) {
    it(`${theme} theme: mark text has >= 4.5:1 contrast ratio (ink on brand-blue-subtle)`, () => {
      const ratio = contrastRatio(ink, markBg);
      expect(ratio).toBeGreaterThanOrEqual(4.5);
    });
  }
});
