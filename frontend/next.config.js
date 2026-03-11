const { withSentryConfig } = require("@sentry/nextjs");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  env: {
    NEXT_PUBLIC_APP_VERSION: require('./package.json').version,
  },
};

module.exports = withSentryConfig(nextConfig, {
  silent: true,
  org: process.env.SENTRY_ORG || "",
  project: process.env.SENTRY_PROJECT || "",
}, {
  widenClientFileUpload: true,
  hideSourceMaps: true,
  disableLogger: true,
});
