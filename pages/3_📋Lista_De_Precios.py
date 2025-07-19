# pages/3_📋Lista_De_Precios.py

import streamlit as st
import pandas as pd
from io import BytesIO
from lista_precios_utils import (
    generar_lista_precios_df,
    crear_excel_con_estilo,
    df_to_pdf
)

def lista_precios_page():
    st.title("Generar Lista de Precios")

    if "df" not in st.session_state:
        st.error("No se encontró el DataFrame con productos. Por favor, carga los productos primero.")
        return

    df = st.session_state.df
    st.markdown("Esta funcionalidad genera una lista de precios en base a los productos disponibles.")

    # 1) Botón que calcula y guarda en session_state
    if st.button("Generar Lista de Precios"):
        try:
            df_out, row_types = generar_lista_precios_df(df)
            st.session_state["df_out"]     = df_out
            st.session_state["row_types"]  = row_types
        except Exception as e:
            st.error(f"Error al generar la lista de precios: {e}")

    # 2) Si ya tenemos df_out en session_state, mostramos todo lo demás
    if "df_out" in st.session_state:
        df_out    = st.session_state["df_out"]
        row_types = st.session_state["row_types"]

        st.markdown("### Vista Previa de la Lista de Precios")
        st.dataframe(df_out)

        # 3) Descarga de Excel
        excel_file = crear_excel_con_estilo(df_out, row_types)
        st.download_button(
            label="Descargar Lista de Precios (Excel)",
            data=excel_file,
            file_name="ListaPrecios.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.markdown("---")
        st.markdown("### Convertir un Excel a PDF")

        # 4) Uploader para que suba el mismo Excel (o cualquier otro)
        uploaded = st.file_uploader(
            label="Sube tu archivo Excel de Lista de Precios",
            type=["xlsx", "xls"]
        )
        if uploaded is not None:
            try:
                pdf_buffer = df_to_pdf(df_out, row_types)
                st.success("Conversión a PDF exitosa 🎉")
                st.download_button(
                    label="Descargar Lista de Precios (PDF)",
                    data=pdf_buffer,
                    file_name="ListaPrecios.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"No se pudo convertir a PDF: {e}")

if __name__ == "__main__":
    lista_precios_page()
