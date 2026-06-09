-- ============================================================
-- PHASE 5 — Stored Procedure #1
-- Función : reporting.sp_generar_reporte_mensual(p_anio, p_mes)
-- Objetivo: Genera un snapshot de KPIs ejecutivos para un
--           período YYYY-MM, calcula variaciones MoM y YoY,
--           identifica top 3 categorías y vendedores, y hace
--           upsert en reporting.reporte_mensual_snapshot.
--
-- Técnicas PL/pgSQL demostradas:
--   • DECLARE variables tipadas
--   • Validación de parámetros con RAISE EXCEPTION / ERRCODE
--   • RAISE NOTICE para logging operacional
--   • make_date() y aritmética de intervalos
--   • SELECT … INTO para asignación desde query
--   • CTEs dentro de RETURN QUERY
--   • LAG / CROSS JOIN con múltiples CTEs
--   • UPSERT con ON CONFLICT … DO UPDATE
--   • GET DIAGNOSTICS ROW_COUNT
--   • Bloque EXCEPTION con re-raise y mensaje genérico
-- ============================================================

CREATE OR REPLACE FUNCTION reporting.sp_generar_reporte_mensual(
    p_anio  INT,
    p_mes   INT
)
RETURNS TABLE (
    periodo                 VARCHAR(7),
    ingresos_totales        NUMERIC(15,2),
    ingresos_mes_anterior   NUMERIC(15,2),
    crecimiento_mom_pct     NUMERIC(8,2),
    ingresos_anio_anterior  NUMERIC(15,2),
    crecimiento_yoy_pct     NUMERIC(8,2),
    total_ordenes           BIGINT,
    ticket_promedio         NUMERIC(10,2),
    top_categoria_1         TEXT,
    top_categoria_2         TEXT,
    top_categoria_3         TEXT,
    top_vendedor_1          TEXT,
    top_vendedor_2          TEXT,
    top_vendedor_3          TEXT,
    score_satisfaccion_avg  NUMERIC(4,2)
)
LANGUAGE plpgsql
AS $$
-- ─── Variables de control ──────────────────────────────────
DECLARE
    v_fecha_inicio  DATE;
    v_fecha_fin     DATE;
    v_periodo       VARCHAR(7);
    v_rows_afectadas INTEGER;
    -- Top-N helpers (pivot manual)
    v_cat1  TEXT;  v_cat2  TEXT;  v_cat3  TEXT;
    v_vend1 TEXT;  v_vend2 TEXT;  v_vend3 TEXT;
