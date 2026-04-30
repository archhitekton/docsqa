import asyncpg
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool = None


async def init_pool():
    """Initialize asyncpg connection pool and run migrations."""
    global _pool

    # Support both DATABASE_URL and DOCSQA_DATABASE_URL (with prefix stripping)
    database_url = os.getenv("DATABASE_URL") or os.getenv("DOCSQA_DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL or DOCSQA_DATABASE_URL environment variable not set")

    logger.info("Initializing database pool...")
    # Supabase uses pgbouncer (transaction pooler) which doesn't support prepared statements
    # Disable statement cache to avoid DuplicatePreparedStatementError
    _pool = await asyncpg.create_pool(database_url, statement_cache_size=0)
    logger.info("Pool created")

    # Run migrations
    await run_migrations()

    # Register vector type for pgvector support
    async with _pool.acquire() as conn:
        await conn.execute("SELECT NULL::vector")
    logger.info("Vector type registered")


async def close_pool():
    """Close the connection pool."""
    global _pool
    if _pool:
        logger.info("Closing database pool...")
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Get the current connection pool."""
    if not _pool:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    return _pool


async def run_migrations():
    """Run all migrations in app/migrations/."""
    migrations_dir = Path(__file__).parent / "migrations"

    if not migrations_dir.exists():
        logger.warning(f"Migrations directory not found: {migrations_dir}")
        return

    async with _pool.acquire() as conn:
        # Get list of migration files
        migration_files = sorted(migrations_dir.glob("*.sql"))

        for migration_file in migration_files:
            logger.info(f"Running migration: {migration_file.name}")
            sql = migration_file.read_text()
            await conn.execute(sql)
            logger.info(f"Migration complete: {migration_file.name}")
