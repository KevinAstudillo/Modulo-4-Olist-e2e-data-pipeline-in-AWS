"""
Phase 4 — Reporting Layer
Crea el schema reporting con 5 vistas SQL avanzadas (CTEs + Window Functions)
sobre el DWH intacto, listas para conectar con Power BI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.settings import load_config
from scripts.utils.logger import get_logger
from scripts.phase4_bi_queries.reporting_builder import run_all

logger = get_logger("phase4_main")


def run() -> None:
    logger.info("=" * 60)
    logger.info("FASE 4 — Reporting Layer  INICIO")
    logger.info("=" * 60)

    cfg = load_config()
    run_all(cfg)

    logger.info("=" * 60)
    logger.info("FASE 4 — Reporting Layer  COMPLETADA")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Vistas disponibles en Aurora schema 'reporting':")
    logger.info("  - vw_revenue_mensual       → revenue MoM con crecimiento %")
    logger.info("  - vw_top_categorias_pareto → análisis Pareto 80/20")
    logger.info("  - vw_ranking_vendedores    → top sellers con RANK()")
    logger.info("  - vw_tiempo_entrega_estado → logística por estado")
    logger.info("  - vw_satisfaccion_cliente  → NPS por categoría")
    logger.info("")
    logger.info("Conecta Power BI a: reporting.vw_*")


if __name__ == "__main__":
    run()
