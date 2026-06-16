"""
Tests de integración: verifica los stored procedures y tablas snapshot.
Requiere conexión activa a Aurora PostgreSQL.
"""
import pytest


@pytest.mark.integration
class TestSnapshotTable:
    """reporte_mensual_snapshot debe tener datos de todos los meses del dataset."""

    def test_snapshot_tiene_filas(self, cursor):
        """reporte_mensual_snapshot debe tener al menos 20 períodos con datos."""
        cursor.execute("SELECT COUNT(*) FROM reporting.reporte_mensual_snapshot")
        assert cursor.fetchone()[0] >= 20, \
            "reporte_mensual_snapshot tiene menos de 20 períodos — batch incompleto"

    def test_snapshot_formato_periodo(self, cursor):
        """Todos los períodos deben estar en formato YYYY-MM."""
        cursor.execute(r"""
            SELECT COUNT(*) FROM reporting.reporte_mensual_snapshot
            WHERE periodo !~ '^\d{4}-\d{2}$'
        """)
        assert cursor.fetchone()[0] == 0, \
            "Existen períodos con formato incorrecto en reporte_mensual_snapshot"

    def test_snapshot_noviembre_2017_es_el_pico(self, cursor):
        """El período con mayor revenue en el snapshot debe ser 2017-11 (Black Friday)."""
        cursor.execute("""
            SELECT periodo FROM reporting.reporte_mensual_snapshot
            ORDER BY ingresos_totales DESC LIMIT 1
        """)
        assert cursor.fetchone()[0] == "2017-11", \
            "El pico de revenue en el snapshot no es noviembre 2017"

    def test_snapshot_ingresos_positivos(self, cursor):
        """Todos los snapshots con datos deben tener ingresos > 0."""
        cursor.execute("""
            SELECT COUNT(*) FROM reporting.reporte_mensual_snapshot
            WHERE ingresos_totales < 0
        """)
        assert cursor.fetchone()[0] == 0, \
            "Existen períodos con ingresos negativos en el snapshot"

    def test_snapshot_tiene_top_categorias(self, cursor):
        """Los períodos con datos deben tener al menos top_categoria_1 definida."""
        cursor.execute("""
            SELECT COUNT(*) FROM reporting.reporte_mensual_snapshot
            WHERE ingresos_totales > 0 AND top_categoria_1 IS NULL
        """)
        assert cursor.fetchone()[0] == 0, \
            "Existen períodos con datos pero sin top_categoria_1"


@pytest.mark.integration
class TestSellerSegments:
    """seller_segments debe tener los 3,095 vendedores clasificados en A/B/C/D."""

    def test_total_vendedores_segmentados(self, cursor):
        """seller_segments debe tener exactamente 3,095 filas."""
        cursor.execute("SELECT COUNT(*) FROM reporting.seller_segments")
        assert cursor.fetchone()[0] == 3_095, \
            "seller_segments no tiene 3,095 vendedores"

    def test_cuatro_segmentos_presentes(self, cursor):
        """Deben existir exactamente los segmentos A, B, C y D."""
        cursor.execute("""
            SELECT segmento FROM reporting.seller_segments
            GROUP BY segmento ORDER BY segmento
        """)
        segmentos = {r[0] for r in cursor.fetchall()}
        assert segmentos == {"A", "B", "C", "D"}, \
            f"Segmentos encontrados: {segmentos}, esperados: A, B, C, D"

    def test_distribucion_cuartiles_uniforme(self, cursor):
        """Cada segmento debe tener aproximadamente el 25% de los vendedores (±5%)."""
        cursor.execute("""
            SELECT segmento, COUNT(*) AS cnt
            FROM reporting.seller_segments
            GROUP BY segmento
        """)
        counts = {r[0]: r[1] for r in cursor.fetchall()}
        total = sum(counts.values())
        for seg, cnt in counts.items():
            pct = cnt / total * 100
            assert 20 <= pct <= 30, \
                f"Segmento {seg} tiene {pct:.1f}% de vendedores — fuera del rango 20-30%"

    def test_segmento_a_tiene_mayor_revenue(self, cursor):
        """El revenue promedio de segmento A debe ser mayor que el de D."""
        cursor.execute("""
            SELECT segmento, AVG(ingresos_total)
            FROM reporting.seller_segments
            GROUP BY segmento
        """)
        avgs = {r[0]: float(r[1]) for r in cursor.fetchall()}
        assert avgs["A"] > avgs["D"], \
            f"Segmento A (avg={avgs['A']:.0f}) debe tener mayor revenue que D (avg={avgs['D']:.0f})"

    def test_segmentos_validos(self, cursor):
        """Ningún vendedor debe tener un segmento fuera de A/B/C/D."""
        cursor.execute("""
            SELECT COUNT(*) FROM reporting.seller_segments
            WHERE segmento NOT IN ('A', 'B', 'C', 'D')
        """)
        assert cursor.fetchone()[0] == 0, \
            "Existen vendedores con segmento inválido en seller_segments"
