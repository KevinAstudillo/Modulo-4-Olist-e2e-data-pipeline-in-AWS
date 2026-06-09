"""
Phase 5 — Stored Procedures
Despliega tablas de soporte y stored procedures en Aurora,
luego los ejecuta en batch para generar snapshots ejecutivos
y la segmentación de vendedores.

Uso:
    python -m scripts.phase5_procedures.main
"""

import sys
import time

from config.settings import load_config
from scripts.utils.logger import get_logger
from scripts.phase5_procedures.procedure_runner import (
    _get_connection,
    create_support_tables,
    create_stored_procedures,
    run_batch_monthly_reports,
    run_seller_segmentation,
)

log = get_logger(__name__)

SEPARATOR = "═" * 60


def main() -> None:
    log.info(SEPARATOR)
    log.info("PHASE 5 — PL/pgSQL Stored Procedures")
    log.info(SEPARATOR)

    cfg = load_config()
    t0 = time.perf_counter()

    try:
        conn = _get_connection(cfg.aurora)
        log.info("Conexión a Aurora establecida.")

        # ── 1. Infraestructura ──────────────────────────────
        log.info("[1/4] Creando tablas de soporte...")
        create_support_tables(conn)

        # ── 2. Desplegar procedures ─────────────────────────
        log.info("[2/4] Desplegando stored procedures...")
        create_stored_procedures(conn)

        # ── 3. Batch de reportes mensuales ──────────────────
        log.info("[3/4] Generando batch de reportes mensuales 2016-2018...")
        n_periodos = run_batch_monthly_reports(conn)
        log.info("  → %d snapshots generados en reporting.reporte_mensual_snapshot.", n_periodos)

        # ── 4. Segmentación de vendedores ───────────────────
        log.info("[4/4] Segmentando vendedores A/B/C/D...")
        segments = run_seller_segmentation(conn)
        total_vendedores = sum(s["total_vendedores"] for s in segments)
        log.info("  → %d vendedores segmentados en reporting.seller_segments.", total_vendedores)

        conn.close()

        elapsed = time.perf_counter() - t0
        log.info(SEPARATOR)
        log.info("Phase 5 completada exitosamente en %.2fs.", elapsed)
        log.info("Tablas disponibles:")
        log.info("  reporting.reporte_mensual_snapshot  (%d filas)", n_periodos)
        log.info("  reporting.seller_segments            (%d filas)", total_vendedores)
        log.info(SEPARATOR)

    except Exception as exc:
        log.exception("Phase 5 falló: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
