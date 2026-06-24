import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(
    page_title="Olist E-Commerce Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_PATH = Path(__file__).parent.parent / "data" / "raw"

# ── Carga y preparación de datos ──────────────────────────────
@st.cache_data
def load_data():
    DATE_COLS_ORDERS = [
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    orders      = pd.read_csv(DATA_PATH / "olist_orders_dataset.csv",      parse_dates=DATE_COLS_ORDERS)
    customers   = pd.read_csv(DATA_PATH / "olist_customers_dataset.csv")
    order_items = pd.read_csv(DATA_PATH / "olist_order_items_dataset.csv")
    payments    = pd.read_csv(DATA_PATH / "olist_order_payments_dataset.csv")
    reviews     = pd.read_csv(DATA_PATH / "olist_order_reviews_dataset.csv")
    products    = pd.read_csv(DATA_PATH / "olist_products_dataset.csv")
    sellers     = pd.read_csv(DATA_PATH / "olist_sellers_dataset.csv")
    translation = pd.read_csv(DATA_PATH / "product_category_name_translation.csv")

    products_full = products.merge(translation, on="product_category_name", how="left")

    order_revenue = (
        order_items.groupby("order_id")
        .agg(revenue=("price", "sum"), freight=("freight_value", "sum"), n_items=("order_item_id", "count"))
        .reset_index()
    )
    orders_full = (
        orders
        .merge(order_revenue, on="order_id", how="left")
        .merge(customers[["customer_id", "customer_state", "customer_city"]], on="customer_id", how="left")
    )

    orders_del = orders[
        (orders["order_status"] == "delivered")
        & orders["order_delivered_customer_date"].notna()
        & orders["order_purchase_timestamp"].notna()
    ].copy()
    orders_del["dias_entrega"] = (
        orders_del["order_delivered_customer_date"] - orders_del["order_purchase_timestamp"]
    ).dt.days
    orders_del["dias_vs_estimado"] = (
        orders_del["order_estimated_delivery_date"] - orders_del["order_delivered_customer_date"]
    ).dt.days
    orders_del = orders_del.merge(customers[["customer_id", "customer_state"]], on="customer_id", how="left")

    items_cat = (
        order_items
        .merge(products[["product_id", "product_category_name"]], on="product_id", how="left")
        .merge(translation, on="product_category_name", how="left")
    )
    items_cat["category"] = (
        items_cat["product_category_name_english"]
        .fillna(items_cat["product_category_name"])
        .fillna("unknown")
    )
    cat_stats = (
        items_cat.groupby("category")
        .agg(revenue=("price", "sum"), n_items=("order_item_id", "count"), n_orders=("order_id", "nunique"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )

    seller_stats = (
        order_items.groupby("seller_id")
        .agg(revenue=("price", "sum"), n_ordenes=("order_id", "nunique"),
             n_items=("order_item_id", "count"), ticket_prom=("price", "mean"))
        .reset_index()
        .merge(sellers[["seller_id", "seller_state"]], on="seller_id", how="left")
        .sort_values("revenue", ascending=False)
    )

    return dict(
        orders=orders, orders_full=orders_full, customers=customers,
        order_items=order_items, payments=payments, reviews=reviews,
        products=products_full, sellers=sellers, translation=translation,
        cat_stats=cat_stats, orders_del=orders_del, seller_stats=seller_stats,
    )


# ── Filtros de sidebar ────────────────────────────────────────
def build_sidebar(orders_full):
    st.sidebar.title("Filtros")

    min_date = orders_full["order_purchase_timestamp"].min().date()
    max_date = orders_full["order_purchase_timestamp"].max().date()
    date_range = st.sidebar.date_input(
        "Rango de fechas",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    all_states = sorted(orders_full["customer_state"].dropna().unique().tolist())
    states = st.sidebar.multiselect("Estado (cliente)", options=all_states, default=[])

    all_status = sorted(orders_full["order_status"].dropna().unique().tolist())
    status = st.sidebar.multiselect("Estado de orden", options=all_status, default=["delivered"])

    st.sidebar.markdown("---")
    st.sidebar.caption("Olist E-Commerce Pipeline — Mod 4")

    return date_range, states, status


def apply_filters(orders_full, date_range, states, status):
    df = orders_full.copy()
    if len(date_range) == 2:
        df = df[
            (df["order_purchase_timestamp"].dt.date >= date_range[0])
            & (df["order_purchase_timestamp"].dt.date <= date_range[1])
        ]
    if states:
        df = df[df["customer_state"].isin(states)]
    if status:
        df = df[df["order_status"].isin(status)]
    return df


# ── KPI Cards ─────────────────────────────────────────────────
def kpi_row(orders_f, reviews, orders_del):
    total_revenue   = orders_f["revenue"].sum()
    avg_ticket      = orders_f["revenue"].mean()
    avg_score       = reviews["review_score"].mean()
    avg_delivery    = orders_del["dias_entrega"].mean()
    pct_on_time     = (orders_del["dias_vs_estimado"] >= 0).mean() * 100
    n_orders        = len(orders_f)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Ordenes", f"{n_orders:,}")
    c2.metric("Revenue Total", f"R$ {total_revenue/1e6:.2f}M")
    c3.metric("Ticket Promedio", f"R$ {avg_ticket:,.0f}")
    c4.metric("Score Satisfaccion", f"{avg_score:.2f} / 5.0")
    c5.metric("Entrega Promedio", f"{avg_delivery:.1f} dias")
    c6.metric("Puntualidad", f"{pct_on_time:.1f}%")


# ── Tabs de análisis ──────────────────────────────────────────
def tab_temporal(orders_f):
    orders_ts = orders_f.copy()
    orders_ts["mes"] = orders_ts["order_purchase_timestamp"].dt.to_period("M")
    monthly = (
        orders_ts.groupby("mes")
        .agg(n_ordenes=("order_id", "count"), revenue=("revenue", "sum"))
        .reset_index()
    )
    monthly["mes_dt"] = monthly["mes"].dt.to_timestamp()

    col1, col2 = st.columns(2)

    with col1:
        fig = px.area(
            monthly, x="mes_dt", y="n_ordenes",
            title="Ordenes Mensuales",
            labels={"mes_dt": "Mes", "n_ordenes": "Ordenes"},
            color_discrete_sequence=["#2563eb"],
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            monthly, x="mes_dt", y="revenue",
            title="Revenue Mensual (BRL)",
            labels={"mes_dt": "Mes", "revenue": "Revenue (BRL)"},
            color_discrete_sequence=["#16a34a"],
        )
        fig.update_layout(showlegend=False)
        fig.update_yaxes(tickprefix="R$")
        st.plotly_chart(fig, use_container_width=True)

    # Tabla resumen
    monthly_disp = monthly[["mes_dt", "n_ordenes", "revenue"]].copy()
    monthly_disp.columns = ["Mes", "Ordenes", "Revenue (BRL)"]
    monthly_disp["Mes"] = monthly_disp["Mes"].dt.strftime("%Y-%m")
    monthly_disp["Revenue (BRL)"] = monthly_disp["Revenue (BRL)"].map("R$ {:,.0f}".format)
    with st.expander("Ver datos mensuales"):
        st.dataframe(monthly_disp, use_container_width=True, hide_index=True)


def tab_geografia(orders_f):
    state_stats = (
        orders_f.groupby("customer_state")
        .agg(n_ordenes=("order_id", "count"), revenue=("revenue", "sum"))
        .reset_index()
        .sort_values("n_ordenes", ascending=False)
    )
    state_stats["pct_ordenes"] = state_stats["n_ordenes"] / state_stats["n_ordenes"].sum() * 100

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            state_stats.sort_values("n_ordenes"),
            x="n_ordenes", y="customer_state",
            orientation="h",
            title="Ordenes por Estado",
            labels={"customer_state": "Estado", "n_ordenes": "Ordenes"},
            color="n_ordenes",
            color_continuous_scale="Blues",
            text="pct_ordenes",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(coloraxis_showscale=False, height=550)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        top15 = state_stats.head(15).sort_values("revenue")
        fig = px.bar(
            top15, x="revenue", y="customer_state",
            orientation="h",
            title="Revenue por Estado — Top 15 (BRL)",
            labels={"customer_state": "Estado", "revenue": "Revenue (BRL)"},
            color="revenue",
            color_continuous_scale="Greens",
        )
        fig.update_layout(coloraxis_showscale=False, height=550)
        fig.update_xaxes(tickprefix="R$")
        st.plotly_chart(fig, use_container_width=True)

    top3_pct = state_stats.head(3)["pct_ordenes"].sum()
    st.info(f"Los 3 estados principales concentran el **{top3_pct:.1f}%** de todas las ordenes.")


def tab_categorias(cat_stats):
    cat_stats = cat_stats.copy()
    cat_stats["revenue_pct"]  = cat_stats["revenue"] / cat_stats["revenue"].sum() * 100
    cat_stats["revenue_acum"] = cat_stats["revenue_pct"].cumsum()
    cat_stats["rank"] = range(1, len(cat_stats) + 1)

    top_n = st.slider("Mostrar top N categorias", min_value=5, max_value=30, value=15, step=5)
    top = cat_stats.head(top_n).sort_values("revenue")

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            top, x="revenue", y="category",
            orientation="h",
            title=f"Revenue por Categoria — Top {top_n}",
            labels={"category": "Categoria", "revenue": "Revenue (BRL)"},
            color="revenue",
            color_continuous_scale="Blues",
            text="revenue_pct",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(coloraxis_showscale=False, height=520)
        fig.update_xaxes(tickprefix="R$")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        pareto = cat_stats.reset_index(drop=True)
        fig = go.Figure()
        fig.add_bar(
            x=pareto["rank"].head(30),
            y=pareto["revenue"].head(30),
            name="Revenue",
            marker_color="#2563eb",
            opacity=0.75,
        )
        fig.add_scatter(
            x=pareto["rank"].head(30),
            y=pareto["revenue_acum"].head(30),
            name="% Acumulado",
            yaxis="y2",
            line=dict(color="#dc2626", width=2),
            mode="lines+markers",
        )
        fig.add_hline(y=80, line_dash="dash", line_color="#dc2626", opacity=0.5, yref="y2")
        fig.update_layout(
            title="Curva de Pareto — Revenue Acumulado",
            yaxis2=dict(overlaying="y", side="right", range=[0, 105], ticksuffix="%"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)

    n80 = (cat_stats["revenue_acum"] <= 80).sum()
    st.info(f"**{n80} categorias** concentran el 80% del revenue total (principio de Pareto).")


def tab_pagos(payments):
    pay_type = (
        payments.groupby("payment_type")
        .agg(n_transacciones=("order_id", "count"), revenue=("payment_value", "sum"),
             cuotas_prom=("payment_installments", "mean"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )

    cc = payments[payments["payment_type"] == "credit_card"]
    cc_inst = cc["payment_installments"].value_counts().sort_index().head(12).reset_index()
    cc_inst.columns = ["cuotas", "transacciones"]

    col1, col2, col3 = st.columns(3)

    with col1:
        fig = px.pie(
            pay_type, names="payment_type", values="revenue",
            title="Revenue por Tipo de Pago",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            pay_type, x="payment_type", y="n_transacciones",
            title="Volumen de Transacciones",
            labels={"payment_type": "Tipo de Pago", "n_transacciones": "Transacciones"},
            color="payment_type",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col3:
        fig = px.bar(
            cc_inst, x="cuotas", y="transacciones",
            title="Distribucion de Cuotas (Tarjeta de Credito)",
            labels={"cuotas": "Numero de Cuotas", "transacciones": "Transacciones"},
            color_discrete_sequence=["#7c3aed"],
        )
        st.plotly_chart(fig, use_container_width=True)

    cc_pct = pay_type[pay_type["payment_type"] == "credit_card"]["revenue"].values[0] / pay_type["revenue"].sum() * 100
    avg_cuotas = cc["payment_installments"].mean()
    st.info(f"Tarjeta de credito: **{cc_pct:.1f}%** del revenue total | Cuotas promedio: **{avg_cuotas:.1f}x**")


def tab_entregas(orders_del):
    bins   = [0, 7, 14, 21, 30, 200]
    labels = ["0-7 dias", "8-14 dias", "15-21 dias", "22-30 dias", "30+ dias"]
    orders_del = orders_del.copy()
    orders_del["rango_entrega"] = pd.cut(orders_del["dias_entrega"], bins=bins, labels=labels)

    state_delivery = (
        orders_del.groupby("customer_state")
        .agg(dias_prom=("dias_entrega", "mean"), n=("order_id", "count"))
        .reset_index()
        .query("n >= 100")
        .sort_values("dias_prom", ascending=False)
    )

    pct_on_time = (orders_del["dias_vs_estimado"] >= 0).mean() * 100

    col1, col2 = st.columns(2)

    with col1:
        fig = px.histogram(
            orders_del[orders_del["dias_entrega"].between(0, 60)],
            x="dias_entrega", nbins=40,
            title="Distribucion de Dias de Entrega",
            labels={"dias_entrega": "Dias desde compra hasta entrega"},
            color_discrete_sequence=["#2563eb"],
        )
        fig.add_vline(x=orders_del["dias_entrega"].mean(), line_dash="dash",
                      line_color="#dc2626", annotation_text=f"Prom: {orders_del['dias_entrega'].mean():.1f}d")
        fig.add_vline(x=orders_del["dias_entrega"].median(), line_dash="dot",
                      line_color="#16a34a", annotation_text=f"Med: {orders_del['dias_entrega'].median():.1f}d")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            state_delivery.head(15).sort_values("dias_prom"),
            x="dias_prom", y="customer_state",
            orientation="h",
            title="Dias de Entrega Promedio por Estado (top 15 lentos)",
            labels={"customer_state": "Estado", "dias_prom": "Dias promedio"},
            color="dias_prom",
            color_continuous_scale="RdYlGn_r",
        )
        avg_nacional = orders_del["dias_entrega"].mean()
        fig.add_vline(x=avg_nacional, line_dash="dash", line_color="gray",
                      annotation_text=f"Nacional: {avg_nacional:.1f}d")
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # Score vs tiempo de entrega
    score_by_rango = (
        orders_del
        .merge(
            pd.read_csv(DATA_PATH / "olist_order_reviews_dataset.csv")[["order_id", "review_score"]],
            on="order_id", how="left"
        )
        .groupby("rango_entrega", observed=True)["review_score"]
        .mean()
        .reset_index()
    )
    fig = px.bar(
        score_by_rango, x="rango_entrega", y="review_score",
        title="Score de Satisfaccion por Rango de Entrega",
        labels={"rango_entrega": "Rango de entrega", "review_score": "Score promedio"},
        color="review_score",
        color_continuous_scale="RdYlGn",
        range_color=[2.5, 5.0],
        text="review_score",
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(coloraxis_showscale=False, yaxis_range=[2, 5.3])
    st.plotly_chart(fig, use_container_width=True)

    st.info(f"**{pct_on_time:.1f}%** de las ordenes llegaron antes de la fecha estimada.")


def tab_satisfaccion(reviews):
    score_counts = reviews["review_score"].value_counts().sort_index().reset_index()
    score_counts.columns = ["score", "cantidad"]
    score_counts["pct"] = score_counts["cantidad"] / len(reviews) * 100

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            score_counts, x="score", y="cantidad",
            title=f"Distribucion de Review Scores (promedio: {reviews['review_score'].mean():.2f})",
            labels={"score": "Estrellas", "cantidad": "Cantidad de resenas"},
            color="score",
            color_continuous_scale=["#dc2626", "#ea580c", "#eab308", "#84cc16", "#16a34a"],
            text="pct",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.pie(
            score_counts, names="score", values="cantidad",
            title="Proporcion por Score",
            hole=0.4,
            color="score",
            color_discrete_map={
                1: "#dc2626", 2: "#ea580c", 3: "#eab308", 4: "#84cc16", 5: "#16a34a"
            },
        )
        st.plotly_chart(fig, use_container_width=True)

    pct_pos = (reviews["review_score"] >= 4).mean() * 100
    pct_neg = (reviews["review_score"] <= 2).mean() * 100
    st.info(
        f"Resenas positivas (4-5 estrellas): **{pct_pos:.1f}%**  |  "
        f"Resenas negativas (1-2 estrellas): **{pct_neg:.1f}%**"
    )


def tab_vendedores(seller_stats):
    seller_stats = seller_stats.copy()
    seller_stats["revenue_pct"]  = seller_stats["revenue"] / seller_stats["revenue"].sum() * 100
    seller_stats["revenue_acum"] = seller_stats["revenue_pct"].cumsum()
    seller_stats["rank"]         = range(1, len(seller_stats) + 1)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.histogram(
            seller_stats, x=np.log10(seller_stats["revenue"] + 1),
            nbins=40,
            title="Distribucion de Revenue por Vendedor (escala log10)",
            labels={"x": "log10(Revenue BRL)"},
            color_discrete_sequence=["#2563eb"],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        state_seller = (
            seller_stats.groupby("seller_state")
            .agg(revenue=("revenue", "sum"), n_sellers=("seller_id", "count"))
            .reset_index()
            .sort_values("revenue", ascending=True)
            .tail(10)
        )
        fig = px.bar(
            state_seller, x="revenue", y="seller_state",
            orientation="h",
            title="Revenue por Estado del Vendedor — Top 10",
            labels={"seller_state": "Estado", "revenue": "Revenue (BRL)"},
            color="revenue",
            color_continuous_scale="Purples",
        )
        fig.update_layout(coloraxis_showscale=False)
        fig.update_xaxes(tickprefix="R$")
        st.plotly_chart(fig, use_container_width=True)

    # Curva de Lorenz
    sorted_rev  = np.sort(seller_stats["revenue"].values)
    cum_rev     = np.cumsum(sorted_rev) / sorted_rev.sum() * 100
    cum_sellers = np.linspace(0, 100, len(sorted_rev))

    fig = go.Figure()
    fig.add_scatter(
        x=cum_sellers, y=cum_rev,
        name="Distribucion real",
        line=dict(color="#2563eb", width=2.5),
        fill="tonexty",
        fillcolor="rgba(37,99,235,0.1)",
    )
    fig.add_scatter(
        x=[0, 100], y=[0, 100],
        name="Igualdad perfecta",
        line=dict(color="black", width=1.5, dash="dash"),
    )
    fig.update_layout(
        title="Curva de Lorenz — Concentracion de Revenue por Vendedor",
        xaxis_title="% acumulado de vendedores",
        yaxis_title="% acumulado de revenue",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

    pct5 = seller_stats[seller_stats["revenue_acum"] <= 50].shape[0] / len(seller_stats) * 100
    st.info(
        f"Top **{pct5:.0f}%** de vendedores genera el **50%** del revenue  |  "
        f"Vendedores con menos de 10 ordenes: **{(seller_stats['n_ordenes'] < 10).mean()*100:.1f}%**"
    )


# ── Main ──────────────────────────────────────────────────────
def main():
    data = load_data()

    date_range, states, status = build_sidebar(data["orders_full"])
    orders_f = apply_filters(data["orders_full"], date_range, states, status)

    st.title("Olist E-Commerce — Dashboard de Analisis")
    period_start = data["orders_full"]["order_purchase_timestamp"].min().strftime("%Y-%m-%d")
    period_end   = data["orders_full"]["order_purchase_timestamp"].max().strftime("%Y-%m-%d")
    st.caption(
        f"Periodo completo: {period_start} → {period_end}  |  "
        f"Ordenes en vista actual: **{len(orders_f):,}** de {len(data['orders_full']):,}"
    )

    st.divider()
    kpi_row(orders_f, data["reviews"], data["orders_del"])
    st.divider()

    tabs = st.tabs([
        "Temporal", "Geografia", "Categorias",
        "Pagos", "Entregas", "Satisfaccion", "Vendedores",
    ])

    with tabs[0]:
        tab_temporal(orders_f)
    with tabs[1]:
        tab_geografia(orders_f)
    with tabs[2]:
        tab_categorias(data["cat_stats"])
    with tabs[3]:
        tab_pagos(data["payments"])
    with tabs[4]:
        tab_entregas(data["orders_del"])
    with tabs[5]:
        tab_satisfaccion(data["reviews"])
    with tabs[6]:
        tab_vendedores(data["seller_stats"])


if __name__ == "__main__":
    main()
