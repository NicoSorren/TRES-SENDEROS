#product_editor.py

import streamlit as st
import pandas as pd

class ProductEditor:
    def __init__(self, dataframe):
        # Almacenar el DataFrame en session_state para mantener los cambios durante la sesión
        if "df" not in st.session_state:
            st.session_state.df = dataframe.copy()
        self.df = st.session_state.df

    def edit_products_by_category(self):
        st.write("### Edición de Productos por Categoría")
        # Obtener las categorías únicas, limpiando espacios
        categorias = self.df["CATEGORIA"].astype(str).str.strip().unique()
        for cat in categorias:
            with st.expander(f"{cat}"):
                # Filtrar productos de la categoría actual
                df_cat = self.df[self.df["CATEGORIA"].astype(str).str.strip() == cat]
                
                # Diccionario temporal para guardar los cambios de esta categoría
                temp_data = {}
                
                with st.form(key=f"form_{cat}"):
                    for index, row in df_cat.iterrows():
                        st.markdown(f"**Producto:** {row['PRODUCTO']}")
                        # Usamos tres columnas para editar Nombre, Precio y Marca
                        col1, col2, col3 = st.columns([2,1,1])
                        
                        with col1:
                            # Editar el NOMBRE del producto
                            new_name = st.text_input(
                                "Nombre",
                                value=row["PRODUCTO"],
                                key=f"name_{index}"
                            )
                            temp_data[f"name_{index}"] = new_name
                        
                        with col2:
                            # Editar el PRECIO
                            try:
                                precio_inicial = float(row["PRECIO VENTA"])
                            except ValueError:
                                precio_inicial = 0.0
                            new_price = st.number_input(
                                "Precio",
                                value=precio_inicial,
                                step=1.0,
                                key=f"precio_{index}"
                            )
                            temp_data[f"precio_{index}"] = new_price
                        
                        with col3:
                            # Editar la MARCA
                            new_brand = st.text_input(
                                "Marca",
                                value=row["MARCA"],
                                key=f"marca_{index}"
                            )
                            temp_data[f"marca_{index}"] = new_brand
                    
                    submitted = st.form_submit_button("Guardar cambios en esta categoría")
                    if submitted:
                        # Aplicamos los cambios al DataFrame en session_state
                        for index, row in df_cat.iterrows():
                            st.session_state.df.at[index, "PRODUCTO"] = temp_data[f"name_{index}"]
                            st.session_state.df.at[index, "PRECIO VENTA"] = temp_data[f"precio_{index}"]
                            st.session_state.df.at[index, "MARCA"] = temp_data[f"marca_{index}"]
                        
                        st.success(f"Cambios guardados para la categoría {cat}")

    def show_data(self):
        st.write("### Datos Actualizados")
        st.dataframe(self.df)