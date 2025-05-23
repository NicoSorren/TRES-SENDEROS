import streamlit as st
import pandas as pd
import re
from sku_generator import generar_sku
from collections import defaultdict

class ProductManager:
    def __init__(self, dataframe):
        if "df" not in st.session_state:
            st.session_state.df = dataframe.copy()
        self.df = st.session_state.df
        if "used_skus" not in st.session_state:
            st.session_state["used_skus"] = defaultdict(int)
        # Inicializamos cat_codes como dict vacío para que se vayan generando los códigos automáticamente
        if "cat_codes" not in st.session_state:
            st.session_state["cat_codes"] = {}

    def add_product(self):
        st.write("### Agregar Producto")

        cat_option = st.radio(
            "¿Categoría existente o nueva?",
            options=["Existente", "Nueva"],
            key="cat_option"
        )
        
        with st.form(key="add_product_form"):
            producto = st.text_input("Nombre del Producto", key="producto_input")
            precio = st.text_input("Precio Venta (ej.: $20.200)", key="precio_input")
            costo  = st.text_input("Costo (ej.: $10.000)", key="costo_input")            # ← Nuevo campo
            marca  = st.text_input("Marca", key="marca_input")

            if cat_option == "Existente":
                categorias_existentes = self.df["CATEGORIA"].astype(str).str.strip().unique().tolist()
                categoria = st.selectbox("Selecciona la Categoría", options=categorias_existentes, key="categoria_existente")
            else:
                categoria = st.text_input("Nombre de la nueva Categoría", key="nueva_categoria")

            tipo  = st.selectbox("Tipo de Venta", options=["KG", "UNIDAD"], key="tipo_venta")
            stock = st.text_input("Stock (usa '-' para stock ilimitado y '0' cuando hay stock)", key="stock_input")
            
            # Lógica de variante igual que antes...
            if cat_option == "Existente" and tipo.upper().strip() == "KG":
                df_cat = self.df[self.df["CATEGORIA"].astype(str).str.strip() == categoria]
                kg_products = df_cat[df_cat["KG / UNIDAD"].astype(str).str.strip().str.upper() == "KG"]

                if not kg_products.empty:
                    frac_values = kg_products["FRACCIONAMIENTO"].dropna().unique()
                    variante = frac_values[0] if len(frac_values) > 0 else ""
                else:
                    variante = ""
            else:
                variante = st.text_input("Fraccionamiento (Ej: 100g, 250g, 500g o 'unidad' para UNIDAD)",
                                        value="", key="variante_input")

            submitted = st.form_submit_button("Agregar Producto")
            if submitted:
                # Parseo del precio
                try:
                    precio_num = float(precio.replace('$','').replace('.', '').replace(',', '.').strip())
                except Exception as e:
                    st.error(f"Error en el precio: {e}")
                    precio_num = 0.0

                # Parseo del costo
                try:
                    costo_num = float(costo.replace('$','').replace('.', '').replace(',', '.').strip())
                except Exception as e:
                    st.error(f"Error en el costo: {e}")
                    costo_num = 0.0

                categoria = categoria.strip()
                if not categoria:
                    st.error("La categoría no puede estar vacía.")
                    return

                # Manejo de categorías nuevas
                current_categories = self.df["CATEGORIA"].astype(str).str.strip().unique().tolist()
                if cat_option == "Nueva" and categoria in current_categories:
                    st.warning(f"La categoría '{categoria}' ya existía, se usará esa.")
                elif cat_option == "Nueva" and categoria not in current_categories:
                    if "category_order" in st.session_state:
                        st.session_state.category_order.append(categoria)
                    else:
                        st.session_state.category_order = current_categories + [categoria]

                # Generación de SKU
                used_skus = st.session_state["used_skus"]
                cat_codes = st.session_state["cat_codes"]
                sku = generar_sku(
                    nombre_producto=producto,
                    categoria=categoria,
                    fraccionamiento=variante,
                    tipo=tipo,
                    used_skus=used_skus,
                    cat_codes=cat_codes
                )

                # Nuevo diccionario incluyendo COSTO
                new_product = {
                    "SKU": sku,
                    "PRODUCTO": producto,
                    "PRECIO VENTA": precio_num,
                    "COSTO": costo_num,                       # ← Se añade aquí
                    "MARCA": marca,
                    "CATEGORIA": categoria,
                    "KG / UNIDAD": tipo,
                    "STOCK": stock,
                    "FRACCIONAMIENTO": variante
                }

                # Inserción en el DataFrame manteniendo orden por categoría
                df_current = st.session_state.df
                indices = df_current[df_current["CATEGORIA"].astype(str).str.strip() == categoria].index.tolist()
                if indices:
                    insert_index = indices[-1] + 1
                    df_before = df_current.iloc[:insert_index]
                    df_after  = df_current.iloc[insert_index:]
                    new_row_df = pd.DataFrame([new_product])
                    st.session_state.df = pd.concat([df_before, new_row_df, df_after], ignore_index=True)
                else:
                    st.session_state.df = pd.concat([df_current, pd.DataFrame([new_product])], ignore_index=True)

                st.success(f"Producto '{producto}' agregado correctamente en la categoría '{categoria}' con SKU {sku}.")
                st.dataframe(st.session_state.df)


    def delete_product(self):
        st.write("### Eliminar Producto")
        if self.df.empty:
            st.info("No hay productos para eliminar.")
            return

        categorias = self.df["CATEGORIA"].astype(str).str.strip().unique().tolist()
        categorias.sort()
        categoria_seleccionada = st.selectbox("Selecciona la categoría", options=categorias, key="delete_category_selectbox")

        df_cat = self.df[self.df["CATEGORIA"].astype(str).str.strip() == categoria_seleccionada]
        if df_cat.empty:
            st.warning("No hay productos en la categoría seleccionada.")
            return

        with st.form(key="delete_product_form"):
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
