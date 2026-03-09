import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ProgressBar } from '@/app/components/loading-progress/ProgressBar';

describe('ProgressBar', () => {
  const defaultProps = {
    progress: 45,
    statusMessage: 'Buscando em 3/5 estados...',
    eta: '~30s restantes',
    timeDisplay: '15s',
    phase: 'fetching',
    itemsFetched: 120,
    itemsFiltered: 0,
  };

  it('should render progress bar with correct width', () => {
    render(<ProgressBar {...defaultProps} />);
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '45');
    expect(bar).toHaveStyle({ width: '45%' });
  });

  it('should display status message', () => {
    render(<ProgressBar {...defaultProps} />);
    expect(screen.getByText('Buscando em 3/5 estados...')).toBeInTheDocument();
  });

  it('should display ETA when provided', () => {
    render(<ProgressBar {...defaultProps} />);
    expect(screen.getByText('~30s restantes')).toBeInTheDocument();
  });

  it('should not show ETA when null', () => {
    render(<ProgressBar {...defaultProps} eta={null} />);
    expect(screen.queryByText(/restantes/)).not.toBeInTheDocument();
  });

  it('should display elapsed time', () => {
    render(<ProgressBar {...defaultProps} />);
    expect(screen.getByText('15s')).toBeInTheDocument();
  });

  it('should show items fetched during fetching phase', () => {
    render(<ProgressBar {...defaultProps} />);
    expect(screen.getByText('120 licitações encontradas até agora')).toBeInTheDocument();
  });

  it('should show items filtered during filtering phase', () => {
    render(<ProgressBar {...defaultProps} phase="filtering" itemsFetched={0} itemsFiltered={50} />);
    expect(screen.getByText('50 licitações filtradas')).toBeInTheDocument();
  });

  it('should show percentage', () => {
    render(<ProgressBar {...defaultProps} />);
    expect(screen.getByText('45%')).toBeInTheDocument();
  });

  it('should enforce minimum 3% width', () => {
    render(<ProgressBar {...defaultProps} progress={0} />);
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveStyle({ width: '3%' });
  });
});
