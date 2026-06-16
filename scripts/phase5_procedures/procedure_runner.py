"""
Ejecuta los stored procedures de Phase 5 contra Aurora PostgreSQL
y muestra los resultados formateados en consola.
"""

from __future__ import annotations

import psycopg2
import psycopg2.extras
from pathlib import Path
from typing import Any

from config.settings import AuroraConfig, load_config
from scripts.utils.logger import get_logger

log = get_logger(__name__)

SQL_DIR = Path(__file__).parent.parent.parent / "sql" / "phase5_procedures"


# ─────────────────────────────────────────────────────────────
# Helpers de conexión y ejecución
# ─────────────────────────────────────────────────────────────

def _get_connection(cfg: AuroraConfig) -> psycopg2.extensions.connection:
    conn = psycopg2.connect(
        host=cfg.host,
        port=cfg.port,
        dbname=cfg.database,
        user=cfg.username,
        password=cfg.password,
        sslmode="require",
        connect_timeout=10,
    )
    conn.autocommit = False
    return conn


def _run_sql_file(conn: psycopg2.extensions.connection, filename: str) -> None:
    sql_path = SQL_DIR / filename
    log.info("Ejecutando script SQL: %s", sql_path.name)
    with open(sql_path, encoding="utf-8") as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    log.info("Script %s completado.", sql_path.name)


def _call_function(
    conn: psycopg2.extensions.connection,
    sql: str,
    params: tuple[Any, ...] | None = None,
) -> list[dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    conn.commit()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────
# Funciones públicas
# ─────────────────────────────────────────────────────────────

def create_support_tables(conn: psycopg2.extensions.connection) -> None:
    """Crea las tablas de soporte (reporte_mensual_snapshot, seller_segments)."""
    _run_sql_file(conn, "01_create_support_tables.sql")


def create_stored_procedures(conn: psycopg2.extensions.connection) -> None:
    """Despliega los dos stored procedures en Aurora."""
    _run_sql_file(conn, "02_sp_generar_reporte_mensual.sql")
    _run_sql_file(conn, "03_sp_segmentar_vendedores.sql")


def run_batch_monthly_reports(conn: psycopg2.extensions.connection) -> int:
    """
    Genera snapshots para todos los períodos 2016-2018 que tienen datos.
    Retorna el número de períodos con revenue > 0.
    """
    log.info("Iniciando batch de reportes mensuales 2016-2018...")
    count_with_data = 0

    for year in range(2016, 2019):
        for month in range(1, 13):
            try:
                rows = _call_function(
                    conn,
                    "SELECT * FROM reporting.sp_generar_reporte_mensual(%s, %s)",
                    (year, month),
                )
                if rows and rows[0]["ingresos_totales"] > 0:
                    r = rows[0]
                    mom = r["crecimiento_mom_pct"]
                    yoy = r["crecimiento_yoy_pct"]
                    log.info(
                        "  %s | Ingresos: $%10.2f | Órdenes: %4d | MoM: %s%% | YoY: %s%%",
                        r["periodo"],
                        r["ingresos_totales"],
                        r["total_ordenes"],
                        f"{mom:+.1f}" if mom is not None else "N/A",
                        f"{yoy:+.1f}" if yoy is not None else "N/A",
                    )
                    count_with_data += 1
            except Exception as exc:  # noqa: BLE001
                conn.rollback()
                log.warning("  %d-%02d sin datos o error: %s", year, month, exc)

    log.info("Batch completado: %d períodos con datos generados.", count_with_data)
    return count_with_data


def run_seller_segmentation(conn: psycopg2.extensions.connection) -> list[dict]:
    """
    Ejecuta sp_segmentar_vendedores() y retorna el resumen por segmento.
    """
    log.info("Ejecutando segmentación de vendedores...")
    rows = _call_function(
        conn,
        "SELECT * FROM reporting.sp_segmentar_vendedores()",
    )
    log.info("Segmentación completada — %d segmentos retornados.", len(rows))
    for r in rows:
        log.info(
            "  Segmento %s (%s): %d vendedores | Revenue: $%.2f | Participación: %.1f%%",
            r["segmento"],
            r["descripcion"],
            r["total_vendedores"],
            r["ingresos_total"],
            r["pct_del_total"],
        )
    return rows
