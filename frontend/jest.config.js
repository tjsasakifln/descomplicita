/**
 * Jest configuration for Descomplicita Frontend
 *
 * This configuration is ready for Next.js 14+ with TypeScript.
 * Install required dependencies:
 *   npm install --save-dev jest @testing-library/react @testing-library/jest-dom
 *   npm install --save-dev @testing-library/user-event jest-environment-jsdom
 */

const nextJest = require('next/jest')

// Provide the path to your Next.js app to load next.config.js and .env files in your test environment
const createJestConfig = nextJest({
  // Path to Next.js app to load next.config.js and .env files
  dir: './',
})

/** @type {import('jest').Config} */
const customJestConfig = {
  // Test environment
  testEnvironment: 'jest-environment-jsdom',

  // Setup files to run after Jest is initialized
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],

  // Module paths
  moduleDirectories: ['node_modules', '<rootDir>/'],

  // Path aliases (sync with tsconfig.json paths)
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
    '^@sentry/nextjs$': '<rootDir>/__mocks__/@sentry/nextjs.js',
  },

  // Test file patterns
  testMatch: [
    '**/__tests__/**/*.[jt]s?(x)',
    '**/?(*.)+(spec|test).[jt]s?(x)'
  ],

  // Coverage configuration
  collectCoverageFrom: [
    'app/**/*.{js,jsx,ts,tsx}',
    'lib/**/*.{js,jsx,ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
    '!**/.next/**',
    '!**/coverage/**',
    '!**/jest.config.js',
  ],

  // Coverage thresholds (story-3.1: branches raised to 65%)
  // Progress: 52.74% → 68.95% branches (+16.21% from story-3.1)
  coverageThreshold: {
    global: {
      branches: 65,    // Current: 68.95%
      functions: 65,    // Current: 69.25%
      lines: 65,        // Current: 67.24%
      statements: 65,   // Current: 66.84%
    },
  },

  // Coverage reporters
  coverageReporters: ['text', 'html', 'lcov'],

  // Ignore patterns
  testPathIgnorePatterns: [
    '/node_modules/',
    '/.next/',
    '/__tests__/e2e/', // E2E tests run via Playwright, not Jest
    '/mswHandlers\\.ts$', // MSW handler fixtures — imported by tests, not run directly
  ],

  // transformIgnorePatterns is patched after next/jest generates the final config
  // (see export section below). The raw pattern here is a fallback for the non-Next
  // code path only.
  transformIgnorePatterns: [
    'node_modules/(?!(uuid|msw|until-async|@bundled-es-modules|is-node-process|outvariant|headers-polyfill|strict-event-emitter|@open-draft)/)',
  ],

  // Transform files
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['@swc/jest', {
      jsc: {
        parser: {
          syntax: 'typescript',
          tsx: true,
        },
        transform: {
          react: {
            runtime: 'automatic',
          },
        },
      },
    }],
  },

  // Module file extensions
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx'],

  // Verbose output
  verbose: true,

  // Clear mocks between tests
  clearMocks: true,

  // Reset mocks between tests
  resetMocks: true,

  // Restore mocks between tests
  restoreMocks: true,
}

// ESM-only packages that must be transformed by @swc/jest.
// next/jest generates its own transformIgnorePatterns (based on the "geist" font),
// so we patch them after generation rather than replacing them outright.
const ESM_PACKAGES = [
  'uuid',
  'msw',
  'until-async',
  '@bundled-es-modules',
  'is-node-process',
  'outvariant',
  'headers-polyfill',
  'strict-event-emitter',
  '@open-draft',
].join('|')

/**
 * Inject ESM package names into every pattern that next/jest produces so that
 * those packages are transformed instead of excluded.
 */
function patchTransformIgnore(config) {
  config.transformIgnorePatterns = (config.transformIgnorePatterns ?? []).map((p) => {
    // next/jest patterns look like: /node_modules/(?!.pnpm)(?!(geist)/)
    // and: /node_modules/.pnpm/(?!(geist)@)
    // We append ESM_PACKAGES into the existing exclusion group.
    if (typeof p === 'string' && p.includes('node_modules') && p.includes('geist')) {
      return p
        .replace('(geist)', `(geist|${ESM_PACKAGES})`)
    }
    return p
  })
  return config
}

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config
// which is async. If Next.js is not yet installed, this will gracefully fallback.
try {
  const baseConfigFn = createJestConfig(customJestConfig)
  // Wrap the async config function to patch transformIgnorePatterns after next/jest resolves.
  module.exports = async () => patchTransformIgnore(await baseConfigFn())
} catch (error) {
  // Fallback for when Next.js is not installed yet (Issue #21 not completed)
  console.warn('⚠️  Next.js not found. Using fallback Jest config.')
  console.warn('   Run `npm install next react react-dom` when setting up Next.js.')
  module.exports = customJestConfig
}
