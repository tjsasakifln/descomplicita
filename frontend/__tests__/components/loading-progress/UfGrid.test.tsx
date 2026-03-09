import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { UfGrid } from '@/app/components/loading-progress/UfGrid';

describe('UfGrid', () => {
  it('should not render when phase is not fetching', () => {
    const { container } = render(
      <UfGrid phase="queued" ufsTotal={3} ufsCompleted={0} selectedUfs={['SC', 'PR', 'RS']} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('should not render when ufsTotal is 0', () => {
    const { container } = render(
      <UfGrid phase="fetching" ufsTotal={0} ufsCompleted={0} selectedUfs={[]} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('should render UF badges when selectedUfs provided', () => {
    render(<UfGrid phase="fetching" ufsTotal={3} ufsCompleted={1} selectedUfs={['SC', 'PR', 'RS']} />);
    expect(screen.getByText('SC')).toBeInTheDocument();
    expect(screen.getByText('PR')).toBeInTheDocument();
    expect(screen.getByText('RS')).toBeInTheDocument();
  });

  it('should show completed count', () => {
    render(<UfGrid phase="fetching" ufsTotal={3} ufsCompleted={1} selectedUfs={['SC', 'PR', 'RS']} />);
    expect(screen.getByText('1 / 3')).toBeInTheDocument();
  });

  it('should mark completed UFs with brand-navy style', () => {
    render(<UfGrid phase="fetching" ufsTotal={3} ufsCompleted={2} selectedUfs={['SC', 'PR', 'RS']} />);
    const sc = screen.getByText('SC');
    expect(sc.className).toContain('bg-brand-navy');
    const pr = screen.getByText('PR');
    expect(pr.className).toContain('bg-brand-navy');
    const rs = screen.getByText('RS');
    expect(rs.className).toContain('bg-brand-blue');
  });

  it('should show simple counter when no selectedUfs', () => {
    render(<UfGrid phase="fetching" ufsTotal={5} ufsCompleted={2} selectedUfs={[]} />);
    expect(screen.getByText('2 / 5')).toBeInTheDocument();
    expect(screen.queryByText('SC')).not.toBeInTheDocument();
  });
});
