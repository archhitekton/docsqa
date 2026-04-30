import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.db import init_pool, close_pool
from app.routes.query import router as query_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle: startup and shutdown."""
    logger.info("Starting up")
    await init_pool()
    logger.info("App started")
    yield
    logger.info("Shutting down")
    await close_pool()
    logger.info("App stopped")


app = FastAPI(
    title="RAG Q&A Engine",
    description="Document Q&A with streaming answers and source attribution",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(query_router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "model": "voyage-3.5-lite"}
