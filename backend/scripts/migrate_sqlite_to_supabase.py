"""One-time migration script: SQLite → Supabase PostgreSQL (v3-story-2.0 / Task 7).

Migrates existing search_history and user_preferences from the local SQLite
database to Supabase PostgreSQL. Since the old schema has no user_id,
migrated records are assigned to a designated "legacy" user account.

Usage:
    # Set environment variables first:
    # SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, LEGACY_USER_EMAIL
    python scripts/migrate_sqlite_to_supabase.py [--sqlite-path path/to/descomplicita.db]

Prerequisites:
    - Supabase project created with migrations applied (001_initial_schema.sql)
    - A legacy user account created in Supabase Auth
    - pip install supabase aiosqlite

NOTE: aiosqlite is no longer in requirements.txt (removed in story-0.2 TD-SYS-001).
      Install it manually if you need to re-run this one-time migration script.
"""

import argparse
import asyncio
import json
import logging
import os
import sys

import aiosqlite

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Default SQLite path
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "descomplicita.db")


async def read_sqlite_data(db_path: str) -> dict:
    """Read all data from SQLite database."""
    data = {"search_history": [], "user_preferences": []}

    if not os.path.exists(db_path):
        logger.warning("SQLite database not found at %s", db_path)
        return data

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        # Read search history
        cursor = await db.execute("SELECT * FROM search_history ORDER BY created_at")
        rows = await cursor.fetchall()
        for row in rows:
            data["search_history"].append({
                "job_id": row["job_id"],
                "ufs": json.loads(row["ufs"]),
                "data_inicial": row["data_inicial"],
                "data_final": row["data_final"],
                "setor_id": row["setor_id"],
                "termos_busca": row["termos_busca"],
                "total_raw": row["total_raw"],
                "total_filtrado": row["total_filtrado"],
                "status": row["status"],
                "created_at": row["created_at"],
                "completed_at": row["completed_at"],
                "elapsed_seconds": row["elapsed_seconds"],
            })

        # Read user preferences
        cursor = await db.execute("SELECT * FROM user_preferences")
        rows = await cursor.fetchall()
        for row in rows:
            data["user_preferences"].append({
                "key": row["key"],
                "value": row["value"],
            })

    logger.info(
        "Read %d search_history rows and %d user_preferences rows from SQLite",
        len(data["search_history"]),
        len(data["user_preferences"]),
    )
    return data


def migrate_to_supabase(data: dict, legacy_user_id: str) -> dict:
    """Migrate data to Supabase using the service role key."""
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    client = create_client(supabase_url, supabase_key)

    results = {"search_history": 0, "user_preferences": 0, "errors": []}

    # Migrate search history
    for record in data["search_history"]:
        try:
            client.table("search_history").upsert({
                "user_id": legacy_user_id,
                "job_id": record["job_id"],
                "ufs": record["ufs"],
                "data_inicial": record["data_inicial"],
                "data_final": record["data_final"],
                "setor_id": record["setor_id"],
                "termos_busca": record["termos_busca"],
                "total_raw": record["total_raw"] or 0,
                "total_filtrado": record["total_filtrado"] or 0,
                "status": record["status"] or "completed",
                "created_at": record["created_at"],
                "completed_at": record["completed_at"],
                "elapsed_seconds": record["elapsed_seconds"],
            }, on_conflict="job_id").execute()
            results["search_history"] += 1
        except Exception as e:
            results["errors"].append(f"search_history {record['job_id']}: {e}")

    # Migrate user preferences
    for pref in data["user_preferences"]:
        try:
            value = pref["value"]
            # Try to parse as JSON, keep as-is if already valid
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass

            client.table("user_preferences").upsert({
                "user_id": legacy_user_id,
                "key": pref["key"],
                "value": value,
            }, on_conflict="user_id,key").execute()
            results["user_preferences"] += 1
        except Exception as e:
            results["errors"].append(f"user_preferences {pref['key']}: {e}")

    return results


def get_or_create_legacy_user() -> str:
    """Get or create the legacy migration user in Supabase."""
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    legacy_email = os.environ.get("LEGACY_USER_EMAIL", "legacy@descomplicita.app")

    client = create_client(supabase_url, supabase_key)

    # Check if user exists
    result = client.table("users").select("id").eq("email", legacy_email).execute()
    if result.data:
        logger.info("Found existing legacy user: %s", result.data[0]["id"])
        return result.data[0]["id"]

    # Create user via admin API
    result = client.auth.admin.create_user({
        "email": legacy_email,
        "password": os.environ.get("LEGACY_USER_PASSWORD", "migration-temp-password-change-me"),
        "email_confirm": True,
        "user_metadata": {"display_name": "Legacy Migration User"},
    })

    user_id = str(result.user.id)
    logger.info("Created legacy user: %s (%s)", user_id, legacy_email)
    return user_id


async def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite data to Supabase")
    parser.add_argument(
        "--sqlite-path",
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite database (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read SQLite and show what would be migrated without writing",
    )
    args = parser.parse_args()

    # Validate environment
    for var in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        if not os.environ.get(var):
            logger.error("Missing required environment variable: %s", var)
            sys.exit(1)

    # Read source data
    data = await read_sqlite_data(args.sqlite_path)

    if not data["search_history"] and not data["user_preferences"]:
        logger.info("No data to migrate. Exiting.")
        return

    if args.dry_run:
        logger.info("DRY RUN — would migrate:")
        logger.info("  search_history: %d records", len(data["search_history"]))
        logger.info("  user_preferences: %d records", len(data["user_preferences"]))
        return

    # Get or create legacy user
    legacy_user_id = get_or_create_legacy_user()

    # Migrate
    results = migrate_to_supabase(data, legacy_user_id)

    logger.info("Migration complete:")
    logger.info("  search_history: %d/%d migrated", results["search_history"], len(data["search_history"]))
    logger.info("  user_preferences: %d/%d migrated", results["user_preferences"], len(data["user_preferences"]))

    if results["errors"]:
        logger.warning("  Errors (%d):", len(results["errors"]))
        for err in results["errors"]:
            logger.warning("    - %s", err)


if __name__ == "__main__":
    asyncio.run(main())
