import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { CuriosityCarousel } from '@/app/components/loading-progress/CuriosityCarousel';
import type { Curiosidade } from '@/app/components/carouselData';

describe('CuriosityCarousel', () => {
  const curiosidade: Curiosidade = {
    texto: 'Compras públicas movimentam 12% do PIB.',
    fonte: 'OCDE / Governo Federal',
    categoria: 'insight',
  };

  it('should render curiosidade text', () => {
    render(<CuriosityCarousel curiosidade={curiosidade} isFading={false} />);
    expect(screen.getByText('Compras públicas movimentam 12% do PIB.')).toBeInTheDocument();
  });

  it('should render source', () => {
    render(<CuriosityCarousel curiosidade={curiosidade} isFading={false} />);
    expect(screen.getByText('Fonte: OCDE / Governo Federal')).toBeInTheDocument();
  });

  it('should render category label', () => {
    render(<CuriosityCarousel curiosidade={curiosidade} isFading={false} />);
    // "Insight de Mercado" appears in both header and badge
    expect(screen.getAllByText('Insight de Mercado').length).toBeGreaterThanOrEqual(1);
  });

  it('should apply fading class when isFading is true', () => {
    const { container } = render(<CuriosityCarousel curiosidade={curiosidade} isFading={true} />);
    expect(container.firstChild).toHaveClass('opacity-0');
  });

  it('should not apply fading class when isFading is false', () => {
    const { container } = render(<CuriosityCarousel curiosidade={curiosidade} isFading={false} />);
    expect(container.firstChild).toHaveClass('opacity-100');
  });

  it('should render all 4 category types correctly', () => {
    const categories = ['legislacao', 'estrategia', 'insight', 'dica'] as const;
    const labels = ['Legislação', 'Estratégia', 'Insight de Mercado', 'Dica Descomplicita'];

    categories.forEach((cat, i) => {
      const item: Curiosidade = { texto: `Test ${cat}`, fonte: 'Test', categoria: cat };
      const { unmount } = render(<CuriosityCarousel curiosidade={item} isFading={false} />);
      // Labels may appear multiple times (header + badge)
      expect(screen.getAllByText(labels[i]).length).toBeGreaterThanOrEqual(1);
      unmount();
    });
  });
});
