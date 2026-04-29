import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.db import init_pool, close_pool
from app.routes.query import router as query_router

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


app = FastAPI(title="RAG Q&A Engine", lifespan=lifespan)
app.include_router(query_router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
