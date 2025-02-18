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
            with st.expander(f"Categoría: {cat}"):
                # Filtrar productos de la categoría actual
                df_cat = self.df[self.df["CATEGORIA"].astype(str).str.strip() == cat]
                # Diccionario temporal para guardar los cambios de esta categoría
                temp_data = {}
                with st.form(key=f"form_{cat}"):
                    for index, row in df_cat.iterrows():
                        st.markdown(f"**Producto:** {row['PRODUCTO']}")
                        col1, col2 = st.columns(2)
                        with col1:
                            try:
                                precio_inicial = float(row["PRECIO VENTA"])
                            except ValueError:
                                precio_inicial = 0.0
                            temp_data[f"precio_{index}"] = st.number_input(
                                f"Precio Venta para {row['PRODUCTO']}",
                                value=precio_inicial,
                                step=1.0,
                                key=f"precio_{index}"
                            )
                        with col2:
                            temp_data[f"marca_{index}"] = st.text_input(
                                f"Marca para {row['PRODUCTO']}",
                                value=row["MARCA"],
                                key=f"marca_{index}"
                            )
                    submitted = st.form_submit_button("Guardar cambios en esta categoría")
                    if submitted:
                        # Actualizamos el DataFrame de la sesión con los valores ingresados en el formulario
                        for index, row in df_cat.iterrows():
                            st.session_state.df.at[index, "PRECIO VENTA"] = temp_data[f"precio_{index}"]
                            st.session_state.df.at[index, "MARCA"] = temp_data[f"marca_{index}"]
                        st.success(f"Cambios guardados para la categoría {cat}")

    def show_data(self):
        st.write("### Datos Actualizados")
        st.dataframe(self.df)
