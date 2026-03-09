import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SearchForm } from '@/app/components/SearchForm';

describe('SearchForm Setores Loading (UXD-002)', () => {
  const defaultProps = {
    searchMode: 'setor' as const,
    onSearchModeChange: jest.fn(),
    setores: [],
    setoresLoading: true,
    setorId: 'vestuario',
    onSetorIdChange: jest.fn(),
    termosArray: [] as string[],
    onTermosArrayChange: jest.fn(),
    termoInput: '',
    onTermoInputChange: jest.fn(),
    onFormChange: jest.fn(),
  };

  it('should show loading spinner when setoresLoading is true', () => {
    render(<SearchForm {...defaultProps} />);
    expect(screen.getByText('Carregando setores...')).toBeInTheDocument();
    expect(screen.getByLabelText('Carregando setores')).toHaveAttribute('aria-busy', 'true');
  });

  it('should show select when setoresLoading is false', () => {
    render(
      <SearchForm
        {...defaultProps}
        setoresLoading={false}
        setores={[
          { id: 'vestuario', name: 'Vestuário e Uniformes', description: '' },
          { id: 'alimentos', name: 'Alimentos e Merenda', description: '' },
        ]}
      />
    );
    expect(screen.queryByText('Carregando setores...')).not.toBeInTheDocument();
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('should not show loading for termos mode', () => {
    render(<SearchForm {...defaultProps} searchMode="termos" />);
    expect(screen.queryByText('Carregando setores...')).not.toBeInTheDocument();
  });
});
