"""
FastAPI API Route Handlers
"""
import time
import logging
from fastapi import APIRouter, HTTPException, Depends, Request

from app.models.schemas import (
    QueryRequest, QueryResponse, SchemasResponse, SchemaInfo,
    HistoryItem, HealthResponse
)
from app.core.database import execute_query, get_pool
from app.services.gnn_service import GNNSchemaService
from app.services.llm_service import GroqLLMService
from app.services.validation_service import SQLValidationService
from app.services.history_store import history_store

logger = logging.getLogger(__name__)
router = APIRouter()


def get_gnn_service(request: Request) -> GNNSchemaService:
    return request.app.state.gnn_service


def get_llm_service(request: Request) -> GroqLLMService:
    return request.app.state.llm_service


def get_validator(request: Request) -> SQLValidationService:
    return request.app.state.validator


# ─────────────────────────────────────────────
#  POST /api/query  — Main pipeline endpoint
# ─────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
async def process_query(
    body: QueryRequest,
    gnn: GNNSchemaService = Depends(get_gnn_service),
    llm: GroqLLMService = Depends(get_llm_service),
    validator: SQLValidationService = Depends(get_validator),
):
    start_time = time.time()
    schema_name = body.schema_name.lower()

    # 1. Validate schema exists
    available_schemas = [s["name"] for s in gnn.get_available_schemas()]
    if schema_name not in available_schemas:
        raise HTTPException(status_code=400, detail=f"Unknown schema '{schema_name}'")

    # 2. GNN: find relevant tables
    relevant_tables = gnn.get_relevant_tables(body.query, schema_name, top_k=4)
    all_tables = gnn.get_all_tables(schema_name)

    # 3. Build schema context for LLM
    schema_context = gnn.get_schema_context(schema_name, relevant_tables)

    # 4. Generate SQL (with retry on error)
    generated_sql = llm.generate_sql(body.query, schema_context)

    # 5. Validate SQL
    is_valid, error_msg = validator.validate(generated_sql, all_tables, schema_name)

    # If invalid, retry once with error feedback
    if not is_valid:
        logger.warning("SQL validation failed (%s), retrying…", error_msg)
        generated_sql = llm.generate_sql(body.query, schema_context, previous_error=error_msg)
        is_valid, error_msg = validator.validate(generated_sql, all_tables, schema_name)
        if not is_valid:
            history_store.add(body.query, generated_sql, schema_name, 0, False)
            return QueryResponse(
                success=False,
                natural_query=body.query,
                generated_sql=generated_sql,
                relevant_tables=relevant_tables,
                error=f"SQL validation failed: {error_msg}",
                execution_time_ms=round((time.time() - start_time) * 1000, 1),
            )

    # 6. Optionally optimize
    optimized_sql = llm.optimize_sql(generated_sql, schema_context)
    final_sql = optimized_sql if optimized_sql else generated_sql

    # 7. Execute
    result = await execute_query(final_sql, schema=schema_name)

    if "error" in result and result["error"]:
        # Retry with DB error feedback
        logger.warning("DB execution error: %s — retrying", result["error"])
        regenerated = llm.generate_sql(body.query, schema_context, previous_error=result["error"])
        result = await execute_query(regenerated, schema=schema_name)
        if "error" in result and result["error"]:
            history_store.add(body.query, final_sql, schema_name, 0, False)
            return QueryResponse(
                success=False,
                natural_query=body.query,
                generated_sql=generated_sql,
                relevant_tables=relevant_tables,
                error=result["error"],
                execution_time_ms=round((time.time() - start_time) * 1000, 1),
            )
        final_sql = regenerated

    exec_time = round((time.time() - start_time) * 1000, 1)

    # 8. Optionally explain
    explanation = None
    if body.explain:
        explanation = llm.explain_results(
            body.query, final_sql,
            result.get("columns", []),
            result.get("rows", []),
            result.get("row_count", 0),
        )

    history_store.add(body.query, final_sql, schema_name, result.get("row_count", 0), True)

    return QueryResponse(
        success=True,
        natural_query=body.query,
        generated_sql=generated_sql,
        optimized_sql=optimized_sql,
        columns=result.get("columns", []),
        rows=result.get("rows", []),
        row_count=result.get("row_count", 0),
        execution_time_ms=exec_time,
        relevant_tables=relevant_tables,
        explanation=explanation,
    )


# ─────────────────────────────────────────────
#  GET /api/schemas
# ─────────────────────────────────────────────

@router.get("/schemas", response_model=SchemasResponse)
async def list_schemas(gnn: GNNSchemaService = Depends(get_gnn_service)):
    schemas = [
        SchemaInfo(name=s["name"], tables=s["tables"], description=s["description"])
        for s in gnn.get_available_schemas()
    ]
    return SchemasResponse(schemas=schemas)


# ─────────────────────────────────────────────
#  GET /api/history
# ─────────────────────────────────────────────

@router.get("/history")
async def get_history(limit: int = 20):
    items = history_store.get_all(limit=limit)
    return {"history": items, "count": len(items)}


# ─────────────────────────────────────────────
#  GET /health
# ─────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health_check(
    gnn: GNNSchemaService = Depends(get_gnn_service),
):
    # Check DB connection
    db_ok = False
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        db_connected=db_ok,
        gnn_loaded=gnn.is_ready,
        groq_available=True,
    )