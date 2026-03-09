import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SkeletonCards } from '@/app/components/loading-progress/SkeletonCards';

describe('SkeletonCards', () => {
  it('should render 3 skeleton cards', () => {
    const { container } = render(<SkeletonCards />);
    const cards = container.querySelectorAll('.rounded-card');
    expect(cards).toHaveLength(3);
  });

  it('should render preparing text', () => {
    render(<SkeletonCards />);
    expect(screen.getByText('Preparando seus resultados...')).toBeInTheDocument();
  });

  it('should have shimmer animation elements', () => {
    const { container } = render(<SkeletonCards />);
    const shimmers = container.querySelectorAll('.animate-shimmer');
    expect(shimmers.length).toBeGreaterThan(0);
  });

  it('should decrease opacity for each successive card', () => {
    const { container } = render(<SkeletonCards />);
    const cards = container.querySelectorAll('.rounded-card');
    expect(cards[0]).toHaveStyle({ opacity: 1 });
    expect(cards[1]).toHaveStyle({ opacity: 0.8 });
    expect(cards[2]).toHaveStyle({ opacity: 0.6 });
  });
});
