import os
import zipfile
from pathlib import Path
from typing import List

import kaggle

from scripts.utils.logger import get_logger

logger = get_logger(__name__)


def authenticate_kaggle(username: str, key: str) -> None:
    """Inyecta las credenciales de Kaggle como env vars, evitando escribir kaggle.json en disco."""
    os.environ["KAGGLE_USERNAME"] = username
    os.environ["KAGGLE_KEY"] = key
    kaggle.api.authenticate()
    logger.info("Autenticación con Kaggle exitosa.")


def download_dataset(dataset: str, download_dir: str) -> Path:
    """Descarga el dataset de Kaggle en formato ZIP al directorio indicado."""
    output_path = Path(download_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Descargando dataset '{dataset}' → '{output_path}' ...")
    kaggle.api.dataset_download_files(dataset, path=str(output_path), quiet=False)

    zip_files = list(output_path.glob("*.zip"))
    if not zip_files:
        raise FileNotFoundError(
            f"No se encontró ningún archivo ZIP en '{output_path}' tras la descarga."
        )
    logger.info(f"ZIP descargado: {zip_files[0].name}")
    return zip_files[0]


def extract_zip(zip_path: Path, extract_to: str) -> List[Path]:
    """Extrae todos los CSVs del ZIP y retorna sus rutas."""
    extract_path = Path(extract_to)
    extract_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Extrayendo '{zip_path.name}' → '{extract_path}' ...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_path)

    csv_files = list(extract_path.glob("*.csv"))
    logger.info(f"{len(csv_files)} CSV(s) extraídos: {[f.name for f in csv_files]}")
    return csv_files
