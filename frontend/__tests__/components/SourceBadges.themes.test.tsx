import { render, fireEvent, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SourceBadges } from '@/app/components/SourceBadges';
import type { SourceStats } from '@/app/types';

const makeStats = (overrides?: Partial<SourceStats>): SourceStats => ({
  total_fetched: 10,
  after_dedup: 10,
  elapsed_ms: 120,
  status: 'success',
  error_message: null,
  ...overrides,
});

const defaultProps = {
  sources: ['pncp', 'comprasgov'],
  stats: {
    pncp: makeStats({ total_fetched: 15, after_dedup: 14, elapsed_ms: 200 }),
    comprasgov: makeStats({ total_fetched: 5, after_dedup: 5, elapsed_ms: 80 }),
  } as Record<string, SourceStats>,
  dedupRemoved: 3,
  truncatedCombos: 2,
};

const themes = ['light', 'paperwhite', 'sepia', 'dim', 'dark'] as const;

describe('SourceBadges — theme snapshots (TD-UX-019)', () => {
  afterEach(() => {
    document.documentElement.removeAttribute('data-theme');
    document.documentElement.classList.remove('dark');
  });

  for (const theme of themes) {
    it(`renders correctly in ${theme} theme`, () => {
      if (theme === 'dark' || theme === 'dim') {
        document.documentElement.classList.add('dark');
      }
      if (theme !== 'light') {
        document.documentElement.setAttribute('data-theme', theme);
      }

      const { container } = render(<SourceBadges {...defaultProps} />);
      expect(container.firstChild).toMatchSnapshot();
    });
  }

  it('truncation warning uses Tailwind text-ink-warning (no inline style)', () => {
    const { container } = render(<SourceBadges {...defaultProps} />);
    // Expand to see truncation warning
    fireEvent.click(screen.getByRole('button'));

    const warningText = container.querySelector('.text-ink-warning');
    expect(warningText).toBeInTheDocument();
    expect(warningText).not.toHaveAttribute('style');
  });
});
