import streamlit as st
import pandas as pd

st.set_page_config(page_title="Ordenar Categorías")

st.title("Reordenar Categorías")

# Verificar que el DataFrame ya esté cargado en session_state (se comparte con la página principal)
if "df" not in st.session_state:
    st.error("No se encontraron datos. Por favor, carga primero los productos desde la página principal.")
else:
    df = st.session_state.df
    # Obtener la lista de categorías actuales en el orden actual (sin duplicados)
    cat_list = list(df["CATEGORIA"].astype(str).str.strip().drop_duplicates())
    
    st.write("Orden actual sugerido:", ", ".join(cat_list))
    
    # Usamos un formulario para que el usuario reordene las categorías mediante selectboxes
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
