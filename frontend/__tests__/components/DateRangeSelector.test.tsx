import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { DateRangeSelector } from '@/app/components/DateRangeSelector';

describe('DateRangeSelector', () => {
  const defaultProps = {
    dataInicial: '2024-01-01',
    dataFinal: '2024-01-07',
    onDataInicialChange: jest.fn(),
    onDataFinalChange: jest.fn(),
    validationErrors: {},
  };

  it('should render date inputs with labels', () => {
    render(<DateRangeSelector {...defaultProps} />);
    expect(screen.getByLabelText('Data inicial:')).toBeInTheDocument();
    expect(screen.getByLabelText('Data final:')).toBeInTheDocument();
  });

  it('should display date values', () => {
    render(<DateRangeSelector {...defaultProps} />);
    expect((screen.getByLabelText('Data inicial:') as HTMLInputElement).value).toBe('2024-01-01');
    expect((screen.getByLabelText('Data final:') as HTMLInputElement).value).toBe('2024-01-07');
  });

  it('should call onDataInicialChange on change', () => {
    render(<DateRangeSelector {...defaultProps} />);
    fireEvent.change(screen.getByLabelText('Data inicial:'), { target: { value: '2024-02-01' } });
    expect(defaultProps.onDataInicialChange).toHaveBeenCalledWith('2024-02-01');
  });

  it('should call onDataFinalChange on change', () => {
    render(<DateRangeSelector {...defaultProps} />);
    fireEvent.change(screen.getByLabelText('Data final:'), { target: { value: '2024-02-15' } });
    expect(defaultProps.onDataFinalChange).toHaveBeenCalledWith('2024-02-15');
  });

  it('should display validation error when present', () => {
    render(<DateRangeSelector {...defaultProps} validationErrors={{ date_range: 'Data final deve ser maior ou igual à data inicial' }} />);
    expect(screen.getByText('Data final deve ser maior ou igual à data inicial')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('should not display error when no validation error', () => {
    render(<DateRangeSelector {...defaultProps} />);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('should use grid layout', () => {
    render(<DateRangeSelector {...defaultProps} />);
    const container = screen.getByLabelText('Data inicial:').closest('div')?.parentElement;
    expect(container).toHaveClass('grid');
  });
});
