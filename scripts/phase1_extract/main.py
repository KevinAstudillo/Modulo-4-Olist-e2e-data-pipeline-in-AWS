"""
Phase 1 — Bronze Ingestion
Extrae el dataset de Olist desde Kaggle y carga los CSVs crudos en S3 (capa Bronze).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.settings import load_config
from scripts.utils.logger import get_logger
from scripts.phase1_extract.kaggle_extractor import (
    authenticate_kaggle,
    download_dataset,
    extract_zip,
)
from scripts.phase1_extract.s3_uploader import build_s3_client, upload_files_to_s3

logger = get_logger("phase1_main")


def run() -> None:
    logger.info("=" * 60)
    logger.info("FASE 1 — Bronze Ingestion  INICIO")
    logger.info("=" * 60)

    cfg = load_config()

    # Paso 1 — Autenticar con Kaggle
    authenticate_kaggle(cfg.kaggle.username, cfg.kaggle.key)

    # Paso 2 — Descargar y extraer dataset
    zip_path = download_dataset(cfg.kaggle.dataset, cfg.raw_data_dir)
    csv_files = extract_zip(zip_path, cfg.raw_data_dir)

    # Paso 3 — Subir CSVs a la capa Bronze en S3
    s3_client = build_s3_client(
        cfg.aws.access_key_id,
        cfg.aws.secret_access_key,
        cfg.aws.region,
        cfg.aws.session_token,
    )
    upload_files_to_s3(s3_client, csv_files, cfg.aws.s3_bucket, cfg.aws.s3_bronze_prefix)

    logger.info("=" * 60)
    logger.info("FASE 1 — Bronze Ingestion  COMPLETADA")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
