from pathlib import Path
from typing import List

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from scripts.utils.logger import get_logger

logger = get_logger(__name__)


def build_s3_client(
    access_key_id: str,
    secret_access_key: str,
    region: str,
    session_token: str | None = None,
):
    """Construye y retorna un cliente boto3 de S3.
    session_token es requerido en AWS Academy (credenciales temporales).
    """
    client = boto3.client(
        "s3",
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        aws_session_token=session_token,
        region_name=region,
    )
    logger.info(f"Cliente S3 creado — región: '{region}'.")
    return client


def upload_files_to_s3(
    s3_client,
    local_files: List[Path],
    bucket: str,
    prefix: str,
) -> None:
    """Sube una lista de archivos locales al bucket S3 bajo el prefijo Bronze dado."""
    if not local_files:
        logger.warning("No hay archivos para subir.")
        return

    for file_path in local_files:
        s3_key = f"{prefix.rstrip('/')}/{file_path.name}"
        try:
            logger.info(f"Subiendo '{file_path.name}' → s3://{bucket}/{s3_key}")
            s3_client.upload_file(
                Filename=str(file_path),
                Bucket=bucket,
                Key=s3_key,
                ExtraArgs={"ServerSideEncryption": "AES256"},
            )
            logger.info(f"Upload exitoso: {file_path.name}")
        except (BotoCoreError, ClientError) as exc:
            logger.error(f"Error al subir '{file_path.name}': {exc}")
            raise
