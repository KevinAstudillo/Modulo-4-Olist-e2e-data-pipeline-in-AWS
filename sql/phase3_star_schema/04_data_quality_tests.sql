-- Fase 3 | Paso 4: Pruebas de calidad de datos
-- Resultado esperado: todas las filas de "resultado" deben ser 0

-- ── Sección 1: Conteos informativos (no son validaciones) ────────────────────
SELECT 'INFO' AS tipo, tabla, filas
FROM (
    SELECT '01 | fact_order_items' AS tabla, COUNT(*)::INT AS filas FROM dwh.fact_order_items
    UNION ALL
    SELECT '02 | dim_customers',                                       COUNT(*)::INT FROM dwh.dim_customers
    UNION ALL
    SELECT '03 | dim_products',                                        COUNT(*)::INT FROM dwh.dim_products
    UNION ALL
    SELECT '04 | dim_sellers',                                         COUNT(*)::INT FROM dwh.dim_sellers
    UNION ALL
    SELECT '05 | dim_orders',                                          COUNT(*)::INT FROM dwh.dim_orders
    UNION ALL
    SELECT '06 | dim_date',                                            COUNT(*)::INT FROM dwh.dim_date
) counts
ORDER BY tabla;

-- ── Sección 2: Validaciones de calidad (resultado esperado = 0) ───────────────
SELECT test, resultado,
       CASE WHEN resultado = 0 THEN 'PASS' ELSE 'FAIL' END AS estado
FROM (
    -- NULLs en claves foráneas
    SELECT '07 | fact_order_items — customer_sk NULL' AS test, COUNT(*)::INT AS resultado FROM dwh.fact_order_items WHERE customer_sk IS NULL
    UNION ALL
    SELECT '08 | fact_order_items — product_sk NULL',           COUNT(*)::INT FROM dwh.fact_order_items WHERE product_sk  IS NULL
    UNION ALL
    SELECT '09 | fact_order_items — seller_sk NULL',            COUNT(*)::INT FROM dwh.fact_order_items WHERE seller_sk   IS NULL
    UNION ALL
    SELECT '10 | fact_order_items — date_sk NULL',              COUNT(*)::INT FROM dwh.fact_order_items WHERE date_sk     IS NULL
    UNION ALL
    -- Rangos de valores
    SELECT '11 | fact_order_items — price negativo',            COUNT(*)::INT FROM dwh.fact_order_items WHERE price < 0
    UNION ALL
    SELECT '12 | fact_reviews — score fuera de 1-5',            COUNT(*)::INT FROM dwh.fact_reviews WHERE review_score NOT BETWEEN 1 AND 5
    UNION ALL
    -- Duplicados
    SELECT '13 | dim_customers — IDs duplicados',
        COUNT(*)::INT FROM (SELECT customer_id FROM dwh.dim_customers GROUP BY customer_id HAVING COUNT(*) > 1) x
    UNION ALL
    SELECT '14 | dim_products  — IDs duplicados',
        COUNT(*)::INT FROM (SELECT product_id  FROM dwh.dim_products  GROUP BY product_id  HAVING COUNT(*) > 1) x
    UNION ALL
    SELECT '15 | dim_sellers   — IDs duplicados',
        COUNT(*)::INT FROM (SELECT seller_id   FROM dwh.dim_sellers   GROUP BY seller_id   HAVING COUNT(*) > 1) x
) validaciones
ORDER BY test;
