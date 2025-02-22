import streamlit as st
import pandas as pd
import re
from collections import defaultdict
from sku_generator import generar_sku

def migrate_sku_page():
    st.title("Migrar SKU a Productos Existentes")
    
    if "df" not in st.session_state:
        st.error("No se encontró el DataFrame con productos.")
        return
    
    # Diccionarios en session_state para llevar control
    if "used_skus" not in st.session_state:
        st.session_state["used_skus"] = defaultdict(int)
    if "cat_codes" not in st.session_state:
        st.session_state["cat_codes"] = {}

    df = st.session_state.df

    st.markdown("Esta función asignará un código SKU a cada producto que no lo tenga (celda vacía o NaN). Solo se hace **una vez**.")

    if st.button("Migrar SKU"):
        df = asignar_skus_a_productos_existentes(df)
        st.session_state.df = df
        st.success("¡Migración de SKU completada!")
    
    st.dataframe(st.session_state.df)

def asignar_skus_a_productos_existentes(df):
    from sku_generator import generar_sku
    
    if "SKU" not in df.columns:
        df["SKU"] = ""
    
    used_skus = st.session_state["used_skus"]
    cat_codes = st.session_state["cat_codes"]
    
    for idx, row in df.iterrows():
        sku_actual = str(row.get("SKU", "")).strip()
        if not sku_actual or sku_actual.upper() == "NAN":
            producto = row["PRODUCTO"]
            categoria = row["CATEGORIA"]
            
            # Revisar tipo de venta. Si no existe la columna "KG / UNIDAD", ajusta la lógica
            tipo = row.get("KG / UNIDAD", "")
            if not tipo:
                tipo = "UNIDAD"  # Por defecto, si no hay nada, consideramos UNIDAD
            
            # FRACCIONAMIENTO puede estar vacío para UNIDAD
            fraccionamiento = str(row.get("FRACCIONAMIENTO", "")).strip()
            
            nuevo_sku = generar_sku(producto, categoria, fraccionamiento, tipo, used_skus, cat_codes)
            df.at[idx, "SKU"] = nuevo_sku
    
    return df

if __name__ == "__main__":
    migrate_sku_page()
