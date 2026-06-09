"""
Phase 3 — Star Schema (Data Warehouse)
Transforma los datos del schema staging hacia el modelo estrella
en el schema dwh, con pruebas de calidad incluidas.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.settings import load_config
from scripts.utils.logger import get_logger
from scripts.phase3_star_schema.star_schema_builder import run_all

logger = get_logger("phase3_main")


def run() -> None:
    logger.info("=" * 60)
    logger.info("FASE 3 — Star Schema DWH  INICIO")
    logger.info("=" * 60)

    cfg = load_config()
    run_all(cfg)

    logger.info("=" * 60)
    logger.info("FASE 3 — Star Schema DWH  COMPLETADA")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
