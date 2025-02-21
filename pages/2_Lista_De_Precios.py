# pages/ListaPrecios.py
import streamlit as st
import pandas as pd
from lista_precios_utils import generar_lista_precios_df, crear_excel_con_estilo

def lista_precios_page():
    st.title("Generar Lista de Precios")
    
    if "df" not in st.session_state:
        st.error("No se encontró el DataFrame con productos. Por favor, carga los productos primero.")
        return
    
    df = st.session_state.df
    st.markdown("Esta funcionalidad genera una lista de precios en base a los productos disponibles.")
    
    if st.button("Generar Lista de Precios"):
        try:
            df_out, row_types = generar_lista_precios_df(df)
        except Exception as e:
            st.error(f"Error al generar la lista de precios: {e}")
            return
        
        st.markdown("### Vista Previa de la Lista de Precios")
        st.dataframe(df_out)
        
        excel_file = crear_excel_con_estilo(df_out, row_types)
        st.download_button(
            label="Descargar Lista de Precios (Excel)",
            data=excel_file,
            file_name="ListaPrecios.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
if __name__ == "__main__":
    lista_precios_page()
