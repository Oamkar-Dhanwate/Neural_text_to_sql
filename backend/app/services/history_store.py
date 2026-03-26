"""
Simple in-memory query history store.
For production, replace with a persistent DB table.
"""
import time
from typing import List, Dict, Any
from collections import deque


class QueryHistoryStore:
    def __init__(self, max_size: int = 100):
        self._store: deque = deque(maxlen=max_size)
        self._counter = 0

    def add(
        self,
        query: str,
        sql: str,
        schema_name: str,
        row_count: int,
        success: bool,
    ) -> int:
        self._counter += 1
        self._store.appendleft({
            "id": self._counter,
            "query": query,
            "sql": sql,
            "schema_name": schema_name,
            "row_count": row_count,
            "success": success,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        return self._counter

    def get_all(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(self._store)[:limit]


# Singleton
history_store = QueryHistoryStore()