# pages/5_📊Dashboard.py

import streamlit as st
import pandas as pd
import datetime
from sheet_connector import SheetConnector
import altair as alt


SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit?gid=0#gid=0"

@st.cache_data(ttl=300, show_spinner=False)
def load_all_data(url: str):
    conn = SheetConnector(url)

    # Productos
    df_prods = conn.get_products()
    if df_prods is None:
        df_prods = pd.DataFrame()

    # Remitos
    df_rem = conn.get_remitos()
    if df_rem is None:
        df_rem = pd.DataFrame()
    else:
        # Fecha
        df_rem["FECHA"] = pd.to_datetime(df_rem["FECHA"], errors="coerce")

        # Reemplazar comas decimales por puntos y convertir
        df_rem["TOTAL FACTURADO"] = pd.to_numeric(
            df_rem["TOTAL FACTURADO"].astype(str).str.replace(",", "."),
            errors="coerce"
        )
        df_rem["GANANCIA"] = pd.to_numeric(
            df_rem.get("GANANCIA", "").astype(str).str.replace(",", "."),
            errors="coerce"
        )
        # Si quieres también convertir Costo Total:
        if "COSTO TOTAL" in df_rem.columns:
            df_rem["COSTO TOTAL"] = pd.to_numeric(
                df_rem["COSTO TOTAL"].astype(str).str.replace(",", "."),
                errors="coerce"
            )

        # Periodo mensual
        df_rem["PERIODO"] = df_rem["FECHA"].dt.to_period("M").astype(str)

    # Detalle de remitos
    df_items = conn.get_remito_items()
    if df_items is None:
        df_items = pd.DataFrame()

    # Clientes
    df_cli = conn.get_clients()
    if df_cli is None:
        df_cli = pd.DataFrame()
    else:
        if "FECHA_ALTA" in df_cli.columns:
            df_cli["FECHA_ALTA"] = pd.to_datetime(df_cli["FECHA_ALTA"], errors="coerce")

    return df_prods, df_rem, df_items, df_cli

