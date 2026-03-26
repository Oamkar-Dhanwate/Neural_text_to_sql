"""
SQL Validation Service
Uses sqlglot + custom rules to validate generated SQL before execution.
"""
import re
import logging
from typing import Tuple, List

try:
    import sqlglot
    import sqlglot.errors
    _SQLGLOT_AVAILABLE = True
except ImportError:
    _SQLGLOT_AVAILABLE = False

logger = logging.getLogger(__name__)

# Disallowed SQL keywords (DML/DDL that could modify data)
DISALLOWED_PATTERNS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bCREATE\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"--",           # SQL comment injection
    r";.*SELECT",    # stacked queries
]


class SQLValidationService:

    def validate(
        self,
        sql: str,
        allowed_tables: List[str],
        schema_name: str,
    ) -> Tuple[bool, str]:
        """
        Validate SQL for safety and correctness.
        
        Returns:
            (is_valid: bool, error_message: str)
        """
        if not sql or not sql.strip():
            return False, "Empty SQL query"

        sql_upper = sql.strip().upper()

        # Rule 1: Must start with SELECT
        if not sql_upper.lstrip().startswith("SELECT"):
            return False, "Only SELECT queries are allowed"

        # Rule 2: Check for disallowed patterns
        for pattern in DISALLOWED_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                return False, f"Disallowed SQL pattern detected: {pattern}"

        # Rule 3: Parse with sqlglot for syntax validation
        if _SQLGLOT_AVAILABLE:
            try:
                parsed = sqlglot.parse_one(sql, dialect="postgres")
                if parsed is None:
                    return False, "Failed to parse SQL"
            except sqlglot.errors.ParseError as e:
                return False, f"SQL syntax error: {str(e)[:200]}"
            except Exception as e:
                logger.warning("sqlglot error: %s", e)
                # Don't fail on sqlglot bugs — fall through

        # Rule 4: Validate tables referenced in SQL
        if allowed_tables:
            referenced_tables = self._extract_table_names(sql)
            for table in referenced_tables:
                if table.lower() not in [t.lower() for t in allowed_tables]:
                    # Table might be schema-qualified (e.g., ecommerce.orders)
                    unqualified = table.split(".")[-1].lower()
                    if unqualified not in [t.lower() for t in allowed_tables]:
                        return (
                            False,
                            f"Table '{table}' not found in schema '{schema_name}'. "
                            f"Available: {', '.join(allowed_tables)}"
                        )

        return True, ""

    @staticmethod
    def _extract_table_names(sql: str) -> List[str]:
        """
        Extract table names from SQL using regex.
        Handles: FROM table, JOIN table, FROM schema.table patterns.
        """
        tables = []

        # Match FROM and JOIN clauses
        patterns = [
            r"\bFROM\s+([a-zA-Z_][a-zA-Z0-9_.]*)",
            r"\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_.]*)",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            for m in matches:
                # Remove alias: "orders o" → "orders"
                table = m.strip().split()[0]
                # Strip parentheses
                table = table.strip("()")
                if table and not table.upper() in ("SELECT", "WHERE", "ON"):
                    tables.append(table)

        return list(set(tables))