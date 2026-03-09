import { render, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { NetworkIndicator } from '@/app/components/NetworkIndicator';

describe('NetworkIndicator (UXD-012)', () => {
  let originalOnLine: boolean;

  beforeEach(() => {
    originalOnLine = navigator.onLine;
  });

  afterEach(() => {
    Object.defineProperty(navigator, 'onLine', { value: originalOnLine, writable: true });
  });

  it('should not show when online', () => {
    Object.defineProperty(navigator, 'onLine', { value: true, writable: true });
    const { container } = render(<NetworkIndicator />);
    expect(container.firstChild).toBeNull();
  });

  it('should show banner when offline', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
    render(<NetworkIndicator />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Sem conexão com a internet/)).toBeInTheDocument();
  });

  it('should show when offline event fires', () => {
    Object.defineProperty(navigator, 'onLine', { value: true, writable: true });
    render(<NetworkIndicator />);

    act(() => {
      window.dispatchEvent(new Event('offline'));
    });

    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('should hide when online event fires after being offline', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
    render(<NetworkIndicator />);

    expect(screen.getByRole('alert')).toBeInTheDocument();

    act(() => {
      window.dispatchEvent(new Event('online'));
    });

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('should be dismissible', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
    render(<NetworkIndicator />);

    const closeBtn = screen.getByLabelText('Fechar aviso');
    fireEvent.click(closeBtn);

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('should reappear after dismiss if offline event fires again', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
    render(<NetworkIndicator />);

    // Dismiss
    fireEvent.click(screen.getByLabelText('Fechar aviso'));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();

    // Go online then offline again
    act(() => { window.dispatchEvent(new Event('online')); });
    act(() => { window.dispatchEvent(new Event('offline')); });

    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});
