/**
 * LargeVolumeWarning Component Tests
 *
 * Covers:
 * - UX4: Warning banner appears when >10 UFs selected
 * - UX5: Warning banner appears when date range >30 days
 * - EA7: Combined trigger — both >10 UFs AND >30 days
 * - UX8: Banner uses CSS custom properties (semantic tokens) not hardcoded colors
 * - Boundary conditions (exactly 10 UFs, exactly 30 days)
 * - Content assertions (UF count, combinations, date range, time estimate, suggestion)
 * - Accessibility attributes (role="status", aria-live="polite")
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import * as fs from 'fs';
import * as path from 'path';
import { LargeVolumeWarning } from '../../app/components/LargeVolumeWarning';

// ---------------------------------------------------------------------------
// Helper: estimateMinutes mirrors the component's internal logic so tests
// can assert the exact rendered value without hard-coding magic numbers.
// ---------------------------------------------------------------------------
function estimateMinutes(ufCount: number, days: number): number {
  const baseSec = 300 + Math.max(0, ufCount - 5) * 15;
  const filterMultiplier = days > 30 ? 1.3 : 1;
  return Math.ceil((baseSec * filterMultiplier) / 60);
}

// ---------------------------------------------------------------------------
// No-render cases
// ---------------------------------------------------------------------------
describe('LargeVolumeWarning — renders nothing when thresholds not met', () => {
  it('returns null when ufCount is 0 and dateRangeDays is 0', () => {
    const { container } = render(
      <LargeVolumeWarning ufCount={0} dateRangeDays={0} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('returns null when ufCount is exactly 10 (boundary — not above threshold)', () => {
    const { container } = render(
      <LargeVolumeWarning ufCount={10} dateRangeDays={0} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('returns null when dateRangeDays is exactly 30 (boundary — not above threshold)', () => {
    const { container } = render(
      <LargeVolumeWarning ufCount={5} dateRangeDays={30} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('returns null when both ufCount <= 10 and dateRangeDays <= 30', () => {
    const { container } = render(
      <LargeVolumeWarning ufCount={10} dateRangeDays={30} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('returns null for typical small search (5 UFs, 7 days)', () => {
    const { container } = render(
      <LargeVolumeWarning ufCount={5} dateRangeDays={7} />
    );
    expect(container.firstChild).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// UX4 — Warning triggered by UF count alone
// ---------------------------------------------------------------------------
describe('LargeVolumeWarning — UX4: UF count trigger', () => {
  it('renders banner when ufCount is 11 (boundary — one above threshold)', () => {
    render(<LargeVolumeWarning ufCount={11} dateRangeDays={0} />);
    expect(
      screen.getByRole('status')
    ).toBeInTheDocument();
  });

  it('renders banner for ufCount = 15 with dateRangeDays within limit', () => {
    render(<LargeVolumeWarning ufCount={15} dateRangeDays={30} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders banner for ufCount = 27 (all Brazilian states)', () => {
    render(<LargeVolumeWarning ufCount={27} dateRangeDays={0} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows UF count in the warning text', () => {
    render(<LargeVolumeWarning ufCount={15} dateRangeDays={0} />);
    expect(screen.getByText(/15 estados selecionados/i)).toBeInTheDocument();
  });

  it('shows number of UF × modalidade combinations (ufCount * 5)', () => {
    render(<LargeVolumeWarning ufCount={15} dateRangeDays={0} />);
    // 15 * 5 = 75 combinations
    expect(screen.getByText(/75 combinações UF × modalidade/i)).toBeInTheDocument();
  });

  it('does NOT show UF list item when ufCount <= 10 (date-only trigger)', () => {
    render(<LargeVolumeWarning ufCount={5} dateRangeDays={60} />);
    expect(screen.queryByText(/estados selecionados/i)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// UX5 — Warning triggered by date range alone
// ---------------------------------------------------------------------------
describe('LargeVolumeWarning — UX5: date range trigger', () => {
  it('renders banner when dateRangeDays is 31 (boundary — one above threshold)', () => {
    render(<LargeVolumeWarning ufCount={0} dateRangeDays={31} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders banner for dateRangeDays = 90 with ufCount within limit', () => {
    render(<LargeVolumeWarning ufCount={10} dateRangeDays={90} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows date range days in the warning text', () => {
    render(<LargeVolumeWarning ufCount={0} dateRangeDays={60} />);
    expect(screen.getByText(/Período de 60 dias selecionado/i)).toBeInTheDocument();
  });

  it('does NOT show date range list item when dateRangeDays <= 30 (UF-only trigger)', () => {
    render(<LargeVolumeWarning ufCount={15} dateRangeDays={7} />);
    expect(screen.queryByText(/dias selecionado/i)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// EA7 — Combined trigger: both conditions active
// ---------------------------------------------------------------------------
describe('LargeVolumeWarning — EA7: combined UF + date range trigger', () => {
  it('renders banner when both ufCount > 10 and dateRangeDays > 30', () => {
    render(<LargeVolumeWarning ufCount={20} dateRangeDays={60} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows both the UF warning item and the date range warning item', () => {
    render(<LargeVolumeWarning ufCount={20} dateRangeDays={60} />);
    expect(screen.getByText(/20 estados selecionados/i)).toBeInTheDocument();
    expect(screen.getByText(/Período de 60 dias selecionado/i)).toBeInTheDocument();
  });

  it('shows correct combinations for combined trigger', () => {
    render(<LargeVolumeWarning ufCount={20} dateRangeDays={60} />);
    // 20 * 5 = 100
    expect(screen.getByText(/100 combinações UF × modalidade/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Time estimate
// ---------------------------------------------------------------------------
describe('LargeVolumeWarning — time estimate', () => {
  it('shows estimated minutes when UF-only trigger fires', () => {
    const ufCount = 15;
    const days = 0;
    const expected = estimateMinutes(ufCount, days);
    render(<LargeVolumeWarning ufCount={ufCount} dateRangeDays={days} />);
    expect(
      screen.getByText(new RegExp(`Tempo estimado: ~${expected} minutos`, 'i'))
    ).toBeInTheDocument();
  });

  it('shows estimated minutes when date-only trigger fires', () => {
    const ufCount = 0;
    const days = 60;
    const expected = estimateMinutes(ufCount, days);
    render(<LargeVolumeWarning ufCount={ufCount} dateRangeDays={days} />);
    expect(
      screen.getByText(new RegExp(`Tempo estimado: ~${expected} minutos`, 'i'))
    ).toBeInTheDocument();
  });

  it('applies 1.3× multiplier when dateRangeDays > 30, yielding higher estimate', () => {
    const ufCount = 15;
    const shortDays = 0;
    const longDays = 60;

    const shortEstimate = estimateMinutes(ufCount, shortDays);
    const longEstimate = estimateMinutes(ufCount, longDays);

    // The long-range estimate must be strictly greater
    expect(longEstimate).toBeGreaterThan(shortEstimate);

    render(<LargeVolumeWarning ufCount={ufCount} dateRangeDays={longDays} />);
    expect(
      screen.getByText(new RegExp(`Tempo estimado: ~${longEstimate} minutos`, 'i'))
    ).toBeInTheDocument();
  });

  it('always shows time estimate list item when banner is visible', () => {
    render(<LargeVolumeWarning ufCount={11} dateRangeDays={0} />);
    expect(screen.getByText(/Tempo estimado:/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Content — fixed copy
// ---------------------------------------------------------------------------
describe('LargeVolumeWarning — static content', () => {
  it('shows heading "Busca de grande volume detectada"', () => {
    render(<LargeVolumeWarning ufCount={15} dateRangeDays={0} />);
    expect(
      screen.getByText('Busca de grande volume detectada')
    ).toBeInTheDocument();
  });

  it('shows reduction suggestion text', () => {
    render(<LargeVolumeWarning ufCount={15} dateRangeDays={0} />);
    expect(
      screen.getByText(
        /Considere selecionar menos estados ou um período menor para resultados mais rápidos/i
      )
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Accessibility
// ---------------------------------------------------------------------------
describe('LargeVolumeWarning — accessibility', () => {
  it('has role="status" on the banner container', () => {
    render(<LargeVolumeWarning ufCount={15} dateRangeDays={0} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('has aria-live="polite" on the banner container', () => {
    render(<LargeVolumeWarning ufCount={15} dateRangeDays={0} />);
    const banner = screen.getByRole('status');
    expect(banner).toHaveAttribute('aria-live', 'polite');
  });

  it('marks the clock emoji as aria-hidden so screen readers skip it', () => {
    const { container } = render(
      <LargeVolumeWarning ufCount={15} dateRangeDays={0} />
    );
    const emojiSpan = container.querySelector('[aria-hidden="true"]');
    expect(emojiSpan).toBeInTheDocument();
    expect(emojiSpan?.textContent).toContain('⏱');
  });
});

// ---------------------------------------------------------------------------
// UX8 — Semantic tokens / CSS custom properties (no hardcoded colours)
//
// JSDOM drops CSS custom properties from element.style, so we verify at the
// source code level that the component uses semantic tokens (var(--...))
// and does not contain hardcoded colour values.
// ---------------------------------------------------------------------------
describe('LargeVolumeWarning — UX8: semantic token styles', () => {
  const componentSource = fs.readFileSync(
    path.resolve(__dirname, '../../app/components/LargeVolumeWarning.tsx'),
    'utf-8'
  );

  it('uses var(--status-warning-bg) for backgroundColor', () => {
    expect(componentSource).toContain('var(--status-warning-bg)');
  });

  it('uses var(--status-warning-border) for borderColor', () => {
    expect(componentSource).toContain('var(--status-warning-border)');
  });

  it('uses var(--status-warning-text) for color', () => {
    expect(componentSource).toContain('var(--status-warning-text)');
  });

  it('does not contain hardcoded hex colour values in style props', () => {
    // Extract only the style={{ ... }} block to check for hardcoded colors
    const styleMatch = componentSource.match(/style=\{\{[\s\S]*?\}\}/);
    expect(styleMatch).toBeTruthy();
    const styleBlock = styleMatch![0];
    expect(styleBlock).not.toMatch(/#[0-9a-fA-F]{3,8}/);
    expect(styleBlock).not.toMatch(/rgb\(/i);
    expect(styleBlock).not.toMatch(/rgba\(/i);
  });
});

// ---------------------------------------------------------------------------
// Snapshot — prevents unintentional structure regressions
// ---------------------------------------------------------------------------
describe('LargeVolumeWarning — snapshot', () => {
  it('matches snapshot for UF-only trigger', () => {
    const { container } = render(
      <LargeVolumeWarning ufCount={15} dateRangeDays={0} />
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it('matches snapshot for date-only trigger', () => {
    const { container } = render(
      <LargeVolumeWarning ufCount={0} dateRangeDays={60} />
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it('matches snapshot for combined trigger', () => {
    const { container } = render(
      <LargeVolumeWarning ufCount={20} dateRangeDays={60} />
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it('matches snapshot for null render (thresholds not met)', () => {
    const { container } = render(
      <LargeVolumeWarning ufCount={10} dateRangeDays={30} />
    );
    expect(container.firstChild).toMatchSnapshot();
  });
});
