"""
Conecta a Aurora PostgreSQL y ejecuta los scripts SQL de la Fase 2
en orden: extensión → tablas staging → carga S3 → verificación.
"""
from pathlib import Path

import psycopg2
from psycopg2.extensions import connection as PgConnection

from scripts.utils.logger import get_logger

logger = get_logger(__name__)

SQL_DIR = Path(__file__).resolve().parents[2] / "sql" / "phase2_aurora_ingestion"

SQL_SCRIPTS = [
    "01_enable_extension.sql",
    "02_create_staging_tables.sql",
    "03_load_from_s3.sql",
    "04_verify_counts.sql",
]


def get_connection(cfg) -> PgConnection:
    """Abre conexión SSL a Aurora PostgreSQL."""
    logger.info(f"Conectando a Aurora: {cfg.aurora.host}:{cfg.aurora.port}")
    conn = psycopg2.connect(
        host=cfg.aurora.host,
        port=cfg.aurora.port,
        dbname=cfg.aurora.database,
        user=cfg.aurora.username,
        password=cfg.aurora.password,
        sslmode="require",
        connect_timeout=10,
    )
    conn.autocommit = False
    logger.info("Conexión a Aurora establecida.")
    return conn


def run_sql_file(conn: PgConnection, sql_path: Path, params: dict) -> None:
    """Lee un archivo SQL, reemplaza parámetros y lo ejecuta."""
    raw_sql = sql_path.read_text(encoding="utf-8")
    sql = raw_sql.format(**params)

    logger.info(f"Ejecutando: {sql_path.name}")
    with conn.cursor() as cur:
        cur.execute(sql)
        if cur.description:
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            logger.info(f"Resultado de {sql_path.name}:")
            logger.info(f"  {cols}")
            for row in rows:
                logger.info(f"  {row}")
    conn.commit()
    logger.info(f"{sql_path.name} ejecutado correctamente.")


def run_all(cfg) -> None:
    """Ejecuta todos los scripts SQL de Phase 2 en orden."""
    params = {
        "bucket":           cfg.aws.s3_bucket,
        "prefix":           cfg.aws.s3_bronze_prefix.rstrip("/"),
        "region":           cfg.aws.region,
        "access_key_id":    cfg.aws.access_key_id,
        "secret_access_key": cfg.aws.secret_access_key,
        "session_token":    cfg.aws.session_token or "",
    }

    conn = get_connection(cfg)
    try:
        for script_name in SQL_SCRIPTS:
            script_path = SQL_DIR / script_name
            run_sql_file(conn, script_path, params)
    except Exception as exc:
        conn.rollback()
        logger.error(f"Error durante la carga. Rollback ejecutado. Detalle: {exc}")
        raise
    finally:
        conn.close()
        logger.info("Conexión a Aurora cerrada.")
