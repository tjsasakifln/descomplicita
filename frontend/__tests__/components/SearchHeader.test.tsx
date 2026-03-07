import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SearchHeader } from '@/app/components/SearchHeader';

jest.mock('next/image', () => ({
  __esModule: true,
  default: (props: any) => <img {...props} />,
}));

jest.mock('@/components/ThemeToggle', () => ({
  ThemeToggle: () => <div data-testid="theme-toggle" />,
}));

jest.mock('@/components/SavedSearchesDropdown', () => ({
  SavedSearchesDropdown: () => <div data-testid="saved-searches" />,
}));

describe('SearchHeader', () => {
  const mockLoadSearch = jest.fn();
  const mockAnalytics = jest.fn();

  it('should render the logo with alt text', () => {
    render(<SearchHeader onLoadSearch={mockLoadSearch} onAnalyticsEvent={mockAnalytics} />);
    expect(screen.getByAltText('DescompLicita')).toBeInTheDocument();
  });

  it('should use self-hosted logo (not Wix CDN)', () => {
    render(<SearchHeader onLoadSearch={mockLoadSearch} onAnalyticsEvent={mockAnalytics} />);
    const logo = screen.getByAltText('DescompLicita');
    expect(logo).toHaveAttribute('src', '/logo-descomplicita.png');
  });

  it('should display subtitle text', () => {
    render(<SearchHeader onLoadSearch={mockLoadSearch} onAnalyticsEvent={mockAnalytics} />);
    expect(screen.getByText('Busca Inteligente de Licitações')).toBeInTheDocument();
  });

  it('should render ThemeToggle', () => {
    render(<SearchHeader onLoadSearch={mockLoadSearch} onAnalyticsEvent={mockAnalytics} />);
    expect(screen.getByTestId('theme-toggle')).toBeInTheDocument();
  });

  it('should render SavedSearchesDropdown', () => {
    render(<SearchHeader onLoadSearch={mockLoadSearch} onAnalyticsEvent={mockAnalytics} />);
    expect(screen.getByTestId('saved-searches')).toBeInTheDocument();
  });

  it('should have sticky header', () => {
    render(<SearchHeader onLoadSearch={mockLoadSearch} onAnalyticsEvent={mockAnalytics} />);
    const header = screen.getByRole('banner');
    expect(header).toHaveClass('sticky', 'top-0');
  });
});
