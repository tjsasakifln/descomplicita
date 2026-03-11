/**
 * Server-side backend authentication helper (v3-story-2.0, story-2.2).
 *
 * Manages authentication headers for Next.js API routes
 * that proxy requests to the FastAPI backend.
 *
 * Priority:
 * 1. Supabase JWT (from cookie session, forwarded as Bearer token)
 * 2. JWT Bearer token (obtained from /auth/token — fetched fresh each request)
 * 3. API key fallback (X-API-Key header)
 *
 * TD-SYS-007 (story-2.2): Removed module-level token cache. In serverless
 * environments (Vercel), module-level state can persist across independent
 * requests, causing token leakage between users or stale tokens.
 * Token is now fetched fresh via Supabase session or /auth/token per request.
 */

import { cookies } from "next/headers";
import { createServerClient } from "@supabase/ssr";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const API_KEY = process.env.BACKEND_API_KEY || "";

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
 * Get a JWT token from the backend (no caching — fresh per request).
 * Returns null if JWT is not configured.
 *
 * TD-SYS-007: Previously cached in module-level variables which is unsafe
 * in serverless environments. Now fetches fresh on every call.
 */
async function getJwtToken(): Promise<string | null> {
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
    return data.access_token ?? null;
  } catch (error) {
    console.warn("Failed to obtain JWT token:", error);
    return null;
  }
}

/**
 * Get authentication headers for backend requests.
 * Prefers Supabase token > custom JWT > API key.
 *
 * Each call fetches a fresh token — no module-level state.
 */
export async function getBackendHeaders(): Promise<Record<string, string>> {
  // 1. Try Supabase token first (user-scoped)
  const supabaseToken = await getSupabaseToken();
  if (supabaseToken) {
    return { Authorization: `Bearer ${supabaseToken}` };
  }

  // 2. Try custom JWT (fresh per request)
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
