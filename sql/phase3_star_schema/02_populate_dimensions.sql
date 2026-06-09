-- Fase 3 | Paso 2: Poblar dimensiones desde staging
-- NULLIF convierte strings vacíos a NULL antes de castear tipos

-- ── dim_date (generada desde los timestamps reales de órdenes) ────────────────
INSERT INTO dwh.dim_date (
    date_sk, full_date, year, quarter, month,
    month_name, day, day_of_week, day_name, is_weekend
)
SELECT
    TO_CHAR(d::DATE, 'YYYYMMDD')::INTEGER,
    d::DATE,
    EXTRACT(YEAR    FROM d)::SMALLINT,
    EXTRACT(QUARTER FROM d)::SMALLINT,
    EXTRACT(MONTH   FROM d)::SMALLINT,
    TRIM(TO_CHAR(d, 'Month')),
    EXTRACT(DAY     FROM d)::SMALLINT,
    EXTRACT(DOW     FROM d)::SMALLINT,
    TRIM(TO_CHAR(d, 'Day')),
    EXTRACT(DOW FROM d) IN (0, 6)
FROM generate_series(
    (SELECT MIN(NULLIF(order_purchase_timestamp, '')::TIMESTAMP)::DATE FROM staging.orders),
    (SELECT MAX(NULLIF(order_purchase_timestamp, '')::TIMESTAMP)::DATE FROM staging.orders),
    '1 day'::INTERVAL
) AS d
ON CONFLICT (date_sk) DO NOTHING;

-- ── dim_customers ─────────────────────────────────────────────────────────────
INSERT INTO dwh.dim_customers (
    customer_id, customer_unique_id,
    customer_zip_code_prefix, customer_city, customer_state
)
SELECT
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    INITCAP(TRIM(customer_city)),
    UPPER(TRIM(customer_state))
FROM staging.customers
ON CONFLICT (customer_id) DO NOTHING;

-- ── dim_sellers ───────────────────────────────────────────────────────────────
INSERT INTO dwh.dim_sellers (
    seller_id, seller_zip_code_prefix, seller_city, seller_state
)
SELECT
    seller_id,
    seller_zip_code_prefix,
    INITCAP(TRIM(seller_city)),
    UPPER(TRIM(seller_state))
FROM staging.sellers
ON CONFLICT (seller_id) DO NOTHING;

-- ── dim_products (con traducción de categoría fusionada) ──────────────────────
INSERT INTO dwh.dim_products (
    product_id, product_category_name, product_category_name_english,
    product_name_lenght, product_description_lenght, product_photos_qty,
    product_weight_g, product_length_cm, product_height_cm, product_width_cm
)
SELECT
    p.product_id,
    p.product_category_name,
    t.product_category_name_english,
    NULLIF(p.product_name_lenght,        '')::INTEGER,
    NULLIF(p.product_description_lenght, '')::INTEGER,
    NULLIF(p.product_photos_qty,         '')::INTEGER,
    NULLIF(p.product_weight_g,           '')::NUMERIC,
    NULLIF(p.product_length_cm,          '')::NUMERIC,
    NULLIF(p.product_height_cm,          '')::NUMERIC,
    NULLIF(p.product_width_cm,           '')::NUMERIC
FROM staging.products p
LEFT JOIN staging.product_category_translation t
       ON p.product_category_name = t.product_category_name
ON CONFLICT (product_id) DO NOTHING;

-- ── dim_orders ────────────────────────────────────────────────────────────────
INSERT INTO dwh.dim_orders (
    order_id, order_status,
    order_purchase_timestamp, order_approved_at,
    order_delivered_carrier_date, order_delivered_customer_date,
    order_estimated_delivery_date
)
SELECT
    order_id,
    order_status,
    NULLIF(order_purchase_timestamp,       '')::TIMESTAMP,
    NULLIF(order_approved_at,              '')::TIMESTAMP,
    NULLIF(order_delivered_carrier_date,   '')::TIMESTAMP,
    NULLIF(order_delivered_customer_date,  '')::TIMESTAMP,
    NULLIF(order_estimated_delivery_date,  '')::TIMESTAMP
FROM staging.orders
ON CONFLICT (order_id) DO NOTHING;
