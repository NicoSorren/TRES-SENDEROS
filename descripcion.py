# descripcion.py
import streamlit as st
from sheet_connector import update_spreadsheet

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit?gid=0#gid=0"

def _on_prod_change():
    """Callback para recargar la descripción cuando cambia el producto."""
    df = st.session_state.df
    idx = df[
        (df["CATEGORIA"].str.strip() == st.session_state.desc_cat)
      & (df["PRODUCTO"] == st.session_state.desc_prod)
    ].index[0]
    # Carga la descripción actual en el estado
    st.session_state.desc_text = df.at[idx, "DESCRIPCION"] or ""


def edit_descriptions():
    with st.expander("✏️ Editar Descripción de Productos", expanded=True):
        st.header("Editar Descripción de Producto")

        df = st.session_state.df

        # 1) Selectbox de categoría (sin callback)
        categorias = (
            df["CATEGORIA"]
             .dropna()
             .astype(str)
             .str.strip()
             .unique()
             .tolist()
        )
        st.selectbox(
            "Selecciona la categoría",
            categorias,
            key="desc_cat",
            # Al cambiar de categoría, también reseteamos el producto
            on_change=lambda: st.session_state.pop("desc_prod", None)
        )

        # 2) Selectbox de producto, con callback
        df_cat = df[df["CATEGORIA"].str.strip() == st.session_state.desc_cat]
        productos = df_cat["PRODUCTO"].dropna().astype(str).unique().tolist()
        st.selectbox(
            "Selecciona el producto",
            productos,
            key="desc_prod",
            on_change=_on_prod_change
        )

        # 3) Text area siempre lee de st.session_state.desc_text
        #    La primera vez, desc_text no existe → lo inicializamos:
        if "desc_text" not in st.session_state:
            # forzamos la carga inicial
            _on_prod_change()

        nueva_desc = st.text_area(
            "Descripción",
            value=st.session_state.desc_text,
            key="desc_text",
            height=150
        )

        # 4) Botón de guardado
        if st.button("Guardar descripción", key="save_desc"):
            # Actualiza DF en sesión y en Google Sheets
            idx = df[
                (df["CATEGORIA"].str.strip() == st.session_state.desc_cat)
              & (df["PRODUCTO"] == st.session_state.desc_prod)
            ].index[0]
            st.session_state.df.at[idx, "DESCRIPCION"] = nueva_desc
            update_spreadsheet(SPREADSHEET_URL, st.session_state.df)
            st.success(f"Descripción de «{st.session_state.desc_prod}» actualizada.")