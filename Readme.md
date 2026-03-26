# 🧠 Neural Text-to-SQL Analytics Engine

A production-grade system combining **Graph Neural Networks (GNN)** and **Groq LLM** to convert natural language queries into optimized SQL.

---

## 🏗️ Architecture

```
User Query → FastAPI Backend → GNN Schema Embedding → Groq LLM → SQL → Neon DB → Frontend Chart
```

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | HTML, CSS, JavaScript | User interface |
| Backend | FastAPI | API & pipeline orchestration |
| Database | Neon PostgreSQL | Cloud database |
| LLM | Groq API (LLaMA3 / Mixtral) | SQL generation & optimization |
| NLP | Sentence Transformers | Query embedding |
| GNN | PyTorch Geometric | Schema understanding |
| Graph | NetworkX | Schema graph construction |
| DB Connector | asyncpg / psycopg2 | Query execution |
| Validation | sqlglot + custom rules | SQL validation |

---

## 📁 Folder Structure

```
neural-text2sql/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI route handlers
│   │   ├── core/         # Config, DB connection
│   │   ├── services/     # GNN, LLM, SQL services
│   │   └── models/       # Pydantic models
│   ├── requirements.txt
│   └── main.py
├── frontend/
│   └── index.html        # Single-page UI
├── notebooks/
│   └── gnn_schema.ipynb  # GNN implementation
├── scripts/
│   ├── setup_db.py       # Create schemas & tables
│   └── generate_data.py  # Synthetic data insertion
├── data/
│   └── schema_metadata.json
└── README.md
```

---

## 🚀 Setup Instructions

### 1. Prerequisites

```bash
python 3.10+
node (optional, for serving frontend)
Neon PostgreSQL account → https://neon.tech
Groq API key → https://console.groq.com
```

### 2. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
# Fill in:
# NEON_DATABASE_URL=postgresql://...
# GROQ_API_KEY=gsk_...
```

### 4. Setup Database

```bash
cd scripts
python setup_db.py
python generate_data.py
```

### 5. Run GNN Notebook

```bash
cd notebooks
jupyter notebook gnn_schema.ipynb
# Run all cells → exports embeddings to data/
```

### 6. Start Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 7. Open Frontend

```bash
# Open frontend/index.html in browser
# Or serve with: python -m http.server 3000 (from frontend/)
```

---

## 💡 Example Queries

- `"Show me total revenue by product category last month"`
- `"Which customers placed more than 5 orders?"`
- `"List top 10 patients by number of visits"`
- `"What's the average transaction amount per bank account?"`

---

## 📊 Schemas Available

| Schema | Tables |
|---|---|
| `ecommerce` | customers, products, orders, order_items, reviews, categories |
| `finance` | accounts, transactions, loans, payments, branches, customers |
| `healthcare` | patients, doctors, appointments, prescriptions, diagnoses, billing |

---

## 🔑 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/query` | Convert NL to SQL and execute |
| GET | `/api/schemas` | List available schemas |
| GET | `/api/history` | Query history |
| GET | `/health` | Health check |