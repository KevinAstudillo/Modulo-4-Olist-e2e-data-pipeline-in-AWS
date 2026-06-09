-- ============================================================
-- PHASE 5: Tablas de soporte para Stored Procedures
-- Proyecto : Olist E-Commerce Data Pipeline
-- Descripción: Tablas destino para snapshots generados por
--              los stored procedures de la Fase 5
-- ============================================================

CREATE SCHEMA IF NOT EXISTS reporting;

-- ─────────────────────────────────────────────────────────────
-- Tabla 1: Snapshots de reporte ejecutivo mensual
--          Destino principal de sp_generar_reporte_mensual()
-- ─────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS reporting.reporte_mensual_snapshot CASCADE;

CREATE TABLE reporting.reporte_mensual_snapshot (
    periodo             VARCHAR(7)      NOT NULL,
    fecha_generacion    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    ingresos_totales    NUMERIC(15,2)   NOT NULL DEFAULT 0,
    total_ordenes       BIGINT          NOT NULL DEFAULT 0,
    ticket_promedio     NUMERIC(10,2)   NOT NULL DEFAULT 0,
    top_categoria_1     TEXT,
    top_categoria_2     TEXT,
    top_categoria_3     TEXT,
    top_vendedor_1      TEXT,
    top_vendedor_2      TEXT,
    top_vendedor_3      TEXT,
    score_satisfaccion  NUMERIC(4,2),

    CONSTRAINT pk_reporte_mensual_snapshot PRIMARY KEY (periodo),
    CONSTRAINT ck_periodo_formato           CHECK (periodo ~ '^\d{4}-\d{2}$')
);

COMMENT ON TABLE  reporting.reporte_mensual_snapshot IS
    'Snapshots ejecutivos mensuales generados por sp_generar_reporte_mensual(). '
    'Cada fila representa un período YYYY-MM con KPIs de negocio.';
COMMENT ON COLUMN reporting.reporte_mensual_snapshot.periodo IS
    'Período en formato YYYY-MM  (ej: 2018-01).';
COMMENT ON COLUMN reporting.reporte_mensual_snapshot.top_categoria_1 IS
    'Categoría de producto con mayor revenue en el período.';
COMMENT ON COLUMN reporting.reporte_mensual_snapshot.score_satisfaccion IS
    'Promedio de review_score (1-5) para el período.';


-- ─────────────────────────────────────────────────────────────
-- Tabla 2: Segmentación de vendedores
--          Destino principal de sp_segmentar_vendedores()
-- ─────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS reporting.seller_segments CASCADE;

CREATE TABLE reporting.seller_segments (
    segment_sk          SERIAL          PRIMARY KEY,
    seller_sk           INTEGER         NOT NULL,
    seller_id           VARCHAR(50)     NOT NULL,
    ciudad              VARCHAR(100),
    estado              CHAR(2),
    ingresos_total      NUMERIC(15,2)   NOT NULL DEFAULT 0,
    total_ordenes       INTEGER         NOT NULL DEFAULT 0,
    productos_distintos INTEGER         NOT NULL DEFAULT 0,
    ticket_promedio     NUMERIC(10,2),
    primera_venta       DATE,
    ultima_venta        DATE,
    segmento            CHAR(1)         NOT NULL,
    fecha_segmentacion  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_seller_segments_seller_id UNIQUE (seller_id),
    CONSTRAINT ck_segmento                  CHECK  (segmento IN ('A','B','C','D'))
);

CREATE INDEX idx_seller_segments_segmento ON reporting.seller_segments (segmento);
CREATE INDEX idx_seller_segments_estado   ON reporting.seller_segments (estado);
CREATE INDEX idx_seller_segments_ingresos ON reporting.seller_segments (ingresos_total DESC);

COMMENT ON TABLE  reporting.seller_segments IS
    'Clasificación de vendedores en segmentos A/B/C/D por cuartil de ingresos. '
    'Generada y actualizada por sp_segmentar_vendedores().';
COMMENT ON COLUMN reporting.seller_segments.segmento IS
    'A = Top 25% ingresos (Alto rendimiento) | '
    'B = 25-50% (Medio-alto) | '
    'C = 50-75% (Medio-bajo) | '
    'D = Bottom 25% (Bajo rendimiento).';
COMMENT ON COLUMN reporting.seller_segments.seller_sk IS
    'FK lógica a dwh.dim_sellers.seller_sk (sin FK formal para flexibilidad).';


-- ─────────────────────────────────────────────────────────────
-- Verificar creación
-- ─────────────────────────────────────────────────────────────
SELECT
    table_schema                    AS schema,
    table_name                      AS tabla,
    pg_size_pretty(pg_total_relation_size(
        quote_ident(table_schema) || '.' || quote_ident(table_name)
    ))                              AS tamaño
FROM information_schema.tables
WHERE table_schema = 'reporting'
  AND table_type   = 'BASE TABLE'
ORDER BY table_name;
