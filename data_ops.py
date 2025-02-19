# data_ops.py

import streamlit as st
import pandas as pd

def update_product(index: int, data: dict):
    """
    Actualiza el producto en el DataFrame central usando el índice y un diccionario de columnas a modificar.
    """
    for col, new_val in data.items():
        st.session_state.df.at[index, col] = new_val

def add_product(new_product: dict, categoria: str):
    """
    Agrega un producto nuevo en el DataFrame central.
    Si existen productos en la categoría, lo inserta al final de esa categoría;
    de lo contrario, lo añade al final.
    """
    df_current = st.session_state.df
    indices = df_current[df_current["CATEGORIA"].astype(str).str.strip() == categoria].index.tolist()
    if indices:
        insert_index = indices[-1] + 1
        df_before = df_current.iloc[:insert_index]
        df_after = df_current.iloc[insert_index:]
        new_row_df = pd.DataFrame([new_product])
        st.session_state.df = pd.concat([df_before, new_row_df, df_after], ignore_index=True)
    else:
        st.session_state.df = pd.concat([df_current, pd.DataFrame([new_product])], ignore_index=True)

def delete_products(indices: list):
    """
    Elimina los productos del DataFrame central a partir de una lista de índices.
    """
    st.session_state.df = st.session_state.df.drop(indices).reset_index(drop=True)
