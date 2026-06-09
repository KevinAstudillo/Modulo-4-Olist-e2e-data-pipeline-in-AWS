"""
Conecta a Aurora y ejecuta los scripts SQL de la Fase 3 en orden:
schema → dimensiones → hechos → calidad de datos.
"""
from pathlib import Path

import psycopg2
from psycopg2.extensions import connection as PgConnection

from scripts.utils.logger import get_logger

logger = get_logger(__name__)

SQL_DIR = Path(__file__).resolve().parents[2] / "sql" / "phase3_star_schema"

SQL_SCRIPTS = [
    "01_create_dwh_schema.sql",
    "02_populate_dimensions.sql",
    "03_populate_facts.sql",
    "04_data_quality_tests.sql",
]


def get_connection(cfg) -> PgConnection:
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
    logger.info("Conexión establecida.")
    return conn


def run_sql_file(conn: PgConnection, sql_path: Path) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    logger.info(f"Ejecutando: {sql_path.name} ...")
    with conn.cursor() as cur:
        cur.execute(sql)
        if cur.description:
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            logger.info(f"  {' | '.join(cols)}")
            for row in rows:
                logger.info(f"  {row}")
    conn.commit()
    logger.info(f"{sql_path.name} completado.")


def run_all(cfg) -> None:
    conn = get_connection(cfg)
    try:
        for script_name in SQL_SCRIPTS:
            run_sql_file(conn, SQL_DIR / script_name)
    except Exception as exc:
        conn.rollback()
        logger.error(f"Error. Rollback ejecutado. Detalle: {exc}")
        raise
    finally:
        conn.close()
        logger.info("Conexión cerrada.")
