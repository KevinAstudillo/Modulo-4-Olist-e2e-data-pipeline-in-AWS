-- Fase 2 | Paso 4: Verificar conteo de filas por tabla
-- Valores esperados del dataset Olist original

SELECT 'staging.customers'               AS tabla, COUNT(*) AS filas FROM staging.customers
UNION ALL
SELECT 'staging.geolocation',                      COUNT(*) FROM staging.geolocation
UNION ALL
SELECT 'staging.orders',                           COUNT(*) FROM staging.orders
UNION ALL
SELECT 'staging.order_items',                      COUNT(*) FROM staging.order_items
UNION ALL
SELECT 'staging.order_payments',                   COUNT(*) FROM staging.order_payments
UNION ALL
SELECT 'staging.order_reviews',                    COUNT(*) FROM staging.order_reviews
UNION ALL
SELECT 'staging.products',                         COUNT(*) FROM staging.products
UNION ALL
SELECT 'staging.sellers',                          COUNT(*) FROM staging.sellers
UNION ALL
SELECT 'staging.product_category_translation',     COUNT(*) FROM staging.product_category_translation
ORDER BY tabla;
