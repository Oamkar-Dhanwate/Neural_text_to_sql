"""
Async database connection pool using asyncpg.
"""
import asyncpg
import logging
from typing import Optional, List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        try:
            _pool = await asyncpg.create_pool(
                dsn=settings.neon_database_url,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
            logger.info("✅ Database connection pool created")
        except Exception as e:
            logger.error(f"❌ Failed to create DB pool: {e}")
            raise
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


async def execute_query(
    sql: str,
    schema: str = "ecommerce",
    params: Optional[List] = None,
) -> Dict[str, Any]:
    """
    Execute a SELECT query and return rows as list of dicts.
    Enforces SELECT-only and row limit.
    """
    sql_upper = sql.strip().upper()

    # Safety: only SELECT allowed
    if not sql_upper.startswith("SELECT"):
        return {"error": "Only SELECT queries are permitted.", "rows": [], "columns": []}

    # Limit rows to prevent huge responses
    if "LIMIT" not in sql_upper:
        sql = sql.rstrip(";") + " LIMIT 500"

    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            # Set search path to requested schema
            await conn.execute(f"SET search_path TO {schema}, public")
            rows = await conn.fetch(sql, *(params or []))
            if not rows:
                return {"rows": [], "columns": [], "row_count": 0}

            columns = list(rows[0].keys())
            data = [dict(row) for row in rows]
            # Convert non-serializable types
            for row in data:
                for k, v in row.items():
                    if hasattr(v, "isoformat"):
                        row[k] = v.isoformat()
                    elif not isinstance(v, (str, int, float, bool, type(None))):
                        row[k] = str(v)

            return {
                "rows": data,
                "columns": columns,
                "row_count": len(data),
            }
    except Exception as e:
        logger.error(f"Query execution error: {e}")
        return {"error": str(e), "rows": [], "columns": [], "row_count": 0}