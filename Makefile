.PHONY: build run ingest query eval deploy demo help db-up db-down db-logs

help:
	@echo "RAG Q&A Engine - Available targets:"
	@echo ""
	@echo "Database:"
	@echo "  make db-up      - Start local Postgres with pgvector (docker-compose)"
	@echo "  make db-down    - Stop Postgres"
	@echo "  make db-logs    - View Postgres logs"
	@echo ""
	@echo "Development:"
	@echo "  make build      - Build Docker image"
	@echo "  make run        - Run API locally (port 8000)"
	@echo "  make ingest     - Ingest documents from ./docs/"
	@echo "  make query      - Run a query (set Q=\"your question\")"
	@echo "  make eval       - Run evaluation harness"
	@echo "  make demo       - Run a canned demo query"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy     - Deploy to Fly.io"

build:
	docker build -t rag-qa-engine .

run:
	set -a && source ~/.claude/credentials/credentials.env && set +a && \
	export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/postgres" && \
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

ingest:
	set -a && source ~/.claude/credentials/credentials.env && set +a && \
	export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/postgres" && \
	uv run python scripts/ingest.py

query:
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make query Q=\"Your question here\""; \
		exit 1; \
	fi
	@curl -s -N -X POST http://localhost:8000/query \
		-H "Content-Type: application/json" \
		-d '{"question": "$(Q)"}' | grep -v '^: ' | sed 's/^data: //' | \
		awk 'BEGIN {RS="\n"; getline; exit} {if ($$0 != "[DONE]" && $$0 ~ /^\{/) {cmd="jq .sources 2>/dev/null"; print | cmd; close(cmd)} else if ($$0 != "[DONE]") print $$0}'

eval:
	set -a && source ~/.claude/credentials/credentials.env && set +a && \
	export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/postgres" && \
	uv run python scripts/eval.py

demo:
	@$(MAKE) query Q="What is the main purpose of this document?"

deploy:
	fly deploy

db-up:
	docker-compose up -d postgres
	@echo "Postgres started. Waiting for health check..."
	@sleep 3
	docker-compose exec postgres pg_isready -U postgres || (echo "Failed to start"; exit 1)
	@echo "✓ Postgres ready on localhost:5432"

db-down:
	docker-compose down

db-logs:
	docker-compose logs -f postgres
