"""
Phase 2 — Aurora Staging Ingestion
Adjunta el LabRole a Aurora y carga los CSVs desde S3 Bronze
hacia las tablas de staging usando la extensión aws_s3.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.settings import load_config
from scripts.utils.logger import get_logger
from scripts.phase2_aurora_ingestion.iam_setup import setup as iam_setup
from scripts.phase2_aurora_ingestion.aurora_loader import run_all

logger = get_logger("phase2_main")


def run() -> None:
    logger.info("=" * 60)
    logger.info("FASE 2 — Aurora Staging Ingestion  INICIO")
    logger.info("=" * 60)

    cfg = load_config()

    # Paso 1 — Adjuntar LabRole al cluster Aurora
    iam_setup(cfg)

    # Paso 2 — Ejecutar scripts SQL en Aurora
    run_all(cfg)

    logger.info("=" * 60)
    logger.info("FASE 2 — Aurora Staging Ingestion  COMPLETADA")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
