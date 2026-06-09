-- Fase 4 | Reporting Layer
-- Schema separado sobre el DWH — el dwh nunca se toca para BI
-- Técnicas avanzadas: CTEs, Window Functions (LAG, RANK, SUM OVER)

CREATE SCHEMA IF NOT EXISTS reporting;

-- ─────────────────────────────────────────────────────────────────────────────
-- VISTA 1: Evolución mensual del revenue con crecimiento MoM
-- Técnica: CTE + LAG() window function
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW reporting.vw_revenue_mensual AS
WITH monthly AS (
    SELECT
        dd.year,
        dd.month,
        dd.month_name,
        SUM(f.total_value)          AS revenue,
        COUNT(DISTINCT f.order_id)  AS total_ordenes,
        ROUND(AVG(f.total_value), 2) AS ticket_promedio
    FROM dwh.fact_order_items f
    JOIN dwh.dim_date dd ON f.date_sk = dd.date_sk
    GROUP BY dd.year, dd.month, dd.month_name
)
SELECT
    year,
    month,
    month_name,
    ROUND(revenue, 2)                                               AS revenue,
    total_ordenes,
    ticket_promedio,
    ROUND(LAG(revenue) OVER (ORDER BY year, month), 2)             AS revenue_mes_anterior,
    ROUND(
        (revenue - LAG(revenue) OVER (ORDER BY year, month))
        / NULLIF(LAG(revenue) OVER (ORDER BY year, month), 0) * 100
    , 2)                                                            AS crecimiento_pct
FROM monthly
ORDER BY year, month;


-- ─────────────────────────────────────────────────────────────────────────────
-- VISTA 2: Análisis de Pareto — categorías que generan el 80% del revenue
-- Técnica: CTE + SUM() OVER() acumulado
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW reporting.vw_top_categorias_pareto AS
WITH revenue_categoria AS (
    SELECT
        COALESCE(dp.product_category_name_english, 'Sin categoría') AS categoria,
        SUM(f.total_value)  AS revenue,
        COUNT(*)            AS total_items
    FROM dwh.fact_order_items f
    JOIN dwh.dim_products dp ON f.product_sk = dp.product_sk
    GROUP BY dp.product_category_name_english
),
total AS (
    SELECT SUM(revenue) AS total_revenue FROM revenue_categoria
)
SELECT
    rc.categoria,
    ROUND(rc.revenue, 2)                                                          AS revenue,
    rc.total_items,
    ROUND(rc.revenue / t.total_revenue * 100, 2)                                  AS pct_del_total,
    ROUND(SUM(rc.revenue) OVER (ORDER BY rc.revenue DESC) / t.total_revenue * 100, 2) AS pct_acumulado,
    RANK() OVER (ORDER BY rc.revenue DESC)                                         AS ranking,
    CASE
        WHEN SUM(rc.revenue) OVER (ORDER BY rc.revenue DESC) / t.total_revenue <= 0.8
        THEN 'Top 80%'
        ELSE 'Restante 20%'
    END AS segmento_pareto
FROM revenue_categoria rc, total t
ORDER BY rc.revenue DESC;


-- ─────────────────────────────────────────────────────────────────────────────
-- VISTA 3: Ranking de vendedores por revenue y por volumen de órdenes
-- Técnica: CTE + RANK() OVER() con múltiples particiones
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW reporting.vw_ranking_vendedores AS
WITH metricas AS (
    SELECT
        ds.seller_id,
        ds.seller_city,
        ds.seller_state,
        SUM(f.total_value)              AS revenue_total,
        COUNT(DISTINCT f.order_id)      AS total_ordenes,
        ROUND(AVG(f.total_value), 2)    AS ticket_promedio,
        COUNT(DISTINCT f.product_sk)    AS productos_distintos
    FROM dwh.fact_order_items f
    JOIN dwh.dim_sellers ds ON f.seller_sk = ds.seller_sk
    GROUP BY ds.seller_id, ds.seller_city, ds.seller_state
)
SELECT
    seller_id,
    seller_city,
    seller_state,
    ROUND(revenue_total, 2)                                 AS revenue_total,
    total_ordenes,
    ticket_promedio,
    productos_distintos,
    RANK() OVER (ORDER BY revenue_total DESC)               AS ranking_revenue,
    RANK() OVER (ORDER BY total_ordenes DESC)               AS ranking_ordenes,
    RANK() OVER (ORDER BY ticket_promedio DESC)             AS ranking_ticket
FROM metricas
ORDER BY revenue_total DESC;


-- ─────────────────────────────────────────────────────────────────────────────
-- VISTA 4: Tiempo promedio de entrega por estado del cliente
-- Técnica: CTE + AVG() + RANK() OVER()
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW reporting.vw_tiempo_entrega_estado AS
WITH tiempos AS (
    SELECT
        dc.customer_state                                           AS estado,
        EXTRACT(DAY FROM (
            dor.order_delivered_customer_date - dor.order_purchase_timestamp
        ))                                                          AS dias_entrega
    FROM dwh.fact_order_items f
    JOIN dwh.dim_customers dc  ON f.customer_sk = dc.customer_sk
    JOIN dwh.dim_orders    dor ON f.order_sk    = dor.order_sk
    WHERE dor.order_delivered_customer_date IS NOT NULL
      AND dor.order_purchase_timestamp      IS NOT NULL
      AND dor.order_delivered_customer_date > dor.order_purchase_timestamp
)
SELECT
    estado,
    ROUND(AVG(dias_entrega), 1)                             AS dias_promedio,
    MIN(dias_entrega)                                       AS entrega_minima,
    MAX(dias_entrega)                                       AS entrega_maxima,
    COUNT(*)                                                AS total_entregas,
    RANK() OVER (ORDER BY AVG(dias_entrega) ASC)            AS ranking_mejor_entrega,
    RANK() OVER (ORDER BY AVG(dias_entrega) DESC)           AS ranking_peor_entrega
FROM tiempos
GROUP BY estado
ORDER BY dias_promedio ASC;


-- ─────────────────────────────────────────────────────────────────────────────
-- VISTA 5: Satisfacción del cliente por categoría de producto
-- Técnica: CTE + JOIN entre fact tables + RANK() OVER()
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW reporting.vw_satisfaccion_cliente AS
WITH base AS (
    SELECT
        COALESCE(dp.product_category_name_english, 'Sin categoría') AS categoria,
        fr.review_score,
        f.total_value
    FROM dwh.fact_order_items f
    JOIN dwh.dim_products  dp ON f.product_sk  = dp.product_sk
    JOIN dwh.fact_reviews  fr ON f.order_id    = fr.order_id
    WHERE fr.review_score IS NOT NULL
)
SELECT
    categoria,
    ROUND(AVG(review_score), 2)                                                     AS score_promedio,
    COUNT(*)                                                                         AS total_reviews,
    SUM(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END)                              AS reviews_positivas,
    SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END)                              AS reviews_negativas,
    ROUND(SUM(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END)::NUMERIC / COUNT(*) * 100, 1) AS pct_satisfaccion,
    ROUND(AVG(total_value), 2)                                                       AS ticket_promedio,
    RANK() OVER (ORDER BY AVG(review_score) DESC)                                    AS ranking_satisfaccion
FROM base
GROUP BY categoria
HAVING COUNT(*) >= 50
ORDER BY score_promedio DESC;
