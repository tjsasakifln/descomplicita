import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Footer } from '@/app/components/Footer';

describe('Footer', () => {
  it('renders brand text', () => {
    render(<Footer />);
    expect(screen.getByText(/DescompLicita/)).toBeInTheDocument();
  });

  it('renders navigation links', () => {
    render(<Footer />);
    expect(screen.getByText('Contato')).toBeInTheDocument();
    expect(screen.getByText('Termos de Uso')).toBeInTheDocument();
  });

  it('renders version number', () => {
    render(<Footer />);
    const nav = screen.getByLabelText('Links do rodapé');
    expect(nav).toBeInTheDocument();
  });

  it('does not set aria-current by default', () => {
    render(<Footer />);
    const termosLink = screen.getByText('Termos de Uso');
    expect(termosLink).not.toHaveAttribute('aria-current');
  });

  it('sets aria-current="page" on termos page', () => {
    render(<Footer currentPage="termos" />);
    const termosLink = screen.getByText('Termos de Uso');
    expect(termosLink).toHaveAttribute('aria-current', 'page');
  });

  it('has correct mailto link', () => {
    render(<Footer />);
    const contatoLink = screen.getByText('Contato');
    expect(contatoLink).toHaveAttribute('href', 'mailto:contato@descomplicita.com.br');
  });

  it('has correct termos link', () => {
    render(<Footer />);
    const termosLink = screen.getByText('Termos de Uso');
    expect(termosLink).toHaveAttribute('href', '/termos');
  });
});
