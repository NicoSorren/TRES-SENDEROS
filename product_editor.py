# product_editor.py
import streamlit as st
import pandas as pd
import re

class ProductEditor:
    def __init__(self, dataframe):
        if "df" not in st.session_state:
            st.session_state.df = dataframe.copy()
        self.df = st.session_state.df

    def edit_products_by_category(self):
        st.write("### Edición de Productos por Categoría")
        categorias = sorted(self.df["CATEGORIA"].astype(str).str.strip().unique())
        selected_category = st.selectbox("Selecciona la categoría a editar", options=categorias)

        df_cat = self.df[self.df["CATEGORIA"].astype(str).str.strip() == selected_category]

        # Este diccionario guardará los datos editados (nombre, precio, marca, etc.)
        # clave: índice del producto, valor: dict con campos editados
        if "temp_data" not in st.session_state:
            st.session_state.temp_data = {}

        # Antes de renderizar el formulario, inicializamos los valores con lo que tenga session_state.temp_data
        temp_data = {}
        for index, row in df_cat.iterrows():
            # Si ya existe en session_state.temp_data, lo usamos. Si no, inicializamos con datos del DF.
            if index not in st.session_state.temp_data:
                st.session_state.temp_data[index] = {
                    "new_name": row["PRODUCTO"],
                    "new_price": float(row.get("PRECIO VENTA", 0)),
                    "new_brand": row.get("MARCA", ""),
                    "new_costo": float(row.get("COSTO", 0)),
                    "selected_stock": "SÍ" if str(row.get("STOCK", "")).strip() == "-" else "NO"
                }
            temp_data[index] = st.session_state.temp_data[index]

        # Creamos un diccionario para detectar qué botón de "Editar Mix" fue presionado
        button_mix_pressed = {}

        with st.form(key=f"form_{selected_category}"):
            for index, row in df_cat.iterrows():
                st.markdown(f"**Producto:** {row['PRODUCTO']} (Index={index})")
                col1, col2, col3, col4, col5, col6 = st.columns([2,1,1,1,1,1])

                # Recuperamos los valores iniciales (ya cargados en temp_data)
                initial = temp_data[index]

                with col1:
                    new_name = st.text_input(
                        "Nombre", 
                        value=initial["new_name"], 
                        key=f"name_{index}"
                    )
                with col2:
                    new_price = st.number_input(
                        "Precio", 
                        value=initial["new_price"], 
                        step=100.0, 
                        key=f"precio_{index}"
                    )
                with col3:
                    new_brand = st.text_input(
                        "Marca", 
                        value=initial["new_brand"], 
                        key=f"marca_{index}"
                    )
                with col4:
                    new_costo = st.number_input(
                        "Costo", 
                        value=initial["new_costo"], 
                        step=1.0, 
                        key=f"costo_{index}"
                    )
                with col5:
                    stock_options = ["SÍ", "NO"]
                    if initial["selected_stock"] == "SÍ":
                        default_index = 0
                    else:
                        default_index = 1
                    selected_stock = st.selectbox(
                        "Stock", 
                        stock_options, 
                        index=default_index, 
                        key=f"stock_{index}"
                    )
                
                # Si la categoría es de MIX, creamos un form_submit_button para "Editar Mix"
                mix_categories = {
                    "MIX DE FRUTOS SECOS | FRUTAS DESECADAS| CEREALES"
                }
                with col6:
                    if selected_category.upper().strip() in mix_categories:
                        # Creamos un form_submit_button único para este producto
                        button_mix_pressed[index] = st.form_submit_button(f"Editar Mix {index}")

                # Guardamos los valores ingresados en temp_data (para persistirlos si se presiona otro botón)
                temp_data[index] = {
                    "new_name": new_name,
                    "new_price": new_price,
                    "new_brand": new_brand,
                    "new_costo": new_costo,
                    "selected_stock": selected_stock
                }

            # Botón global para guardar cambios de la categoría
            save_button = st.form_submit_button("Guardar cambios en esta categoría")

        # Ahora, fuera del form, detectamos cuál botón fue presionado
        # Actualizamos st.session_state.temp_data con los nuevos valores (para no perderlos en el rerun)
        for idx in temp_data:
            st.session_state.temp_data[idx] = temp_data[idx]

        # 1) Chequeamos si se presionó alguno de los botones "Editar Mix ..."
        mix_index_pressed = None
        for idx, pressed in button_mix_pressed.items():
            if pressed:
                mix_index_pressed = idx
                break  # Tomamos el primero que encontremos

        if mix_index_pressed is not None:
            # Se presionó "Editar Mix" para un producto en particular
            st.session_state["mix_edit_index"] = mix_index_pressed
            # NOTA: No guardamos cambios al DF. Solo iremos a configurar el mix.
        
        # 2) Chequeamos si se presionó "Guardar cambios en esta categoría"
        elif save_button:
            # Guardamos al DataFrame
            for index, row in df_cat.iterrows():
                changes = st.session_state.temp_data[index]
                st.session_state.df.at[index, "PRODUCTO"] = changes["new_name"]
                st.session_state.df.at[index, "PRECIO VENTA"] = changes["new_price"]
                st.session_state.df.at[index, "MARCA"] = changes["new_brand"]
                st.session_state.df.at[index, "COSTO"] = changes["new_costo"]
                if changes["selected_stock"] == "SÍ":
                    st.session_state.df.at[index, "STOCK"] = "-"
                else:
                    st.session_state.df.at[index, "STOCK"] = "0"
            st.success(f"Cambios guardados para la categoría {selected_category}")
            st.dataframe(st.session_state.df)

        # Si se ha solicitado editar un mix para un producto, mostrar la UI especial
        if "mix_edit_index" in st.session_state:
            index_to_edit = st.session_state["mix_edit_index"]
            self.configurar_mix(index_to_edit)

    def configurar_mix(self, index):
        st.markdown("#### Configurar Mix para el Producto")
        product_row = st.session_state.df.loc[index]
        st.write("Producto:", product_row["PRODUCTO"])
        st.write("Precio base (por kg):", product_row["PRECIO VENTA"])
        
        # Inicializamos (o reutilizamos) la lista de componentes de mix en session_state
        if "mix_components_edit" not in st.session_state:
            st.session_state.mix_components_edit = []

        st.info("Agrega los componentes que integrarán el mix (total de 1 kg).")
        col1, col2 = st.columns(2)
        with col1:
            categorias = sorted(st.session_state.df["CATEGORIA"].astype(str).str.strip().unique())
            comp_cat = st.selectbox("Categoría del componente", options=categorias, key=f"mix_comp_cat_{index}")
        with col2:
            df_comp = st.session_state.df[st.session_state.df["CATEGORIA"].astype(str).str.strip() == comp_cat]
            prod_options = df_comp["PRODUCTO"].astype(str).unique().tolist()
            comp_prod = st.selectbox("Producto del componente", options=prod_options, key=f"mix_comp_prod_{index}")
        
        comp_qty = st.number_input("Cantidad (g) para este componente", min_value=1, max_value=1000, value=250, key=f"mix_comp_qty_{index}")
        if st.button("Agregar Componente", key=f"add_mix_comp_{index}"):
            new_comp = {"Categoría": comp_cat, "Producto": comp_prod, "Cantidad (g)": comp_qty}
            st.session_state.mix_components_edit.append(new_comp)
            st.success("Componente agregado.")
        
        if st.session_state.mix_components_edit:
            st.write("Componentes agregados:")
            df_mix_comp = pd.DataFrame(st.session_state.mix_components_edit)
            st.dataframe(df_mix_comp)
            
            # Calcular el precio del mix en tiempo real
            total_subtotal = 0
            for comp in st.session_state.mix_components_edit:
                df_price = st.session_state.df[st.session_state.df["PRODUCTO"] == comp["Producto"]]
                if not df_price.empty:
                    precio_kg = float(df_price.iloc[0]["PRECIO VENTA"])
                else:
                    precio_kg = 0
                total_subtotal += precio_kg * (comp["Cantidad (g)"] / 1000)
            
            factor = st.number_input("Factor de preparación", min_value=1.0, value=1.10, step=0.01, key=f"mix_factor_{index}")
            precio_mix = total_subtotal * factor
            st.markdown(f"**Precio Calculado del Mix: ARS {precio_mix:,.2f}**")
            
            if st.button("Guardar Precio de Mix", key=f"save_mix_{index}"):
                st.session_state.df.at[index, "PRECIO VENTA"] = precio_mix
                st.success("Precio actualizado en el producto.")
                # Limpiamos la variable que indica que estamos editando este mix
                st.session_state.pop("mix_edit_index")
                st.session_state.mix_components_edit = []

if __name__ == "__main__":
    # Normalmente no se ejecuta en multipage, pero queda como ejemplo
    if "df" not in st.session_state:
        st.session_state.df = pd.DataFrame(...)  # Carga tu DataFrame de ejemplo
    editor = ProductEditor(st.session_state.df)
    editor.edit_products_by_category()
