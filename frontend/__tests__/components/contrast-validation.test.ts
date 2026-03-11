/**
 * RT3: Contrast ratio validation for --ink-muted across all 5 themes.
 * Validates WCAG AA minimum 4.5:1 contrast ratio.
 */

// Relative luminance calculation per WCAG 2.1
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

// Theme ink-muted values and their background canvas colors
const themes: Record<string, { inkMuted: string; canvas: string }> = {
  light: { inkMuted: '#4f5f6f', canvas: '#ffffff' },
  paperwhite: { inkMuted: '#4a5a6a', canvas: '#F5F0E8' },
  sepia: { inkMuted: '#4a5968', canvas: '#EDE0CC' },
  dim: { inkMuted: '#8a99a9', canvas: '#2A2A2E' },
  dark: { inkMuted: '#8a99a9', canvas: '#121212' },
};

describe('WCAG AA contrast validation: --ink-muted', () => {
  for (const [theme, { inkMuted, canvas }] of Object.entries(themes)) {
    it(`${theme} theme: ink-muted has >= 4.5:1 contrast ratio`, () => {
      const ratio = contrastRatio(inkMuted, canvas);
      expect(ratio).toBeGreaterThanOrEqual(4.5);
    });
  }
});
