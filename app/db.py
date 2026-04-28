import asyncio
import asyncpg
import os
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL")
pool = None


async def init_pool():
    """Initialize asyncpg connection pool and run migrations."""
    global pool
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)

    # Run migrations first (creates pgvector extension)
    await run_migrations()

    # Register vector type for pgvector support
    async with pool.acquire() as conn:
        await conn.execute("SELECT NULL::vector")


async def close_pool():
    """Close the connection pool."""
    global pool
    if pool:
        await pool.close()


async def run_migrations():
    """Run SQL migrations from app/migrations directory."""
    global pool
    migration_dir = Path(__file__).parent / "migrations"

    for migration_file in sorted(migration_dir.glob("*.sql")):
        async with pool.acquire() as conn:
            sql = migration_file.read_text()
            await conn.execute(sql)
            print(f"✓ Ran migration: {migration_file.name}")


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
