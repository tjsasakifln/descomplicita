/**
 * Server-side backend authentication helper (TD-C02/XD-SEC-02).
 *
 * Manages JWT token acquisition and caching for Next.js API routes
 * that proxy requests to the FastAPI backend.
 *
 * Priority:
 * 1. JWT Bearer token (obtained from /auth/token, cached until expiry)
 * 2. API key fallback (X-API-Key header)
 */

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const API_KEY = process.env.BACKEND_API_KEY || "";
const JWT_SECRET = process.env.JWT_SECRET || "";

let cachedToken: string | null = null;
let tokenExpiresAt = 0;

/**
 * Get a JWT token from the backend, with caching.
 * Returns null if JWT is not configured.
 */
async function getJwtToken(): Promise<string | null> {
  if (!JWT_SECRET && !API_KEY) return null;

  // Return cached token if still valid (with 5min buffer)
  if (cachedToken && Date.now() / 1000 < tokenExpiresAt - 300) {
    return cachedToken;
  }

  if (!API_KEY) return null;

  try {
    const response = await fetch(`${BACKEND_URL}/auth/token`, {
      method: "POST",
      headers: {
        "X-API-Key": API_KEY,
      },
    });

    if (!response.ok) {
      console.warn(`JWT token request failed: ${response.status}`);
      return null;
    }

    const data = await response.json();
    cachedToken = data.access_token;
    tokenExpiresAt = Date.now() / 1000 + (data.expires_in || 86400);
    return cachedToken;
  } catch (error) {
    console.warn("Failed to obtain JWT token:", error);
    return null;
  }
}

/**
 * Get authentication headers for backend requests.
 * Prefers JWT Bearer token, falls back to API key.
 */
export async function getBackendHeaders(): Promise<Record<string, string>> {
  // Try JWT first
  const token = await getJwtToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }

  // Fallback to API key
  if (API_KEY) {
    return { "X-API-Key": API_KEY };
  }

  return {};
}
