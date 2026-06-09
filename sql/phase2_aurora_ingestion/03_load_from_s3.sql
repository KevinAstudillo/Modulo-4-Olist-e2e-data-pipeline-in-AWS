-- Fase 2 | Paso 3: Cargar CSVs desde S3 Bronze a las tablas de staging
-- Usa credenciales explícitas para compatibilidad con AWS Academy

SELECT aws_s3.table_import_from_s3(
    'staging.customers', '',
    '(format csv, header true, encoding UTF8)',
    '{bucket}', '{prefix}/olist_customers_dataset.csv', '{region}',
    '{access_key_id}', '{secret_access_key}', '{session_token}'
);

SELECT aws_s3.table_import_from_s3(
    'staging.geolocation', '',
    '(format csv, header true, encoding UTF8)',
    '{bucket}', '{prefix}/olist_geolocation_dataset.csv', '{region}',
    '{access_key_id}', '{secret_access_key}', '{session_token}'
);

SELECT aws_s3.table_import_from_s3(
    'staging.orders', '',
    '(format csv, header true, encoding UTF8)',
    '{bucket}', '{prefix}/olist_orders_dataset.csv', '{region}',
    '{access_key_id}', '{secret_access_key}', '{session_token}'
);

SELECT aws_s3.table_import_from_s3(
    'staging.order_items', '',
    '(format csv, header true, encoding UTF8)',
    '{bucket}', '{prefix}/olist_order_items_dataset.csv', '{region}',
    '{access_key_id}', '{secret_access_key}', '{session_token}'
);

SELECT aws_s3.table_import_from_s3(
    'staging.order_payments', '',
    '(format csv, header true, encoding UTF8)',
    '{bucket}', '{prefix}/olist_order_payments_dataset.csv', '{region}',
    '{access_key_id}', '{secret_access_key}', '{session_token}'
);

SELECT aws_s3.table_import_from_s3(
    'staging.order_reviews', '',
    '(format csv, header true, encoding UTF8)',
    '{bucket}', '{prefix}/olist_order_reviews_dataset.csv', '{region}',
    '{access_key_id}', '{secret_access_key}', '{session_token}'
);

SELECT aws_s3.table_import_from_s3(
    'staging.products', '',
    '(format csv, header true, encoding UTF8)',
    '{bucket}', '{prefix}/olist_products_dataset.csv', '{region}',
    '{access_key_id}', '{secret_access_key}', '{session_token}'
);

SELECT aws_s3.table_import_from_s3(
    'staging.sellers', '',
    '(format csv, header true, encoding UTF8)',
    '{bucket}', '{prefix}/olist_sellers_dataset.csv', '{region}',
    '{access_key_id}', '{secret_access_key}', '{session_token}'
);

SELECT aws_s3.table_import_from_s3(
    'staging.product_category_translation', '',
    '(format csv, header true, encoding UTF8)',
    '{bucket}', '{prefix}/product_category_name_translation.csv', '{region}',
    '{access_key_id}', '{secret_access_key}', '{session_token}'
);
