# mix_manager.py

import streamlit as st
import pandas as pd
from sku_generator import generar_sku


class MixManager:
    def __init__(self, df: pd.DataFrame, default_factor: float = 1.5):
        self.df = df
        self.default_factor = default_factor
        # Recalcular mixes existentes al iniciarse
        self.recalc_all_mixes()

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
            factor = row.get('FACTOR', self.default_factor) or self.default_factor
            price = round(total_cost * factor, 2)
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
                mix_str = 'SI|' + ','.join(f'{c}:{pesos[c]}' for c in pesos)
                idx = self.df[self.df['PRODUCTO'] == sel].index[0]
                self.df.at[idx, 'CATEGORIA'] = cat
                self.df.at[idx, 'PRODUCTO'] = f"{base_name} ({' / '.join(comp_sel)})"
                self.df.at[idx, 'MIX'] = mix_str
                self.df.at[idx, 'FACTOR'] = factor_input
                self.df.at[idx, 'COSTO'] = round(costo_total, 2)
                self.df.at[idx, 'PRECIO VENTA'] = precio
                st.success('Mix actualizado correctamente')
                st.subheader('Catálogo de productos actualizado')
                st.dataframe(self.df.reset_index(drop=True))

    def _create_mix_flow(self):
        """Flujo para crear un nuevo mix compuesto, con estado de preview persistente."""
        st.subheader('Crear nuevo mix compuesto')

        # 1) Selección o creación de categoría
        cats = self.list_mix_categories()
        if cats:
            categoria_opcion = st.selectbox(
                'Categoría de mix',
                ['<Crear nueva categoría>'] + cats,
                key='select_new_mix_category'
            )
        else:
            st.info('No hay categorías de mixes existentes.')
            categoria_opcion = '<Crear nueva categoría>'

        if categoria_opcion == '<Crear nueva categoría>':
            nueva_categoria = st.text_input(
                'Nombre de la nueva categoría de mix',
                key='input_new_mix_category'
            )
        else:
            nueva_categoria = categoria_opcion

        # 2) Formulario de previsualización
        with st.form(key='form_new_mix'):
            base_name = st.text_input(
                'Nombre base del mix (p.ej. MIX 1)',
                key='new_base'
            )
            factor_input = st.number_input(
                'Factor de precio (margen)',
                min_value=0.0,
                value=self.default_factor,
                step=0.1,
                key='new_factor'
            )

            opciones = (
                self.df.loc[
                    ~self.df['MIX'].astype(str).str.upper().str.startswith('SI'),
                    'PRODUCTO'
                ]
                .dropna()
                .tolist()
            )
            componentes = st.multiselect(
                'Selecciona los componentes del mix',
                opciones,
                key='new_components'
            )

            # Cantidades por componente
            pesos = {}
            if componentes:
                default_g = 1000.0 / len(componentes)
                st.markdown(
                    '**Define la cantidad en gramos de cada componente. La suma debe ser 1000 g.**'
                )
                for comp in componentes:
                    pesos[comp] = st.number_input(
                        f'{comp} (g)',
                        min_value=0.0,
                        value=round(default_g, 2),
                        step=1.0,
                        key=f'newpeso_{comp}'
                    )

            # En lugar de usar preview local, guardamos el submit en session_state
            if st.form_submit_button('Previsualizar mix'):
                st.session_state['preview_mix'] = True

        # 3) Si hubo preview o ya se guardó, seguimos mostrando detalle y botón
        if st.session_state.get('preview_mix', False):
            total_g = sum(pesos.values())
            errors = []
            if not nueva_categoria:
                errors.append('Define la categoría del mix.')
            if not base_name:
                errors.append('Ingresa un nombre base para el mix.')
            if not componentes:
                errors.append('Selecciona al menos un producto componente.')
            if total_g != 1000.0:
                errors.append(
                    f'Suma de gramos debe ser 1000 g (actual: {total_g:.1f} g)'
                )
            if errors:
                for e in errors:
                    st.error(e)
                return

            # Cálculo de detalle y precios
            detalles = []
            for comp, gr in pesos.items():
                uc = float(self.df.loc[self.df['PRODUCTO'] == comp, 'COSTO'].iloc[0])
                cost_part = uc * (gr / 1000.0)
                detalles.append({
                    'Producto': comp,
                    'Cantidad (g)': gr,
                    'Costo parte ($)': round(cost_part, 2)
                })
            df_det = pd.DataFrame(detalles).set_index('Producto')
            costo_total = df_det['Costo parte ($)'].sum()
            precio = round(costo_total * factor_input, 2)
            nombre_completo = f"{base_name} ({' / '.join(componentes)})"

            st.subheader('Detalle de mix')
            st.dataframe(df_det)
            st.write(f'Costo total mix: ${costo_total:,.2f}')
            st.write(f'Precio venta sugerido: ${precio:,.2f}')

            # 4) Botón de guardado (sólo si no se ha guardado ya)
            if not st.session_state.get('mix_guardado', False):
                if st.button('Agregar mix al catálogo', key='save_new_mix'):
                    mix_str = 'SI|' + ','.join(f"{c}:{pesos[c]}" for c in pesos)
                    sku = generar_sku(
                    nombre_producto=nombre_completo,
                    categoria=nueva_categoria,
                    fraccionamiento="",      # nuestros mixes no tienen "variante"
                    tipo="KG",               # asumimos KG; cambia si usas otro
                    used_skus=st.session_state["used_skus"],
                    cat_codes=st.session_state["cat_codes"]
                )
                    new_row = {
                        "SKU": sku, 
                        'MIX': mix_str,
                        'CATEGORIA': nueva_categoria,
                        'PRODUCTO': nombre_completo,
                        'COSTO': round(costo_total, 2),
                        'PRECIO VENTA': precio,
                        'FACTOR': factor_input
                    }

                    if nueva_categoria in self.df['CATEGORIA'].values:
                        template = self.df[self.df['CATEGORIA'] == nueva_categoria].iloc[0].to_dict()
                        # template tiene todas las columnas de esa fila
                        for col, val in template.items():
                            # añadimos solo las columnas que aún no estén en new_row
                            if col not in new_row:
                                new_row[col] = val
                            # Insertamos la nueva fila
                    if nueva_categoria in self.df['CATEGORIA'].values:
                        template = (
                            self.df[self.df['CATEGORIA'] == nueva_categoria]
                            .iloc[0]
                            .to_dict()
                        )
                        for col, val in template.items():
                            if col not in new_row:
                                new_row[col] = val
                    
                    inds = self.df.index[self.df['CATEGORIA'] == nueva_categoria].tolist()

                    if inds:
                        insert_at = max(inds) + 1
                        top = self.df.iloc[:insert_at]
                        bottom = self.df.iloc[insert_at:]
                        # Concatenamos top + nuevo mix + bottom
                        self.df = pd.concat(
                            [top, pd.DataFrame([new_row]), bottom],
                            ignore_index=True
                        )
                    else:
                        # Si no había ningún producto de esa categoría, lo agregamos al final
                        self.df.loc[len(self.df)] = new_row
                    
                    st.session_state['df'] = self.df
                    # Marcamos guardado y persistimos preview para no perder detalle
                    st.session_state['mix_guardado'] = True
                    st.session_state['preview_mix'] = True

            # 5) Mensaje de éxito y mostrar catálogo actualizado
            if st.session_state.get('mix_guardado', False):
                st.success('Mix agregado correctamente')
                st.subheader('Catálogo de productos actualizado')
                st.dataframe(self.df.reset_index(drop=True))

                # Botón para limpiar y crear otro mix
                if st.button('Agregar otro MIX', key='add_another_mix'):
                    # 1) Limpiar siempre las keys usadas  
                    for k in list(st.session_state.keys()):
                        if k.startswith('new') or k in (
                            'mix_guardado',
                            'preview_mix',
                            'select_new_mix_category',
                            'input_new_mix_category'
                        ):
                            del st.session_state[k]
                    # 2) Devolver control para que Streamlit haga rerun naturalmente  
                    return
