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
	docker run --env-file .env -p 8000:8000 rag-qa-engine

ingest:
	uv run python scripts/ingest.py

query:
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make query Q=\"Your question here\""; \
		exit 1; \
	fi
	uv run python -c "import asyncio; from scripts.query import main; asyncio.run(main('$(Q)'))"

eval:
	uv run python scripts/eval.py

demo:
	@uv run python -c "import asyncio; from scripts.query import main; asyncio.run(main('What is the main purpose of this system?'))"

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
