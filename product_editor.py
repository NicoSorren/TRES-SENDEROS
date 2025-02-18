# product_editor.py
import streamlit as st
import pandas as pd

class ProductEditor:
    def __init__(self, dataframe):
        # Almacena el DataFrame en session_state para mantener los cambios durante la sesión
        if "df" not in st.session_state:
            st.session_state.df = dataframe.copy()
        self.df = st.session_state.df

    def edit_products_by_category(self):
        st.write("### Edición de Productos por Categoría")
        # Obtener las categorías únicas del DataFrame
        categorias = self.df["CATEGORIA"].astype(str).str.strip().unique()
        # Iterar sobre cada categoría y crear un expander
        for cat in categorias:
            with st.expander(f"Categoría: {cat}"):
                # Filtrar productos de la categoría actual
                df_cat = self.df[self.df["CATEGORIA"].astype(str).str.strip() == cat]
                for index, row in df_cat.iterrows():
                    st.markdown(f"**Producto:** {row['PRODUCTO']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        # Usamos la función parse_price para convertir a número; en este ejemplo usamos float() asumiendo que ya están limpios
                        try:
                            precio_inicial = (row["PRECIO VENTA"])
                        except:
                            precio_inicial = 0.0
                        new_price = st.number_input(
                            f"Precio Venta para {row['PRODUCTO']}",
                            value=precio_inicial,
                            step=1.0,
                            key=f"precio_{index}"
                        )
                    with col2:
                        new_brand = st.text_input(
                            f"Marca para {row['PRODUCTO']}",
                            value=row["MARCA"],
                            key=f"marca_{index}"
                        )
                    # Actualizar el DataFrame en session_state
                    st.session_state.df.at[index, "PRECIO VENTA"] = new_price
                    st.session_state.df.at[index, "MARCA"] = new_brand

    def show_data(self):
        st.write("### Datos Actualizados")
        st.dataframe(self.df)
