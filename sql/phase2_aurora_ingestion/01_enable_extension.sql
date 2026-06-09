-- Fase 2 | Paso 1: Habilitar extensiones necesarias para importar desde S3
-- Requiere que el LabRole ya esté adjuntado al cluster Aurora

CREATE EXTENSION IF NOT EXISTS aws_commons CASCADE;
CREATE EXTENSION IF NOT EXISTS aws_s3 CASCADE;
