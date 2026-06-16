# Arquitectura del Pipeline — Olist E2E Data Pipeline en AWS

## Visión General

Pipeline de datos end-to-end sobre el dataset público de Olist (Brazilian E-Commerce), construido sobre AWS siguiendo la arquitectura **Medallion** (Bronze → Silver → Gold → BI).

---

## Diagrama de Arquitectura General

```mermaid
flowchart LR
    subgraph ORIGEN["📦 Fuente de Datos"]
        K["🗂️ Kaggle API\nBrazilian E-Commerce\n~100K órdenes · 9 CSVs · ~162MB"]
    end

    subgraph BRONZE["🥉 Bronze — AWS S3"]
        S3["☁️ S3 Bucket\nbronze/olist/\nSSE-AES256\n9 archivos CSV"]
    end

    subgraph SILVER["🥈 Silver — Aurora PostgreSQL"]
        STG["🐘 schema: staging\n9 tablas TEXT\nCopia exacta sin transformar"]
    end

    subgraph GOLD["🥇 Gold — Aurora PostgreSQL"]
        DWH["⭐ schema: dwh\nStar Schema\n5 dims + 3 facts\nTipos correctos + FKs"]
    end

    subgraph BI_LAYER["📊 BI Layer — Aurora PostgreSQL"]
        REP["📐 schema: reporting\n5 vistas SQL\n2 stored procedures\n2 tablas snapshot"]
    end

    subgraph VISUALIZACION["📈 Visualización"]
        PBI["Power BI\nDirectQuery\n3 páginas\n5 KPIs"]
    end

    K -->|"Phase 1\nboto3 + SSE-AES256"| S3
    S3 -->|"Phase 2\naws_s3 extension"| STG
    STG -->|"Phase 3\nSQL ETL puro"| DWH
    DWH -->|"Phase 4\nCTEs + Window Functions"| REP
    REP -->|"Phase 5\nPL/pgSQL SPs"| REP
    REP -->|DirectQuery| PBI

    style ORIGEN fill:#f5a623,color:#000
    style BRONZE fill:#cd7f32,color:#fff
    style SILVER fill:#aaa,color:#fff
    style GOLD fill:#f4c430,color:#000
    style BI_LAYER fill:#2980b9,color:#fff
    style VISUALIZACION fill:#8e44ad,color:#fff
```

---

## Arquitectura Medallion por Capas

| Capa | Tecnología | Schema | Responsabilidad |
|---|---|---|---|
| **Ingesta** | Python + Kaggle API | — | Descarga y descompresión de CSVs |
| **Bronze** | AWS S3 + SSE-AES256 | `bronze/olist/` | Datos crudos inmutables, cifrados en reposo |
| **Silver** | Aurora PostgreSQL | `staging` | Copia fiel en BD, todo TEXT, sin transformar |
| **Gold** | Aurora PostgreSQL | `dwh` | Star Schema tipado, surrogate keys, FKs formales |
| **BI** | Aurora PostgreSQL | `reporting` | Vistas pre-calculadas + snapshots para BI |
| **Visualización** | Power BI Desktop | — | Dashboards DirectQuery sobre `reporting.*` |

---

## Flujo de Datos Detallado

