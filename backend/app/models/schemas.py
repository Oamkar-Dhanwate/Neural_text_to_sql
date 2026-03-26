"""
Pydantic models for request/response schemas.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500, description="Natural language query")
    schema_name: str = Field(default="ecommerce", description="Target database schema")
    explain: bool = Field(default=False, description="Include natural language explanation")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Show me top 10 customers by total order value",
                "schema_name": "ecommerce",
                "explain": True,
            }
        }


class QueryResponse(BaseModel):
    success: bool
    natural_query: str
    generated_sql: str
    optimized_sql: Optional[str] = None
    columns: List[str] = []
    rows: List[Dict[str, Any]] = []
    row_count: int = 0
    execution_time_ms: float = 0
    relevant_tables: List[str] = []
    explanation: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SchemaInfo(BaseModel):
    name: str
    tables: List[str]
    description: str


class SchemasResponse(BaseModel):
    schemas: List[SchemaInfo]


class HistoryItem(BaseModel):
    id: int
    query: str
    sql: str
    schema_name: str
    row_count: int
    timestamp: str
    success: bool


class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    gnn_loaded: bool
    groq_available: bool