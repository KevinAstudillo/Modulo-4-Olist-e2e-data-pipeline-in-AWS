"""
Tests de integración: verifica las vistas del schema reporting.
Requiere conexión activa a Aurora PostgreSQL.
"""
import pytest
from decimal import Decimal


@pytest.mark.integration
class TestViewRowCounts:
    """Las 5 vistas deben retornar exactamente los registros documentados."""

    def test_vw_revenue_mensual_count(self, cursor):
        cursor.execute("SELECT COUNT(*) FROM reporting.vw_revenue_mensual")
        assert cursor.fetchone()[0] == 24

    def test_vw_top_categorias_pareto_count(self, cursor):
        cursor.execute("SELECT COUNT(*) FROM reporting.vw_top_categorias_pareto")
        assert cursor.fetchone()[0] == 72

    def test_vw_ranking_vendedores_count(self, cursor):
        cursor.execute("SELECT COUNT(*) FROM reporting.vw_ranking_vendedores")
        assert cursor.fetchone()[0] == 3_095

    def test_vw_tiempo_entrega_estado_count(self, cursor):
        cursor.execute("SELECT COUNT(*) FROM reporting.vw_tiempo_entrega_estado")
        assert cursor.fetchone()[0] == 27

    def test_vw_satisfaccion_cliente_count(self, cursor):
        cursor.execute("SELECT COUNT(*) FROM reporting.vw_satisfaccion_cliente")
        assert cursor.fetchone()[0] == 60


@pytest.mark.integration
class TestRevenueView:
    """Spot-checks de vw_revenue_mensual contra datos del README."""

    def test_noviembre_2017_es_el_pico(self, cursor):
        """Noviembre 2017 debe ser el mes con mayor revenue (Black Friday)."""
        cursor.execute("""
            SELECT year, month FROM reporting.vw_revenue_mensual
            ORDER BY revenue DESC LIMIT 1
        """)
        year, month = cursor.fetchone()
        assert year == 2017 and month == 11, \
            f"El pico de revenue esperado es Nov-2017, encontrado: {year}-{month:02d}"

    def test_crecimiento_noviembre_2017(self, cursor):
        """Noviembre 2017 debe tener crecimiento MoM de ~53.27%."""
        cursor.execute("""
            SELECT crecimiento_pct FROM reporting.vw_revenue_mensual
            WHERE year = 2017 AND month = 11
        """)
        pct = float(cursor.fetchone()[0])
        assert 50.0 <= pct <= 56.0, \
            f"Crecimiento Nov-2017 esperado ~53.27%, encontrado {pct:.2f}%"

    def test_revenue_creciente_2017_a_2018(self, cursor):
        """Revenue promedio de 2018 debe ser mayor que el de 2017."""
        cursor.execute("""
            SELECT year, AVG(revenue) FROM reporting.vw_revenue_mensual
            GROUP BY year ORDER BY year
        """)
        rows = cursor.fetchall()
        rev_2017 = float(next(r[1] for r in rows if r[0] == 2017))
        rev_2018 = float(next(r[1] for r in rows if r[0] == 2018))
        assert rev_2018 > rev_2017, \
            "Revenue promedio 2018 debe ser mayor que 2017"


@pytest.mark.integration
class TestParetoView:
    """Spot-checks de vw_top_categorias_pareto."""

    def test_health_beauty_es_ranking_1(self, cursor):
        """health_beauty debe ser la categoría #1 por revenue."""
        cursor.execute("""
            SELECT categoria FROM reporting.vw_top_categorias_pareto
            WHERE ranking = 1
        """)
        assert cursor.fetchone()[0] == "health_beauty"

    def test_pareto_80_pct_en_menos_de_20_categorias(self, cursor):
        """Menos del 28% de las categorías deben cubrir el 80% del revenue."""
        cursor.execute("""
            SELECT COUNT(*) FROM reporting.vw_top_categorias_pareto
            WHERE segmento_pareto = 'Top 80%'
        """)
        count = cursor.fetchone()[0]
        assert count <= 20, \
            f"{count} categorías cubren el 80% del revenue (Pareto: esperado ≤20)"

    def test_pct_acumulado_es_creciente(self, cursor):
        """pct_acumulado debe ser siempre creciente (vista ordenada correctamente)."""
        cursor.execute("""
            SELECT pct_acumulado FROM reporting.vw_top_categorias_pareto
            ORDER BY ranking
        """)
        valores = [float(r[0]) for r in cursor.fetchall()]
        assert valores == sorted(valores), \
            "pct_acumulado no es creciente — la curva de Pareto está mal calculada"


