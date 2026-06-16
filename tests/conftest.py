"""
Fixtures compartidas para toda la suite de tests.
La fixture `db_conn` salta automáticamente si no hay credenciales de Aurora.
"""
import os
import pytest
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


@pytest.fixture(scope="session")
def db_conn():
    """Conexión a Aurora reutilizada en toda la sesión de tests."""
    host = os.getenv("AURORA_HOST")
    if not host:
        pytest.skip("AURORA_HOST no configurado — tests de integración omitidos")

    conn = psycopg2.connect(
        host=host,
        port=int(os.getenv("AURORA_PORT", "5432")),
        dbname=os.getenv("AURORA_DATABASE", "postgres"),
        user=os.getenv("AURORA_USERNAME"),
        password=os.getenv("AURORA_PASSWORD"),
        sslmode="require",
        connect_timeout=10,
    )
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def cursor(db_conn):
    """Cursor reutilizable para queries de solo lectura."""
    with db_conn.cursor() as cur:
        yield cur
