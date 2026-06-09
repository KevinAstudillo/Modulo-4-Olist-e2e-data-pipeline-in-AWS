-- Fase 3 | Paso 1: Crear schema DWH y tablas del modelo estrella
-- DROP en orden inverso para respetar foreign keys (facts primero, dims después)

CREATE SCHEMA IF NOT EXISTS dwh;

-- ── Drops ────────────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dwh.fact_order_items;
DROP TABLE IF EXISTS dwh.fact_payments;
DROP TABLE IF EXISTS dwh.fact_reviews;
DROP TABLE IF EXISTS dwh.dim_customers;
DROP TABLE IF EXISTS dwh.dim_products;
DROP TABLE IF EXISTS dwh.dim_sellers;
DROP TABLE IF EXISTS dwh.dim_orders;
DROP TABLE IF EXISTS dwh.dim_date;

-- ── Dimensiones ───────────────────────────────────────────────────────────────

CREATE TABLE dwh.dim_date (
    date_sk      INTEGER      PRIMARY KEY,  -- formato YYYYMMDD
    full_date    DATE         NOT NULL,
    year         SMALLINT     NOT NULL,
    quarter      SMALLINT     NOT NULL,
    month        SMALLINT     NOT NULL,
    month_name   VARCHAR(20)  NOT NULL,
    day          SMALLINT     NOT NULL,
    day_of_week  SMALLINT     NOT NULL,     -- 0=domingo, 6=sábado
    day_name     VARCHAR(20)  NOT NULL,
    is_weekend   BOOLEAN      NOT NULL
);

CREATE TABLE dwh.dim_customers (
    customer_sk              SERIAL       PRIMARY KEY,
    customer_id              VARCHAR(32)  NOT NULL UNIQUE,
    customer_unique_id       VARCHAR(32),
    customer_zip_code_prefix VARCHAR(8),
    customer_city            VARCHAR(100),
    customer_state           VARCHAR(2)
);

CREATE TABLE dwh.dim_sellers (
    seller_sk              SERIAL       PRIMARY KEY,
    seller_id              VARCHAR(32)  NOT NULL UNIQUE,
    seller_zip_code_prefix VARCHAR(8),
    seller_city            VARCHAR(100),
    seller_state           VARCHAR(2)
);

CREATE TABLE dwh.dim_products (
    product_sk                    SERIAL       PRIMARY KEY,
    product_id                    VARCHAR(32)  NOT NULL UNIQUE,
    product_category_name         VARCHAR(100),
    product_category_name_english VARCHAR(100),
    product_name_lenght           INTEGER,
    product_description_lenght    INTEGER,
    product_photos_qty            INTEGER,
    product_weight_g              NUMERIC(10,2),
    product_length_cm             NUMERIC(10,2),
    product_height_cm             NUMERIC(10,2),
    product_width_cm              NUMERIC(10,2)
);

CREATE TABLE dwh.dim_orders (
    order_sk                       SERIAL      PRIMARY KEY,
    order_id                       VARCHAR(32) NOT NULL UNIQUE,
    order_status                   VARCHAR(20),
    order_purchase_timestamp       TIMESTAMP,
    order_approved_at              TIMESTAMP,
    order_delivered_carrier_date   TIMESTAMP,
    order_delivered_customer_date  TIMESTAMP,
    order_estimated_delivery_date  TIMESTAMP
);

-- ── Tablas de Hechos ──────────────────────────────────────────────────────────

CREATE TABLE dwh.fact_order_items (
    order_item_sk  SERIAL       PRIMARY KEY,
    order_id       VARCHAR(32)  NOT NULL,
    order_item_id  INTEGER      NOT NULL,
    customer_sk    INTEGER      REFERENCES dwh.dim_customers(customer_sk),
    product_sk     INTEGER      REFERENCES dwh.dim_products(product_sk),
    seller_sk      INTEGER      REFERENCES dwh.dim_sellers(seller_sk),
    order_sk       INTEGER      REFERENCES dwh.dim_orders(order_sk),
    date_sk        INTEGER      REFERENCES dwh.dim_date(date_sk),
    price          NUMERIC(10,2),
    freight_value  NUMERIC(10,2),
    total_value    NUMERIC(10,2)
);

CREATE TABLE dwh.fact_payments (
    payment_sk           SERIAL      PRIMARY KEY,
    order_id             VARCHAR(32) NOT NULL,
    payment_sequential   INTEGER,
    payment_type         VARCHAR(30),
    payment_installments INTEGER,
    payment_value        NUMERIC(10,2)
);

CREATE TABLE dwh.fact_reviews (
    review_sk               SERIAL      PRIMARY KEY,
    review_id               VARCHAR(32),
    order_id                VARCHAR(32) NOT NULL,
    review_score            SMALLINT,
    review_comment_title    TEXT,
    review_comment_message  TEXT,
    review_creation_date    TIMESTAMP,
    review_answer_timestamp TIMESTAMP
);
