"""
Adjunta el LabRole de AWS Academy al cluster Aurora para que pueda
leer archivos directamente desde S3 usando la extensión aws_s3.
"""
import boto3
from botocore.exceptions import ClientError

from scripts.utils.logger import get_logger

logger = get_logger(__name__)

FEATURE_NAME = "s3Import"


def get_lab_role_arn(iam_client, account_id: str) -> str:
    """Retorna el ARN del LabRole pre-creado en AWS Academy."""
    arn = f"arn:aws:iam::{account_id}:role/LabRole"
    logger.info(f"Usando LabRole de AWS Academy: {arn}")
    return arn


def get_account_id(sts_client) -> str:
    return sts_client.get_caller_identity()["Account"]


def attach_role_to_cluster(rds_client, cluster_id: str, role_arn: str) -> None:
    """Adjunta el IAM role al cluster Aurora. Si ya está adjuntado, lo ignora."""
    try:
        rds_client.add_role_to_db_cluster(
            DBClusterIdentifier=cluster_id,
            RoleArn=role_arn,
            FeatureName=FEATURE_NAME,
        )
        logger.info(f"LabRole adjuntado al cluster '{cluster_id}' para s3Import.")
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "DBClusterRoleAlreadyExists":
            logger.info("El LabRole ya estaba adjuntado al cluster. Continuando.")
        else:
            logger.error(f"Error adjuntando rol: {e}")
            raise


def setup(cfg) -> str:
    """Orquesta la configuración IAM. Retorna el ARN del role usado."""
    logger.info("── IAM Setup ───────────────────────────────")

    sts = boto3.client(
        "sts",
        aws_access_key_id=cfg.aws.access_key_id,
        aws_secret_access_key=cfg.aws.secret_access_key,
        aws_session_token=cfg.aws.session_token,
        region_name=cfg.aws.region,
    )
    iam = boto3.client(
        "iam",
        aws_access_key_id=cfg.aws.access_key_id,
        aws_secret_access_key=cfg.aws.secret_access_key,
        aws_session_token=cfg.aws.session_token,
        region_name=cfg.aws.region,
    )
    rds = boto3.client(
        "rds",
        aws_access_key_id=cfg.aws.access_key_id,
        aws_secret_access_key=cfg.aws.secret_access_key,
        aws_session_token=cfg.aws.session_token,
        region_name=cfg.aws.region,
    )

    account_id = get_account_id(sts)
    role_arn = get_lab_role_arn(iam, account_id)
    attach_role_to_cluster(rds, cfg.aurora.cluster_id, role_arn)

    logger.info(f"IAM Setup completo. Role ARN: {role_arn}")
    return role_arn
