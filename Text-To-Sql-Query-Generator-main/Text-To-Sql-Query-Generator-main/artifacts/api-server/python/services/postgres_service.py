from __future__ import annotations
import time
from typing import Any

import psycopg2
import psycopg2.extras


def _build_dsn(row_dict: dict) -> str:
    """Build a psycopg2 DSN from a db_connections row dict."""
    host = row_dict.get("host") or "localhost"
    port = row_dict.get("port") or 5432
    dbname = row_dict.get("database") or "postgres"
    user = row_dict.get("username") or "postgres"
    password = row_dict.get("password_enc") or ""
    return f"host={host} port={port} dbname={dbname} user={user} password={password} connect_timeout=5"


def test_pg_connection(row_dict: dict) -> tuple[bool, str]:
    """
    Actually connect to PostgreSQL and return (success, message).
    """
    try:
        dsn = _build_dsn(row_dict)
        con = psycopg2.connect(dsn)
        cur = con.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        cur.close()
        con.close()
        return True, f"Connected! Server: {version[:60]}"
    except Exception as exc:
        return False, str(exc)


def get_pg_schema(row_dict: dict, schema: str = "public") -> str:
    """
    Fetch table + column information from the PostgreSQL database and return
    a human‑readable schema string the AI prompt can understand.
    """
    try:
        dsn = _build_dsn(row_dict)
        con = psycopg2.connect(dsn)
        cur = con.cursor()

        # List tables in the given schema
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """,
            (schema,),
        )
        tables = [r[0] for r in cur.fetchall()]

        parts: list[str] = []
        for tbl in tables:
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """,
                (schema, tbl),
            )
            cols = cur.fetchall()
            col_defs = ", ".join(
                f"{c[0]} {c[1]}{'?' if c[2] == 'YES' else ''}" for c in cols
            )
            parts.append(f"Table {tbl}: ({col_defs})")

        cur.close()
        con.close()
        return "\n".join(parts) if parts else f"No tables found in schema '{schema}'"
    except Exception as exc:
        return f"Could not retrieve schema: {exc}"


def execute_pg_query(row_dict: dict, sql: str) -> tuple[list[str], list[dict[str, Any]], float]:
    """
    Execute a SQL query against PostgreSQL and return (columns, rows, elapsed_ms).
    """
    dsn = _build_dsn(row_dict)
    con = psycopg2.connect(dsn)
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    t0 = time.perf_counter()
    cur.execute(sql)
    rows_raw = cur.fetchall() if cur.description else []
    elapsed_ms = (time.perf_counter() - t0) * 1000

    columns: list[str] = [desc.name for desc in cur.description] if cur.description else []
    
    rows: list[dict[str, Any]] = []
    for r in rows_raw:
        row_map = {}
        for col in columns:
            val = r[col]
            if hasattr(val, 'isoformat'):
                row_map[col] = val.isoformat()
            else:
                row_map[col] = val
        rows.append(row_map)

    cur.close()
    con.close()
    return columns, rows, elapsed_ms
