/**
 * Server-side backend authentication helper (v3-story-2.0).
 *
 * Manages authentication headers for Next.js API routes
 * that proxy requests to the FastAPI backend.
 *
 * Priority:
 * 1. Supabase JWT (from cookie session, forwarded as Bearer token)
 * 2. JWT Bearer token (obtained from /auth/token, cached until expiry)
 * 3. API key fallback (X-API-Key header)
 */

import { cookies } from "next/headers";
import { createServerClient } from "@supabase/ssr";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const API_KEY = process.env.BACKEND_API_KEY || "";
const JWT_SECRET = process.env.JWT_SECRET || "";

let cachedToken: string | null = null;
let tokenExpiresAt = 0;

/**
 * Try to get Supabase access token from the cookie session.
 * Returns null if Supabase is not configured or no session exists.
 */
async function getSupabaseToken(): Promise<string | null> {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseKey) return null;

  try {
    const cookieStore = await cookies();

    const supabase = createServerClient(supabaseUrl, supabaseKey, {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll() {
          // Read-only in this context
        },
      },
    });

    const {
      data: { session },
    } = await supabase.auth.getSession();
    return session?.access_token ?? null;
  } catch {
    return null;
  }
}

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
 * Prefers Supabase token > custom JWT > API key.
 */
export async function getBackendHeaders(): Promise<Record<string, string>> {
  // 1. Try Supabase token first (user-scoped)
  const supabaseToken = await getSupabaseToken();
  if (supabaseToken) {
    return { Authorization: `Bearer ${supabaseToken}` };
  }

  // 2. Try custom JWT
  const token = await getJwtToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }

  // 3. Fallback to API key
  if (API_KEY) {
    return { "X-API-Key": API_KEY };
  }

  return {};
}
