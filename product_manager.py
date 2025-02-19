#product_manager.py
import streamlit as st
import pandas as pd

class ProductManager:
    def __init__(self, dataframe):
        if "df" not in st.session_state:
            st.session_state.df = dataframe.copy()
        self.df = st.session_state.df

    def add_product(self):
        st.write("### Agregar Producto")

        cat_option = st.radio(
        "¿Categoría existente o nueva?",
        options=["Existente", "Nueva"],
        key="cat_option"
    )
        
        with st.form(key="add_product_form"):
            producto = st.text_input("Nombre del Producto")
            precio = st.text_input("Precio Venta (ej.: $20.200)")
            marca = st.text_input("Marca")

            if cat_option == "Existente":
                # Categoría existente
                categorias_existentes = self.df["CATEGORIA"].astype(str).str.strip().unique().tolist()
                categoria = st.selectbox("Selecciona la Categoría", options=categorias_existentes)
            else:
                # Crear nueva categoría
                categoria = st.text_input("Nombre de la nueva Categoría")
    
            tipo = st.selectbox("Tipo de Venta", options=["KG", "UNIDAD"])
            stock = st.text_input("Stock (usa '-' para stock ilimitado)")
            submitted = st.form_submit_button("Agregar Producto")

            if submitted:
                try:
                    precio_num = float(precio.replace('$','').replace('.', '').replace(',', '.').strip())
                except:
                    precio_num = 0.0

                categoria = categoria.strip()
                if not categoria:
                    st.error("La categoría no puede estar vacía.")
                    return

                # Validar si la categoría ya existe
                current_categories = self.df["CATEGORIA"].astype(str).str.strip().unique().tolist()
                if cat_option == "Nueva" and categoria in current_categories:
                    st.warning(f"La categoría '{categoria}' ya existía, se usará esa.")
                elif cat_option == "Nueva" and categoria not in current_categories:
                    # Agregamos la categoría al order si es que hay un category_order
                    if "category_order" in st.session_state:
                        st.session_state.category_order.append(categoria)
                    else:
                        st.session_state.category_order = current_categories + [categoria]

                # Crear el nuevo producto en el DataFrame
                new_product = {
                    "PRODUCTO": producto,
                    "PRECIO VENTA": precio_num,
                    "MARCA": marca,
                    "CATEGORIA": categoria,
                    "KG / UNIDAD": tipo,
                    "STOCK": stock
                }

                df_current = st.session_state.df
                # Insertar el nuevo producto al final de la categoría
                indices = df_current[df_current["CATEGORIA"].astype(str).str.strip() == categoria].index.tolist()
                if indices:
                    insert_index = indices[-1] + 1
                    df_before = df_current.iloc[:insert_index]
                    df_after = df_current.iloc[insert_index:]
                    new_row_df = pd.DataFrame([new_product])
                    st.session_state.df = pd.concat([df_before, new_row_df, df_after], ignore_index=True)
                else:
                    st.session_state.df = pd.concat([df_current, pd.DataFrame([new_product])], ignore_index=True)

                st.success(f"Producto '{producto}' agregado correctamente en la categoría '{categoria}'.")
                st.dataframe(st.session_state.df)

    def delete_product(self):
        st.write("### Eliminar Producto")
        if self.df.empty:
            st.info("No hay productos para eliminar.")
            return
        
        with st.form(key="delete_product_form"):
            categorias = self.df["CATEGORIA"].astype(str).str.strip().unique().tolist()
            categoria_seleccionada = st.selectbox("Selecciona la categoría", options=categorias)
            
            df_cat = self.df[self.df["CATEGORIA"].astype(str).str.strip() == categoria_seleccionada]
            if df_cat.empty:
                st.warning("No hay productos en la categoría seleccionada.")
            else:
                opciones = df_cat.apply(lambda row: f"{row.name} - {row['PRODUCTO']}", axis=1).tolist()
                productos_a_eliminar = st.multiselect("Selecciona los productos a eliminar", options=opciones)
            
            submitted = st.form_submit_button("Eliminar Productos Seleccionados")
            if submitted:
                if not productos_a_eliminar:
                    st.warning("No seleccionaste ningún producto.")
                else:
                    indices = [int(op.split(" - ")[0]) for op in productos_a_eliminar]
                    st.session_state.df = st.session_state.df.drop(indices).reset_index(drop=True)
                    st.success("Productos eliminados correctamente.")
                    st.dataframe(st.session_state.df)