@pytest.mark.integration
class TestEntregaView:
    """Spot-checks de vw_tiempo_entrega_estado."""

    def test_sp_es_el_mas_rapido(self, cursor):
        """SP debe tener ranking_mejor_entrega = 1 (más rápido)."""
        cursor.execute("""
            SELECT ranking_mejor_entrega FROM reporting.vw_tiempo_entrega_estado
            WHERE estado = 'SP'
        """)
        assert cursor.fetchone()[0] == 1, "SP debe ser el estado con entrega más rápida"

    def test_sp_dias_promedio(self, cursor):
        """SP debe tener ~8.3 días promedio de entrega."""
        cursor.execute("""
            SELECT dias_promedio FROM reporting.vw_tiempo_entrega_estado
            WHERE estado = 'SP'
        """)
        dias = float(cursor.fetchone()[0])
        assert 7.0 <= dias <= 10.0, \
            f"SP días promedio esperado ~8.3, encontrado {dias}"

    def test_norte_tiene_peor_entrega(self, cursor):
        """Los estados del norte (AP, RR, AM) deben estar en el top 5 de peores tiempos."""
        cursor.execute("""
            SELECT estado FROM reporting.vw_tiempo_entrega_estado
            WHERE ranking_peor_entrega <= 5
        """)
        peores = {r[0] for r in cursor.fetchall()}
        norte = {"AP", "RR", "AM"}
        assert norte & peores, \
            f"Ningún estado del norte en el top 5 de peores entregas. Top 5: {peores}"


@pytest.mark.integration
class TestSatisfaccionView:
    """Spot-checks de vw_satisfaccion_cliente."""

    def test_books_lidera_satisfaccion(self, cursor):
        """books_general_interest debe estar en el top 3 de satisfacción."""
        cursor.execute("""
            SELECT ranking_satisfaccion FROM reporting.vw_satisfaccion_cliente
            WHERE categoria = 'books_general_interest'
        """)
        ranking = cursor.fetchone()[0]
        assert ranking <= 3, \
            f"books_general_interest está en ranking {ranking}, esperado ≤3"

    def test_office_furniture_peor_satisfaccion(self, cursor):
        """office_furniture debe estar en el bottom 5 de satisfacción."""
        cursor.execute("""
            SELECT ranking_satisfaccion FROM reporting.vw_satisfaccion_cliente
            WHERE categoria = 'office_furniture'
        """)
        ranking = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM reporting.vw_satisfaccion_cliente")
        total = cursor.fetchone()[0]
        assert ranking >= total - 4, \
            f"office_furniture en ranking {ranking}/{total}, esperado en el bottom 5"

    def test_minimo_50_reviews_por_categoria(self, cursor):
        """Ninguna categoría debe tener menos de 50 reseñas (filtro HAVING)."""
        cursor.execute("""
            SELECT MIN(total_reviews) FROM reporting.vw_satisfaccion_cliente
        """)
        assert cursor.fetchone()[0] >= 50, \
            "Existe al menos una categoría con menos de 50 reseñas en la vista"

    def test_scores_en_rango_valido(self, cursor):
        """score_promedio debe estar siempre entre 1.0 y 5.0."""
        cursor.execute("""
            SELECT COUNT(*) FROM reporting.vw_satisfaccion_cliente
            WHERE score_promedio < 1.0 OR score_promedio > 5.0
        """)
        assert cursor.fetchone()[0] == 0, \
            "Existen categorías con score_promedio fuera del rango 1-5"
