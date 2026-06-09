# Power BI — Olist E-Commerce Dashboard

Esta carpeta contiene los entregables de Business Intelligence del proyecto.

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `olist_dashboard_v1.pbix` | Archivo de Power BI Desktop — modelo de datos + dashboards |
| `olist_dashboard_v1.pdf` | Exportación PDF del tablero para visualización rápida en GitHub |

## Fuente de datos

El tablero se conecta a las vistas de la capa `reporting` en Aurora PostgreSQL:

| Vista | Descripción |
|-------|-------------|
| `reporting.vw_revenue_mensual` | Revenue mensual con crecimiento MoM |
| `reporting.vw_top_categorias_pareto` | Categorías que generan el 80% del revenue |
| `reporting.vw_ranking_vendedores` | Ranking de vendedores por revenue |
| `reporting.vw_tiempo_entrega_estado` | Tiempo de entrega promedio por estado |
| `reporting.vw_satisfaccion_cliente` | Score de satisfacción por categoría |

## Cómo abrir

1. Tener Power BI Desktop instalado
2. Abrir `olist_dashboard_v1.pbix`
3. En **Inicio → Transformar datos → Configuración del origen de datos**, actualizar las credenciales de Aurora PostgreSQL con los valores de tu `.env`
4. Hacer clic en **Actualizar**
