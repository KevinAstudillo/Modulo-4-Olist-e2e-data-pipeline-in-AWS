-- ============================================================
-- PHASE 5 — Stored Procedure #2
-- Función : reporting.sp_segmentar_vendedores()
-- Objetivo: Clasifica a TODOS los vendedores activos en
--           segmentos A/B/C/D según cuartil de ingresos totales
--           (NTILE 4). Usa un cursor FOR para iterar e insertar
--           fila a fila con logging de progreso, luego retorna
--           el resumen agregado por segmento.
--
-- Técnicas PL/pgSQL demostradas:
--   • DECLARE con múltiples tipos (INTEGER, RECORD, CHAR)
--   • TRUNCATE antes de recalcular
--   • SELECT … INTO para conteo inicial
--   • Cursor implícito con FOR r IN (...) LOOP
--   • NTILE(4) dentro del query del cursor
--   • CASE … WHEN en asignación de variable
--   • INSERT individual dentro del loop
--   • Modulo (%) para logging periódico cada 500 registros
--   • GET DIAGNOSTICS ROW_COUNT
--   • RETURNS TABLE con RETURN QUERY y GROUP BY
--   • Bloque EXCEPTION genérico con SQLSTATE/SQLERRM
-- ============================================================

CREATE OR REPLACE FUNCTION reporting.sp_segmentar_vendedores()
RETURNS TABLE (
    segmento         CHAR(1),
    descripcion      VARCHAR(30),
    total_vendedores BIGINT,
    ingresos_min     NUMERIC(15,2),
    ingresos_max     NUMERIC(15,2),
    ingresos_avg     NUMERIC(15,2),
    ingresos_total   NUMERIC(15,2),
    pct_del_total    NUMERIC(6,2)
)
LANGUAGE plpgsql
AS $$
-- ─── Variables de control ──────────────────────────────────
DECLARE
    v_total_vendedores  INTEGER;
    v_procesados        INTEGER := 0;
    v_ingreso_global    NUMERIC(15,2);
    r_vendedor          RECORD;
    v_segmento          CHAR(1);
