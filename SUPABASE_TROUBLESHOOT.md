# Supabase Connectivity Troubleshooting

## Issue
RAG ingest pipeline fails with DNS resolution error:
```
socket.gaierror: [Errno 8] nodename nor servname provided, or not known
Host: db.rimocswtapssbebwctqr.supabase.co
```

## Context
- Project: docsqa RAG Q&A Engine
- Environment: macOS development
- Credentials: DOCSQA_DATABASE_URL loaded from ~/.claude/credentials/credentials.env
- Connection string format: `postgresql://postgres:***@db.rimocswtapssbebwctqr.supabase.co:5432/postgres`
- Python 3.12, asyncpg 0.31.0

## Questions for Claude Desktop

```
My RAG ingest pipeline can't reach Supabase pgvector instance. 
DNS resolution fails for db.rimocswtapssbebwctqr.supabase.co.

Environment:
- Credentials loaded: ✓ DATABASE_URL=postgresql://postgres:***@db.rimocswtapssbebwctqr.supabase.co:5432/postgres
- Connection string valid: ✓
- Firewall/VPN: [CHECK YOUR NETWORK]
- Network connectivity: [CAN YOU PING THE HOST?]

Steps taken:
1. Verified credentials in ~/.claude/credentials/credentials.env
2. Confirmed DATABASE_URL env var is set
3. asyncpg pool initialization fails at DNS lookup

What should I check?
- Is db.rimocswtapssbebwctqr.supabase.co reachable from this network?
- Should I add a custom DNS resolver or proxy?
- Is there a Supabase IP allowlist I need to configure?
- Should I use a different connection string format (e.g., connection pooler vs direct)?
```

## Workarounds (if DNS unreachable)

### Option 1: Local Postgres (Development)
Use local Docker Postgres for dev/test, keep Supabase for production:
```bash
docker-compose up -d postgres
# Update DATABASE_URL to localhost Postgres
```

### Option 2: Connection Pooling
Try Supabase Transaction Pooler endpoint instead of direct:
```
postgresql://postgres:***@[pooler.db.REGION.supabase.co]:6543/postgres?sslmode=require
```

### Option 3: SSH Tunnel
If firewall blocks direct access:
```bash
ssh -L 5432:db.rimocswtapssbebwctqr.supabase.co:5432 user@bastion
# Then connect to localhost:5432
```

## Status
- Code: ✓ Correct (verified chunking, embedding, schema)
- Database: ✗ Network unreachable (environment issue, not code)
- Next: Resolve network connectivity before proceeding to T4 (API endpoint)
