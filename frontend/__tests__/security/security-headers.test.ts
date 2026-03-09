/**
 * Security Headers Tests (v2-story-2.0 Chain 1)
 *
 * Validates that:
 * - vercel.json contains all required security headers (TD-M07, TD-M08, XD-SEC-01)
 * - layout.tsx does NOT contain dangerouslySetInnerHTML (XD-SEC-03)
 * - theme-init.js exists and sets data-theme attribute (TD-M10)
 */

import * as fs from 'fs';
import * as path from 'path';

// __dirname = frontend/__tests__/security
const FRONTEND = path.resolve(__dirname, '..', '..'); // frontend/
const PROJECT_ROOT = path.resolve(FRONTEND, '..'); // project root

describe('Security Headers in vercel.json', () => {
  let vercelConfig: {
    headers: Array<{
      source: string;
      headers: Array<{ key: string; value: string }>;
    }>;
  };

  beforeAll(() => {
    const raw = fs.readFileSync(path.join(PROJECT_ROOT, 'vercel.json'), 'utf-8');
    vercelConfig = JSON.parse(raw);
  });

  function getHeader(key: string): string | undefined {
    for (const block of vercelConfig.headers) {
      const found = block.headers.find(
        (h) => h.key.toLowerCase() === key.toLowerCase()
      );
      if (found) return found.value;
    }
    return undefined;
  }

  it('should have Content-Security-Policy header (TD-M07)', () => {
    const csp = getHeader('Content-Security-Policy');
    expect(csp).toBeDefined();
    expect(csp).toContain("default-src 'self'");
    expect(csp).toContain("script-src 'self'");
    // unsafe-inline should NOT be in script-src (only acceptable in style-src)
    const scriptSrc = csp!.match(/script-src\s+([^;]+)/)?.[1] || '';
    expect(scriptSrc).not.toContain("'unsafe-inline'");
  });

  it('should allow Sentry in CSP', () => {
    const csp = getHeader('Content-Security-Policy');
    expect(csp).toContain('sentry.io');
  });

  it('should allow Mixpanel in CSP', () => {
    const csp = getHeader('Content-Security-Policy');
    expect(csp).toContain('mixpanel.com');
  });

  it('should allow Google Fonts in CSP style-src', () => {
    const csp = getHeader('Content-Security-Policy');
    expect(csp).toContain('fonts.googleapis.com');
    expect(csp).toContain('fonts.gstatic.com');
  });

  it('should have frame-ancestors none in CSP', () => {
    const csp = getHeader('Content-Security-Policy');
    expect(csp).toContain("frame-ancestors 'none'");
  });

  it('should have Strict-Transport-Security header (TD-M08)', () => {
    const hsts = getHeader('Strict-Transport-Security');
    expect(hsts).toBeDefined();
    expect(hsts).toContain('max-age=31536000');
    expect(hsts).toContain('includeSubDomains');
  });

  it('should have X-Content-Type-Options header', () => {
    expect(getHeader('X-Content-Type-Options')).toBe('nosniff');
  });

  it('should have X-Frame-Options header', () => {
    expect(getHeader('X-Frame-Options')).toBe('DENY');
  });

  it('should have Referrer-Policy header (XD-SEC-01)', () => {
    expect(getHeader('Referrer-Policy')).toBe('strict-origin-when-cross-origin');
  });

  it('should have Permissions-Policy header (XD-SEC-01)', () => {
    const pp = getHeader('Permissions-Policy');
    expect(pp).toBeDefined();
    expect(pp).toContain('camera=()');
    expect(pp).toContain('microphone=()');
    expect(pp).toContain('geolocation=()');
  });
});

describe('layout.tsx security (XD-SEC-03)', () => {
  let layoutSource: string;

  beforeAll(() => {
    layoutSource = fs.readFileSync(
      path.join(FRONTEND, 'app', 'layout.tsx'),
      'utf-8'
    );
  });

  it('should NOT contain dangerouslySetInnerHTML', () => {
    expect(layoutSource).not.toContain('dangerouslySetInnerHTML');
  });

  it('should use next/script for theme initialization', () => {
    expect(layoutSource).toContain('next/script');
    expect(layoutSource).toContain('theme-init.js');
    expect(layoutSource).toContain('beforeInteractive');
  });
});

describe('theme-init.js (TD-M10)', () => {
  let themeInitSource: string;

  beforeAll(() => {
    themeInitSource = fs.readFileSync(
      path.join(FRONTEND, 'public', 'theme-init.js'),
      'utf-8'
    );
  });

  it('should exist in public directory', () => {
    expect(themeInitSource).toBeTruthy();
  });

  it('should read from localStorage with correct key', () => {
    expect(themeInitSource).toContain('descomplicita-theme');
  });

  it('should set data-theme attribute', () => {
    expect(themeInitSource).toContain('data-theme');
    expect(themeInitSource).toContain('setAttribute');
  });

  it('should add dark class for dark/dim themes', () => {
    expect(themeInitSource).toContain("classList.add('dark')");
  });

  it('should be wrapped in try-catch for safety', () => {
    expect(themeInitSource).toContain('try');
    expect(themeInitSource).toContain('catch');
  });
});
