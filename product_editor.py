# product_editor.py
import streamlit as st
import pandas as pd
from numbers import Number
from mix_manager import MixManager
import math
from utils_factors import parse_factor, is_factor_valid


class ProductEditor:
    def __init__(self, dataframe):
        # 1) Copiamos el DataFrame que llega del conector
        df0 = dataframe.copy()

        # 3) Actualizamos el session_state
        st.session_state.df = df0
        self.df = st.session_state.df

    def edit_products_by_category(self):
        st.write("### Edición de Productos por Categoría")

        # — Helper para limpiar y convertir moneda a float —
        def parse_moneda(val):
            if isinstance(val, Number):
                return float(val)
            s = str(raw_factor).strip().replace("$", "").replace(" ", "")
            if "," in s and "." in s:
                # Formato tipo '1.234,56' → '1234.56'
                s = s.replace(".", "").replace(",", ".")
            elif "," in s:
                # Formato '1,50' → '1.50'
                s = s.replace(",", ".")
            # else: si no hay coma, asumimos que '.' es separador decimal y NO lo tocamos
            try:
                factor0 = float(s)
            except:
                factor0 = 1.0

        # 1) Selección de categoría (mantengo orden de la hoja)
        categorias = (
            self.df["CATEGORIA"]
            .astype(str)
            .str.strip()
            .drop_duplicates()
            .tolist()
        )
        selected_category = st.selectbox(
            "Selecciona la categoría a editar",
            options=categorias
        )

        # 2) Filtrar productos de esa categoría
        df_cat = self.df[
            self.df["CATEGORIA"].astype(str).str.strip() == selected_category
        ]
        if df_cat.empty:
            st.info("No hay productos en esta categoría.")
            return

        # Extraigo subcategorías en orden alfabético
        subcats = sorted(
            df_cat["SUBCATEGORIA"]
            .fillna("Sin Subcategoría")
            .astype(str)
            .unique()
        )

        # 3) Inicializar temp_data UNA VEZ para todos los productos de la categoría
        st.session_state.temp_data = {}
        temp_data = {}
        for idx, row in df_cat.iterrows():
            # Parseo factor de la fila
            # Parseo factor de la fila (SIN corregir)
            raw_factor = row.get("FACTOR", None)
            factor0 = parse_factor(raw_factor)
            factor_valid = is_factor_valid(factor0) if factor0 is not None else False

            init_name  = row.get("PRODUCTO", "")
            init_costo = int(parse_moneda(row.get("COSTO", 0)))
            init_brand = row.get("MARCA", "")
            init_stock = "SÍ" if str(row.get("STOCK", "")).strip() == "-" else "NO"

            st.session_state.temp_data[idx] = {
                "new_name": init_name,
                "new_costo": init_costo,
                "factor":   factor0 if factor0 is not None else 1.00,  # valor editable en UI
                "factor_invalid": not factor_valid,                    # flag para avisar
                "new_brand": init_brand,
                "selected_stock": init_stock
            }
            temp_data[idx] = st.session_state.temp_data[idx]

        # 4) Formulario único por categoría, que recorre todas las subcategorías
        with st.form(key=f"form_{selected_category}", clear_on_submit=False):
            for sub in subcats:
                st.subheader(sub)
                df_sub = df_cat[
                    df_cat["SUBCATEGORIA"].fillna("Sin Subcategoría").astype(str) == sub
                ]
                for idx, row in df_sub.iterrows():
                    st.markdown(f"**Producto:** {row['PRODUCTO']}")
                    c1, c2, c3, c4, c5, c6 = st.columns([2,1,1,1,1,1])
                    init = temp_data[idx]

                    # Nombre editable
                    with c1:
                        new_name = st.text_input(
                            "Nombre",
                            value=init["new_name"],
                            key=f"name_{idx}"
                        )
                    # Costo (entero)
                    with c2:
                        new_costo = st.number_input(
                            "Costo",
                            value=init["new_costo"],
                            min_value=0,
                            step=1,
                            format="%d",
                            key=f"costo_{idx}"
                        )
                    # Factor (decimal)
                    # Aviso si el factor original/actual está fuera de rango
                    if init.get("factor_invalid", False):
                        st.error(f"Factor fuera de rango [1.00–2.00] en '{row['PRODUCTO']}'. Corrígelo antes de guardar.")

                    with c3:
                        factor = st.number_input(
                            "Factor",
                            value=init["factor"],
                            min_value=0.0,
                            step=0.01,
                            format="%.2f",
                            key=f"factor_{idx}"
                        )
                    # Precio calculado (solo lectura)
                    raw_price = new_costo * factor
                    precio_calc = int(math.floor(raw_price/10 + 0.5) * 10)
                    with c4:
                        st.number_input(
                            "Precio",
                            value=precio_calc,
                            min_value=0,
                            step=1,
                            format="%d",
                            disabled=True,
                            key=f"precio_calc_{idx}"
                        )
                    # Marca editable
                    with c5:
                        new_brand = st.text_input(
                            "Marca",
                            value=init["new_brand"],
                            key=f"marca_{idx}"
                        )
                    # Stock
                    with c6:
                        stock_opts = ["SÍ", "NO"]
                        default_i = 0 if init["selected_stock"] == "SÍ" else 1
                        selected_stock = st.selectbox(
                            "Stock",
                            options=stock_opts,
                            index=default_i,
                            key=f"stock_{idx}"
                        )

                    # Actualizo temp_data local
                    temp_data[idx] = {
                        "new_name": new_name,
                        "new_costo": new_costo,
                        "factor": factor,
                        "new_brand": new_brand,
                        "selected_stock": selected_stock
                    }

            save_button = st.form_submit_button("Guardar cambios en esta categoría")
        # Revalidar todos los factores editados antes de guardar
        invalid_items = []
        for _idx, ch in temp_data.items():
            f = parse_factor(ch["factor"])
            if f is None or not is_factor_valid(f):
                prod_name = ch.get("new_name", f"Idx:{_idx}")
                invalid_items.append(f"- {prod_name}: {ch['factor']}")

        if save_button:
            if invalid_items:
                st.error("No se puede guardar. Hay factores fuera de rango [1.00–2.00]:\n" + "\n".join(invalid_items))
                st.stop()  # bloquea guardado

        # 5) Sincronizar session_state con los cambios
        st.session_state.temp_data.update(temp_data)

        # 6) Procesar guardado y recalc de mixes
        if save_button:
            for idx, ch in temp_data.items():
                st.session_state.df.at[idx, "PRODUCTO"]       = ch["new_name"]
                st.session_state.df.at[idx, "COSTO"]          = ch["new_costo"]
                st.session_state.df.at[idx, "PRECIO VENTA"]  = int(ch["new_costo"] * ch["factor"])
                st.session_state.df.at[idx, "FACTOR"]         = ch["factor"]
                st.session_state.df.at[idx, "MARCA"]          = ch["new_brand"]
                st.session_state.df.at[idx, "STOCK"]          = "-" if ch["selected_stock"] == "SÍ" else "0"

            # Reflejo cambios en el DataFrame de la página
            self.df = st.session_state.df

            # Limpio estado de temp_data y widgets para el rerun
            del st.session_state["temp_data"]
            for key in list(st.session_state.keys()):
                if key.startswith(("name_", "costo_", "factor_", "marca_", "stock_")):
                    del st.session_state[key]

            # Recalcular mixes y mostrar confirmación
            mix_manager = MixManager(self.df)
            mix_manager.recalc_all_mixes()

            st.success(f"Cambios guardados para '{selected_category}'.")
            st.dataframe(self.df)

            from fudo_manager import build_export_df_from_dfs
            df_export = build_export_df_from_dfs(
                st.session_state.df,
                st.session_state.df_fudo 
            )

            st.session_state.df_fudo = df_export.copy()

            # Forzar rerun para recargar valores actualizados
            return
