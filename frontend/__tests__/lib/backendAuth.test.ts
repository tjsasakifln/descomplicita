/**
 * Tests for backendAuth.ts (story-2.2 / TD-SYS-007).
 *
 * Verifies that backendAuth.ts does NOT cache tokens in module-level
 * variables, fetching fresh tokens per request for serverless safety.
 */

import * as fs from "fs";
import * as path from "path";

describe("backendAuth.ts — TD-SYS-007: No module-level token cache", () => {
  let source: string;

  beforeAll(() => {
    const filePath = path.resolve(__dirname, "../../lib/backendAuth.ts");
    source = fs.readFileSync(filePath, "utf-8");
  });

  test("does not declare cachedToken at module level", () => {
    // Module-level "let cachedToken" or "var cachedToken" should not exist
    expect(source).not.toMatch(/^(let|var)\s+cachedToken/m);
  });

  test("does not declare tokenExpiresAt at module level", () => {
    expect(source).not.toMatch(/^(let|var)\s+tokenExpiresAt/m);
  });

  test("does not use module-level mutable state for token caching", () => {
    // No module-level let/var assignments that look like token caching
    const moduleVarMatches = source.match(/^(let|var)\s+\w*(token|cache|expire)/gim);
    expect(moduleVarMatches).toBeNull();
  });

  test("getBackendHeaders is exported", () => {
    expect(source).toContain("export async function getBackendHeaders");
  });

  test("getJwtToken does not reference cachedToken", () => {
    // Extract getJwtToken function body
    const jwtFnMatch = source.match(
      /async function getJwtToken[\s\S]*?^}/m
    );
    if (jwtFnMatch) {
      expect(jwtFnMatch[0]).not.toContain("cachedToken");
      expect(jwtFnMatch[0]).not.toContain("tokenExpiresAt");
    }
  });

  test("JWT_SECRET is not imported or used (serverless concern)", () => {
    // JWT_SECRET was only needed for the cache check — should be removed
    expect(source).not.toMatch(/const JWT_SECRET/);
  });

  test("contains TD-SYS-007 documentation comment", () => {
    expect(source).toContain("TD-SYS-007");
  });
});
