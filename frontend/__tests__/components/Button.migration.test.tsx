/**
 * Story 1.1 Tasks 1 & 2: Button component adoption tests.
 * Validates that migrated buttons preserve click, disabled, and loading behavior.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Button } from '@/app/components/Button';

describe('Button migration — Task 1: Buscar button', () => {
  it('renders with loading state and shows Spinner', () => {
    render(
      <Button loading size="lg" className="w-full">
        Buscando...
      </Button>
    );
    const btn = screen.getByRole('button');
    expect(btn).toBeDisabled();
    expect(btn.querySelector('svg')).toHaveClass('animate-spin');
    expect(btn).toHaveTextContent('Buscando...');
  });

  it('renders enabled when not loading and not disabled', () => {
    render(
      <Button size="lg" className="w-full">
        Buscar Vestuário e Uniformes
      </Button>
    );
    const btn = screen.getByRole('button');
    expect(btn).not.toBeDisabled();
    expect(btn).toHaveTextContent('Buscar Vestuário e Uniformes');
  });

  it('disables when canSearch is false', () => {
    render(
      <Button disabled size="lg" className="w-full">
        Buscar Vestuário e Uniformes
      </Button>
    );
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('fires onClick when clicked', () => {
    const onClick = jest.fn();
    render(
      <Button onClick={onClick} size="lg" className="w-full">
        Buscar
      </Button>
    );
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

describe('Button migration — Task 2: Other buttons', () => {
  it('danger variant for error retry', () => {
    const onClick = jest.fn();
    render(
      <Button onClick={onClick} variant="danger" size="sm">
        Tentar novamente
      </Button>
    );
    const btn = screen.getByRole('button');
    expect(btn).toHaveClass('bg-error', 'text-white');
    fireEvent.click(btn);
    expect(onClick).toHaveBeenCalled();
  });

  it('secondary variant for save search', () => {
    render(
      <Button variant="secondary" className="w-full">
        Salvar Busca
      </Button>
    );
    const btn = screen.getByRole('button');
    expect(btn).toHaveClass('bg-surface-0', 'text-brand-navy');
  });

  it('ghost variant for cancel', () => {
    const onClick = jest.fn();
    render(
      <Button variant="ghost" size="sm" onClick={onClick}>
        Cancelar
      </Button>
    );
    const btn = screen.getByRole('button');
    expect(btn).toHaveClass('bg-transparent');
    fireEvent.click(btn);
    expect(onClick).toHaveBeenCalled();
  });

  it('primary variant for EmptyState adjust button', () => {
    const onClick = jest.fn();
    render(
      <Button onClick={onClick} size="lg">
        Ajustar critérios de busca
      </Button>
    );
    const btn = screen.getByRole('button');
    expect(btn).toHaveClass('bg-brand-navy', 'text-white');
    fireEvent.click(btn);
    expect(onClick).toHaveBeenCalled();
  });

  it('download button with loading state', () => {
    render(
      <Button loading size="lg" className="w-full">
        Preparando download...
      </Button>
    );
    const btn = screen.getByRole('button');
    expect(btn).toBeDisabled();
    expect(btn.querySelector('svg')).toHaveClass('animate-spin');
  });

  it('ghost cancel button in LoadingProgress', () => {
    const onClick = jest.fn();
    render(
      <Button variant="ghost" size="sm" onClick={onClick}
        className="text-ink-muted hover:text-error hover:bg-error-subtle">
        Cancelar busca
      </Button>
    );
    const btn = screen.getByRole('button');
    expect(btn).toHaveClass('text-ink-muted');
    fireEvent.click(btn);
    expect(onClick).toHaveBeenCalled();
  });
});
