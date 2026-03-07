import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SaveSearchDialog } from '@/app/components/SaveSearchDialog';

describe('SaveSearchDialog', () => {
  const defaultProps = {
    saveSearchName: 'Uniformes Sul',
    onNameChange: jest.fn(),
    onConfirm: jest.fn(),
    onCancel: jest.fn(),
    saveError: null,
  };

  it('should render dialog with title', () => {
    render(<SaveSearchDialog {...defaultProps} />);
    expect(screen.getByText('Salvar Busca')).toBeInTheDocument();
  });

  it('should have dialog role', () => {
    render(<SaveSearchDialog {...defaultProps} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('should render name input with value', () => {
    render(<SaveSearchDialog {...defaultProps} />);
    const input = screen.getByLabelText('Nome da busca:') as HTMLInputElement;
    expect(input.value).toBe('Uniformes Sul');
  });

  it('should display character count', () => {
    render(<SaveSearchDialog {...defaultProps} />);
    expect(screen.getByText('13/50 caracteres')).toBeInTheDocument();
  });

  it('should call onNameChange when typing', () => {
    render(<SaveSearchDialog {...defaultProps} />);
    fireEvent.change(screen.getByLabelText('Nome da busca:'), { target: { value: 'Nova busca' } });
    expect(defaultProps.onNameChange).toHaveBeenCalledWith('Nova busca');
  });

  it('should call onConfirm when Salvar clicked', () => {
    render(<SaveSearchDialog {...defaultProps} />);
    fireEvent.click(screen.getByText('Salvar'));
    expect(defaultProps.onConfirm).toHaveBeenCalled();
  });

  it('should call onCancel when Cancelar clicked', () => {
    render(<SaveSearchDialog {...defaultProps} />);
    fireEvent.click(screen.getByText('Cancelar'));
    expect(defaultProps.onCancel).toHaveBeenCalled();
  });

  it('should disable Salvar when name is empty', () => {
    render(<SaveSearchDialog {...defaultProps} saveSearchName="" />);
    expect(screen.getByText('Salvar')).toBeDisabled();
  });

  it('should display error when saveError is set', () => {
    render(<SaveSearchDialog {...defaultProps} saveError="Limite atingido" />);
    expect(screen.getByText('Limite atingido')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('should not display error when saveError is null', () => {
    render(<SaveSearchDialog {...defaultProps} />);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('should have maxLength on input', () => {
    render(<SaveSearchDialog {...defaultProps} />);
    const input = screen.getByLabelText('Nome da busca:') as HTMLInputElement;
    expect(input.maxLength).toBe(50);
  });
});
