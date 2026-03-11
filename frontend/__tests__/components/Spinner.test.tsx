import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Spinner } from '@/app/components/Spinner';

describe('Spinner', () => {
  it('renders with default size (md)', () => {
    render(<Spinner />);
    const svg = document.querySelector('svg');
    expect(svg).toHaveClass('w-5', 'h-5');
  });

  it('renders with sm size', () => {
    render(<Spinner size="sm" />);
    const svg = document.querySelector('svg');
    expect(svg).toHaveClass('w-4', 'h-4');
  });

  it('renders with lg size', () => {
    render(<Spinner size="lg" />);
    const svg = document.querySelector('svg');
    expect(svg).toHaveClass('w-8', 'h-8');
  });

  it('applies animate-spin class', () => {
    render(<Spinner />);
    const svg = document.querySelector('svg');
    expect(svg).toHaveClass('animate-spin');
  });

  it('has role="status"', () => {
    render(<Spinner />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('has sr-only text for screen readers', () => {
    render(<Spinner />);
    expect(screen.getByText('Carregando...')).toHaveClass('sr-only');
  });

  it('applies additional className', () => {
    render(<Spinner className="text-brand-blue" />);
    const wrapper = screen.getByRole('status');
    expect(wrapper).toHaveClass('text-brand-blue');
  });
});
