.PHONY: help build seed run ingest query eval demo deploy

help:
	@echo "RAG Q&A Engine - Available targets:"
	@echo ""
	@echo "Setup:"
	@echo "  make build      - Build Docker image"
	@echo "  make seed       - Download corpus PDFs into ./docs/"
	@echo ""
	@echo "Development:"
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

seed:
	python scripts/seed.py
	@echo "Corpus ready in ./docs/ — run 'make ingest' next"

run:
	@set -a && source ~/.claude/credentials/credentials.env && set +a && \
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

ingest:
	@set -a && source ~/.claude/credentials/credentials.env && set +a && \
	python scripts/ingest.py

query:
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make query Q=\"Your question here\""; \
		exit 1; \
	fi
	@set -a && source ~/.claude/credentials/credentials.env && set +a && \
	curl -s -N -X POST http://localhost:8000/query \
		-H "Content-Type: application/json" \
		-d '{"question": "$(Q)"}'

eval:
	@set -a && source ~/.claude/credentials/credentials.env && set +a && \
	python scripts/eval.py

demo:
	@$(MAKE) query Q="What is a recursive function?"

deploy:
	fly deploy