def show_kpis(df_rem: pd.DataFrame, df_cli: pd.DataFrame):
    now = pd.Timestamp.now()
    total_rev   = df_rem["TOTAL FACTURADO"].sum()
    rem_mes     = df_rem[
        (df_rem["FECHA"].dt.year  == now.year) &
        (df_rem["FECHA"].dt.month == now.month)
    ].shape[0]
    ticket_prom = df_rem["TOTAL FACTURADO"].mean() or 0
    nuevos = 0
    if "FECHA_ALTA" in df_cli.columns:
        nuevos = df_cli[
            (df_cli["FECHA_ALTA"].dt.year  == now.year) &
            (df_cli["FECHA_ALTA"].dt.month == now.month)
        ].shape[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Facturación total", f"${total_rev:,.2f}")
    c2.metric("📦 Remitos este mes", rem_mes)
    c3.metric("🎟️ Ticket promedio", f"${ticket_prom:,.2f}")
    c4.metric("🆕 Clientes nuevos", nuevos)

import pandas as pd  # asegúrate de tener esto importado

def show_monthly_trend(df_rem: pd.DataFrame):
    st.markdown("---")
    st.subheader("Tendencia mensual de facturación")
    if df_rem.empty:
        st.info("No hay datos de remitos para graficar.")
        return

    # 1) Calculamos la facturación mensual
    monthly = (
        df_rem.set_index("FECHA")
              .resample("M")["TOTAL FACTURADO"]
              .sum()
              .rename("Facturación")
              .reset_index()
    )

    # 2) Definimos el dominio de la regresión (extendido 3 meses)
    extent_start = monthly["FECHA"].min()
    extent_end   = monthly["FECHA"].max() + pd.DateOffset(months=3)

    # 3) Gráfico base: facturación real
    chart_actual = (
        alt.Chart(monthly)
           .mark_line(point=True)
           .encode(
               x=alt.X("FECHA:T", title="Mes", axis=alt.Axis(format="%b %Y")),
               y=alt.Y("Facturación:Q", title="Facturación"),
               tooltip=[
                   alt.Tooltip("FECHA:T", title="Mes", format="%B %Y"),
                   alt.Tooltip("Facturación:Q", title="Total facturado", format=",.2f")
               ]
           )
    )

    # 4) Capa de regresión lineal (predicción) con línea punteada roja
    chart_reg = (
        alt.Chart(monthly)
           .transform_regression(
               "FECHA", "Facturación",
               method="linear"   # <–– sin extent
           )
           .mark_line(color="firebrick", strokeDash=[5,5])
           .encode(
               x="FECHA:T",
               y="Facturación:Q",
               tooltip=[
                   alt.Tooltip("FECHA:T", title="Mes", format="%B %Y"),
                   alt.Tooltip("Facturación:Q", title="Tendencia", format=",.2f")
               ]
           )
    )

    layered = alt.layer(chart_actual, chart_reg).properties(
        width="container", height=300
    )
    st.altair_chart(layered, use_container_width=True)



def show_top_clients(df_rem: pd.DataFrame, df_cli: pd.DataFrame):
    st.markdown("---")
    st.subheader("Top clientes por facturación")
    if df_rem.empty or df_cli.empty:
        st.info("No hay suficientes datos para mostrar el Top clientes.")
        return

    top_n = st.slider("¿Cuántos clientes mostrar?", 3, 20, 5)
    periodos = ["Todos"] + sorted(df_rem["PERIODO"].unique(), reverse=True)
    sel = st.selectbox("Filtrar periodo", periodos, index=0)
    df_filt = df_rem if sel == "Todos" else df_rem[df_rem["PERIODO"] == sel]

    if df_filt.empty:
        st.warning(f"No hay remitos en el periodo {sel}.")
    else:
        rev_by_cli = (
            df_filt.groupby("ID CLIENTE")["TOTAL FACTURADO"]
                   .sum()
                   .nlargest(top_n)
                   .reset_index(name="Facturación")
        )
        rev_by_cli["Cliente"] = rev_by_cli["ID CLIENTE"].map(
            df_cli.set_index("ID CLIENTE")["NOMBRE"]
        )
        chart = (
            alt.Chart(rev_by_cli)
               .mark_bar()
               .encode(
                   y=alt.Y("Cliente:N", sort="-x", title="Cliente"),
                   x=alt.X("Facturación:Q", title="Total facturado"),
                   tooltip=[alt.Tooltip("Cliente:N"), alt.Tooltip("Facturación:Q", format=",.2f")]
               )
               .properties(width="container", height=300)
        )
        st.altair_chart(chart, use_container_width=True)

def show_fact_vs_gain(df_rem: pd.DataFrame):
    st.markdown("---")
    st.subheader("Facturación vs Ganancia")
    if df_rem.empty:
        st.info("No hay datos para este análisis.")
        return

    # Preparar datos para los últimos 12 meses
    last_year = df_rem.set_index("FECHA").last("365D")
    df2 = (
        last_year.resample("M")[['TOTAL FACTURADO', 'GANANCIA']]
                 .sum()
                 .reset_index()
                 .melt("FECHA", var_name="Tipo", value_name="Monto")
    )

    # Gráfica: línea con puntos para cada métrica
    chart = (
        alt.Chart(df2)
           .mark_line(point=True)
           .encode(
               x=alt.X("FECHA:T", title="Mes", axis=alt.Axis(format="%b %Y")),
               y=alt.Y("Monto:Q", title="Monto"),
               color=alt.Color("Tipo:N", title="Concepto", scale=alt.Scale(scheme="category10")),
               tooltip=[
                   alt.Tooltip("FECHA:T", title="Mes", format="%B %Y"),
                   alt.Tooltip("Monto:Q", title="Importe"),
                   alt.Tooltip("Tipo:N", title="Concepto")
               ]
           )
           .properties(width="container", height=300)
    )
    st.altair_chart(chart, use_container_width=True)


def show_top_products(df_items: pd.DataFrame, df_prods: pd.DataFrame, df_rem: pd.DataFrame):
    st.markdown("---")
    st.subheader("Productos más vendidos")

    # Filtrar items según los remitos en el rango
    valid_remitos = df_rem.get("NUMERO REMITO", [])
    df_items_filt = df_items[df_items["NUMERO REMITO"].isin(valid_remitos)]

    if df_items_filt.empty:
        st.info("No hay datos de venta de productos en el rango seleccionado.")
        return

    # Unir categoría usando 'ARTICULO' y 'PRODUCTO'
    if "ARTICULO" in df_items_filt.columns and "PRODUCTO" in df_prods.columns:
        df_full = df_items_filt.merge(
            df_prods.rename(columns={"PRODUCTO": "ARTICULO"})[["ARTICULO", "CATEGORIA"]],
            on="ARTICULO",
            how="left"
        )
    else:
        df_full = df_items_filt.copy()
        df_full["CATEGORIA"] = "Sin categoría"

    # Selección de Top N y categoría
    top_n = st.slider("Mostrar Top N productos:", 5, 20, 5)
    modo = st.radio("Ver:", ["Todas las categorías", "Por categoría"], horizontal=True)
    if modo == "Por categoría":
        categoria = st.selectbox("Selecciona categoría", sorted(df_full["CATEGORIA"].unique()))
        df_full = df_full[df_full["CATEGORIA"] == categoria]

    # Calcular métricas
    top_prod = (
        df_full.groupby("ARTICULO")["CANTIDAD"]
               .sum()
               .nlargest(top_n)
               .reset_index(name="Unidades vendidas")
    )

    # Gráfica Altair
    chart = (
        alt.Chart(top_prod)
           .mark_bar()
           .encode(
               y=alt.Y("ARTICULO:N", sort="-x", title="Producto"),
               x=alt.X("Unidades vendidas:Q", title="Unidades vendidas"),
               tooltip=[
                   alt.Tooltip("ARTICULO:N", title="Producto"),
                   alt.Tooltip("Unidades vendidas:Q", title="Cantidad")
               ]
           )
           .properties(width="container", height=300)
    )
    st.altair_chart(chart, use_container_width=True)

def show_remitos_by_weekday(df_rem: pd.DataFrame):
    st.markdown("---")
    st.subheader("Remitos por día de la semana")
    if df_rem.empty:
        st.info("No hay datos de remitos para este análisis.")
        return

    dias_map = {
        "Monday": "Lunes", "Tuesday": "Martes",
        "Wednesday": "Miércoles", "Thursday": "Jueves",
        "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
    }
    df = df_rem.copy()
    df["DIA_SEMANA"] = df["FECHA"].dt.day_name().map(dias_map)

    conteo = (
        df["DIA_SEMANA"]
          .value_counts()
          .reindex(list(dias_map.values()), fill_value=0)
          .rename_axis("Día")
          .reset_index(name="Remitos")
    )

    chart = (
        alt.Chart(conteo)
           .mark_bar()
           .encode(
               x=alt.X("Día:N", sort=list(dias_map.values()), title="Día"),
               y=alt.Y("Remitos:Q", title="Cantidad de remitos"),
               tooltip=[
                   alt.Tooltip("Día:N"),
                   alt.Tooltip("Remitos:Q", title="Remitos")
               ]
           )
           .properties(width="container", height=300)
    )
    st.altair_chart(chart, use_container_width=True)


def show_sales_by_category(df_items: pd.DataFrame, df_prods: pd.DataFrame, df_rem: pd.DataFrame):
    st.markdown("---")
    st.subheader("Participación de categorías en ventas")

    # 1) Filtrar items según remitos en el rango
    valid = df_rem["NUMERO REMITO"]
    df = df_items[df_items["NUMERO REMITO"].isin(valid)]

    # 2) Asociar categoría
    merged = df.merge(
        df_prods.rename(columns={"PRODUCTO": "ARTICULO"})[["ARTICULO","CATEGORIA"]],
        left_on="ARTICULO", right_on="ARTICULO", how="left"
    )

    # 3) Sumar importe por categoría
    by_cat = (
        merged.groupby("CATEGORIA")["SUBTOTAL"]
              .sum()
              .reset_index(name="Monto")
    )
    if by_cat["Monto"].sum() == 0:
        st.info("No hay ventas para mostrar por categoría.")
        return

    # 4) Pie / donut chart
    chart = (
        alt.Chart(by_cat)
           .mark_arc(innerRadius=50)
           .encode(
               theta=alt.Theta("Monto:Q", title=""),
               color=alt.Color(
                   "CATEGORIA:N",
                   title="Categoría",
                   legend=alt.Legend(orient="right", title="Categoría")
               ),
               tooltip=[
                   alt.Tooltip("CATEGORIA:N", title="Categoría"),
                   alt.Tooltip("Monto:Q", title="Total", format=",.2f")
               ]
           )
           .properties(width="container", height=300)
    )

    st.altair_chart(chart, use_container_width=True)


def show_ticket_distribution(df_rem: pd.DataFrame):
    st.markdown("---")
    st.subheader("Distribución de valor de remitos")

    if df_rem.empty:
        st.info("No hay remitos para analizar.")
        return

    chart = (
        alt.Chart(df_rem)
           .mark_bar()
           .encode(
               x=alt.X("TOTAL FACTURADO:Q",
                       bin=alt.Bin(maxbins=30),
                       title="Valor del remito"),
               y=alt.Y("count()", title="Cantidad de remitos"),
               tooltip=[alt.Tooltip("count()", title="Remitos")]
           )
           .properties(width="container", height=300)
    )
    st.altair_chart(chart, use_container_width=True)

def show_daily_heatmap(df_rem: pd.DataFrame):
    st.markdown("---")
    st.subheader("Mapa de calor diario de facturación")

    if df_rem.empty:
        st.info("No hay datos de remitos para este análisis.")
        return

    # 1) Agregar columna date y totalizar por día
    df2 = (
        df_rem
        .groupby(df_rem["FECHA"].dt.date)["TOTAL FACTURADO"]
        .sum()
        .reset_index(name="Monto")
        .rename(columns={"FECHA": "date"})
    )

    # 2) Calcular día de la semana y número de semana ISO
    df2["dow"]  = pd.to_datetime(df2["date"]).dt.day_name()
    df2["week"] = pd.to_datetime(df2["date"]).dt.isocalendar().week

    # Orden de días en español
    orden_dias = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    nombres_es = {
        "Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles",
        "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sábado","Sunday":"Domingo"
    }
    df2["dow"] = pd.Categorical(df2["dow"], categories=orden_dias, ordered=True)
    df2["dow_es"] = df2["dow"].map(nombres_es)

    # 3) Construir el heatmap
    chart = (
        alt.Chart(df2)
           .mark_rect()
           .encode(
               x=alt.X("week:O", title="Semana del año"),
               y=alt.Y("dow_es:N", title="Día de la semana", sort=list(nombres_es.values())),
               color=alt.Color("Monto:Q", title="Facturación"),
               tooltip=[
                   alt.Tooltip("date:T", title="Fecha"),
                   alt.Tooltip("Monto:Q", title="Total facturado")
               ]
           )
           .properties(height=200, width="container")
    )

    st.altair_chart(chart, use_container_width=True)



def dashboard_page():
    st.title("📊 Dashboard de Ventas")

    df_prods, df_rem, df_items, df_cli = load_all_data(SPREADSHEET_URL)

    # — Filtro global de fechas —
    if df_rem.empty:
        st.info("No hay remitos cargados.")
        return

    min_date = df_rem["FECHA"].dt.date.min()
    max_date = df_rem["FECHA"].dt.date.max()
    start_date, end_date = st.date_input(
        "Selecciona rango de fechas",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )
    df_rem = df_rem[
        (df_rem["FECHA"].dt.date >= start_date) &
        (df_rem["FECHA"].dt.date <= end_date)
    ]

    # Una pequeña confirmación del conteo
    st.caption(f"{df_rem.shape[0]} remitos entre {start_date} y {end_date}")

    # Mostrar secciones
    show_kpis(df_rem, df_cli)
    show_monthly_trend(df_rem)
    show_top_clients(df_rem, df_cli)
    show_fact_vs_gain(df_rem)
    show_top_products(df_items, df_prods, df_rem)
    show_remitos_by_weekday(df_rem)
    show_sales_by_category(df_items, df_prods, df_rem)
    show_ticket_distribution(df_rem)
    show_daily_heatmap(df_rem)

if __name__ == "__main__":
    dashboard_page()
