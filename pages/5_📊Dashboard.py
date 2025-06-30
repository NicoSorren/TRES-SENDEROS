# pages/Dashboard.py

import streamlit as st
import pandas as pd
from sheet_connector import SheetConnector

# URL de tu spreadsheet (la misma que en Remito y Clientes)
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit?gid=0#gid=0"

@st.cache_data(ttl=300, show_spinner=False)
def load_products(url: str) -> pd.DataFrame:
    connector = SheetConnector(url)
    df = connector.get_products()
    return df if df is not None else pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def load_remito_items(url: str) -> pd.DataFrame:
    conn = SheetConnector(url)
    return conn.get_remito_items()

@st.cache_data(ttl=300, show_spinner=False)
def load_remitos(url: str) -> pd.DataFrame:
    conn = SheetConnector(url)
    df = conn.get_remitos()
    if df is None:
        return pd.DataFrame()
    # Preparo fechas y totales
    df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce")
    df["TOTAL FACTURADO"] = pd.to_numeric(df["TOTAL FACTURADO"], errors="coerce")
    # Columna mes-año para filtro
    df["PERIODO"] = df["FECHA"].dt.to_period("M").astype(str)
    return df

@st.cache_data(ttl=300, show_spinner=False)
def load_clients(url: str) -> pd.DataFrame:
    conn = SheetConnector(url)
    df = conn.get_clients()
    if df is None:
        return pd.DataFrame()
    # Preparo fecha de alta
    if "FECHA_ALTA" in df.columns:
        df["FECHA_ALTA"] = pd.to_datetime(df["FECHA_ALTA"], errors="coerce")
    return df

