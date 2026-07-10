from __future__ import annotations
import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from models.schemas import DbConnection, DbConnectionInput, ConnectionTestResult
from services.duckdb_service import get_connection

router = APIRouter()


class ConnectionCredentials(BaseModel):
    name: Optional[str] = None
    dbType: str
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    connectionString: Optional[str] = None


@router.post("/connections/test-credentials")
async def test_credentials(body: ConnectionCredentials):
    """Test a connection directly from form data (no saved connection needed)."""
    row_dict = {
        "db_type": body.dbType,
        "host": body.host or "localhost",
        "port": body.port or 5432,
        "database": body.database or "postgres",
        "username": body.username or "postgres",
        "password_enc": body.password or "",
    }

    if body.dbType == "duckdb":
        return ConnectionTestResult(success=True, message="DuckDB connection is active").model_dump()

    if body.dbType == "postgresql":
        from services.postgres_service import test_pg_connection
        success, message = test_pg_connection(row_dict)
        return ConnectionTestResult(success=success, message=message).model_dump()

    return ConnectionTestResult(
        success=False, message=f"Unsupported database type: {body.dbType}"
    ).model_dump()




def _row_to_connection(row: dict) -> DbConnection:
    return DbConnection(
        id=row["id"],
        name=row["name"],
        dbType=row["db_type"],
        host=row.get("host"),
        port=row.get("port"),
        database=row.get("database"),
        username=row.get("username"),
        createdAt=row["created_at"],
        isActive=bool(row.get("is_active", True))
    )


@router.get("/connections")
async def list_connections():
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM db_connections ORDER BY created_at DESC"
        ).fetchall()
        if not rows:
            return []
        cols = [d[0] for d in conn.description]
        return [_row_to_connection(dict(zip(cols, r))).model_dump() for r in rows]
    finally:
        conn.close()


@router.post("/connections", status_code=201)
async def create_connection(body: DbConnectionInput):
    conn_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO db_connections (id, name, db_type, host, port, database, username,
               password_enc, connection_string, created_at, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [conn_id, body.name, body.dbType, body.host, body.port,
             body.database, body.username, body.password,
             body.connectionString, created_at, True]
        )
    finally:
        conn.close()

    return DbConnection(
        id=conn_id,
        name=body.name,
        dbType=body.dbType,
        host=body.host,
        port=body.port,
        database=body.database,
        username=body.username,
        createdAt=created_at,
        isActive=True
    ).model_dump()


@router.delete("/connections/{connection_id}", status_code=204)
async def delete_connection(connection_id: str):
    conn = get_connection()
    try:
        result = conn.execute(
            "SELECT id FROM db_connections WHERE id = ?", [connection_id]
        ).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Connection not found")
        conn.execute("DELETE FROM db_connections WHERE id = ?", [connection_id])
    finally:
        conn.close()


@router.post("/connections/{connection_id}/test")
async def test_connection(connection_id: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM db_connections WHERE id = ?", [connection_id]
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Connection not found")
        cols = [d[0] for d in conn.description]
        row_dict = dict(zip(cols, row))
    finally:
        conn.close()

    db_type = row_dict["db_type"]

    if db_type == "duckdb":
        return ConnectionTestResult(success=True, message="DuckDB connection is active").model_dump()

    if db_type == "postgresql":
        from services.postgres_service import test_pg_connection
        success, message = test_pg_connection(row_dict)
        return ConnectionTestResult(success=success, message=message).model_dump()

    return ConnectionTestResult(
        success=False, message=f"Unsupported database type: {db_type}"
    ).model_dump()
