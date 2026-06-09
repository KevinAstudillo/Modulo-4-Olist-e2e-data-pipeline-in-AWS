-- Fase 3 | Paso 3: Poblar tablas de hechos con joins a las dimensiones

-- ── fact_order_items (tabla de hechos principal) ──────────────────────────────
INSERT INTO dwh.fact_order_items (
    order_id, order_item_id,
    customer_sk, product_sk, seller_sk, order_sk, date_sk,
    price, freight_value, total_value
)
SELECT
    oi.order_id,
    oi.order_item_id::INTEGER,
    dc.customer_sk,
    dp.product_sk,
    ds.seller_sk,
    dor.order_sk,
    TO_CHAR(dor.order_purchase_timestamp, 'YYYYMMDD')::INTEGER AS date_sk,
    oi.price::NUMERIC(10,2),
    oi.freight_value::NUMERIC(10,2),
    (oi.price::NUMERIC + oi.freight_value::NUMERIC)::NUMERIC(10,2) AS total_value
FROM staging.order_items oi
JOIN staging.orders   so  ON oi.order_id    = so.order_id
JOIN dwh.dim_customers dc  ON so.customer_id  = dc.customer_id
JOIN dwh.dim_products  dp  ON oi.product_id   = dp.product_id
JOIN dwh.dim_sellers   ds  ON oi.seller_id    = ds.seller_id
JOIN dwh.dim_orders    dor ON oi.order_id     = dor.order_id
WHERE dor.order_purchase_timestamp IS NOT NULL;

-- ── fact_payments ─────────────────────────────────────────────────────────────
INSERT INTO dwh.fact_payments (
    order_id, payment_sequential, payment_type,
    payment_installments, payment_value
)
SELECT
    order_id,
    NULLIF(payment_sequential,   '')::INTEGER,
    payment_type,
    NULLIF(payment_installments, '')::INTEGER,
    NULLIF(payment_value,        '')::NUMERIC(10,2)
FROM staging.order_payments;

-- ── fact_reviews ──────────────────────────────────────────────────────────────
INSERT INTO dwh.fact_reviews (
    review_id, order_id, review_score,
    review_comment_title, review_comment_message,
    review_creation_date, review_answer_timestamp
)
SELECT
    review_id,
    order_id,
    NULLIF(review_score, '')::SMALLINT,
    NULLIF(review_comment_title,   ''),
    NULLIF(review_comment_message, ''),
    NULLIF(review_creation_date,      '')::TIMESTAMP,
    NULLIF(review_answer_timestamp,   '')::TIMESTAMP
FROM staging.order_reviews;
