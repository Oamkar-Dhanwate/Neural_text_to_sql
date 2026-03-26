neural-text2sql/
├── frontend/index.html          ← Full UI (dark theme, Chart.js, SQL highlighting)
├── backend/
│   ├── main.py                  ← FastAPI app with lifespan management
│   ├── app/api/routes.py        ← POST /query, GET /schemas, /history, /health
│   ├── app/core/config.py       ← Pydantic settings + .env loading
│   ├── app/core/database.py     ← asyncpg pool, safe SELECT execution
│   ├── app/models/schemas.py    ← Request/Response Pydantic models
│   └── app/services/
│       ├── gnn_service.py       ← GNN embedding loader + table relevance
│       ├── llm_service.py       ← Groq API: generate, optimize, explain
│       ├── validation_service.py← sqlglot + custom SQL safety rules
│       └── history_store.py     ← In-memory query history
├── scripts/
│   ├── setup_db.py              ← Creates 3 schemas, 18 tables, all FKs
│   └── generate_data.py         ← Faker: 500-3000 rows per table
├── notebooks/gnn_schema.ipynb   ← GraphSAGE + NetworkX + embeddings export
└── data/schema_metadata.json    ← Full schema definitions (3 schemas)