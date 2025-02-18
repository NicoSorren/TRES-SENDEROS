import streamlit as st
import pandas as pd

class ProductEditor:
    def __init__(self, dataframe):
        # Guardamos el DataFrame en session_state para persistencia durante la sesión
        if "df" not in st.session_state:
            st.session_state.df = dataframe.copy()
        self.df = st.session_state.df

    def filter_by_category(self):
        # Filtra el DataFrame por categoría usando un multiselect en el sidebar
        categorias = self.df["CATEGORIA"].unique()
        selected = st.sidebar.multiselect("Selecciona las categorías a editar", options=categorias, default=list(categorias))
        filtered = self.df[self.df["CATEGORIA"].isin(selected)]
        return filtered

    def edit_products(self, filtered_df):
        st.write("### Edición de Precio y Marca")
        for index, row in filtered_df.iterrows():
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
            # Actualizar los valores en el DataFrame almacenado en session_state
            st.session_state.df.at[index, "PRECIO VENTA"] = new_price
            st.session_state.df.at[index, "MARCA"] = new_brand

    def show_data(self):
        st.write("### Datos Actualizados")
        st.dataframe(self.df)
