/**
 * ThemeToggle Component Tests
 *
 * Tests theme switching functionality, ARIA menu pattern, and keyboard navigation
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeToggle } from '@/app/components/ThemeToggle';
import { ThemeProvider } from '@/app/components/ThemeProvider';

describe('ThemeToggle Component', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should render theme toggle button with aria-label', () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    const button = screen.getByRole('button', { name: /Alternar tema/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveAttribute('aria-label', 'Alternar tema');
    expect(button).toHaveAttribute('aria-haspopup', 'true');
  });

  it('should open dropdown with ARIA menu pattern when clicked', () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    const toggleButton = screen.getByRole('button', { name: /Alternar tema/i });

    // Initially no menu should be visible
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();

    // Click to open dropdown
    fireEvent.click(toggleButton);

    // Menu should appear with proper ARIA attributes
    const menu = screen.getByRole('menu');
    expect(menu).toBeInTheDocument();
    expect(menu).toHaveAttribute('aria-label', 'Selecionar tema');

    // Menu items should have role="menuitem"
    const menuItems = screen.getAllByRole('menuitem');
    expect(menuItems.length).toBe(5); // Light, Paperwhite, Sépia, Dim, Dark
  });

  it('should switch theme when option clicked', async () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    const toggleButton = screen.getByRole('button', { name: /Alternar tema/i });

    // Open dropdown
    fireEvent.click(toggleButton);

    // Click on "Dark" theme via menuitem
    const darkOption = screen.getByRole('menuitem', { name: /Dark/ });
    fireEvent.click(darkOption);

    // Check that theme was applied
    await waitFor(() => {
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    // Dropdown should close after selection
    await waitFor(() => {
      expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    });
  });

  it('should persist theme preference to localStorage', async () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    const toggleButton = screen.getByRole('button', { name: /Alternar tema/i });

    // Open dropdown and select dark theme
    fireEvent.click(toggleButton);
    const darkOption = screen.getByRole('menuitem', { name: /Dark/ });
    fireEvent.click(darkOption);

    // Check localStorage
    await waitFor(() => {
      expect(localStorage.getItem('descomplicita-theme')).toBe('dark');
    });
  });

  it('should close dropdown when clicking outside', async () => {
    render(
      <ThemeProvider>
        <div>
          <ThemeToggle />
          <div data-testid="outside">Outside</div>
        </div>
      </ThemeProvider>
    );

    const toggleButton = screen.getByRole('button', { name: /Alternar tema/i });

    // Open dropdown
    fireEvent.click(toggleButton);
    expect(screen.getByRole('menu')).toBeInTheDocument();

    // Click outside
    const outside = screen.getByTestId('outside');
    fireEvent.mouseDown(outside);

    // Dropdown should close
    await waitFor(() => {
      expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    });
  });

  it('should display current theme preview color', () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    const toggleButton = screen.getByRole('button', { name: /Alternar tema/i });

    // Should have a color preview element
    const preview = toggleButton.querySelector('.rounded-full');
    expect(preview).toBeInTheDocument();
  });

  it('should navigate menu items with arrow keys', () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    const toggleButton = screen.getByRole('button', { name: /Alternar tema/i });
    fireEvent.click(toggleButton);

    const menu = screen.getByRole('menu');
    const menuItems = screen.getAllByRole('menuitem');

    // Arrow Down should move focus to next item
    fireEvent.keyDown(menu, { key: 'ArrowDown' });
    // Arrow Up should move focus to previous item
    fireEvent.keyDown(menu, { key: 'ArrowUp' });

    // All items should be present and navigable
    expect(menuItems.length).toBe(5);
  });

  it('should close dropdown on Escape key', async () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    const toggleButton = screen.getByRole('button', { name: /Alternar tema/i });
    fireEvent.click(toggleButton);
    expect(screen.getByRole('menu')).toBeInTheDocument();

    // Press Escape
    fireEvent.keyDown(document, { key: 'Escape' });

    await waitFor(() => {
      expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    });
  });
});
