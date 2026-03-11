/**
 * Application version, sourced from package.json via NEXT_PUBLIC_APP_VERSION.
 * Exposed at build time through next.config.js env configuration.
 */
export const APP_VERSION = `v${process.env.NEXT_PUBLIC_APP_VERSION || '3.0.0'}`;
