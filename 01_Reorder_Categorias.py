import streamlit as st
import pandas as pd

st.title("Reordenar Categorías")

# Se asume que el DataFrame ya está cargado en st.session_state.df desde app.py
if "df" not in st.session_state:
    st.error("No se encontraron datos. Por favor, carga primero los productos.")
else:
    df = st.session_state.df
    # Obtener la lista de categorías según el orden actual (sin ordenar)
    cat_list = list(df["CATEGORIA"].astype(str).str.strip().drop_duplicates())
    
    st.write("Orden actual sugerido:", ", ".join(cat_list))
    
    with st.form(key="reorder_form"):
        new_order = []
        st.write("Selecciona la categoría para cada posición:")
        for i in range(len(cat_list)):
            selected = st.selectbox(f"Posición {i+1}", options=cat_list, index=i, key=f"pos_{i}")
            new_order.append(selected)
        submitted = st.form_submit_button("Aplicar Orden de Categorías")
        if submitted:
            if len(set(new_order)) != len(new_order):
                st.error("Cada posición debe tener una categoría única. Revisa tu selección.")
            else:
                st.session_state.category_order = new_order
                st.session_state.df["CATEGORIA"] = pd.Categorical(
                    st.session_state.df["CATEGORIA"].astype(str).str.strip(),
                    categories=new_order,
                    ordered=True
                )
                st.session_state.df.sort_values(by=["CATEGORIA", "PRODUCTO"], inplace=True)
                st.session_state.df.reset_index(drop=True, inplace=True)
                st.success("Orden de categorías actualizado correctamente.")
                st.write("Nuevo orden:", ", ".join(new_order))
                st.dataframe(st.session_state.df)
