-- Fase 4 | Validar que todas las vistas retornan datos

SELECT 'vw_revenue_mensual'       AS vista, COUNT(*) AS filas FROM reporting.vw_revenue_mensual
UNION ALL
SELECT 'vw_top_categorias_pareto',          COUNT(*) FROM reporting.vw_top_categorias_pareto
UNION ALL
SELECT 'vw_ranking_vendedores',             COUNT(*) FROM reporting.vw_ranking_vendedores
UNION ALL
SELECT 'vw_tiempo_entrega_estado',          COUNT(*) FROM reporting.vw_tiempo_entrega_estado
UNION ALL
SELECT 'vw_satisfaccion_cliente',           COUNT(*) FROM reporting.vw_satisfaccion_cliente
ORDER BY vista;
