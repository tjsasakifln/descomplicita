/**
 * ThemeProvider Security Tests (v2-story-2.0 Chain 1)
 *
 * Validates that ThemeProvider sets data-theme attribute on <html>
 * for all 5 themes, enabling CSS-only FOUC prevention.
 */

import { render, act } from '@testing-library/react';
import { ThemeProvider, THEMES, useTheme, type ThemeId } from '@/app/components/ThemeProvider';

// Helper component to expose setTheme for testing
function ThemeSetter({ themeId }: { themeId: ThemeId }) {
  const { setTheme } = useTheme();

  return (
    <button onClick={() => setTheme(themeId)} data-testid="set-theme">
      Set Theme
    </button>
  );
}

describe('ThemeProvider data-theme attribute', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
    document.documentElement.classList.remove('dark');
    // Clear any inline styles
    document.documentElement.style.cssText = '';
  });

  it('should set data-theme attribute when theme is applied', () => {
    localStorage.setItem('descomplicita-theme', 'dark');

    render(
      <ThemeProvider>
        <div>test</div>
      </ThemeProvider>
    );

    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it.each(THEMES.map((t) => [t.id, t.isDark]))(
    'should set data-theme="%s" correctly (isDark=%s)',
    (themeId, isDark) => {
      localStorage.setItem('descomplicita-theme', themeId as string);

      render(
        <ThemeProvider>
          <div>test</div>
        </ThemeProvider>
      );

      expect(document.documentElement.getAttribute('data-theme')).toBe(themeId);

      if (isDark) {
        expect(document.documentElement.classList.contains('dark')).toBe(true);
      } else {
        expect(document.documentElement.classList.contains('dark')).toBe(false);
      }
    }
  );

  it('should update data-theme when theme changes via setTheme', () => {
    render(
      <ThemeProvider>
        <ThemeSetter themeId="sepia" />
      </ThemeProvider>
    );

    act(() => {
      const button = document.querySelector('[data-testid="set-theme"]');
      button?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(document.documentElement.getAttribute('data-theme')).toBe('sepia');
  });

  it('should default to light theme when no stored theme', () => {
    render(
      <ThemeProvider>
        <div>test</div>
      </ThemeProvider>
    );

    // applyTheme is called with 'light', so data-theme should be set
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  it('should set canvas and ink CSS variables for each theme', () => {
    for (const theme of THEMES) {
      localStorage.setItem('descomplicita-theme', theme.id);
      document.documentElement.style.cssText = '';

      const { unmount } = render(
        <ThemeProvider>
          <div>test</div>
        </ThemeProvider>
      );

      const style = document.documentElement.style;
      expect(style.getPropertyValue('--canvas')).toBe(theme.canvas);
      expect(style.getPropertyValue('--ink')).toBe(theme.ink);

      unmount();
    }
  });
});
