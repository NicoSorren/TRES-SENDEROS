import streamlit as st
import pandas as pd
from sku_generator import generar_sku
from collections import defaultdict
import re

class ProductManager:
    def __init__(self, dataframe):
        import streamlit as st
        from collections import defaultdict

        # 1) Copiamos el DataFrame que llega del conector
        df0 = dataframe.copy()

        # 2) No tocamos FACTOR: dejamos la columna tal cual venga

        # 3) Actualizamos el session_state
        st.session_state.df = df0
        self.df = st.session_state.df

        # 4) Inicializamos auxiliares
        if "used_skus" not in st.session_state:
            st.session_state["used_skus"] = defaultdict(int)
        if "cat_codes" not in st.session_state:
            st.session_state["cat_codes"] = {}

    def add_product(self):
        st.write("### Agregar Producto")

        # ←– Inicializo flag de confirmación y configuración de categorías –→
        if "confirm_add_step" not in st.session_state:
            st.session_state.confirm_add_step = False
        if "categoria_config" not in st.session_state:
            st.session_state.categoria_config = {}

        # — Inputs generales fuera del form —
        producto = st.text_input("Nombre del Producto", key="producto_input")
        costo = st.number_input(
            "Costo de KG o UNIDAD (en $)",
            min_value=0,
            format="%d",
            key="costo_input"
        )
        factor = st.number_input(
            "Factor de venta (ej. 1.5 = +50%)",
            min_value=0.0,
            value=1.50,
            step=0.1,
            format="%.2f",
            key="factor_input"
        )
        precio_sugerido = int(round(costo * factor))
        st.markdown(f"**Precio de Venta:** ${precio_sugerido:,}")
        marca = st.text_input("Marca", value="GRANEL", key="marca_input")

        stock_option = st.selectbox(
            "Stock disponible?",
            ["SI", "NO"],
            key="stock_input"
        )
        stock_str = "-" if stock_option == "SI" else "0"

        cat_option = st.radio(
            "¿Categoría existente o nueva?",
            ["Existente", "Nueva"],
            key="cat_option"
        )

        # — Si elige Nueva, capturo el nombre y el tipo de categoría ANTES del form —
        if cat_option == "Nueva":
            nueva_categoria = st.text_input(
                "Nombre de la Nueva Categoría",
                key="nueva_categoria"
            )
            tipo_categoria = st.radio(
                "La nueva categoría almacenará productos de…",
                ["KG", "UNIDAD", "AMBOS"],
                key="nueva_cat_tipo"
            )
        else:
            nueva_categoria = None
            tipo_categoria = None

        # — Formulario principal para elegir/resto de datos —
        with st.form(key="add_product_form", clear_on_submit=False):
            # 1) Categoría
            if cat_option == "Existente":
                opciones = (
                    self.df["CATEGORIA"].astype(str).str.strip().unique().tolist()
                )
                opciones.sort()
                categoria = st.selectbox(
                    "Selecciona la Categoría",
                    opciones,
                    key="categoria_existente"
                )
            else:
                # reutilizo lo que se escribió fuera
                categoria = nueva_categoria

            # 2) Tipo de Venta
            tipo = st.selectbox(
                "Tipo de Venta",
                ["KG", "UNIDAD"],
                key="tipo_venta"
            )

            # 3) No pedimos fraccionamiento aquí (siempre queda vacío)
            variante = ""

            # 4) Validación de campos obligatorios
            all_valid = (
                producto.strip() != ""
                and marca.strip() != ""
                and costo > 0
                and factor > 0
                and str(categoria).strip() != ""
                and tipo in ("KG", "UNIDAD")
            )
            submitted = st.form_submit_button(
                "Agregar Producto",
                disabled=not all_valid
            )

        # — Si enviaron el formulario, paso a confirmación —
        if submitted:
            st.session_state.confirm_add_step = True

        # — Fase 2: mostrar confirmación e insertar definitivamente —
        if st.session_state.confirm_add_step:
            precio_num    = precio_sugerido
            costo_num     = costo
            factor_num    = round(factor, 2)
            factor_str    = f"{factor_num:.2f}"
            producto_str  = producto.strip()
            categoria_str = str(categoria).strip()
            marca_str     = marca.strip()
            tipo_str      = tipo
            variante_str  = variante  # siempre ""

            st.write("#### Confirma los datos del nuevo producto:")
            st.markdown(f"- **Producto:** {producto_str}")
            st.markdown(f"- **Categoría:** {categoria_str}")
            st.markdown(f"- **Costo:** ${costo_num}")
            st.markdown(f"- **Factor:** {factor_str}")
            st.markdown(f"- **Precio Venta:** ${precio_num}")
            st.markdown(f"- **Stock:** {stock_str}")

            with st.form(key="confirm_add_form", clear_on_submit=False):
                confirm     = st.radio(
                    "¿Estás seguro de agregar este producto?",
                    ["SI", "NO"],
                    key="confirm_add"
                )
                confirm_btn = st.form_submit_button("Confirmar Producto Nuevo")

            if confirm_btn:
                if confirm == "SI":
                    df_current = self.df
                    dup = (
                        (df_current["PRODUCTO"].str.strip().str.lower() == producto_str.lower())
                        & (df_current["CATEGORIA"].str.strip().str.lower() == categoria_str.lower())
                        & (df_current["KG / UNIDAD"].astype(str).str.upper() == tipo_str.upper())
                        & (
                            df_current["FRACCIONAMIENTO"].fillna("").astype(str)
                            .str.strip().str.lower() == variante_str.lower()
                        )
                    )
                    if dup.any():
                        st.warning(
                            f"El producto '{producto_str}' en '{categoria_str}' ya existe."
                        )
                    else:
                        sku = generar_sku(
                            nombre_producto=producto_str,
                            categoria=categoria_str,
                            fraccionamiento=variante_str,
                            tipo=tipo_str,
                            used_skus=st.session_state["used_skus"],
                            cat_codes=st.session_state["cat_codes"]
                        )
                        new_product = {
                            "SKU": sku,
                            "PRODUCTO": producto_str,
                            "PRECIO VENTA": precio_num,
                            "COSTO": costo_num,
                            "FACTOR": factor_str,
                            "MARCA": marca_str,
                            "CATEGORIA": categoria_str,
                            "KG / UNIDAD": tipo_str,
                            "STOCK": stock_str,
                            "FRACCIONAMIENTO": variante_str,
                        }

                        mask_cat    = df_current["CATEGORIA"].astype(str).str.strip() == categoria_str
                        cat_indices = df_current[mask_cat].index.tolist()
                        if cat_indices:
                            existing = df_current.loc[cat_indices, "PRODUCTO"].astype(str).str.strip().tolist()
                            pos = sum(1 for n in existing if producto_str.lower() > n.lower())
                            insert_at = cat_indices[pos] if pos < len(cat_indices) else cat_indices[-1] + 1
                            before = df_current.iloc[:insert_at]
                            after  = df_current.iloc[insert_at:]
                            st.session_state.df = pd.concat(
                                [before, pd.DataFrame([new_product]), after],
                                ignore_index=True
                            )
                        else:
                            st.session_state.df = pd.concat(
                                [df_current, pd.DataFrame([new_product])],
                                ignore_index=True
                            )

                        # Refrescar y sanear
                        self.df = st.session_state.df
                        def parse_costo(val):
                            s = str(val)
                            s = re.sub(r"[^\d,\.]", "", s)
                            s = s.replace(".", "").replace(",", ".")
                            try:
                                return float(s)
                            except:
                                return 0.0
                        self.df["COSTO"]  = self.df["COSTO"].apply(parse_costo)
                        self.df["FACTOR"] = self.df["FACTOR"].astype(str)

                        # Guardar configuración de nueva categoría
                        if cat_option == "Nueva":
                            st.session_state.categoria_config[categoria_str] = tipo_categoria

                        st.success(
                            f"Producto '{producto_str}' agregado correctamente con SKU {sku}."
                        )
                        st.dataframe(self.df)
                else:
                    st.info("Agregado cancelado. Puedes modificar los campos y volver a Agregar.")

                # Botón “Agregar Otro Producto”
                if st.button("Agregar Otro Producto"):
                    st.session_state.confirm_add_step = False
                    st.experimental_rerun()


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
            st.write("Una vez que se eliminen no se podrán recuperar")
            if submitted:
                if not productos_a_eliminar:
                    st.warning("No seleccionaste ningún producto.")
                else:
                    indices = [int(op.split(" - ")[0]) for op in productos_a_eliminar]
                    st.session_state.df = st.session_state.df.drop(indices).reset_index(drop=True)
                    st.success("Productos eliminados correctamente.")
                    st.dataframe(st.session_state.df)