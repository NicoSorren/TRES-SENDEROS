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

        # Mostrar todas las categorías disponibles
        cat_options = self.df["CATEGORIA"].astype(str).str.strip().drop_duplicates().tolist()
        selected_cat = st.selectbox("Selecciona la categoría", options=cat_options)
        
        # Filtrar productos KG de la categoría elegida
        mask_kg = (
            (self.df["CATEGORIA"].astype(str).str.strip() == selected_cat) &
            (self.df["KG / UNIDAD"].astype(str).str.strip().str.upper() == "KG")
        )
        df_cat_kg = self.df[mask_kg]

        # Verificamos si hay productos en esa categoría con UNIDAD
        mask_unidad = (
            (self.df["CATEGORIA"].astype(str).str.strip() == selected_cat) &
            (self.df["KG / UNIDAD"].astype(str).str.strip().str.upper() == "UNIDAD")
        )
        df_cat_unidad = self.df[mask_unidad]

        # Si no hay productos en KG, no se aplica fraccionamiento
        if df_cat_kg.empty:
            st.info("No hay productos medidos en KG en la categoría seleccionada. No se aplicará fraccionamiento.")
            return

        # Si hay productos UNIDAD en la misma categoría, limitamos a 2 fraccionamientos
        if not df_cat_unidad.empty:
            max_frac = 2
            st.warning("Esta categoría contiene productos UNIDAD y KG, "
                    "por lo que solo puedes seleccionar hasta 2 fraccionamientos.")
        else:
            max_frac = 3

        # Opciones predefinidas
        opciones = ["100g", "250g", "500g", "1kg", "Personalizable"]

        # 1) Obtenemos el valor de FRACCIONAMIENTO que ya tenga esta categoría (si existe)
        fracc_existente = df_cat_kg["FRACCIONAMIENTO"].dropna().unique()
        pre_selected = []
        if len(fracc_existente) > 0:
            # Tomamos la primera no-nula
            fracc_str = fracc_existente[0]  # ejemplo: "100g, 250g"
            pre_selected = [f.strip() for f in fracc_str.split(",") if f.strip()]

        # 2) Creamos el multiselect con preselección y max_frac
        selected_options = st.multiselect(
            "Selecciona hasta 3 opciones de fraccionamiento" if max_frac == 3 else "Selecciona hasta 2 opciones de fraccionamiento",
            options=opciones,
            default=pre_selected,
            max_selections=max_frac
        )

        # 3) Manejo de "Personalizable"
        custom_value = ""
        if "Personalizable" in selected_options:
            # Buscamos valores personalizados previos
            personalizables = [
                x for x in pre_selected
                if x not in ["100g", "250g", "500g", "1kg", "Personalizable"]
            ]
            if personalizables:
                custom_value = personalizables[0]
            custom_value = st.text_input("Ingresa el valor para fraccionamiento personalizable (ej. '200g')", value=custom_value)

        # 4) Botón para aplicar
        if st.button("Aplicar Fraccionamiento"):
            fracc_values = []
            for op in selected_options:
                if op == "Personalizable":
                    if custom_value.strip() != "":
                        fracc_values.append(custom_value.strip())
                else:
                    fracc_values.append(op)
            fracc_str = ", ".join(fracc_values)
            
            # Actualizamos la columna FRACCIONAMIENTO solo en productos KG de la categoría
            self.df.loc[mask_kg, "FRACCIONAMIENTO"] = fracc_str
            
            st.success(f"Fraccionamiento '{fracc_str}' aplicado a los productos medidos en KG de la categoría '{selected_cat}'.")
            st.dataframe(self.df[mask_kg])

                
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
