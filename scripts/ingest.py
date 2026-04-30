#!/usr/bin/env python3
"""Ingest documents: convert, chunk, embed, and store in Supabase."""

import asyncio
import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import init_pool, close_pool


async def ingest_documents(dry_run=False):
    """Ingest documents from ./docs/ directory."""
    if dry_run:
        # Verify DATABASE_URL is set without connecting
        database_url = os.getenv("DATABASE_URL") or os.getenv("DOCSQA_DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        print("DB connected")
        return

    await init_pool()

    try:
        # TODO: T3 — Convert, chunk, embed, store logic here
        pass

    finally:
        await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Test DB connection only")
    args = parser.parse_args()

    asyncio.run(ingest_documents(dry_run=args.dry_run))
