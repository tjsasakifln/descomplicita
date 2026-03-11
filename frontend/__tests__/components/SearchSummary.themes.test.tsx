import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SearchSummary } from '@/app/components/SearchSummary';
import type { BuscaResult } from '@/app/types';

jest.mock('@/app/components/SourceBadges', () => ({
  SourceBadges: () => <div data-testid="source-badges" />,
  default: () => <div data-testid="source-badges" />,
}));

const mockResult: BuscaResult = {
  resumo: {
    resumo_executivo: 'Encontradas 15 licitações de uniformes',
    total_oportunidades: 15,
    valor_total: 450000,
    destaques: ['Destaque 1'],
    distribuicao_uf: { SC: 6 },
    alerta_urgencia: null,
  },
  download_id: 'dl-1',
  total_raw: 200,
  total_filtrado: 15,
  total_atas: 5,
  total_licitacoes: 10,
  filter_stats: null,
  sources_used: ['pncp'],
  source_stats: { pncp: { total_fetched: 200, after_dedup: 195, elapsed_ms: 500, status: 'success', error_message: null } },
  dedup_removed: 5,
  truncated_combos: 0,
};

const themes = ['light', 'paperwhite', 'sepia', 'dim', 'dark'] as const;

describe('SearchSummary — theme snapshots (TD-UX-011)', () => {
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

      const { container } = render(<SearchSummary result={mockResult} />);
      expect(container.firstChild).toMatchSnapshot();
    });
  }

  it('badge classes use Tailwind tokens (no inline style={{}})', () => {
    const { container } = render(<SearchSummary result={mockResult} />);
    const badges = container.querySelectorAll('.rounded-full');

    badges.forEach(badge => {
      expect(badge).not.toHaveAttribute('style');
    });
  });
});
