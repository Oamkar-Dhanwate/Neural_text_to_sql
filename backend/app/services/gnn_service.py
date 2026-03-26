"""
GNN Schema Service
Loads pre-computed embeddings from the Jupyter Notebook and
provides table/column relevance scoring for incoming queries.
"""
import json
import os
import logging
import numpy as np
from typing import List, Tuple, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Try importing sentence transformers (optional at runtime)
try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False
    logger.warning("sentence-transformers not available; using keyword fallback")


class GNNSchemaService:
    """
    Wraps GNN schema embeddings produced by the Jupyter notebook.
    Falls back to keyword matching if embeddings aren't available.
    """

    def __init__(self, metadata_path: str, embeddings_path: Optional[str] = None):
        self._metadata = self._load_json(metadata_path)
        self._embeddings: Optional[Dict] = None
        self._st_model: Optional["SentenceTransformer"] = None
        self._ready = False

        # Load GNN package if it exists
        if embeddings_path and os.path.exists(embeddings_path):
            pkg = self._load_json(embeddings_path)
            self._embeddings = pkg.get("schema_embeddings")
            self._table_columns = pkg.get("schema_table_columns", {})
            logger.info("✅ GNN embeddings loaded from %s", embeddings_path)
        else:
            logger.warning("No GNN embeddings found — using keyword fallback")
            self._table_columns = {
                schema: {t: info["columns"] for t, info in data["tables"].items()}
                for schema, data in self._metadata["schemas"].items()
            }

        # Load sentence transformer
        if _ST_AVAILABLE:
            try:
                self._st_model = SentenceTransformer("all-MiniLM-L6-v2")
                self._ready = True
                logger.info("✅ Sentence transformer loaded")
            except Exception as e:
                logger.warning("Could not load sentence transformer: %s", e)

    # ──────────────────────────────────────────
    def get_relevant_tables(
        self,
        query: str,
        schema_name: str,
        top_k: int = 4,
    ) -> List[str]:
        """
        Return the top-k most relevant table names for the given query.
        Uses cosine similarity on GNN embeddings when available,
        else falls back to keyword matching.
        """
        if self._embeddings and self._st_model:
            return self._embedding_search(query, schema_name, top_k)
        return self._keyword_search(query, schema_name, top_k)

    def get_schema_context(self, schema_name: str, relevant_tables: List[str]) -> str:
        """
        Build a condensed schema context string for the LLM prompt.
        Includes table names, columns, and FK relationships.
        """
        schema_data = self._metadata["schemas"].get(schema_name, {})
        tables = schema_data.get("tables", {})
        relationships = schema_data.get("relationships", [])

        lines = [f"Schema: {schema_name}\n"]

        for table_name in relevant_tables:
            if table_name not in tables:
                continue
            info = tables[table_name]
            cols = ", ".join(info["columns"])
            lines.append(f"Table: {table_name}({cols})")
            if "foreign_keys" in info:
                for col, ref in info["foreign_keys"].items():
                    lines.append(f"  FK: {table_name}.{col} → {ref}")

        # Add cross-table relationships
        rel_lines = []
        for rel in relationships:
            if rel["from"] in relevant_tables or rel["to"] in relevant_tables:
                rel_lines.append(f"  {rel['from']} →[{rel['type']}]→ {rel['to']}")
        if rel_lines:
            lines.append("\nRelationships:")
            lines.extend(rel_lines)

        return "\n".join(lines)

    def get_all_tables(self, schema_name: str) -> List[str]:
        schema_data = self._metadata["schemas"].get(schema_name, {})
        return list(schema_data.get("tables", {}).keys())

    def get_available_schemas(self) -> List[Dict]:
        result = []
        for name, data in self._metadata["schemas"].items():
            result.append({
                "name": name,
                "tables": list(data["tables"].keys()),
                "description": data.get("description", ""),
            })
        return result

    @property
    def is_ready(self) -> bool:
        return self._ready or True  # fallback always works

    # ──────────────────────────────────────────  Private

    def _embedding_search(
        self, query: str, schema_name: str, top_k: int
    ) -> List[str]:
        schema_embs = self._embeddings.get(schema_name, {})
        if not schema_embs:
            return self._keyword_search(query, schema_name, top_k)

        query_vec = self._st_model.encode([query])  # (1, dim)

        scores: List[Tuple[str, float]] = []
        for node_name, emb in schema_embs.items():
            # Only table nodes (identified by having exactly schema.table format)
            parts = node_name.split(".")
            if len(parts) != 2:  # columns have 3 parts
                continue
            node_vec = np.array(emb).reshape(1, -1)
            sim = float(
                np.dot(query_vec, node_vec.T)
                / (np.linalg.norm(query_vec) * np.linalg.norm(node_vec) + 1e-9)
            )
            scores.append((parts[1], sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in scores[:top_k]]

    def _keyword_search(
        self, query: str, schema_name: str, top_k: int
    ) -> List[str]:
        """Simple keyword overlap fallback."""
        schema_data = self._metadata["schemas"].get(schema_name, {})
        tables = schema_data.get("tables", {})
        query_tokens = set(query.lower().split())

        scores: List[Tuple[str, int]] = []
        for table_name, info in tables.items():
            table_tokens = set(table_name.lower().replace("_", " ").split())
            col_tokens: set = set()
            for col in info["columns"]:
                col_tokens |= set(col.replace("_", " ").split())
            desc_tokens = set((info.get("description", "")).lower().split())

            score = len(query_tokens & (table_tokens | col_tokens | desc_tokens))
            scores.append((table_name, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        # Always include at least the top table even with 0 score
        selected = [t for t, _ in scores[:top_k]]
        if not selected:
            selected = list(tables.keys())[:top_k]
        return selected

    @staticmethod
    def _load_json(path: str) -> Dict:
        full_path = Path(path)
        if not full_path.exists():
            # Try relative to this file's parent
            alt = Path(__file__).parent.parent.parent / path
            if alt.exists():
                full_path = alt
            else:
                logger.warning("JSON file not found: %s", path)
                return {}
        with open(full_path) as f:
            return json.load(f)