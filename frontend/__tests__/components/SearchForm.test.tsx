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
    expect(screen.getByPlaceholderText(/Separe termos/i)).toBeInTheDocument();
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

  it('should add multi-word term when comma is typed', () => {
    const onTermosArrayChange = jest.fn();
    const onTermoInputChange = jest.fn();
    const onFormChange = jest.fn();
    render(
      <SearchForm
        {...defaultProps}
        searchMode="termos"
        onTermosArrayChange={onTermosArrayChange}
        onTermoInputChange={onTermoInputChange}
        onFormChange={onFormChange}
      />
    );
    const input = screen.getByPlaceholderText(/Separe termos/i);
    fireEvent.change(input, { target: { value: 'camisa polo,' } });
    expect(onTermosArrayChange).toHaveBeenCalled();
    expect(onTermoInputChange).toHaveBeenCalledWith('');
    expect(onFormChange).toHaveBeenCalled();
  });

  it('should show comma hint text in termos mode', () => {
    render(<SearchForm {...defaultProps} searchMode="termos" />);
    expect(screen.getByText(/Separe termos por/)).toBeInTheDocument();
    expect(screen.getByText(/vírgula/)).toBeInTheDocument();
  });

  it('should not add empty term on lone comma', () => {
    const onTermosArrayChange = jest.fn();
    render(
      <SearchForm
        {...defaultProps}
        searchMode="termos"
        onTermosArrayChange={onTermosArrayChange}
      />
    );
    const input = screen.getByPlaceholderText(/Separe termos/i);
    fireEvent.change(input, { target: { value: ',' } });
    expect(onTermosArrayChange).not.toHaveBeenCalled();
  });

  it('should not add duplicate multi-word term via comma', () => {
    const onTermosArrayChange = jest.fn();
    render(
      <SearchForm
        {...defaultProps}
        searchMode="termos"
        termosArray={['camisa polo']}
        onTermosArrayChange={onTermosArrayChange}
      />
    );
    const input = screen.getByPlaceholderText(/Adicionar mais/i);
    fireEvent.change(input, { target: { value: 'camisa polo,' } });
    expect(onTermosArrayChange).not.toHaveBeenCalled();
  });

  it('should show fallback indicator when setoresFallback is true', () => {
    render(<SearchForm {...defaultProps} setoresFallback={true} />);
    expect(screen.getByText(/Usando lista de setores em cache/)).toBeInTheDocument();
  });

  it('should not show fallback indicator when setoresFallback is false', () => {
    render(<SearchForm {...defaultProps} setoresFallback={false} />);
    expect(screen.queryByText(/Usando lista de setores em cache/)).not.toBeInTheDocument();
  });

  it('should show loading state with spinner', () => {
    render(<SearchForm {...defaultProps} setoresLoading={true} />);
    expect(screen.getByText('Carregando setores...')).toBeInTheDocument();
    expect(screen.getByLabelText('Carregando setores')).toHaveAttribute('aria-busy', 'true');
  });

  it('should add term on space', () => {
    const onTermosArrayChange = jest.fn();
    const onTermoInputChange = jest.fn();
    const onFormChange = jest.fn();
    render(
      <SearchForm
        {...defaultProps}
        searchMode="termos"
        onTermosArrayChange={onTermosArrayChange}
        onTermoInputChange={onTermoInputChange}
        onFormChange={onFormChange}
      />
    );
    const input = screen.getByPlaceholderText(/Separe termos/i);
    fireEvent.change(input, { target: { value: 'uniforme ' } });
    expect(onTermosArrayChange).toHaveBeenCalled();
    expect(onTermoInputChange).toHaveBeenCalledWith('');
  });

  it('should not add empty term on space', () => {
    const onTermosArrayChange = jest.fn();
    render(
      <SearchForm
        {...defaultProps}
        searchMode="termos"
        onTermosArrayChange={onTermosArrayChange}
      />
    );
    const input = screen.getByPlaceholderText(/Separe termos/i);
    fireEvent.change(input, { target: { value: ' ' } });
    expect(onTermosArrayChange).not.toHaveBeenCalled();
  });

  it('should not add duplicate term on space', () => {
    const onTermosArrayChange = jest.fn();
    render(
      <SearchForm
        {...defaultProps}
        searchMode="termos"
        termosArray={['uniforme']}
        onTermosArrayChange={onTermosArrayChange}
      />
    );
    const input = screen.getByPlaceholderText(/Adicionar mais/i);
    fireEvent.change(input, { target: { value: 'uniforme ' } });
    expect(onTermosArrayChange).not.toHaveBeenCalled();
  });

  it('should update input value on normal typing', () => {
    const onTermoInputChange = jest.fn();
    render(
      <SearchForm
        {...defaultProps}
        searchMode="termos"
        onTermoInputChange={onTermoInputChange}
      />
    );
    const input = screen.getByPlaceholderText(/Separe termos/i);
    fireEvent.change(input, { target: { value: 'test' } });
    expect(onTermoInputChange).toHaveBeenCalledWith('test');
  });

  it('should remove last term on Backspace with empty input', () => {
    const onTermosArrayChange = jest.fn();
    const onFormChange = jest.fn();
    render(
      <SearchForm
        {...defaultProps}
        searchMode="termos"
        termosArray={['a', 'b']}
        termoInput=""
        onTermosArrayChange={onTermosArrayChange}
        onFormChange={onFormChange}
      />
    );
    const input = screen.getByPlaceholderText(/Adicionar mais/i);
    fireEvent.keyDown(input, { key: 'Backspace' });
    expect(onTermosArrayChange).toHaveBeenCalled();
    expect(onFormChange).toHaveBeenCalled();
  });

  it('should add term on Enter key', () => {
    const onTermosArrayChange = jest.fn();
    const onTermoInputChange = jest.fn();
    render(
      <SearchForm
        {...defaultProps}
        searchMode="termos"
        termoInput="jaleco"
        onTermosArrayChange={onTermosArrayChange}
        onTermoInputChange={onTermoInputChange}
      />
    );
    const input = screen.getByRole('textbox');
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onTermosArrayChange).toHaveBeenCalled();
    expect(onTermoInputChange).toHaveBeenCalledWith('');
  });

  it('should not add empty term on Enter', () => {
    const onTermosArrayChange = jest.fn();
    render(
      <SearchForm
        {...defaultProps}
        searchMode="termos"
        termoInput=""
        onTermosArrayChange={onTermosArrayChange}
      />
    );
    const input = screen.getByRole('textbox');
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onTermosArrayChange).not.toHaveBeenCalled();
  });

  it('should remove specific term when X clicked', () => {
    const onTermosArrayChange = jest.fn();
    const onFormChange = jest.fn();
    render(
      <SearchForm
        {...defaultProps}
        searchMode="termos"
        termosArray={['uniforme', 'escolar']}
        onTermosArrayChange={onTermosArrayChange}
        onFormChange={onFormChange}
      />
    );
    fireEvent.click(screen.getByLabelText('Remover termo uniforme'));
    expect(onTermosArrayChange).toHaveBeenCalled();
    expect(onFormChange).toHaveBeenCalled();
  });

  it('displays singular term count', () => {
    render(<SearchForm {...defaultProps} searchMode="termos" termosArray={['uniforme']} />);
    expect(screen.getByText(/1 termo selecionado$/)).toBeInTheDocument();
  });
});
