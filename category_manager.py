#category_manager.py

import streamlit as st
import pandas as pd

class CategoryManager:
    def __init__(self):
        if "df" not in st.session_state:
            st.error("No se encontraron datos. Carga primero los productos.")
        self.df = st.session_state.df

    def move_products(self):
        st.subheader("Mover Productos entre Categorías")
        with st.form(key="move_cat_form"):
            source_cat = st.selectbox(
                "Categoría de origen",
                options=self.df["CATEGORIA"].astype(str).str.strip().drop_duplicates()
            )
            df_source = self.df[self.df["CATEGORIA"].astype(str).str.strip() == source_cat]
            if df_source.empty:
                st.info("No hay productos en la categoría de origen seleccionada.")
            else:
                options = df_source.apply(lambda row: f"{row.name} - {row['PRODUCTO']}", axis=1).tolist()
                products_to_move = st.multiselect("Productos a mover", options=options)
                
                # Seleccionar la categoría de destino
                cat_list = self.df["CATEGORIA"].astype(str).str.strip().drop_duplicates().tolist()
                dest_cat = st.selectbox("Categoría de destino", options=cat_list)
                
                submitted = st.form_submit_button("Mover Productos")
                if submitted:
                    if not products_to_move:
                        st.warning("No seleccionaste productos.")
                    else:
                        indices = [int(item.split(" - ")[0]) for item in products_to_move]
                        st.session_state.df.loc[indices, "CATEGORIA"] = dest_cat
                        st.success("Productos movidos correctamente.")
                        st.dataframe(st.session_state.df)

    def delete_category(self):
        st.subheader("Eliminar Categoría")
        cat_list = list(self.df["CATEGORIA"].astype(str).str.strip().drop_duplicates())
        if not cat_list:
            st.info("No hay categorías para eliminar.")
            return
        with st.form(key="delete_category_form"):
            cat_to_delete = st.selectbox("Categoría a eliminar", options=cat_list)
            submitted = st.form_submit_button("Eliminar Categoría")
            if submitted:
                df_cat = self.df[self.df["CATEGORIA"].astype(str).str.strip() == cat_to_delete]
                if not df_cat.empty:
                    st.warning(f"La categoría '{cat_to_delete}' tiene {len(df_cat)} producto(s). Se eliminarán esos productos.")
                    st.session_state.df = self.df[self.df["CATEGORIA"].astype(str).str.strip() != cat_to_delete].reset_index(drop=True)
                # Actualizar la lista de categorías en session_state.category_order
                if "category_order" in st.session_state:
                    st.session_state.category_order = [cat for cat in st.session_state.category_order if cat != cat_to_delete]
                st.success(f"Categoría '{cat_to_delete}' eliminada correctamente.")
                st.dataframe(st.session_state.df)

    def modify_category(self):
        st.subheader("Modificar Nombre de Categoría")
        cat_list = sorted(self.df["CATEGORIA"].astype(str).str.strip().drop_duplicates().tolist())
        if not cat_list:
            st.info("No hay categorías para modificar.")
            return
        with st.form(key="modify_category_form"):
            old_cat = st.selectbox("Selecciona la categoría a modificar", options=cat_list)
            new_cat = st.text_input("Nuevo nombre para la categoría", value=old_cat)
            submitted = st.form_submit_button("Modificar Categoría")
            if submitted:
                st.session_state.df.loc[
                    st.session_state.df["CATEGORIA"].astype(str).str.strip() == old_cat,
                    "CATEGORIA"
                ] = new_cat
                st.success(f"Categoría '{old_cat}' modificada a '{new_cat}'.")
                if "category_order" in st.session_state:
                    st.session_state.category_order = [
                        new_cat if cat == old_cat else cat for cat in st.session_state.category_order
                    ]
                st.dataframe(st.session_state.df)

    def manage_categories(self):
        st.write("## Gestionar Categorías")
        with st.expander("Modificar Nombre de Categoría", expanded=False):
            self.modify_category()
        with st.expander("Mover Productos de una Categoría a otra", expanded=True):
            self.move_products()
        with st.expander("Eliminar Categoría", expanded=False):
            self.delete_category()