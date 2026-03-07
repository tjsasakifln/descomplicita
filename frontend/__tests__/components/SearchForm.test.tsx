import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SearchForm } from '@/app/components/SearchForm';

describe('SearchForm', () => {
  const defaultProps = {
    searchMode: 'setor' as const,
    onSearchModeChange: jest.fn(),
    setores: [
      { id: 'vestuario', name: 'Vestuário e Uniformes', description: '' },
      { id: 'alimentos', name: 'Alimentos e Merenda', description: '' },
    ],
    setorId: 'vestuario',
    onSetorIdChange: jest.fn(),
    termosArray: [] as string[],
    onTermosArrayChange: jest.fn(),
    termoInput: '',
    onTermoInputChange: jest.fn(),
    onFormChange: jest.fn(),
  };

  it('should render mode toggle buttons', () => {
    render(<SearchForm {...defaultProps} />);
    expect(screen.getByText('Setor')).toBeInTheDocument();
    expect(screen.getByText('Termos Específicos')).toBeInTheDocument();
  });

  it('should highlight active mode', () => {
    render(<SearchForm {...defaultProps} />);
    expect(screen.getByText('Setor')).toHaveClass('bg-brand-navy');
    expect(screen.getByText('Termos Específicos')).not.toHaveClass('bg-brand-navy');
  });

  it('should call onSearchModeChange when mode toggled', () => {
    render(<SearchForm {...defaultProps} />);
    fireEvent.click(screen.getByText('Termos Específicos'));
    expect(defaultProps.onSearchModeChange).toHaveBeenCalledWith('termos');
  });

  it('should render sector select in setor mode', () => {
    render(<SearchForm {...defaultProps} />);
    expect(screen.getByRole('combobox')).toBeInTheDocument();
    expect(screen.getByText('Vestuário e Uniformes')).toBeInTheDocument();
  });

  it('should not render sector select in termos mode', () => {
    render(<SearchForm {...defaultProps} searchMode="termos" />);
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
  });

  it('should render terms input in termos mode', () => {
    render(<SearchForm {...defaultProps} searchMode="termos" />);
    expect(screen.getByPlaceholderText(/Digite um termo/i)).toBeInTheDocument();
  });

  it('should render existing terms as tags', () => {
    render(<SearchForm {...defaultProps} searchMode="termos" termosArray={['uniforme', 'escolar']} />);
    expect(screen.getByText('uniforme')).toBeInTheDocument();
    expect(screen.getByText('escolar')).toBeInTheDocument();
  });

  it('should have remove button for each term tag', () => {
    render(<SearchForm {...defaultProps} searchMode="termos" termosArray={['uniforme']} />);
    expect(screen.getByLabelText('Remover termo uniforme')).toBeInTheDocument();
  });

  it('should display terms count', () => {
    render(<SearchForm {...defaultProps} searchMode="termos" termosArray={['uniforme', 'escolar']} />);
    expect(screen.getByText(/2 termos selecionados/)).toBeInTheDocument();
  });
});
