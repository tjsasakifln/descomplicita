/**
 * Structured logging utility for frontend (TD-SYS-017).
 *
 * Generates correlation IDs for cross-stack request tracing.
 * The correlation ID is sent as X-Correlation-Id header in API calls
 * and included in all structured log entries.
 */

import { v4 as uuidv4 } from "uuid";

export type LogLevel = "debug" | "info" | "warn" | "error";

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  correlationId?: string;
  context?: Record<string, unknown>;
}

// Per-session correlation context
let sessionCorrelationId: string = "";

/**
 * Get or create a session-scoped correlation ID.
 */
export function getSessionCorrelationId(): string {
  if (!sessionCorrelationId) {
    sessionCorrelationId = uuidv4();
  }
  return sessionCorrelationId;
}

/**
 * Generate a new correlation ID for a specific request/operation.
 */
export function createCorrelationId(): string {
  return uuidv4();
}

/**
 * Create a structured log entry and output it.
 */
function log(
  level: LogLevel,
  message: string,
  context?: Record<string, unknown>,
  correlationId?: string,
): void {
  const entry: LogEntry = {
    timestamp: new Date().toISOString(),
    level,
    message,
    correlationId: correlationId || getSessionCorrelationId(),
    context,
  };

  // In production, use structured JSON. In development, use readable format.
  if (process.env.NODE_ENV === "production") {
    const output = JSON.stringify(entry);
    switch (level) {
      case "error":
        console.error(output);
        break;
      case "warn":
        console.warn(output);
        break;
      default:
        console.log(output);
    }
  } else {
    const prefix = `[${entry.level.toUpperCase()}] [${entry.correlationId?.slice(0, 8)}]`;
    switch (level) {
      case "error":
        console.error(prefix, message, context || "");
        break;
      case "warn":
        console.warn(prefix, message, context || "");
        break;
      case "debug":
        console.debug(prefix, message, context || "");
        break;
      default:
        console.log(prefix, message, context || "");
    }
  }
}

export const logger = {
  debug: (msg: string, ctx?: Record<string, unknown>, corrId?: string) =>
    log("debug", msg, ctx, corrId),
  info: (msg: string, ctx?: Record<string, unknown>, corrId?: string) =>
    log("info", msg, ctx, corrId),
  warn: (msg: string, ctx?: Record<string, unknown>, corrId?: string) =>
    log("warn", msg, ctx, corrId),
  error: (msg: string, ctx?: Record<string, unknown>, corrId?: string) =>
    log("error", msg, ctx, corrId),
};

/**
 * Create headers with correlation ID for API requests.
 * Use this when making fetch calls to the backend.
 */
export function correlationHeaders(
  correlationId?: string,
): Record<string, string> {
  return {
    "X-Correlation-Id": correlationId || createCorrelationId(),
  };
}
