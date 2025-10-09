# mix_manager.py

import streamlit as st
import pandas as pd
import sku_generator  # ⬅️ importa el módulo (no solo la función)
from utils_factors import parse_factor, is_factor_valid


class MixManager:
    def __init__(self, df: pd.DataFrame, default_factor: float = 1.6):
        self.df = df
        self.default_factor = default_factor
        sku_generator.init_existing_skus(self.df)
        self.recalc_all_mixes()

    def list_all_categories(self) -> list:
        """Retorna todas las categorías del catálogo, existan o no mixes en ellas."""
        cats = (
            self.df['CATEGORIA']
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )
        return sorted(cats, key=lambda x: x.lower())


    def recalc_all_mixes(self):
        """
        Recalcula el COSTO y PRECIO VENTA de todos los mixes existentes.
        La columna MIX contiene 'SI|ProdA:gr,ProdB:gr,...'.
        """
        mask = self.df['MIX'].astype(str).str.upper().str.startswith('SI')
        for idx, row in self.df[mask].iterrows():
            parts = str(row['MIX']).split('|', 1)
            if len(parts) != 2:
                continue
            comp_str = parts[1]
            total_cost = 0.0
            for item in comp_str.split(','):
                try:
                    prod, grams = item.split(':')
                    grams = float(grams)
                except ValueError:
                    continue
                uc = self.df.loc[self.df['PRODUCTO'] == prod, 'COSTO']
                if uc.empty:
                    continue
                total_cost += float(uc.iloc[0]) * (grams / 1000.0)
            raw = row.get('FACTOR', self.default_factor)
            f = parse_factor(raw)
            if f is None or not is_factor_valid(f):
                st.error(
                    f"[MIX] Factor fuera de rango [1.00–2.00] en '{row.get('PRODUCTO','(sin nombre)')}'. "
                    "Corrígelo para recalcular el precio."
                )
                # No tocamos COSTO/PRECIO VENTA si el factor es inválido
                continue

            price = round(total_cost * float(f), 2)
            self.df.at[idx, 'COSTO'] = int(round(total_cost))
            self.df.at[idx, 'PRECIO VENTA'] = price


    def list_mix_categories(self) -> list:
        """Retorna categorías que contienen mixes (columna MIX empieza con 'SI')."""
        mask = self.df['MIX'].astype(str).str.upper().str.startswith('SI')
        cats = self.df.loc[mask, 'CATEGORIA'].dropna().str.strip().unique().tolist()
        return sorted(cats, key=lambda x: x.lower())

    def list_mixes_by_category(self, category: str) -> pd.DataFrame:
        """Filtra los mixes de una categoría dada."""
        mask = (
            self.df['MIX'].astype(str).str.upper().str.startswith('SI') &
            self.df['CATEGORIA'].str.strip().str.lower().eq(category.strip().lower())
        )
        return self.df[mask]

    def parse_mix(self, mix_value: str) -> dict:
        """Parsea 'SI|Prod:gr,...' en un dict {prod: gr} de floats."""
        comps = {}
        try:
            comp_str = mix_value.split('|', 1)[1]
        except (IndexError, AttributeError):
            return comps
        for item in comp_str.split(','):
            try:
                prod, gr = item.split(':')
                comps[prod] = float(gr)
            except ValueError:
                continue
        return comps

    def manage_mixes(self):
        """Interfaz principal: elegir editar o crear mix."""
        self.recalc_all_mixes()
        st.header('MIXES')
        action = st.radio(
            '¿Qué deseas hacer?',
            ['Editar mix existente', 'Crear mix nuevo'],
            horizontal=True
        )
        if action == 'Editar mix existente':
            self._edit_mix_flow()
        else:
            self._create_mix_flow()

    def _edit_mix_flow(self):
        """Flujo para editar un mix existente."""
        cats = self.list_mix_categories()
        if not cats:
            st.info('No hay mixes existentes para editar.')
            return
        cat = st.selectbox('Selecciona categoría', cats)
        df_cat = self.list_mixes_by_category(cat)
        sel = st.selectbox('Selecciona el mix a editar', df_cat['PRODUCTO'].tolist())
        row = df_cat[df_cat['PRODUCTO'] == sel].iloc[0]
        comps = self.parse_mix(row['MIX'])

        with st.form(key='form_edit_mix'):
            base_name = st.text_input(
                'Nombre base del mix', value=sel.split('(')[0].strip()
            )
            raw_factor = row.get('FACTOR', self.default_factor)
            factor_input = st.number_input(
                'Factor de precio', min_value=0.0,
                value=float(raw_factor), step=0.1,
                key='edit_factor'
            )
            opciones = self.df.loc[
                ~self.df['MIX'].astype(str).str.upper().str.startswith('SI'),
                'PRODUCTO'
            ].dropna().tolist()
            comp_sel = st.multiselect(
                'Componentes', opciones, default=list(comps.keys()),
                key='edit_components'
            )
            st.markdown('**Ajusta cantidades en gramos (suma debe ser 1000g):**')
            pesos = {}
            for comp in comp_sel:
                default_val = comps.get(comp, 1000.0 / max(len(comp_sel), 1))
                pesos[comp] = st.number_input(
                    f'{comp} (g)', min_value=0.0,
                    value=round(default_val, 2), step=1.0,
                    key=f'edit_peso_{comp}'
                )
            preview = st.form_submit_button('Previsualizar cambios')

        if preview:
            f = parse_factor(factor_input)
            if f is None or not is_factor_valid(f):
                st.error("El factor debe estar en el rango [1.00–2.00]. Corrígelo antes de continuar.")
                return
            total_g = sum(pesos.values())
            if total_g != 1000.0:
                st.error(f'Suma de gramos debe ser 1000 g (actual: {total_g:.1f} g)')
                return
            detalles = []
            for comp, gr in pesos.items():
                unit = float(self.df.loc[
                    self.df['PRODUCTO'] == comp, 'COSTO'
                ].iloc[0])
                cost_part = unit * (gr / 1000.0)
                detalles.append({
                    'Producto': comp,
                    'Cantidad (g)': gr,
                    'Costo parte ($)': int(round(cost_part))
                })
            df_det = pd.DataFrame(detalles).set_index('Producto')
            costo_total = df_det['Costo parte ($)'].sum()
            precio = int(round(costo_total * factor_input))

            st.subheader('Resumen de edición')
            st.dataframe(df_det)
            st.write(f'Costo total mix: ${costo_total:,.2f}')
            st.write(f'Precio venta sugerido: ${precio:,.2f}')

            if st.button('Guardar cambios', key='save_edit_mix'):
                f = parse_factor(factor_input)
                if f is None or not is_factor_valid(f):
                    st.error("No se puede guardar: el factor está fuera de [1.00–2.00].")
                    return
                mix_str = 'SI|' + ','.join(f'{c}:{pesos[c]}' for c in pesos)
                idx = self.df[self.df['PRODUCTO'] == sel].index[0]
                self.df.at[idx, 'CATEGORIA'] = cat
                self.df.at[idx, 'PRODUCTO'] = f"{base_name} ({' / '.join(comp_sel)})"
                self.df.at[idx, 'MIX'] = mix_str
                self.df.at[idx, 'FACTOR'] = float(f)
                self.df.at[idx, 'COSTO'] = round(costo_total, 2)
                self.df.at[idx, 'PRECIO VENTA'] = int(round(costo_total * float(f)))
                st.success('Mix actualizado correctamente')
                st.subheader('Catálogo de productos actualizado')
                st.dataframe(self.df.reset_index(drop=True))

    def _create_mix_flow(self):
        """Crear un nuevo mix en cualquier categoría (exista o no un mix previo)."""
        import pandas as pd

        st.subheader('Crear nuevo mix compuesto')

        # Estado para persistir la preview entre reruns
        if 'mix_preview' not in st.session_state:
            st.session_state['mix_preview'] = None

        # ---- Selección/creación de categoría
        modo_cat = st.radio(
            '¿Dónde querés guardar el mix?',
            ['Usar categoría existente', 'Crear nueva categoría'],
            horizontal=True,
            key='mix_cat_mode'
        )

        if modo_cat == 'Usar categoría existente':
            todas = self.list_all_categories()
            if not todas:
                st.info('No hay categorías en el catálogo. Creá una nueva categoría para el mix.')
                nueva_categoria = st.text_input('Nombre de la nueva categoría de mix', key='input_new_mix_category')
                categoria_final = nueva_categoria.strip()
            else:
                categoria_final = st.selectbox('Categoría', todas, key='select_mix_category')
        else:
            nueva_categoria = st.text_input('Nombre de la nueva categoría de mix', key='input_new_mix_category')
            categoria_final = nueva_categoria.strip()

        # ---- Form con doble submit: Previsualizar / Guardar
        with st.form(key='form_new_mix'):
            base_name = st.text_input('Nombre base del mix (p.ej. MIX 1)', key='new_base')

            factor_input = st.number_input(
                'Factor de precio (margen)',
                min_value=0.0,
                value=float(self.default_factor),
                step=0.1,
                key='new_factor'
            )

            # Componentes: solo productos NO-mix
            opciones = (
                self.df.loc[~self.df['MIX'].astype(str).str.upper().str.startswith('SI'), 'PRODUCTO']
                .dropna()
                .tolist()
            )
            componentes = st.multiselect('Seleccioná los componentes del mix', opciones, key='new_components')

            # Cantidades por componente
            pesos = {}
            if componentes:
                default_g = 1000.0 / len(componentes)
                st.markdown('**Definí la cantidad en gramos de cada componente. La suma debe ser 1000 g.**')
                for comp in componentes:
                    pesos[comp] = st.number_input(
                        f'{comp} (g)',
                        min_value=0.0,
                        value=round(default_g, 2),
                        step=1.0,
                        key=f'newpeso_{comp}'
                    )

            c1, c2 = st.columns(2)
            pre_btn  = c1.form_submit_button('Previsualizar mix')
            save_btn = c2.form_submit_button('Guardar mix')

        # ---- Validaciones y armado de preview (si se tocó algún submit)
        if pre_btn or save_btn:
            errores = []
            if not categoria_final:
                errores.append('Definí la categoría del mix.')
            if not base_name.strip():
                errores.append('Ingresá un nombre base para el mix.')
            if not componentes:
                errores.append('Seleccioná al menos un producto componente.')
            total_g = sum(pesos.values())
            if abs(total_g - 1000.0) > 0.01:
                errores.append(f'La suma de gramos debe ser 1000 g (actual: {total_g:.2f} g).')
            f = parse_factor(factor_input)
            if f is None or not is_factor_valid(f):
                errores.append('El factor debe estar en el rango [1.00–2.00].')

            if errores:
                st.session_state['mix_preview'] = None
                for e in errores:
                    st.error(e)
            else:
                st.session_state['mix_preview'] = {
                'categoria': categoria_final,
                'base': base_name.strip(),
                'factor': float(f),            # usar f validado
                'componentes': componentes,
                'pesos': pesos
            }

        # ---- Mostrar preview (si existe)
        if st.session_state['mix_preview']:
            prev = st.session_state['mix_preview']

            # Cálculo de detalle y precios
            detalles = []
            for comp, gr in prev['pesos'].items():
                uc = float(self.df.loc[self.df['PRODUCTO'] == comp, 'COSTO'].iloc[0])
                cost_part = uc * (gr / 1000.0)
                detalles.append({
                    'Producto': comp,
                    'Cantidad (g)': gr,
                    'Costo parte ($)': round(cost_part, 2)
                })
            df_det = pd.DataFrame(detalles).set_index('Producto')
            costo_total = float(df_det['Costo parte ($)'].sum())
            precio = round(costo_total * prev['factor'], 2)
            nombre_completo = f"{prev['base']} ({' / '.join(prev['componentes'])})"

            st.subheader('Detalle del mix')
            st.dataframe(df_det, use_container_width=True)
            st.write(f'Costo total mix: ${costo_total:,.2f}')
            st.write(f'Precio venta sugerido: ${precio:,.2f}')

            # Si se tocó Guardar en este mismo run (save_btn) o en el próximo
            # (volverá a entrar con la preview viva), procedemos a guardar.
            if save_btn:
                f = parse_factor(prev['factor'])
                if f is None or not is_factor_valid(f):
                    st.error("No se puede guardar: el factor está fuera de [1.00–2.00].")
                    return
                from sku_generator import generar_sku

                categoria = prev['categoria']

                # --- 1) Subcategoría heredada si existe en el catálogo
                if (self.df['CATEGORIA'] == categoria).any() and ('SUBCATEGORIA' in self.df.columns):
                    subc_val = self.df.loc[self.df['CATEGORIA'] == categoria, 'SUBCATEGORIA'].dropna().astype(str).str.strip()
                    subc_val = subc_val.iloc[0] if not subc_val.empty else ""
                else:
                    subc_val = ""

                # --- 2) FRACCIONAMIENTO:
                # Regla: si la categoría EXISTE y tiene fraccionamiento definido en productos KG,
                # el MIX hereda ese fraccionamiento. Si no hay, y el MIX es tipo KG, usamos "1kg" como fallback
                # (para no dejarlo vacío en KG, como pediste).
                fracc_for_mix = ""
                if (self.df['CATEGORIA'] == categoria).any():
                    df_cat = self.df[self.df['CATEGORIA'] == categoria]
                    # casos con KG / UNIDAD == "KG" y fraccionamiento no vacío
                    if 'KG / UNIDAD' in df_cat.columns and 'FRACCIONAMIENTO' in df_cat.columns:
                        mask_kg = df_cat['KG / UNIDAD'].astype(str).str.upper().str.strip().eq("KG")
                        cand = (
                            df_cat.loc[mask_kg, 'FRACCIONAMIENTO']
                                .dropna()
                                .astype(str)
                                .str.strip()
                                .replace("nan", "", regex=False)
                        )
                        # Elegimos el más frecuente (moda) si hay varios
                        if not cand.empty:
                            fracc_for_mix = (
                                cand.value_counts()
                                    .idxmax()  # moda
                            )
                # Si sigue vacío y el MIX es KG, forzamos "1kg" para no dejarlo vacío
                if not fracc_for_mix:
                    fracc_for_mix = "1kg"  # fallback seguro para KG

                # --- 3) Tipo fijo KG para mixes (como venimos usando)
                tipo_mix = "KG"

                # --- 4) Generar nombre y SKU
                nombre_completo = f"{prev['base']} ({' / '.join(prev['componentes'])})"
                sku = generar_sku(
                    nombre_producto=nombre_completo,
                    categoria=categoria,
                    subcategoria=subc_val,
                    fraccionamiento=fracc_for_mix,
                    tipo=tipo_mix
                )  # usa fraccionamiento heredado / "1kg" en KG, firma correcta del generador :contentReference[oaicite:2]{index=2}

                # --- 5) Construir la fila nueva del MIX
                new_row = {
                    "SKU": sku,
                    "MIX": 'SI|' + ','.join(f"{c}:{prev['pesos'][c]}" for c in prev['componentes']),
                    "CATEGORIA": categoria,
                    "SUBCATEGORIA": subc_val,
                    "PRODUCTO": nombre_completo,
                    "KG / UNIDAD": "KG",
                    "FRACCIONAMIENTO": fracc_for_mix,  # <-- clave
                    "COSTO": round(costo_total, 2),
                    "PRECIO VENTA": round(costo_total * float(f), 2),
                    "FACTOR": float(f),
                    "STOCK": "-",
                    "MARCA": (
                        self.df.loc[self.df['CATEGORIA'] == categoria, 'MARCA'].dropna().astype(str).str.strip().iloc[0]
                        if (self.df['CATEGORIA'] == categoria).any() and ('MARCA' in self.df.columns)
                        else "GRANEL"
                    ),
                    "ACTIVO": "Si"
                }

                # Completar columnas faltantes para no romper formato
                for col in self.df.columns:
                    if col not in new_row:
                        new_row[col] = ""

                # Insertar junto al bloque de la categoría si existe
                inds = self.df.index[self.df['CATEGORIA'] == categoria].tolist()
                if inds:
                    insert_at = max(inds) + 1
                    top = self.df.iloc[:insert_at]
                    bottom = self.df.iloc[insert_at:]
                    self.df = pd.concat([top, pd.DataFrame([new_row]), bottom], ignore_index=True)
                else:
                    self.df.loc[len(self.df)] = new_row

                st.session_state['df'] = self.df
                st.success(f"Mix agregado en **{categoria}** con SKU **{sku}** (fraccionamiento: **{fracc_for_mix}**).")
                st.subheader('Catálogo actualizado')
                st.dataframe(self.df.reset_index(drop=True), use_container_width=True)

                # Limpiar preview para el próximo alta
                st.session_state['mix_preview'] = None
