# Migrating to Supabase

When ready to move from local Postgres to production Supabase pgvector:

## 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create new project (pick a region close to your users)
3. Wait for database initialization (~2 min)

## 2. Enable pgvector Extension

In Supabase dashboard:
1. Go to **SQL Editor**
2. Run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

## 3. Get Connection String

In Supabase dashboard:
1. Go to **Project Settings → Database → Connection Strings**
2. Select **Transaction Pooler** (recommended for app connections)
3. Copy the connection string

## 4. Update .env

```bash
# Replace with Supabase connection string
DATABASE_URL="postgresql://postgres:[PASSWORD]@[PROJECT-REF]-pooler.supabase.co:6543/postgres"

# Keep API keys as-is
ANTHROPIC_API_KEY="sk-ant-..."
VOYAGE_API_KEY="pa-..."
```

## 5. Verify Connection

```bash
uv run python scripts/ingest.py --dry-run
```

Should output: `✓ DB connected`

## 6. Ingest Data

```bash
make ingest
```

## 7. Test Queries

```bash
make query Q="Your test question"
```

## Notes

- Transaction Pooler is better for serverless/app deployments
- Session Pooler can be used for persistent connections
- Backup your data: Supabase automatic backups are available in dashboard
- Monitor costs: pgvector IVFFlat indexes consume additional storage
