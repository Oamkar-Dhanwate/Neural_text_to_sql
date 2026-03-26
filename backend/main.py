"""
Neural Text-to-SQL Analytics Engine
FastAPI Application Entrypoint

Start with: uvicorn main:app --reload --port 8000
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import get_pool, close_pool
from app.api.routes import router
from app.services.gnn_service import GNNSchemaService
from app.services.llm_service import GroqLLMService
from app.services.validation_service import SQLValidationService

logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  Application Lifespan
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Neural Text-to-SQL Engine...")

    # Init services
    metadata_path = os.path.join(os.path.dirname(__file__), "..", "data", "schema_metadata.json")
    embeddings_path = os.path.join(os.path.dirname(__file__), "..", "data", "gnn_package.json")

    app.state.gnn_service = GNNSchemaService(
        metadata_path=metadata_path,
        embeddings_path=embeddings_path if os.path.exists(embeddings_path) else None,
    )
    app.state.llm_service = GroqLLMService()
    app.state.validator = SQLValidationService()

    # Init DB pool (non-fatal if DB is not configured yet)
    try:
        await get_pool()
        logger.info("✅ Database pool ready")
    except Exception as e:
        logger.warning("⚠️  Database not available: %s", e)

    logger.info("✅ All services initialized")
    yield

    # Cleanup
    await close_pool()
    logger.info("👋 Shutdown complete")


# ─────────────────────────────────────────────
#  FastAPI App
# ─────────────────────────────────────────────

app = FastAPI(
    title="Neural Text-to-SQL Analytics Engine",
    description="Convert natural language to SQL using GNN + Groq LLM",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router, prefix="/api")

# Serve frontend static files (if available)
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_dir, "index.html"))
else:
    @app.get("/")
    async def root():
        return {
            "message": "Neural Text-to-SQL Engine is running 🚀",
            "docs": "/docs",
            "api": "/api",
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)