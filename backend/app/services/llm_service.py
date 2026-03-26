"""
Groq LLM Service
Handles SQL generation, optimization, and natural language explanation
using the Groq API (LLaMA3 / Mixtral).
"""
import logging
import re
from typing import Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential

from groq import Groq
from app.core.config import settings

logger = logging.getLogger(__name__)


SQL_GENERATION_SYSTEM = """You are an expert SQL engineer. Convert natural language questions into precise PostgreSQL queries.

RULES:
1. Write ONLY SELECT statements — never INSERT, UPDATE, DELETE, DROP, CREATE, or ALTER
2. Keep queries simple and readable
3. Use table aliases only when necessary (avoid AS keywords for columns unless renaming)
4. Avoid CTEs (WITH clauses) unless absolutely necessary
5. Limit result sets to 100 rows maximum using LIMIT
6. Use proper PostgreSQL syntax
7. Always qualify ambiguous column names with table name or alias
8. Return ONLY the SQL query with no explanation, no markdown, no backticks
9. Use lowercase for SQL keywords (select, from, where, join, etc.)
10. Prefer INNER JOIN over LEFT JOIN unless nulls are needed

SCHEMA CONTEXT will be provided. Use ONLY the tables and columns shown.
"""

SQL_OPTIMIZATION_SYSTEM = """You are a PostgreSQL query optimization expert.
Review the provided SQL query and return an optimized version.
Improvements may include: better joins, removing redundant subqueries, adding appropriate aggregations.
Return ONLY the optimized SQL query with no explanation.
If the query is already optimal, return it unchanged.
"""

EXPLANATION_SYSTEM = """You are a helpful data analyst.
Given a SQL query and its results, write a 2-3 sentence natural language explanation
of what the query found. Be specific about numbers and insights.
Write for a non-technical business user.
"""


class GroqLLMService:
    def __init__(self):
        self._client = Groq(api_key=settings.groq_api_key)
        self._model = settings.groq_model
        logger.info("✅ Groq client initialized with model: %s", self._model)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def generate_sql(
        self,
        natural_query: str,
        schema_context: str,
        previous_error: Optional[str] = None,
    ) -> str:
        """
        Generate SQL from natural language query using Groq LLM.
        
        Args:
            natural_query: The user's natural language question
            schema_context: Schema description (tables, columns, FKs)
            previous_error: If retrying after an error, pass the error message
        
        Returns:
            Generated SQL string
        """
        user_prompt = f"""Database Schema:
{schema_context}

User Question: {natural_query}"""

        if previous_error:
            user_prompt += f"""

The previous SQL attempt failed with this error:
{previous_error}

Please generate a corrected SQL query that avoids this error."""

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SQL_GENERATION_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,  # Low temperature for deterministic SQL
                max_tokens=500,
            )
            raw = response.choices[0].message.content.strip()
            sql = self._clean_sql(raw)
            logger.info("Generated SQL: %s", sql[:100])
            return sql
        except Exception as e:
            logger.error("Groq generation error: %s", e)
            raise

    def optimize_sql(self, sql: str, schema_context: str) -> Optional[str]:
        """
        Optionally optimize the generated SQL.
        Returns None if optimization fails (use original).
        """
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SQL_OPTIMIZATION_SYSTEM},
                    {"role": "user", "content": f"Schema:\n{schema_context}\n\nSQL to optimize:\n{sql}"},
                ],
                temperature=0.0,
                max_tokens=500,
            )
            raw = response.choices[0].message.content.strip()
            optimized = self._clean_sql(raw)
            return optimized if optimized != sql else None
        except Exception as e:
            logger.warning("SQL optimization failed: %s", e)
            return None

    def explain_results(
        self,
        query: str,
        sql: str,
        columns: list,
        rows: list,
        row_count: int,
    ) -> str:
        """
        Generate a natural language explanation of the query results.
        """
        # Summarize results for the prompt (avoid huge payloads)
        preview_rows = rows[:5]
        result_summary = f"{row_count} rows returned. Columns: {', '.join(columns)}\n"
        if preview_rows:
            result_summary += "Sample data:\n"
            for row in preview_rows:
                result_summary += f"  {dict(row)}\n"

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": EXPLANATION_SYSTEM},
                    {
                        "role": "user",
                        "content": f"Question: {query}\n\nSQL: {sql}\n\nResults:\n{result_summary}",
                    },
                ],
                temperature=0.3,
                max_tokens=200,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning("Explanation generation failed: %s", e)
            return f"Query returned {row_count} results."

    @staticmethod
    def _clean_sql(raw: str) -> str:
        """Remove markdown fences and whitespace from LLM output."""
        # Remove ```sql ... ``` or ``` ... ```
        raw = re.sub(r"```sql\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"```\s*", "", raw)
        # Remove leading/trailing whitespace
        sql = raw.strip()
        # Remove trailing semicolon (we'll add it if needed)
        sql = sql.rstrip(";").strip()
        return sql