# category_manager.py
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
            # Selección de categoría de origen
            source_cat = st.selectbox(
                "Categoría de origen",
                options=self.df["CATEGORIA"].astype(str).str.strip().drop_duplicates()
            )
            df_source = self.df[self.df["CATEGORIA"].astype(str).str.strip() == source_cat]
            if df_source.empty:
                st.info("No hay productos en la categoría de origen seleccionada.")
            else:
                # Mostrar productos de la categoría de origen
                options = df_source.apply(lambda row: f"{row.name} - {row['PRODUCTO']}", axis=1).tolist()
                products_to_move = st.multiselect("Productos a mover", options=options)
                
                # Seleccionar la categoría destino
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
                if "category_order" in st.session_state:
                    st.session_state.category_order = [cat for cat in st.session_state.category_order if cat != cat_to_delete]
                st.success(f"Categoría '{cat_to_delete}' eliminada correctamente.")
                st.dataframe(st.session_state.df)
                
                # Actualizar el spreadsheet eliminando las filas correspondientes a la categoría
                SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit?gid=0#gid=0"
                from sheet_connector import SheetConnector
                connector = SheetConnector(SPREADSHEET_URL)
                connector.delete_category_rows(cat_to_delete)

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

    def configure_fractionation(self):
        st.subheader("Configurar Fraccionamiento")
        cat_options = self.df["CATEGORIA"].astype(str).str.strip().drop_duplicates().tolist()
        selected_cat = st.selectbox("Selecciona la categoría", options=cat_options)
        
        # Filtrar productos KG de la categoría
        mask = (
            (self.df["CATEGORIA"].astype(str).str.strip() == selected_cat) &
            (self.df["KG / UNIDAD"].astype(str).str.strip().str.upper() == "KG")
        )
        df_cat_kg = self.df[mask]
        
        if df_cat_kg.empty:
            st.info("No hay productos medidos en KG en la categoría seleccionada. No se aplicará fraccionamiento.")
            return

        # Opciones predefinidas de fraccionamiento
        opciones = ["100g", "250g", "500g", "1kg", "Personalizable"]

        # 1) Obtenemos los valores de "FRACCIONAMIENTO" que ya tenga esta categoría
        #    Si hay múltiples productos con distintos fraccionamientos, aquí podrías
        #    tomar el primero, o usar alguna lógica adicional.
        fracc_existente = df_cat_kg["FRACCIONAMIENTO"].dropna().unique()
        # Si hay varias filas con distinto fraccionamiento, tomamos la primera
        pre_selected = []
        if len(fracc_existente) > 0:
            # Tomamos el primer valor no-nulo
            fracc_str = fracc_existente[0]  # "100g, 250g" por ejemplo
            # Lo convertimos en lista, separando por comas
            pre_selected = [f.strip() for f in fracc_str.split(",") if f.strip()]

        # 2) Creamos el multiselect con preselección
        selected_options = st.multiselect(
            "Selecciona hasta 3 opciones de fraccionamiento",
            options=opciones,
            default=pre_selected,  # aquí usamos la lista que acabamos de armar
            max_selections=3
        )

        # 3) Si "Personalizable" estaba en pre_selected, deberíamos mostrar el campo de texto
        #    con el valor que tenía (si es que existía). Esto requiere parsear el fraccionamiento
        #    personalizable de forma distinta. Para simplicidad, asumimos que si la lista
        #    contenía algo distinto a 100g, 250g, 500g, 1kg, lo consideramos "Personalizable".
        custom_value = ""
        if "Personalizable" in selected_options:
            # Buscamos cuál era el valor "personalizable" previo
            # (Por ejemplo, si pre_selected contenía "200g")
            # Lógica sencilla: cualquier string en pre_selected que no esté en opciones fijas
            # lo consideramos personalizable.
            personalizables = [
                x for x in pre_selected 
                if x not in ["100g", "250g", "500g", "1kg", "Personalizable"]
            ]
            if personalizables:
                custom_value = personalizables[0]  # Tomamos el primero
            # Creamos el text_input con ese valor
            custom_value = st.text_input("Ingresa el valor para fraccionamiento personalizable (ej. '200g')", value=custom_value)
        else:
            # Si no se seleccionó "Personalizable", el campo no se muestra
            pass

        # 4) Botón para aplicar
        if st.button("Aplicar Fraccionamiento"):
            # Construir el string de fraccionamiento
            fracc_values = []
            for op in selected_options:
                if op == "Personalizable":
                    if custom_value.strip() != "":
                        fracc_values.append(custom_value.strip())
                else:
                    fracc_values.append(op)
            fracc_str = ", ".join(fracc_values)
            
            # Actualizar la columna FRACCIONAMIENTO
            self.df.loc[mask, "FRACCIONAMIENTO"] = fracc_str
            
            st.success(f"Fraccionamiento '{fracc_str}' aplicado a los productos medidos en KG de la categoría '{selected_cat}'.")
            st.dataframe(self.df[mask])

                
    def manage_categories(self):
        st.write("## Gestionar Categorías")
        with st.expander("Modificar Nombre de Categoría", expanded=False):
            self.modify_category()
        with st.expander("Mover Productos de una Categoría a otra", expanded=False):
            self.move_products()
        with st.expander("Eliminar Categoría", expanded=False):
            self.delete_category()
        with st.expander("Configurar Fraccionamiento", expanded=False):
            self.configure_fractionation()