def dashboard_page():
    st.title("📊 Dashboard de Ventas")

    # — Carga de datos —
    df_rem = load_remitos(SPREADSHEET_URL)
    df_cli = load_clients(SPREADSHEET_URL)
    df_items  = load_remito_items(SPREADSHEET_URL)
    df_prods  = load_products(SPREADSHEET_URL)
    st.write(df_prods.head(5))

    # — Métricas —
    now = pd.Timestamp.now()
    total_revenue = df_rem["TOTAL FACTURADO"].sum()
    mask_mes = ((df_rem["FECHA"].dt.year == now.year) & (df_rem["FECHA"].dt.month == now.month))
    remitos_mes = int(mask_mes.sum())
    ticket_prom = df_rem["TOTAL FACTURADO"].mean()
    nuevos_mes = 0
    if "FECHA_ALTA" in df_cli.columns:
        mask_nuevos = ((df_cli["FECHA_ALTA"].dt.year == now.year) &
                       (df_cli["FECHA_ALTA"].dt.month == now.month))
        nuevos_mes = int(mask_nuevos.sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Facturación total", f"${total_revenue:,.2f}")
    c2.metric("📦 Remitos este mes", remitos_mes)
    c3.metric("🎟️ Ticket promedio", f"${ticket_prom or 0:,.2f}")
    c4.metric("🆕 Clientes nuevos", nuevos_mes)

    st.markdown("---")

    # — Tendencia mensual —
    st.subheader("Tendencia mensual de facturación")
    if df_rem.empty:
        st.info("No hay datos de remitos para graficar.")
    else:
        monthly = (df_rem.set_index("FECHA")
                     .resample("M")["TOTAL FACTURADO"]
                     .sum()
                     .rename("Facturación"))
        st.line_chart(monthly)

    st.markdown("---")

    # — Top 5 clientes con filtro de mes —
    st.subheader("Top 5 clientes por facturación")
    if df_rem.empty or df_cli.empty:
        st.info("No hay suficientes datos para mostrar el top 5.")
    else:
        # Construyo lista de periodos únicos y añado “Todos”
        periodos = ["Todos"] + sorted(df_rem["PERIODO"].unique(), reverse=True)
        sel_periodo = st.selectbox("Filtrar periodo", periodos, index=0)

        if sel_periodo != "Todos":
            df_filt = df_rem[df_rem["PERIODO"] == sel_periodo]
        else:
            df_filt = df_rem

        if df_filt.empty:
            st.warning(f"No hay remitos en {sel_periodo}.")
        else:
            rev_by_client = (df_filt.groupby("ID CLIENTE")["TOTAL FACTURADO"]
                                    .sum()
                                    .sort_values(ascending=False)
                                    .head(5))
            # reemplazo ID por Nombre
            names_map = df_cli.set_index("ID CLIENTE")["NOMBRE"].to_dict()
            rev_by_client.index = [names_map.get(cid, cid) for cid in rev_by_client.index]
            rev_by_client = rev_by_client.rename("Facturación")
            st.bar_chart(rev_by_client)

    st.markdown("---")

    # — Gráfico 3: Facturación y Ganancia en dos columnas —
    st.subheader("Facturación y Ganancia")

    if df_rem.empty or "GANANCIA" not in df_rem.columns:
        st.info("No hay datos de remitos o falta columna GANANCIA.")
    else:
        # Aseguramos numérico
        df_rem["GANANCIA"] = pd.to_numeric(df_rem["GANANCIA"], errors="coerce").fillna(0)

        # Rango de fechas
        min_fecha = df_rem["FECHA"].min().date()
        max_fecha = df_rem["FECHA"].max().date()
        fecha_inicio, fecha_fin = st.date_input(
            "Filtrar por fecha",
            value=(min_fecha, max_fecha),
            min_value=min_fecha,
            max_value=max_fecha
        )

        mask = (
            (df_rem["FECHA"].dt.date >= fecha_inicio) &
            (df_rem["FECHA"].dt.date <= fecha_fin)
        )
        df_filt = df_rem.loc[mask]

        if df_filt.empty:
            st.warning("No hay remitos en ese rango de fechas.")
        else:
            # Agrupo por día y sumo columnas
            series = (
                df_filt
                .set_index("FECHA")
                .resample("D")[["TOTAL FACTURADO", "GANANCIA"]]
                .sum()
            )

            # Creamos dos columnas para los dos gráficos
            col_fact, col_gan = st.columns(2)
            with col_fact:
                st.subheader("Total Facturado")
                # Área mejor visual para ver el volumen
                st.area_chart(series["TOTAL FACTURADO"])
            with col_gan:
                st.subheader("Total Ganancia")
                st.area_chart(series["GANANCIA"])

    st.markdown("---")
    st.subheader("Productos más vendidos")

    if df_items.empty:
        st.info("Aún no hay datos de venta de productos.")
    else:
        # 1) Unir categoría
        if not df_prods.empty and {"PRODUCTO","CATEGORIA"}.issubset(df_prods.columns):
            df_full = df_items.merge(
                df_prods[["PRODUCTO","CATEGORIA"]]
                    .rename(columns={"PRODUCTO":"ARTICULO"}),
                on="ARTICULO",
                how="left"
            )
        else:
            df_full = df_items.copy()
            df_full["CATEGORIA"] = "Sin categoría"

        # 2) Top N
        top_n = st.selectbox("Mostrar Top:", [5, 10], key="top_n")

        # 3) Filtrar por categoría
        modo_cat = st.radio("Ver:", ["Todas las categorías", "Por categoría"], horizontal=True, key="modo_cat")
        if modo_cat == "Por categoría":
            cats = sorted(df_full["CATEGORIA"].dropna().unique())
            sel_cat = st.selectbox("Selecciona categoría:", cats, key="sel_cat")
            df_filt = df_full[df_full["CATEGORIA"] == sel_cat]
        else:
            df_filt = df_full

        # 4) Agrupar y mostrar
        if df_filt.empty:
            st.warning("No hay ventas en la selección actual.")
        else:
            top_prod = (
                df_filt
                .groupby("ARTICULO")["CANTIDAD"]
                .sum()
                .sort_values(ascending=False)
                .head(top_n)
                .rename("Unidades vendidas")
            )
            st.bar_chart(top_prod)

    st.markdown("---")
    st.subheader("Remitos por día de la semana")

    if df_rem.empty:
        st.info("No hay datos de remitos para este análisis.")
    else:
        # Contamos cuántos remitos caen en cada día
        df_rem["DIA_SEMANA"] = df_rem["FECHA"].dt.day_name()
        # (Opcional: si quieres en español, mapea así)
        dias_map = {
            "Monday":    "Lunes",
            "Tuesday":   "Martes",
            "Wednesday": "Miércoles",
            "Thursday":  "Jueves",
            "Friday":    "Viernes",
            "Saturday":  "Sábado",
            "Sunday":    "Domingo"
        }
        df_rem["DIA_SEMANA"] = df_rem["DIA_SEMANA"].map(dias_map)

        conteo = (
            df_rem["DIA_SEMANA"]
            .value_counts()
            .reindex(["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"])
            .fillna(0)
        )
        st.bar_chart(conteo.rename("Remitos"))

    # — Aquí podríamos añadir más gráficas… —

if __name__ == "__main__":
    dashboard_page()
