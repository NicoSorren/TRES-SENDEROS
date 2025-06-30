# product_editor.py
import streamlit as st
import pandas as pd
from numbers import Number
from mix_manager import MixManager

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
            s = str(val).replace("$", "").strip()
            if "," in s:
                # coma decimal: quito puntos de miles y cambio coma a punto
                s = s.replace(".", "").replace(",", ".")
            else:
                # sin coma: elimino todos los puntos (eran miles)
                s = s.replace(".", "")
            try:
                return float(s)
            except:
                return 0.0

        # 1) Selección de categoría
        categorias = sorted(self.df["CATEGORIA"].astype(str).str.strip().unique())
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

        # 3) Estado temporal de edición
        st.session_state.temp_data = {}
        temp_data = {}

        # Inicializar temp_data con los valores actuales
        # Dentro de edit_products_by_category, inicialización de temp_data
        for idx, row in df_cat.iterrows():
            # Leemos directamente el valor tal cual lo trae pandas
            raw_factor = row.get("FACTOR", 1)

            # Si es un número muy grande (>10), asumimos que vino multiplicado x100
            if isinstance(raw_factor, (int, float)):
                if raw_factor > 10:
                    factor0 = raw_factor / 100
                else:
                    factor0 = float(raw_factor)
            else:
                # tu parsing de cadena en caso venga como texto
                s = str(raw_factor).strip().replace("$", "")
                if "," in s:
                    s = s.replace(".", "").replace(",", ".")
                else:
                    s = s.replace(".", "")
                try:
                    factor0 = float(s)
                except:
                    factor0 = 0000
            
            # Guardamos en temp_data para usarlo luego en los inputs
            st.session_state.temp_data[idx] = {
                "new_name": row.get("PRODUCTO", ""),
                "new_costo": int(parse_moneda(row.get("COSTO", 0))),
                "factor": factor0,
                "new_brand": row.get("MARCA", ""),
                "selected_stock": "SÍ" if str(row.get("STOCK", "")).strip() == "-" else "NO"
            }
            temp_data[idx] = st.session_state.temp_data[idx]

        # 4) Formulario para editar la categoría
        with st.form(key=f"form_{selected_category}", clear_on_submit=False):
            for idx, row in df_cat.iterrows():
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
                with c3:
                    factor = st.number_input(
                        "Factor",
                        value=init["factor"],
                        min_value=0.0,
                        step=0.01,
                        format="%.2f",
                        key=f"factor_{idx}"
                    )
                # Precio calculado (solo lectura, entero)
                precio_calc = int(new_costo * factor)
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

        # 5) Sincronizar session_state con los cambios
        st.session_state.temp_data.update(temp_data)

        # 6) Procesar guardado
        if save_button:

            idxs = list(temp_data.keys())
    
            for idx, ch in temp_data.items():
                st.session_state.df.at[idx, "PRODUCTO"] = ch["new_name"]
                st.session_state.df.at[idx, "COSTO"] = ch["new_costo"]
                st.session_state.df.at[idx, "PRECIO VENTA"] = int(ch["new_costo"] * ch["factor"])
                st.session_state.df.at[idx, "FACTOR"]       = ch["factor"]
                st.session_state.df.at[idx, "MARCA"] = ch["new_brand"]
                st.session_state.df.at[idx, "STOCK"] = "-" if ch["selected_stock"] == "SÍ" else "0"

                    # Sincronizamos la referencia local
            self.df = st.session_state.df

            # 2) Limpiar el estado de los widgets para que al rerun tomen los nuevos valores
            if "temp_data" in st.session_state:
                del st.session_state["temp_data"]

            mix_manager = MixManager(st.session_state.df)
            mix_manager.recalc_all_mixes()

            for key in list(st.session_state.keys()):
                if (
                    key.startswith("name_")
                    or key.startswith("costo_")
                    or key.startswith("factor_")
                    or key.startswith("marca_")
                    or key.startswith("stock_")
                ):
                    del st.session_state[key]

            # 3) Mostrar confirmación y catálogo actualizado
            st.success(f"Cambios guardados para '{selected_category}'.")
            st.dataframe(self.df)

            # 4) Salir para forzar un rerun natural y recargar los inputs
            return