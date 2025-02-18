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
        # Obtener las categorías únicas del DataFrame
        categorias = self.df["CATEGORIA"].unique()
        for cat in categorias:
            with st.expander(f"Categoría: {cat}"):
                # Filtrar productos de la categoría actual
                df_cat = self.df[self.df["CATEGORIA"] == cat]
                for index, row in df_cat.iterrows():
                    st.write(f"**Producto:** {row['PRODUCTO']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        new_price = st.number_input(
                            f"Precio Venta para {row['PRODUCTO']}",
                            value=float(row["PRECIO VENTA"]),
                            step=1,
                            key=f"precio_{index}"
                        )
                    with col2:
                        new_brand = st.text_input(
                            f"Marca para {row['PRODUCTO']}",
                            value=row["MARCA"],
                            key=f"marca_{index}"
                        )
                    # Actualizar los valores en el DataFrame en session_state
                    st.session_state.df.at[index, "PRECIO VENTA"] = new_price
                    st.session_state.df.at[index, "MARCA"] = new_brand

    def show_data(self):
        st.write("### Datos Actualizados")
        st.dataframe(self.df)