BEGIN

    -- ══════════════════════════════════════════════════════
    -- 1. VALIDACIÓN DE PARÁMETROS
    -- ══════════════════════════════════════════════════════
    IF p_mes NOT BETWEEN 1 AND 12 THEN
        RAISE EXCEPTION
            'Mes inválido: %. El parámetro p_mes debe estar entre 1 y 12.', p_mes
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    IF p_anio NOT BETWEEN 2000 AND 2100 THEN
        RAISE EXCEPTION
            'Año fuera de rango: %. Use un valor entre 2000 y 2100.', p_anio
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    -- ══════════════════════════════════════════════════════
    -- 2. CALCULAR RANGO DE FECHAS DEL PERÍODO
    -- ══════════════════════════════════════════════════════
    v_fecha_inicio := make_date(p_anio, p_mes, 1);
    v_fecha_fin    := (v_fecha_inicio + INTERVAL '1 month' - INTERVAL '1 day')::DATE;
    v_periodo      := TO_CHAR(v_fecha_inicio, 'YYYY-MM');

    RAISE NOTICE '[sp_generar_reporte_mensual] Iniciando cálculo para período: % (% → %)',
        v_periodo, v_fecha_inicio, v_fecha_fin;

    -- ══════════════════════════════════════════════════════
    -- 3. TOP 3 CATEGORÍAS POR REVENUE EN EL PERÍODO
    --    Técnica: pivot con MAX + CASE sobre ROW_NUMBER()
    -- ══════════════════════════════════════════════════════
    SELECT
        MAX(CASE WHEN rn = 1 THEN categoria END),
        MAX(CASE WHEN rn = 2 THEN categoria END),
        MAX(CASE WHEN rn = 3 THEN categoria END)
    INTO v_cat1, v_cat2, v_cat3
    FROM (
        SELECT
            COALESCE(p.category_name_english, p.category_name, 'Sin Categoría') AS categoria,
            ROW_NUMBER() OVER (ORDER BY SUM(fi.total_value) DESC)               AS rn
        FROM dwh.fact_order_items fi
        JOIN dwh.dim_products     p  ON fi.product_sk = p.product_sk
        JOIN dwh.dim_date         dd ON fi.date_sk    = dd.date_sk
        WHERE dd.full_date BETWEEN v_fecha_inicio AND v_fecha_fin
        GROUP BY COALESCE(p.category_name_english, p.category_name, 'Sin Categoría')
    ) ranked
    WHERE rn <= 3;

    RAISE NOTICE '[sp_generar_reporte_mensual] Top 3 categorías: %, %, %',
        COALESCE(v_cat1,'—'), COALESCE(v_cat2,'—'), COALESCE(v_cat3,'—');

    -- ══════════════════════════════════════════════════════
    -- 4. TOP 3 VENDEDORES POR REVENUE EN EL PERÍODO
    -- ══════════════════════════════════════════════════════
    SELECT
        MAX(CASE WHEN rn = 1 THEN vendedor END),
        MAX(CASE WHEN rn = 2 THEN vendedor END),
        MAX(CASE WHEN rn = 3 THEN vendedor END)
    INTO v_vend1, v_vend2, v_vend3
    FROM (
        SELECT
            s.seller_id                                                  AS vendedor,
            ROW_NUMBER() OVER (ORDER BY SUM(fi.total_value) DESC)       AS rn
        FROM dwh.fact_order_items fi
        JOIN dwh.dim_sellers      s  ON fi.seller_sk = s.seller_sk
        JOIN dwh.dim_date         dd ON fi.date_sk   = dd.date_sk
        WHERE dd.full_date BETWEEN v_fecha_inicio AND v_fecha_fin
        GROUP BY s.seller_id
    ) ranked
    WHERE rn <= 3;

    RAISE NOTICE '[sp_generar_reporte_mensual] Top 3 vendedores: %, %, %',
        COALESCE(v_vend1,'—'), COALESCE(v_vend2,'—'), COALESCE(v_vend3,'—');

    -- ══════════════════════════════════════════════════════
    -- 5. UPSERT EN TABLA SNAPSHOT
    --    Si ya existe el período, actualiza los valores
    -- ══════════════════════════════════════════════════════
    INSERT INTO reporting.reporte_mensual_snapshot (
        periodo,
        fecha_generacion,
        ingresos_totales,
        total_ordenes,
        ticket_promedio,
        top_categoria_1, top_categoria_2, top_categoria_3,
        top_vendedor_1,  top_vendedor_2,  top_vendedor_3,
        score_satisfaccion
    )
    SELECT
        v_periodo,
        NOW(),
        COALESCE(SUM(fi.total_value), 0),
        COUNT(DISTINCT fi.order_id),
        COALESCE(AVG(fi.total_value),  0),
        v_cat1,  v_cat2,  v_cat3,
        v_vend1, v_vend2, v_vend3,
        (
            SELECT AVG(fr.review_score::NUMERIC)
            FROM dwh.fact_order_items   fi2
            JOIN dwh.dim_date           dd2 ON fi2.date_sk  = dd2.date_sk
            JOIN dwh.fact_reviews       fr  ON fi2.order_id = fr.order_id
            WHERE dd2.full_date BETWEEN v_fecha_inicio AND v_fecha_fin
              AND fr.review_score IS NOT NULL
        )
    FROM dwh.fact_order_items fi
    JOIN dwh.dim_date         dd ON fi.date_sk = dd.date_sk
    WHERE dd.full_date BETWEEN v_fecha_inicio AND v_fecha_fin
    ON CONFLICT (periodo) DO UPDATE
        SET fecha_generacion  = EXCLUDED.fecha_generacion,
            ingresos_totales  = EXCLUDED.ingresos_totales,
            total_ordenes     = EXCLUDED.total_ordenes,
            ticket_promedio   = EXCLUDED.ticket_promedio,
            top_categoria_1   = EXCLUDED.top_categoria_1,
            top_categoria_2   = EXCLUDED.top_categoria_2,
            top_categoria_3   = EXCLUDED.top_categoria_3,
            top_vendedor_1    = EXCLUDED.top_vendedor_1,
            top_vendedor_2    = EXCLUDED.top_vendedor_2,
            top_vendedor_3    = EXCLUDED.top_vendedor_3,
            score_satisfaccion = EXCLUDED.score_satisfaccion;

    GET DIAGNOSTICS v_rows_afectadas = ROW_COUNT;
    RAISE NOTICE '[sp_generar_reporte_mensual] Snapshot actualizado para % — % fila(s) afectada(s).',
        v_periodo, v_rows_afectadas;

    -- ══════════════════════════════════════════════════════
    -- 6. RETURN QUERY — KPIs completos con comparativas
    --    CTEs: mes_actual | mes_anterior | anio_anterior | satisfaccion
    -- ══════════════════════════════════════════════════════
    RETURN QUERY
    WITH mes_actual AS (
        SELECT
            COALESCE(SUM(fi.total_value), 0)         AS ingresos,
            COUNT(DISTINCT fi.order_id)               AS ordenes,
            COALESCE(AVG(fi.total_value), 0)          AS ticket
        FROM dwh.fact_order_items fi
        JOIN dwh.dim_date         dd ON fi.date_sk = dd.date_sk
        WHERE dd.full_date BETWEEN v_fecha_inicio AND v_fecha_fin
    ),
    mes_anterior AS (
        SELECT COALESCE(SUM(fi.total_value), 0) AS ingresos
        FROM dwh.fact_order_items fi
        JOIN dwh.dim_date         dd ON fi.date_sk = dd.date_sk
        WHERE dd.full_date
              BETWEEN (v_fecha_inicio - INTERVAL '1 month')::DATE
                  AND (v_fecha_fin   - INTERVAL '1 month')::DATE
    ),
    anio_anterior AS (
        SELECT COALESCE(SUM(fi.total_value), 0) AS ingresos
        FROM dwh.fact_order_items fi
        JOIN dwh.dim_date         dd ON fi.date_sk = dd.date_sk
        WHERE dd.full_date
              BETWEEN (v_fecha_inicio - INTERVAL '1 year')::DATE
                  AND (v_fecha_fin   - INTERVAL '1 year')::DATE
    ),
    satisfaccion AS (
        SELECT COALESCE(AVG(fr.review_score::NUMERIC), 0) AS score
        FROM dwh.fact_order_items fi
        JOIN dwh.dim_date         dd ON fi.date_sk  = dd.date_sk
        JOIN dwh.fact_reviews      fr ON fi.order_id = fr.order_id
        WHERE dd.full_date BETWEEN v_fecha_inicio AND v_fecha_fin
          AND fr.review_score IS NOT NULL
    )
    SELECT
        v_periodo::VARCHAR(7),
        -- Métricas del período actual
        ma.ingresos::NUMERIC(15,2),
        -- Comparativa mes anterior
        prev.ingresos::NUMERIC(15,2),
        CASE
            WHEN prev.ingresos = 0 THEN NULL
            ELSE ROUND(((ma.ingresos - prev.ingresos) / prev.ingresos) * 100, 2)
        END::NUMERIC(8,2)                               AS crecimiento_mom_pct,
        -- Comparativa año anterior
        anio.ingresos::NUMERIC(15,2),
        CASE
            WHEN anio.ingresos = 0 THEN NULL
            ELSE ROUND(((ma.ingresos - anio.ingresos) / anio.ingresos) * 100, 2)
        END::NUMERIC(8,2)                               AS crecimiento_yoy_pct,
        -- Volumen y ticket
        ma.ordenes::BIGINT,
        ma.ticket::NUMERIC(10,2),
        -- Top-N (calculados en pasos 3 y 4)
        v_cat1, v_cat2, v_cat3,
        v_vend1, v_vend2, v_vend3,
        -- Satisfacción
        sat.score::NUMERIC(4,2)
    FROM mes_actual  ma
    CROSS JOIN mes_anterior  prev
    CROSS JOIN anio_anterior anio
    CROSS JOIN satisfaccion  sat;

-- ══════════════════════════════════════════════════════════
-- MANEJO DE ERRORES
-- ══════════════════════════════════════════════════════════
EXCEPTION
    WHEN invalid_parameter_value THEN
        -- Re-lanza el error de validación sin modificarlo
        RAISE;
    WHEN OTHERS THEN
        RAISE EXCEPTION
            '[sp_generar_reporte_mensual] Error inesperado generando reporte %: [SQLSTATE %] %',
            v_periodo, SQLSTATE, SQLERRM;
END;
$$;

-- ─────────────────────────────────────────────────────────────
-- Metadata y permisos
-- ─────────────────────────────────────────────────────────────
COMMENT ON FUNCTION reporting.sp_generar_reporte_mensual(INT, INT) IS
    'Genera snapshot ejecutivo mensual con KPIs de revenue, ordenes, ticket, '
    'variaciones MoM/YoY, top 3 categorías y vendedores, y score de satisfacción. '
    'Hace UPSERT en reporting.reporte_mensual_snapshot. '
    'Uso: SELECT * FROM reporting.sp_generar_reporte_mensual(2018, 8);';
