import streamlit as st
import pandas as pd

def reorder_categories():
    st.header("Reordenar Categorías")
    # Obtener las categorías actuales del DataFrame en session_state
    # Se asume que ya tienes st.session_state.df cargado
    df = st.session_state.df
    cat_list = list(df["CATEGORIA"].astype(str).str.strip().drop_duplicates())
    
    with st.form(key="reorder_form"):
        new_order = []
        st.write("Asigna la categoría para cada posición:")
        # Para cada posición, un selectbox con las categorías disponibles
        for i in range(len(cat_list)):
            selected = st.selectbox(f"Posición {i+1}", options=cat_list, index=i, key=f"pos_{i}")
            new_order.append(selected)
        submitted = st.form_submit_button("Aplicar Orden de Categorías")
        if submitted:
            # Validar que no haya duplicados
            if len(set(new_order)) != len(new_order):
                st.error("Cada posición debe tener una categoría única. Por favor, revisa la selección.")
            else:
                st.session_state.category_order = new_order
                # Convertir la columna "CATEGORIA" del DataFrame a tipo categórico con este orden
                st.session_state.df["CATEGORIA"] = pd.Categorical(
                    st.session_state.df["CATEGORIA"].astype(str).str.strip(),
                    categories=new_order,
                    ordered=True
                )
                st.session_state.df.sort_values(by=["CATEGORIA", "PRODUCTO"], inplace=True)
                st.session_state.df.reset_index(drop=True, inplace=True)
                st.success("Orden de categorías actualizado correctamente.")
                st.dataframe(st.session_state.df)
    return st.session_state.get("category_order", cat_list)
