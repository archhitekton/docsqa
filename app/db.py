import asyncio
import asyncpg
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
pool = None


async def init_pool():
    """Initialize asyncpg connection pool and run migrations."""
    global pool
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")

    logger.debug("Creating connection pool")
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
    logger.debug("Pool created")

    # Run migrations first (creates pgvector extension)
    await run_migrations()

    # Register vector type for pgvector support
    logger.debug("Registering vector type")
    async with pool.acquire() as conn:
        await conn.execute("SELECT NULL::vector")
    logger.debug("Vector type registered")


async def close_pool():
    """Close the connection pool."""
    global pool
    if pool:
        await pool.close()


async def run_migrations():
    """Run SQL migrations from app/migrations directory."""
    global pool
    migration_dir = Path(__file__).parent / "migrations"

    migration_files = sorted(migration_dir.glob("*.sql"))
    logger.info(f"Running {len(migration_files)} migrations")

    for migration_file in migration_files:
        logger.debug(f"Running migration: {migration_file.name}")
        async with pool.acquire() as conn:
            sql = migration_file.read_text()
            await conn.execute(sql)
        logger.info(f"✓ Ran migration: {migration_file.name}")


async def get_connection():
    """Get a connection from the pool."""
    global pool
    if not pool:
        raise RuntimeError("Pool not initialized. Call init_pool() first.")
    return pool.acquire()


def get_pool():
    """Get the connection pool instance."""
    global pool
    return pool
