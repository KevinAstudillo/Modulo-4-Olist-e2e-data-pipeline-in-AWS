"""
Script de diagnóstico: verifica que las credenciales de Kaggle y AWS
sean válidas ANTES de ejecutar el pipeline completo.
No descarga ni sube nada.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import load_config
from scripts.utils.logger import get_logger

logger = get_logger("test_connections")


def test_kaggle(cfg) -> bool:
    logger.info("── TEST 1: Kaggle ──────────────────────────")
    try:
        import os
        import kaggle
        os.environ["KAGGLE_USERNAME"] = cfg.kaggle.username
        os.environ["KAGGLE_KEY"] = cfg.kaggle.key
        kaggle.api.authenticate()
        # Busca el dataset para confirmar que existe y es accesible
        result = kaggle.api.dataset_list(search="olistbr/brazilian-ecommerce")
        logger.info(f"Kaggle OK — usuario autenticado: {cfg.kaggle.username}")
        return True
    except Exception as e:
        logger.error(f"Kaggle FALLO: {e}")
        return False


def test_s3(cfg) -> bool:
    logger.info("── TEST 2: AWS S3 ──────────────────────────")
    logger.info(f"Región configurada en .env : {cfg.aws.region}")
    logger.info(f"Bucket configurado en .env : {cfg.aws.s3_bucket}")
    try:
        import boto3
        s3 = boto3.client(
            "s3",
            aws_access_key_id=cfg.aws.access_key_id,
            aws_secret_access_key=cfg.aws.secret_access_key,
            aws_session_token=cfg.aws.session_token,
            region_name=cfg.aws.region,
        )
        # Obtiene la región real del bucket para comparar
        location = s3.get_bucket_location(Bucket=cfg.aws.s3_bucket)
        real_region = location["LocationConstraint"] or "us-east-1"
        logger.info(f"Región real del bucket en AWS : {real_region}")

        if real_region != cfg.aws.region:
            logger.error(
                f"REGIÓN INCORRECTA — el bucket está en '{real_region}' "
                f"pero tu .env dice '{cfg.aws.region}'. "
                f"Cambia AWS_REGION={real_region} en tu .env"
            )
            return False

        s3.head_bucket(Bucket=cfg.aws.s3_bucket)
        logger.info(f"AWS S3 OK — bucket accesible: s3://{cfg.aws.s3_bucket}")
        return True
    except Exception as e:
        logger.error(f"AWS S3 FALLO: {e}")
        return False


def test_aurora(cfg) -> bool:
    logger.info("── TEST 3: Aurora PostgreSQL ───────────────")
    logger.info(f"Host  : {cfg.aurora.host}")
    logger.info(f"Puerto: {cfg.aurora.port}")
    logger.info(f"BD    : {cfg.aurora.database}")
    logger.info(f"User  : {cfg.aurora.username}")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=cfg.aurora.host,
            port=cfg.aurora.port,
            dbname=cfg.aurora.database,
            user=cfg.aurora.username,
            password=cfg.aurora.password,
            sslmode="require",
            connect_timeout=10,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
        conn.close()
        logger.info(f"Aurora OK — {version[:50]}...")
        return True
    except Exception as e:
        logger.error(f"Aurora FALLO: {e}")
        return False


def run():
    logger.info("=" * 50)
    logger.info("DIAGNÓSTICO DE CONEXIONES")
    logger.info("=" * 50)

    try:
        cfg = load_config()
        logger.info("Variables de entorno cargadas correctamente.")
    except EnvironmentError as e:
        logger.error(f"Error en .env: {e}")
        sys.exit(1)

    kaggle_ok = test_kaggle(cfg)
    s3_ok     = test_s3(cfg)
    aurora_ok = test_aurora(cfg)

    logger.info("=" * 50)
    logger.info(f"Kaggle : {'OK' if kaggle_ok else 'FALLO'}")
    logger.info(f"AWS S3 : {'OK' if s3_ok     else 'FALLO'}")
    logger.info(f"Aurora : {'OK' if aurora_ok  else 'FALLO'}")
    logger.info("=" * 50)

    if kaggle_ok and s3_ok and aurora_ok:
        logger.info("Todo listo. Puedes ejecutar la Fase 2.")
    else:
        logger.error("Revisa los errores anteriores antes de continuar.")
        sys.exit(1)


if __name__ == "__main__":
    run()
