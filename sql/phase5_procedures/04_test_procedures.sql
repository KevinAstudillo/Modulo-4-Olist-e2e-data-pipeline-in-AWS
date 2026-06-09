-- ============================================================
-- PHASE 5 — Script de prueba y ejecución batch
-- Ejecutar DESPUÉS de los scripts 01, 02 y 03
-- ============================================================

-- ─────────────────────────────────────────────────────────────
-- TEST 1: sp_generar_reporte_mensual — mes individual
-- ─────────────────────────────────────────────────────────────
\echo '=== TEST 1: Reporte agosto 2018 ==='
SELECT * FROM reporting.sp_generar_reporte_mensual(2018, 8);

\echo ''
\echo '=== TEST 2: Reporte noviembre 2017 ==='
SELECT * FROM reporting.sp_generar_reporte_mensual(2017, 11);

-- ─────────────────────────────────────────────────────────────
-- TEST 3: Validación de parámetros — debe lanzar EXCEPTION
-- ─────────────────────────────────────────────────────────────
\echo ''
\echo '=== TEST 3: Mes inválido (debe lanzar error) ==='
DO $$
BEGIN
    PERFORM reporting.sp_generar_reporte_mensual(2018, 13);
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Error capturado correctamente: %', SQLERRM;
END;
$$;

-- ─────────────────────────────────────────────────────────────
-- TEST 4: Batch — generar reporte para TODOS los períodos
--         con datos en el dataset (2016-2018)
-- ─────────────────────────────────────────────────────────────
\echo ''
\echo '=== TEST 4: Batch completo 2016-2018 ==='
DO $$
DECLARE
    v_anio  INT;
    v_mes   INT;
    rec     RECORD;
    v_count INT := 0;
BEGIN
    FOR v_anio IN 2016..2018 LOOP
        FOR v_mes IN 1..12 LOOP
            FOR rec IN
                SELECT * FROM reporting.sp_generar_reporte_mensual(v_anio, v_mes)
            LOOP
                -- Solo muestra períodos con datos reales
                IF rec.ingresos_totales > 0 THEN
                    v_count := v_count + 1;
                    RAISE NOTICE '% | Ingresos: $% | Órdenes: % | MoM: %% | YoY: %%',
                        rec.periodo,
                        TO_CHAR(rec.ingresos_totales, 'FM999,999.00'),
                        rec.total_ordenes,
                        COALESCE(rec.crecimiento_mom_pct::TEXT, 'N/A'),
                        COALESCE(rec.crecimiento_yoy_pct::TEXT, 'N/A');
                END IF;
            END LOOP;
        END LOOP;
    END LOOP;
    RAISE NOTICE '——— Batch completo: % períodos con datos generados. ———', v_count;
END;
$$;

-- ─────────────────────────────────────────────────────────────
-- TEST 5: sp_segmentar_vendedores
-- ─────────────────────────────────────────────────────────────
\echo ''
\echo '=== TEST 5: Segmentación de vendedores ==='
SELECT * FROM reporting.sp_segmentar_vendedores();

-- ─────────────────────────────────────────────────────────────
-- VERIFICACIÓN FINAL: Contenido de las tablas snapshot
-- ─────────────────────────────────────────────────────────────
\echo ''
\echo '=== VERIFICACIÓN: Snapshots mensuales generados ==='
SELECT
    periodo,
    TO_CHAR(ingresos_totales, 'FM$999,999.00') AS ingresos,
    total_ordenes                               AS ordenes,
    TO_CHAR(ticket_promedio,  'FM$999.00')      AS ticket,
    top_categoria_1                             AS cat_top1,
    score_satisfaccion                          AS satisfaccion,
    TO_CHAR(fecha_generacion, 'YYYY-MM-DD HH24:MI') AS generado
FROM reporting.reporte_mensual_snapshot
ORDER BY periodo;

\echo ''
\echo '=== VERIFICACIÓN: Distribución de segmentos de vendedores ==='
SELECT
    segmento,
    COUNT(*)                                           AS vendedores,
    TO_CHAR(AVG(ingresos_total), 'FM$999,999.00')     AS revenue_promedio,
    TO_CHAR(MIN(ingresos_total), 'FM$999,999.00')     AS revenue_min,
    TO_CHAR(MAX(ingresos_total), 'FM$999,999.00')     AS revenue_max,
    TO_CHAR(AVG(total_ordenes),  'FM999.0')           AS ordenes_promedio
FROM reporting.seller_segments
GROUP BY segmento
ORDER BY segmento;

\echo ''
\echo '=== TOP 10 vendedores Segmento A ==='
SELECT
    seller_id,
    ciudad,
    estado,
    TO_CHAR(ingresos_total, 'FM$999,999.00') AS ingresos,
    total_ordenes                             AS ordenes,
    productos_distintos                       AS skus,
    primera_venta,
    ultima_venta
FROM reporting.seller_segments
WHERE segmento = 'A'
ORDER BY ingresos_total DESC
LIMIT 10;
