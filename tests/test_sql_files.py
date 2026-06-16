"""
Tests unitarios: verifica que todos los scripts SQL existen y tienen contenido.
No requieren conexión a AWS ni Aurora.
"""
import pytest
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"

EXPECTED_SQL_FILES = [
    "phase2_aurora_ingestion/01_enable_extension.sql",
    "phase2_aurora_ingestion/02_create_staging_tables.sql",
    "phase2_aurora_ingestion/03_load_from_s3.sql",
    "phase2_aurora_ingestion/04_verify_counts.sql",
    "phase3_star_schema/01_create_dwh_schema.sql",
    "phase3_star_schema/02_populate_dimensions.sql",
    "phase3_star_schema/03_populate_facts.sql",
    "phase3_star_schema/04_data_quality_tests.sql",
    "phase4_bi_queries/01_create_reporting_views.sql",
    "phase4_bi_queries/02_validate_views.sql",
    "phase5_procedures/01_create_support_tables.sql",
    "phase5_procedures/02_sp_generar_reporte_mensual.sql",
    "phase5_procedures/03_sp_segmentar_vendedores.sql",
    "phase5_procedures/04_test_procedures.sql",
]


@pytest.mark.unit
@pytest.mark.parametrize("relative_path", EXPECTED_SQL_FILES)
def test_sql_file_exists(relative_path):
    """Cada script SQL del pipeline debe existir en el repositorio."""
    path = SQL_DIR / relative_path
    assert path.exists(), f"Script SQL faltante: {relative_path}"


@pytest.mark.unit
@pytest.mark.parametrize("relative_path", EXPECTED_SQL_FILES)
def test_sql_file_not_empty(relative_path):
    """Cada script SQL debe tener contenido (no estar vacío)."""
    path = SQL_DIR / relative_path
    assert path.stat().st_size > 0, f"Script SQL vacío: {relative_path}"


@pytest.mark.unit
def test_all_sql_phases_present():
    """Los 4 directorios de fases SQL deben existir."""
    for phase in ["phase2_aurora_ingestion", "phase3_star_schema",
                  "phase4_bi_queries", "phase5_procedures"]:
        assert (SQL_DIR / phase).is_dir(), f"Directorio SQL faltante: {phase}"


@pytest.mark.unit
def test_stored_procedures_contain_plpgsql():
    """Los stored procedures deben declarar LANGUAGE plpgsql."""
    for sp_file in ["02_sp_generar_reporte_mensual.sql",
                    "03_sp_segmentar_vendedores.sql"]:
        content = (SQL_DIR / "phase5_procedures" / sp_file).read_text(encoding="utf-8")
        assert "plpgsql" in content.lower(), \
            f"{sp_file} no contiene declaración LANGUAGE plpgsql"


@pytest.mark.unit
def test_dwh_schema_uses_cascade():
    """El DROP TABLE en fase 3 debe usar CASCADE para no romper vistas existentes."""
    content = (SQL_DIR / "phase3_star_schema" / "01_create_dwh_schema.sql")\
        .read_text(encoding="utf-8")
    assert "CASCADE" in content.upper(), \
        "DROP TABLE sin CASCADE — fallará si las vistas de reporting existen"


@pytest.mark.unit
def test_fact_payments_has_order_sk():
    """fact_payments debe tener columna order_sk con FK a dim_orders."""
    content = (SQL_DIR / "phase3_star_schema" / "01_create_dwh_schema.sql")\
        .read_text(encoding="utf-8")
    assert "order_sk" in content and "fact_payments" in content, \
        "fact_payments no tiene columna order_sk definida"


@pytest.mark.unit
def test_fact_reviews_has_order_sk():
    """fact_reviews debe tener columna order_sk con FK a dim_orders."""
    content = (SQL_DIR / "phase3_star_schema" / "01_create_dwh_schema.sql")\
        .read_text(encoding="utf-8")
    assert "order_sk" in content and "fact_reviews" in content, \
        "fact_reviews no tiene columna order_sk definida"
