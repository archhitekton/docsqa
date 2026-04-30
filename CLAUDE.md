# Credentials Setup

## Required Environment Variables

All credentials stored in `~/.claude/credentials/credentials.env` with `DOCSQA_` prefix:
- `DOCSQA_ANTHROPIC_API_KEY` → `ANTHROPIC_API_KEY` (Claude API key)
- `DOCSQA_VOYAGE_API_KEY` → `VOYAGE_API_KEY` (Voyage AI embeddings)
- `DOCSQA_DATABASE_URL` → `DATABASE_URL` (Supabase pgvector connection string)

## Credential Sourcing Pattern

For bash execution, always source and strip prefix:
```bash
set -a
source ~/.claude/credentials/credentials.env
set +a
# Credentials now available as ANTHROPIC_API_KEY, VOYAGE_API_KEY, DATABASE_URL
```

## Security Gate — MANDATORY

**NEVER log raw credential values in CLI output.** Before committing or reporting:
1. Verify no credential file content logged (mask with `***...***` if referenced)
2. Check bash outputs for API keys, tokens, connection strings
3. Review git diff for secrets before commit
4. Test ingest/query flow logs don't emit credential values

Violations block merge.