BEGIN

    -- ══════════════════════════════════════════════════════
    -- 1. INICIALIZACIÓN
    -- ══════════════════════════════════════════════════════
    RAISE NOTICE '[sp_segmentar_vendedores] ══ Iniciando segmentación de vendedores ══';

    -- Limpiar tabla destino para recalcular desde cero
    TRUNCATE TABLE reporting.seller_segments;
    RAISE NOTICE '[sp_segmentar_vendedores] Tabla seller_segments vaciada (TRUNCATE).';

    -- Contar vendedores activos con al menos una venta
    SELECT COUNT(DISTINCT seller_sk)
    INTO   v_total_vendedores
    FROM   dwh.fact_order_items;

    -- Calcular revenue global para porcentajes
    SELECT COALESCE(SUM(total_value), 0)
    INTO   v_ingreso_global
    FROM   dwh.fact_order_items;

    RAISE NOTICE '[sp_segmentar_vendedores] Vendedores activos: %  |  Revenue global: $%',
        v_total_vendedores,
        TO_CHAR(v_ingreso_global, 'FM999,999,999.00');

    IF v_total_vendedores = 0 THEN
        RAISE EXCEPTION '[sp_segmentar_vendedores] No se encontraron vendedores activos en dwh.fact_order_items.'
            USING ERRCODE = 'no_data_found';
    END IF;

    -- ══════════════════════════════════════════════════════
    -- 2. CURSOR FOR: Calcular métricas + NTILE y recorrer
    --    fila por fila para insertar en seller_segments
    -- ══════════════════════════════════════════════════════
    FOR r_vendedor IN
        WITH metricas_vendedor AS (
            SELECT
                s.seller_sk,
                s.seller_id,
                s.city                                      AS ciudad,
                s.state                                     AS estado,
                COALESCE(SUM(fi.total_value), 0)            AS ingresos_total,
                COUNT(DISTINCT fi.order_id)                 AS total_ordenes,
                COUNT(DISTINCT fi.product_sk)               AS productos_distintos,
                COALESCE(AVG(fi.total_value), 0)            AS ticket_promedio,
                MIN(dd.full_date)                           AS primera_venta,
                MAX(dd.full_date)                           AS ultima_venta
            FROM dwh.fact_order_items fi
            JOIN dwh.dim_sellers      s  ON fi.seller_sk = s.seller_sk
            JOIN dwh.dim_date         dd ON fi.date_sk   = dd.date_sk
            GROUP BY s.seller_sk, s.seller_id, s.city, s.state
        ),
        con_cuartil AS (
            SELECT
                *,
                -- NTILE(4) ordena por ingresos desc: cuartil 1 = top 25%
                NTILE(4) OVER (ORDER BY ingresos_total DESC) AS cuartil
            FROM metricas_vendedor
        )
        SELECT
            c.*,
            CASE c.cuartil
                WHEN 1 THEN 'A'
                WHEN 2 THEN 'B'
                WHEN 3 THEN 'C'
                WHEN 4 THEN 'D'
                ELSE       'D'   -- fallback defensivo
            END AS segmento_calculado
        FROM con_cuartil c
        ORDER BY c.ingresos_total DESC
    LOOP
        -- Asignar segmento a variable local
        v_segmento := r_vendedor.segmento_calculado;

        -- Insertar fila en tabla destino
        INSERT INTO reporting.seller_segments (
            seller_sk,
            seller_id,
            ciudad,
            estado,
            ingresos_total,
            total_ordenes,
            productos_distintos,
            ticket_promedio,
            primera_venta,
            ultima_venta,
            segmento,
            fecha_segmentacion
        ) VALUES (
            r_vendedor.seller_sk,
            r_vendedor.seller_id,
            r_vendedor.ciudad,
            r_vendedor.estado,
            r_vendedor.ingresos_total,
            r_vendedor.total_ordenes,
            r_vendedor.productos_distintos,
            r_vendedor.ticket_promedio,
            r_vendedor.primera_venta,
            r_vendedor.ultima_venta,
            v_segmento,
            NOW()
        );

        v_procesados := v_procesados + 1;

        -- Log de progreso cada 500 registros
        IF v_procesados % 500 = 0 THEN
            RAISE NOTICE '[sp_segmentar_vendedores] Progreso: %/% vendedores procesados...',
                v_procesados, v_total_vendedores;
        END IF;

    END LOOP;

    RAISE NOTICE '[sp_segmentar_vendedores] ✓ Segmentación completa: % vendedores clasificados en A/B/C/D.',
        v_procesados;

    -- ══════════════════════════════════════════════════════
    -- 3. RETURN QUERY — Resumen ejecutivo por segmento
    --    Incluye % del revenue total aportado por cada segmento
    -- ══════════════════════════════════════════════════════
    RETURN QUERY
    SELECT
        ss.segmento::CHAR(1),
        CASE ss.segmento
            WHEN 'A' THEN 'Alto rendimiento'
            WHEN 'B' THEN 'Medio-alto'
            WHEN 'C' THEN 'Medio-bajo'
            WHEN 'D' THEN 'Bajo rendimiento'
        END::VARCHAR(30)                            AS descripcion,
        COUNT(*)::BIGINT                            AS total_vendedores,
        MIN(ss.ingresos_total)::NUMERIC(15,2)       AS ingresos_min,
        MAX(ss.ingresos_total)::NUMERIC(15,2)       AS ingresos_max,
        AVG(ss.ingresos_total)::NUMERIC(15,2)       AS ingresos_avg,
        SUM(ss.ingresos_total)::NUMERIC(15,2)       AS ingresos_total,
        ROUND(
            (SUM(ss.ingresos_total) / NULLIF(v_ingreso_global, 0)) * 100,
            2
        )::NUMERIC(6,2)                             AS pct_del_total
    FROM reporting.seller_segments ss
    GROUP BY ss.segmento
    ORDER BY ss.segmento;

-- ══════════════════════════════════════════════════════════
-- MANEJO DE ERRORES
-- ══════════════════════════════════════════════════════════
EXCEPTION
    WHEN no_data_found THEN
        RAISE;
    WHEN OTHERS THEN
        RAISE EXCEPTION
            '[sp_segmentar_vendedores] Error durante segmentación en el vendedor #% de %: [SQLSTATE %] %',
            v_procesados, v_total_vendedores, SQLSTATE, SQLERRM;
END;
$$;

-- ─────────────────────────────────────────────────────────────
-- Metadata
-- ─────────────────────────────────────────────────────────────
COMMENT ON FUNCTION reporting.sp_segmentar_vendedores() IS
    'Clasifica todos los vendedores activos en segmentos A/B/C/D por cuartil '
    'de revenue usando NTILE(4). Usa cursor FOR para iterar e insertar en '
    'reporting.seller_segments. Retorna resumen por segmento con % del total. '
    'Uso: SELECT * FROM reporting.sp_segmentar_vendedores();';
