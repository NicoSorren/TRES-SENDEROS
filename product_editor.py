

# product_editor.py
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
        # Obtener las categorías únicas, ordenadas para mejor experiencia
        categorias = sorted(self.df["CATEGORIA"].astype(str).str.strip().unique())
        
        # Selección de la categoría a editar
        selected_category = st.selectbox("Selecciona la categoría a editar", options=categorias)
        
        # Filtrar los productos de la categoría seleccionada
        df_cat = self.df[self.df["CATEGORIA"].astype(str).str.strip() == selected_category]
        
        # Diccionario temporal para guardar los cambios
        temp_data = {}
        
        with st.form(key=f"form_{selected_category}"):
            for index, row in df_cat.iterrows():
                st.markdown(f"**Producto:** {row['PRODUCTO']}")
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                
                with col1:
                    new_name = st.text_input("Nombre", value=row["PRODUCTO"], key=f"name_{index}")
                    temp_data[f"name_{index}"] = new_name
                
                with col2:
                    try:
                        precio_inicial = float(row["PRECIO VENTA"])
                    except ValueError:
                        precio_inicial = 0.0
                    new_price = st.number_input("Precio", value=precio_inicial, step=1.0, key=f"precio_{index}")
                    temp_data[f"precio_{index}"] = new_price
                
                with col3:
                    new_brand = st.text_input("Marca", value=row["MARCA"], key=f"marca_{index}")
                    temp_data[f"marca_{index}"] = new_brand

                with col4:
                            try:
                                costo_inicial = float(row["COSTO"])
                            except (ValueError, TypeError):
                                costo_inicial = 0.0
                            new_costo = st.number_input(
                                "Costo",
                                value=costo_inicial,
                                step=1.0,
                                key=f"costo_{index}"
                            )
                            temp_data[f"costo_{index}"] = new_costo
            
            submitted = st.form_submit_button("Guardar cambios en esta categoría")
            if submitted:
                # Aplicar los cambios al DataFrame en session_state
                for index, row in df_cat.iterrows():
                    st.session_state.df.at[index, "PRODUCTO"] = temp_data[f"name_{index}"]
                    st.session_state.df.at[index, "PRECIO VENTA"] = temp_data[f"precio_{index}"]
                    st.session_state.df.at[index, "MARCA"] = temp_data[f"marca_{index}"]
                    st.session_state.df.at[index, "COSTO"] = temp_data[f"costo_{index}"]
                st.success(f"Cambios guardados para la categoría {selected_category}")
