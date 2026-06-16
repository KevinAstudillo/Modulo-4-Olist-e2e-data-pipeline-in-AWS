"""
Tests de integración: verifica el Star Schema en Aurora (schema dwh).
Requiere conexión activa a Aurora PostgreSQL.
"""
import pytest


# ── Row counts esperados (valores reales del dataset Olist) ──────────────────
EXPECTED_COUNTS = {
    "dwh.dim_customers":   99_441,
    "dwh.dim_products":    32_951,
    "dwh.dim_sellers":      3_095,
    "dwh.dim_orders":      99_441,
    "dwh.dim_date":           774,
    "dwh.fact_order_items": 112_650,
    "dwh.fact_payments":   103_886,
    "dwh.fact_reviews":     99_224,
}


@pytest.mark.integration
@pytest.mark.parametrize("table, expected", EXPECTED_COUNTS.items())
def test_table_row_count(cursor, table, expected):
    """Cada tabla del DWH debe tener exactamente los registros esperados."""
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    actual = cursor.fetchone()[0]
    assert actual == expected, \
        f"{table}: esperado {expected:,} filas, encontrado {actual:,}"


@pytest.mark.integration
def test_fact_order_items_no_null_fks(cursor):
    """fact_order_items no debe tener NULL en ninguna FK (customer, product, seller, order, date)."""
    cursor.execute("""
        SELECT
            SUM(CASE WHEN customer_sk IS NULL THEN 1 ELSE 0 END) AS null_customer,
            SUM(CASE WHEN product_sk  IS NULL THEN 1 ELSE 0 END) AS null_product,
            SUM(CASE WHEN seller_sk   IS NULL THEN 1 ELSE 0 END) AS null_seller,
            SUM(CASE WHEN order_sk    IS NULL THEN 1 ELSE 0 END) AS null_order,
            SUM(CASE WHEN date_sk     IS NULL THEN 1 ELSE 0 END) AS null_date
        FROM dwh.fact_order_items
    """)
    row = cursor.fetchone()
    assert all(v == 0 for v in row), \
        f"FKs con NULL en fact_order_items: customer={row[0]}, product={row[1]}, " \
        f"seller={row[2]}, order={row[3]}, date={row[4]}"


@pytest.mark.integration
def test_fact_payments_order_sk_coverage(cursor):
    """Al menos el 99% de fact_payments debe tener order_sk resuelto (no NULL)."""
    cursor.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN order_sk IS NULL THEN 1 ELSE 0 END) AS sin_order_sk
        FROM dwh.fact_payments
    """)
    total, sin_sk = cursor.fetchone()
    pct_resuelto = (total - sin_sk) / total * 100
    assert pct_resuelto >= 99.0, \
        f"Solo {pct_resuelto:.1f}% de fact_payments tiene order_sk resuelto (esperado ≥99%)"


@pytest.mark.integration
def test_fact_reviews_order_sk_coverage(cursor):
    """Al menos el 99% de fact_reviews debe tener order_sk resuelto (no NULL)."""
    cursor.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN order_sk IS NULL THEN 1 ELSE 0 END) AS sin_order_sk
        FROM dwh.fact_reviews
    """)
    total, sin_sk = cursor.fetchone()
    pct_resuelto = (total - sin_sk) / total * 100
    assert pct_resuelto >= 99.0, \
        f"Solo {pct_resuelto:.1f}% de fact_reviews tiene order_sk resuelto (esperado ≥99%)"


@pytest.mark.integration
def test_fact_payments_order_sk_integrity(cursor):
    """order_sk en fact_payments debe coincidir con order_id en dim_orders."""
    cursor.execute("""
        SELECT COUNT(*)
        FROM dwh.fact_payments fp
        JOIN dwh.dim_orders dor ON fp.order_sk = dor.order_sk
        WHERE fp.order_id <> dor.order_id
    """)
    mismatches = cursor.fetchone()[0]
    assert mismatches == 0, \
        f"{mismatches} filas en fact_payments tienen order_sk que no coincide con order_id"


@pytest.mark.integration
def test_no_negative_prices(cursor):
    """fact_order_items no debe tener precios negativos."""
    cursor.execute("""
        SELECT COUNT(*) FROM dwh.fact_order_items
        WHERE price < 0 OR freight_value < 0 OR total_value < 0
    """)
    assert cursor.fetchone()[0] == 0, "Existen precios negativos en fact_order_items"


@pytest.mark.integration
def test_review_scores_in_range(cursor):
    """Todos los review_score deben estar entre 1 y 5."""
    cursor.execute("""
        SELECT COUNT(*) FROM dwh.fact_reviews
        WHERE review_score NOT BETWEEN 1 AND 5
          AND review_score IS NOT NULL
    """)
    assert cursor.fetchone()[0] == 0, "Existen review_score fuera del rango 1-5"


@pytest.mark.integration
def test_dim_date_no_gaps(cursor):
    """dim_date debe tener 774 días consecutivos sin huecos."""
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT full_date,
                   LEAD(full_date) OVER (ORDER BY full_date) AS next_date
            FROM dwh.dim_date
        ) t
        WHERE next_date - full_date > 1
    """)
    gaps = cursor.fetchone()[0]
    assert gaps == 0, f"dim_date tiene {gaps} huecos en el calendario"