```mermaid
flowchart TD
    subgraph PH1["Phase 1 — Bronze Ingestion (Python)"]
        P1A["authenticate_kaggle()\nLee vars de entorno\nsin archivos en disco"]
        P1B["download_dataset()\nZIP ~45MB → 9 CSVs"]
        P1C["upload_files_to_s3()\nboto3 · ServerSideEncryption=AES256"]
        P1A --> P1B --> P1C
    end

    subgraph PH2["Phase 2 — Silver Ingestion (SQL)"]
        P2A["01_enable_extension.sql\naws_s3 extension en Aurora"]
        P2B["02_create_staging_tables.sql\n9 tablas · todas TEXT"]
        P2C["03_load_from_s3.sql\naws_s3.table_import_from_s3()"]
        P2D["04_verify_counts.sql\nValidación de filas"]
        P2A --> P2B --> P2C --> P2D
    end

    subgraph PH3["Phase 3 — Gold / Star Schema (SQL)"]
        P3A["01_create_dwh_schema.sql\nDROP CASCADE + CREATE\n5 dims + 3 facts"]
        P3B["02_populate_dimensions.sql\nNULLIF · CAST · INITCAP · generate_series"]
        P3C["03_populate_facts.sql\nLEFT JOIN dims → surrogate keys"]
        P3D["04_data_quality_tests.sql\n15+ tests: FKs · PKs · rangos"]
        P3A --> P3B --> P3C --> P3D
    end

    subgraph PH4["Phase 4 — Reporting Views (SQL)"]
        P4A["vw_revenue_mensual\nCTE + LAG()"]
        P4B["vw_top_categorias_pareto\nCTE + SUM() OVER()"]
        P4C["vw_ranking_vendedores\nRANK() OVER() múltiple"]
        P4D["vw_tiempo_entrega_estado\nEXTRACT + AVG + RANK"]
        P4E["vw_satisfaccion_cliente\nJOIN facts + RANK"]
    end

    subgraph PH5["Phase 5 — Stored Procedures (PL/pgSQL)"]
        P5A["sp_generar_reporte_mensual()\nKPIs + MoM + YoY + UPSERT"]
        P5B["sp_segmentar_vendedores()\nNTILE(4) → segmentos A/B/C/D"]
    end

    PH1 --> PH2 --> PH3 --> PH4 --> PH5

    style PH1 fill:#cd7f32,color:#fff
    style PH2 fill:#888,color:#fff
    style PH3 fill:#c9a800,color:#000
    style PH4 fill:#1a6fa8,color:#fff
    style PH5 fill:#1a6fa8,color:#fff
```

---

## Modelo Dimensional — Star Schema

```mermaid
erDiagram
    DIM_DATE {
        int      date_sk     PK
        date     full_date
        smallint year
        smallint quarter
        smallint month
        varchar  month_name
        smallint day
        boolean  is_weekend
    }
    DIM_CUSTOMERS {
        int     customer_sk  PK
        varchar customer_id  UK
        varchar customer_city
        varchar customer_state
    }
    DIM_PRODUCTS {
        int     product_sk   PK
        varchar product_id   UK
        varchar product_category_name_english
        numeric product_weight_g
    }
    DIM_SELLERS {
        int     seller_sk    PK
        varchar seller_id    UK
        varchar seller_city
        varchar seller_state
    }
    DIM_ORDERS {
        int       order_sk   PK
        varchar   order_id   UK
        varchar   order_status
        timestamp order_purchase_timestamp
        timestamp order_delivered_customer_date
    }
    FACT_ORDER_ITEMS {
        int     order_item_sk  PK
        int     customer_sk    FK
        int     product_sk     FK
        int     seller_sk      FK
        int     order_sk       FK
        int     date_sk        FK
        numeric price
        numeric freight_value
        numeric total_value
    }
    FACT_PAYMENTS {
        int     payment_sk     PK
        int     order_sk       FK
        varchar payment_type
        int     payment_installments
        numeric payment_value
    }
    FACT_REVIEWS {
        int      review_sk     PK
        int      order_sk      FK
        smallint review_score
        text     review_comment_message
    }

    DIM_DATE       ||--o{ FACT_ORDER_ITEMS : "date_sk"
    DIM_CUSTOMERS  ||--o{ FACT_ORDER_ITEMS : "customer_sk"
    DIM_PRODUCTS   ||--o{ FACT_ORDER_ITEMS : "product_sk"
    DIM_SELLERS    ||--o{ FACT_ORDER_ITEMS : "seller_sk"
    DIM_ORDERS     ||--o{ FACT_ORDER_ITEMS : "order_sk"
    DIM_ORDERS     ||--o{ FACT_PAYMENTS    : "order_sk"
    DIM_ORDERS     ||--o{ FACT_REVIEWS     : "order_sk"
```

