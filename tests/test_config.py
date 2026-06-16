"""
Tests unitarios para config/settings.py
No requieren conexión a AWS ni Aurora.
"""
import os
import pytest
from unittest.mock import patch


@pytest.mark.unit
class TestConfigLoading:

    def test_load_config_succeeds_with_all_vars(self):
        """load_config() retorna AppConfig cuando todas las vars están presentes."""
        env = {
            "KAGGLE_USERNAME": "test_user",
            "KAGGLE_KEY": "test_key",
            "KAGGLE_DATASET": "olistbr/brazilian-ecommerce",
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_REGION": "us-east-1",
            "S3_BUCKET_NAME": "test-bucket",
            "AURORA_HOST": "localhost",
            "AURORA_USERNAME": "postgres",
            "AURORA_PASSWORD": "password",
        }
        with patch.dict(os.environ, env, clear=True):
            from config.settings import load_config
            cfg = load_config()

        assert cfg.kaggle.username == "test_user"
        assert cfg.aws.region == "us-east-1"
        assert cfg.aurora.host == "localhost"

    def test_missing_required_var_raises(self):
        """load_config() lanza EnvironmentError si falta una variable requerida."""
        with patch.dict(os.environ, {}, clear=True):
            from config.settings import load_config
            with pytest.raises(OSError, match="KAGGLE_USERNAME"):
                load_config()

    def test_aurora_port_default(self):
        """AURORA_PORT tiene valor por defecto 5432."""
        env = {
            "KAGGLE_USERNAME": "u", "KAGGLE_KEY": "k",
            "KAGGLE_DATASET": "olistbr/brazilian-ecommerce",
            "AWS_ACCESS_KEY_ID": "id", "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_REGION": "us-east-1", "S3_BUCKET_NAME": "bucket",
            "AURORA_HOST": "host", "AURORA_USERNAME": "user",
            "AURORA_PASSWORD": "pass",
        }
        with patch.dict(os.environ, env, clear=True):
            from config.settings import load_config
            cfg = load_config()
        assert cfg.aurora.port == 5432

    def test_session_token_is_optional(self):
        """AWS_SESSION_TOKEN es opcional (None si no está definido)."""
        env = {
            "KAGGLE_USERNAME": "u", "KAGGLE_KEY": "k",
            "KAGGLE_DATASET": "olistbr/brazilian-ecommerce",
            "AWS_ACCESS_KEY_ID": "id", "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_REGION": "us-east-1", "S3_BUCKET_NAME": "bucket",
            "AURORA_HOST": "host", "AURORA_USERNAME": "user",
            "AURORA_PASSWORD": "pass",
        }
        with patch.dict(os.environ, env, clear=True):
            from config.settings import load_config
            cfg = load_config()
        assert cfg.aws.session_token is None

    def test_config_is_immutable(self):
        """AppConfig es frozen=True — no permite modificaciones."""
        env = {
            "KAGGLE_USERNAME": "u", "KAGGLE_KEY": "k",
            "KAGGLE_DATASET": "olistbr/brazilian-ecommerce",
            "AWS_ACCESS_KEY_ID": "id", "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_REGION": "us-east-1", "S3_BUCKET_NAME": "bucket",
            "AURORA_HOST": "host", "AURORA_USERNAME": "user",
            "AURORA_PASSWORD": "pass",
        }
        with patch.dict(os.environ, env, clear=True):
            from config.settings import load_config
            cfg = load_config()
        with pytest.raises((AttributeError, TypeError)):
            cfg.aurora = None
