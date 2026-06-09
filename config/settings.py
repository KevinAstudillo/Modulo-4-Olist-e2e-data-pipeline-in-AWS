import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


@dataclass(frozen=True)
class KaggleConfig:
    username: str
    key: str
    dataset: str


@dataclass(frozen=True)
class AWSConfig:
    access_key_id: str
    secret_access_key: str
    session_token: str | None  # Requerido en AWS Academy (credenciales temporales)
    region: str
    s3_bucket: str
    s3_bronze_prefix: str


@dataclass(frozen=True)
class AuroraConfig:
    host: str
    port: int
    database: str
    username: str
    password: str
    cluster_id: str


@dataclass(frozen=True)
class AppConfig:
    kaggle: KaggleConfig
    aws: AWSConfig
    aurora: AuroraConfig
    log_level: str
    raw_data_dir: str


def load_config() -> AppConfig:
    def _require(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise EnvironmentError(
                f"Variable de entorno requerida '{key}' no está definida. "
                "Revisa tu archivo .env"
            )
        return value

    return AppConfig(
        kaggle=KaggleConfig(
            username=_require("KAGGLE_USERNAME"),
            key=_require("KAGGLE_KEY"),
            dataset=_require("KAGGLE_DATASET"),
        ),
        aws=AWSConfig(
            access_key_id=_require("AWS_ACCESS_KEY_ID"),
            secret_access_key=_require("AWS_SECRET_ACCESS_KEY"),
            session_token=os.getenv("AWS_SESSION_TOKEN"),
            region=_require("AWS_REGION"),
            s3_bucket=_require("S3_BUCKET_NAME"),
            s3_bronze_prefix=os.getenv("S3_BRONZE_PREFIX", "bronze/olist/"),
        ),
        aurora=AuroraConfig(
            host=_require("AURORA_HOST"),
            port=int(os.getenv("AURORA_PORT", "5432")),
            database=os.getenv("AURORA_DATABASE", "postgres"),
            username=_require("AURORA_USERNAME"),
            password=_require("AURORA_PASSWORD"),
            cluster_id=os.getenv("AURORA_CLUSTER_ID", "aurora-mod4"),
        ),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        raw_data_dir=os.getenv("RAW_DATA_DIR", "data/raw"),
    )
