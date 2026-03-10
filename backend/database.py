"""Persistence layer using Supabase PostgreSQL (v3-story-2.0).

Replaces the SQLite ephemeral storage (TD-H04) with Supabase for:
- Search history (per-user, with RLS)
- User preferences (per-user key-value store)

Design decisions:
- supabase-py client with service role key for backend operations
- user_id required on all mutations (multi-tenant isolation DB-001)
- RLS policies enforce isolation at DB level as defense-in-depth
- Graceful fallback: if Supabase unavailable, operations return empty/None
- SQLite compatibility maintained in method signatures for smooth migration
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


class Database:
    """Supabase PostgreSQL database for search history and preferences."""

    def __init__(
        self,
        supabase_url: str = SUPABASE_URL,
        supabase_key: str = SUPABASE_SERVICE_ROLE_KEY,
    ) -> None:
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self._client = None

    async def connect(self) -> None:
        """Initialize Supabase client."""
        if not self.supabase_url or not self.supabase_key:
            logger.warning(
                "Supabase not configured (SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing). "
                "Database persistence disabled."
            )
            return

        try:
            from supabase import create_client

            self._client = create_client(self.supabase_url, self.supabase_key)
            # Verify connectivity with a simple query
            self._client.table("users").select("id").limit(1).execute()
            logger.info("Supabase connected: %s", self.supabase_url)
        except Exception as e:
            logger.warning("Supabase connection failed (%s), persistence disabled", e)
            self._client = None

    async def close(self) -> None:
        """Close Supabase client (no-op, HTTP client is stateless)."""
        self._client = None
        logger.info("Supabase client released")

    @property
    def is_connected(self) -> bool:
        """Check if database client is available."""
        return self._client is not None

    # --- User Management ---

    async def get_or_create_user(self, user_id: str, email: str = "") -> Optional[dict]:
        """Get existing user or create a new profile entry.

        The auto-trigger on auth.users handles creation on signup,
        but this is a fallback for edge cases.
        """
        if not self._client:
            return None
        try:
            result = self._client.table("users").select("*").eq("id", user_id).execute()
            if result.data:
                return result.data[0]

            # Create user profile if not exists (fallback)
            if email:
                result = self._client.table("users").insert({
                    "id": user_id,
                    "email": email,
                    "display_name": email.split("@")[0],
                }).execute()
                return result.data[0] if result.data else None
            return None
        except Exception as e:
            logger.warning("Failed to get/create user %s: %s", user_id, e)
            return None

    # --- Search History ---

    async def record_search(
        self,
        job_id: str,
        ufs: list[str],
        data_inicial: str,
        data_final: str,
        setor_id: str,
        termos_busca: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """Record a new search job in history."""
        if not self._client:
            return
        if not user_id:
            logger.debug("Skipping record_search: no user_id")
            return
        try:
            self._client.table("search_history").insert({
                "user_id": user_id,
                "job_id": job_id,
                "ufs": ufs,
                "data_inicial": data_inicial,
                "data_final": data_final,
                "setor_id": setor_id,
                "termos_busca": termos_busca,
                "status": "queued",
            }).execute()
        except Exception as e:
            logger.warning("Failed to record search %s: %s", job_id, e)

    async def complete_search(
        self,
        job_id: str,
        total_raw: int,
        total_filtrado: int,
        elapsed_seconds: float,
    ) -> None:
        """Update search history with completion data."""
        if not self._client:
            return
        try:
            self._client.table("search_history").update({
                "status": "completed",
                "total_raw": total_raw,
                "total_filtrado": total_filtrado,
                "elapsed_seconds": round(elapsed_seconds, 2),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("job_id", job_id).execute()
        except Exception as e:
            logger.warning("Failed to complete search %s: %s", job_id, e)

    async def fail_search(self, job_id: str) -> None:
        """Mark a search as failed in history."""
        if not self._client:
            return
        try:
            self._client.table("search_history").update({
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("job_id", job_id).execute()
        except Exception as e:
            logger.warning("Failed to mark search %s as failed: %s", job_id, e)

    async def get_recent_searches(
        self,
        limit: int = 20,
        user_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Get recent search history for a specific user."""
        if not self._client:
            return []
        if not user_id:
            return []
        try:
            result = (
                self._client.table("search_history")
                .select(
                    "job_id, ufs, data_inicial, data_final, setor_id, "
                    "termos_busca, total_raw, total_filtrado, status, "
                    "created_at, elapsed_seconds"
                )
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.warning("Failed to get recent searches: %s", e)
            return []

    # --- User Preferences ---

    async def set_preference(
        self,
        key: str,
        value: Any,
        user_id: Optional[str] = None,
    ) -> None:
        """Set a user preference (upsert)."""
        if not self._client or not user_id:
            return
        try:
            self._client.table("user_preferences").upsert({
                "user_id": user_id,
                "key": key,
                "value": json.dumps(value) if not isinstance(value, (dict, list)) else value,
            }, on_conflict="user_id,key").execute()
        except Exception as e:
            logger.warning("Failed to set preference %s: %s", key, e)

    async def get_preference(
        self,
        key: str,
        user_id: Optional[str] = None,
    ) -> Optional[Any]:
        """Get a user preference by key."""
        if not self._client or not user_id:
            return None
        try:
            result = (
                self._client.table("user_preferences")
                .select("value")
                .eq("user_id", user_id)
                .eq("key", key)
                .execute()
            )
            if result.data:
                val = result.data[0]["value"]
                return json.loads(val) if isinstance(val, str) else val
            return None
        except Exception as e:
            logger.warning("Failed to get preference %s: %s", key, e)
            return None

    async def get_all_preferences(
        self,
        user_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get all user preferences as a dict."""
        if not self._client or not user_id:
            return {}
        try:
            result = (
                self._client.table("user_preferences")
                .select("key, value")
                .eq("user_id", user_id)
                .execute()
            )
            prefs = {}
            for row in result.data or []:
                val = row["value"]
                prefs[row["key"]] = json.loads(val) if isinstance(val, str) else val
            return prefs
        except Exception as e:
            logger.warning("Failed to get all preferences: %s", e)
            return {}