---

## Stack Tecnológico

```mermaid
mindmap
  root((Olist Pipeline))
    Extracción
      Python 3.11
      kaggle API
      boto3 SDK
    Almacenamiento
      AWS S3
        SSE-AES256
        Bronze Layer
      Aurora PostgreSQL 17
        staging schema
        dwh schema
        reporting schema
    Transformación
      SQL puro
        NULLIF pattern
        generate_series
        surrogate keys
      PL/pgSQL
        NTILE window function
        ON CONFLICT UPSERT
        variable_conflict
    Testing
      pytest
        38 unit tests
        43 integration tests
    Visualización
      Power BI Desktop
        DirectQuery
        3 páginas
        DAX measures
    EDA
      Jupyter Notebook
        pandas
        matplotlib 3.11
        seaborn
```

---

## Decisiones de Arquitectura Clave

### 1. Staging con tipos TEXT
Todos los CSVs se cargan primero como TEXT en `staging`. Los CSVs de Kaggle contienen strings vacíos donde debería haber NULL. Cargar como TEXT permite detectar y limpiar estos errores en SQL antes de castear a los tipos finales.

### 2. Surrogate Keys (SERIAL) en todas las dimensiones
Los JOINs entre INTEGER son hasta 3x más rápidos que entre VARCHAR en tablas de millones de filas. El `order_id` VARCHAR original se conserva en todas las tablas para trazabilidad y debugging.

### 3. `fact_payments` y `fact_reviews` con FK formal a `dim_orders`
Ambas tablas tienen `order_sk INTEGER REFERENCES dim_orders(order_sk)` resuelto en el ETL mediante `LEFT JOIN dwh.dim_orders ON order_id`. El `order_id` VARCHAR se preserva para verificación:

```sql
-- Test de integridad (debe retornar 0):
SELECT COUNT(*) FROM dwh.fact_payments fp
JOIN dwh.dim_orders dor ON fp.order_sk = dor.order_sk
WHERE fp.order_id <> dor.order_id;
```

### 4. `dim_date` generada con `generate_series`
En lugar de copiar solo los días con ventas, se genera el calendario completo desde la fecha mínima a la máxima. Esto habilita análisis de días sin ventas y gaps en el negocio.

### 5. Schema `reporting` separado del DWH
La lógica de negocio queda en vistas SQL versionadas en Git. Power BI solo lee de `reporting.*`, nunca toca el DWH directamente. Las vistas se pueden recrear en segundos si el modelo cambia.

### 6. `#variable_conflict use_column` en stored procedures
Los stored procedures usan `RETURNS TABLE` con columnas que comparten nombre con columnas de las tablas que consultan. La directiva `#variable_conflict use_column` resuelve la ambigüedad a favor de las columnas de tabla.

---

## Seguridad

| Decisión | Implementación |
|---|---|
| Sin credenciales en código | `python-dotenv` + `.env` excluido de git |
| Datos cifrados en S3 | `ServerSideEncryption: AES256` en cada upload |
| Credenciales AWS temporales | `AWS_SESSION_TOKEN` rotado cada 4h (AWS Academy) |
| IAM Role para Aurora↔S3 | `LabRole` adjuntado via `iam_setup.py` |
| Datos raw excluidos de git | `data/` en `.gitignore` — solo vive en S3 y local |

---

## Métricas del Pipeline

| Componente | Cantidad |
|---|---|
| Archivos Python | 15 scripts (~1,000 líneas) |
| Scripts SQL | 14 archivos (~3,000 líneas) |
| Tablas en Aurora | 17 (9 staging + 5 dims + 3 facts) |
| Vistas de reporting | 5 |
| Stored Procedures | 2 (PL/pgSQL) |
| Tests automatizados | 81 (38 unit + 43 integration) |
| Páginas Power BI | 3 |
| Secciones EDA Notebook | 12 |
| Datos procesados | ~162MB (9 CSVs) |
| Registros en DWH | ~515,000 filas totales |
