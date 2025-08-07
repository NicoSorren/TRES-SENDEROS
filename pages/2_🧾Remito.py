"""
---
title: "🧾 Remito"
---
"""

import streamlit as st
import pandas as pd
import datetime
from io import BytesIO
import re

from invoice_manager import InvoiceManager
from sheet_connector import SheetConnector  # reusa tu conector existente
from validation import validate_client_data, normalize_phone


# Copiamos la misma URL que definiste en Gestionar_Productos.py
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit?gid=0#gid=0"


def remito_integration_page():
    st.title("🧾 Remito")


    # ——————————————————————————
    # 0) Estado inicial
    # ——————————————————————————
    if "df" not in st.session_state:
        st.error("No se encontró el DataFrame con productos. Carga los productos primero.")
        return

    if "remito_items" not in st.session_state:
        st.session_state["remito_items"] = []
    if "remito_pdf" not in st.session_state:
        st.session_state["remito_pdf"] = None
    if "remito_file_name" not in st.session_state:
        st.session_state["remito_file_name"] = None

    df = st.session_state.df
    connector = SheetConnector(SPREADSHEET_URL)

    tab1, tab2 = st.tabs(["Generar Remito", "Historial de Remitos"])

    with tab1:

        # ——————————————————————————
        # 1) Selección de categoría y producto (fuera de form)
        # ——————————————————————————
        st.subheader("Selecciona el producto")
        categorias   = df["CATEGORIA"].astype(str).str.strip().unique().tolist()
        cat_selected = st.selectbox("Categoría", options=categorias, key="cat_selectbox")

        df_cat = df[df["CATEGORIA"].astype(str).str.strip() == cat_selected]
        if df_cat.empty:
            st.warning("No hay productos en esta categoría.")
            return

        productos_cat = df_cat["PRODUCTO"].astype(str).unique().tolist()
        prod_selected = st.selectbox("Producto", options=productos_cat, key="prod_selectbox")

        df_prod    = df_cat[df_cat["PRODUCTO"].astype(str) == prod_selected].iloc[0]
        tipo       = df_prod["KG / UNIDAD"]
        precio_base = float(df_prod["PRECIO VENTA"])

        # ——————————————————————————
        # 2) Fraccionamiento (dinámico, fuera de form)
        # ——————————————————————————
        fraction_label  = ""
        fraction_factor = 1.0

        if tipo.upper().strip() == "KG":
            st.write("El producto se vende por KG. Selecciona fraccionamiento:")
            fracc_options  = ["100g", "250g", "500g", "1kg", "Personalizable"]
            fracc_selected = st.selectbox("Fraccionamiento", options=fracc_options, key="fracc_selectbox")
            if fracc_selected == "100g":
                fraction_label, fraction_factor = "100g", 0.1
            elif fracc_selected == "250g":
                fraction_label, fraction_factor = "250g", 0.25
            elif fracc_selected == "500g":
                fraction_label, fraction_factor = "500g", 0.5
            elif fracc_selected == "1kg":
                fraction_label, fraction_factor = "1kg", 1.0
            else:  # Personalizable
                grams = st.number_input("Ingresa la cantidad de gramos", min_value=1, value=200)
                fraction_label = f"{grams}g"
                fraction_factor = grams / 1000.0
        else:
            st.write("El producto se vende por UNIDAD.")
            fraction_label = ""

        fraction_price = precio_base * fraction_factor

        # ——————————————————————————
        # 3) Añadir ítem al remito
        # ——————————————————————————
        with st.form("add_item_form"):
            quantity       = st.number_input("¿Cuántos paquetes de ese fraccionamiento?", min_value=1, value=1)
            add_submitted  = st.form_submit_button("Añadir al remito")
            if add_submitted:
                total_line_price = fraction_price * quantity
                if tipo.upper().strip() == "KG" and fraction_label:
                    item_name = f"{prod_selected} ({fraction_label})"
                else:
                    item_name = prod_selected
                st.session_state["remito_items"].append({
                    "Artículo": item_name,
                    "Cantidad": quantity,
                    "Precio": fraction_price,
                    "Subtotal": total_line_price
                })
                st.success(f"Artículo '{item_name}' agregado al remito.")

        # ——————————————————————————
        # 4) Mostrar items en tabla
        # ——————————————————————————
        st.subheader("Artículos en el remito")
        if st.session_state["remito_items"]:
            df_items  = pd.DataFrame(st.session_state["remito_items"])
            edited_df = st.data_editor(df_items, num_rows="dynamic", use_container_width=True, key="remito_data_editor")
            total_remito = edited_df["Subtotal"].sum() if "Subtotal" in edited_df.columns else 0
            st.write(f"**Total:** {total_remito:.2f} ARS")
            st.session_state["remito_items"] = edited_df.to_dict("records")
        else:
            st.info("Aún no hay artículos en el remito.")

        df_remitos = connector.get_remitos()
        if df_remitos is None:
            df_remitos = pd.DataFrame()
        if not df_remitos.empty and "NUMERO REMITO" in df_remitos.columns:
            # Extraemos la parte numérica al final de cada remito
            nums = (
                df_remitos["NUMERO REMITO"]
                .str.extract(r"(\d+)$")[0]
                .pipe(pd.to_numeric, errors="coerce")
                .dropna()
            )
            next_num = int(nums.max()) + 1 if not nums.empty else 1
        else:
            next_num = 1
        auto_remito_id = f"REM-{next_num:03d}"  # ← AUTO-ID

        # ——————————————————————————
        # 5) Selección de cliente (ANTES del form de PDF)
        # ——————————————————————————
        st.write("---")
        st.subheader("Datos del Cliente")
        modo_cliente = st.radio("¿Cliente existente o nuevo?", ["Existente", "Nuevo"], horizontal=True)

        client_data = {"ID CLIENTE": "", "NOMBRE": "", "DIRECCION": "", "TELEFONO": "", "EMAIL": "", "OBSERVACIONES": ""}

        if modo_cliente == "Existente":
            # … aquí va tu código para cliente existente …
            df_clients = connector.get_clients()
            nombres    = df_clients["NOMBRE"].tolist()
            cliente_sel = st.selectbox("Selecciona cliente existente", nombres, key="cliente_existente")
            row = df_clients[df_clients["NOMBRE"] == cliente_sel].iloc[0]
            client_data = {
                "ID CLIENTE":    row.get("ID CLIENTE", ""),
                "NOMBRE":        row.get("NOMBRE", ""),
                "DIRECCION":     row.get("DIRECCION", ""),
                "TELEFONO":      row.get("TELEFONO", ""),
                "EMAIL":         row.get("EMAIL", ""),
                "OBSERVACIONES": row.get("OBSERVACIONES", "")
            }

        else:  # Cliente NUEVO
            df_clients = connector.get_clients()

            # Calcular el próximo ID con formato CLI-###
            if not df_clients.empty and "ID CLIENTE" in df_clients.columns:
                nums = pd.to_numeric(
                    df_clients["ID CLIENTE"]
                            .str.replace(r"^CLI-", "", regex=True),
                    errors="coerce"
                ).dropna()
                max_id = int(nums.max()) if not nums.empty else 0
                next_num = max_id + 1
            else:
                next_num = 1

            cli_id = f"CLI-{next_num:03d}"

            # Formulario para dar de alta al cliente
            with st.form("form_add_cliente"):
                st.text_input("ID Cliente", value=cli_id, disabled=True)
                nombre    = st.text_input("Nombre", key="nuevo_nombre")
                direccion = st.text_input("Dirección", key="nuevo_direccion")

                # Prefijo fijo +54 9; el usuario teclea sólo el resto
                st.markdown("**Número de teléfono**: +54 9 *", unsafe_allow_html=True)
                telefono_local = st.text_input(
                    "Sólo dígitos después de +54 9",
                    placeholder="2615112106",
                    key="nuevo_telefono",
                    help="Ejemplo: para +54 9 261 511-2106 escribe 2615112106"
                )

                email = st.text_input("Email", key="nuevo_email")
                obs   = st.text_area("Observaciones", key="nuevo_obs")

                add_cli = st.form_submit_button("Agregar Cliente")

            if add_cli:
                # 1) Verificar que puso algo en teléfono
                if not telefono_local:
                    st.error("El teléfono es obligatorio.")
                    st.stop()

                if not direccion:
                    st.error("La dirección es obligatoria")
                    st.stop()

                # 2) Normalizar y validar formato E.164
                raw_phone = f"+549{telefono_local}"
                normalized_phone = normalize_phone(raw_phone)
                if not normalized_phone:
                    st.error("Número inválido. Revisa que sean sólo dígitos y 10–11 caracteres tras +54 9.")
                    st.stop()

                # 3) Armar datos y validarlos
                client_data = {
                    "ID CLIENTE":    cli_id,
                    "NOMBRE":        nombre,
                    "DIRECCION":     direccion,
                    "TELEFONO":      normalized_phone,
                    "EMAIL":         email,
                    "OBSERVACIONES": obs
                }
                errors = validate_client_data(client_data)
                if errors:
                    for field, msg in errors.items():
                        st.error(f"{field}: {msg}")
                else:
                    connector.add_client(client_data)
                    st.success(f"Cliente {cli_id} \"{nombre}\" agregado correctamente.")
                    st.session_state["cliente_nuevo"] = client_data


            # Si ya agregaste, recuperas de session_state
            if st.session_state.get("cliente_nuevo"):
                client_data = st.session_state["cliente_nuevo"]

        # ——————————————————————————
        # 6) Formulario para generar PDF del remito
        # ——————————————————————————
        st.subheader("Generar PDF del remito")
        with st.form("generate_remito_form"):
            remito_number    = st.text_input("Número de remito", value=auto_remito_id, disabled=True)
            remito_date      = st.date_input("Fecha", value=datetime.date.today(), key="gen_date")
            from_            = st.text_input("Remitente", value="Tres Senderos", key="gen_from")
            to_              = st.text_input("Destinatario", value=client_data["NOMBRE"], key="gen_to")
            address          = st.text_area("Dirección del cliente", value=client_data["DIRECCION"], key="gen_address")
            notes            = st.text_area("Notas", key="gen_notes")
            terms            = st.text_area("Términos", value="Envío sin cargo", key="gen_terms")
            discount_percent = st.number_input("Descuento global (%)", min_value=0, value=0, key="gen_discount")

            generate_submitted = st.form_submit_button("Generar Remito")
            if generate_submitted:
                
                # C) Validaciones previas
                rem_errors = []
                items = st.session_state.get("remito_items", [])
                if not items:
                    rem_errors.append("El remito debe tener al menos un artículo.")
                if not (0 <= discount_percent <= 100):
                    rem_errors.append("El descuento global debe estar entre 0 y 100 %.")

                if rem_errors:
                    for msg in rem_errors:
                        st.error(msg)
                    st.stop()
                # Recalculamos subtotal y descuento
                items_df       = pd.DataFrame(st.session_state["remito_items"] or [])
                subtotal       = items_df["Subtotal"].sum() if not items_df.empty else 0
                discount_amount    = subtotal * discount_percent / 100
                discount_title_str = f"Descuento ({discount_percent}%)"

                # Preparamos datos para la API
                data = {
                    "from":             from_,
                    "to":               to_,
                    "ship_to":          address,
                    "logo":             "https://i.ibb.co/Kzy83dbF/pixelcut-export.jpg",
                    "number":           remito_number,
                    "date":             remito_date.strftime("%b %d, %Y"),
                    "fields[discounts]":"true",
                    "discounts":        discount_amount,
                    "notes":            notes,
                    "terms":            terms,
                    "header":           "",
                    "currency":         "ARS",
                    "unit_cost_header":"Importe",
                    "amount_header":    "TOTAL",
                    "discounts_title":  discount_title_str
                }
                for i, item in enumerate(st.session_state["remito_items"]):
                    data[f"items[{i}][name]"]     = item["Artículo"]
                    data[f"items[{i}][quantity]"] = item["Cantidad"]
                    data[f"items[{i}][unit_cost]"] = item["Precio"]

                manager = InvoiceManager(api_key=st.secrets["invoice_api"]["key"])
                try:
                    pdf_bytes = manager.generate_invoice_pdf(data)
                    st.session_state["remito_pdf"]       = pdf_bytes
                    file_name = f"{remito_number} - {client_data['NOMBRE']}.pdf"
                    st.session_state["remito_file_name"] = file_name
                    st.success("¡Remito generado exitosamente!")

                    # ——— Registro en REMITOS ———
                    conn = SheetConnector(SPREADSHEET_URL)
                    # 1) Calcular Costo Total y Ganancia
                    costo_total = 0.0
                    for item in st.session_state["remito_items"]:
                        articulo = item["Artículo"]

                        # Buscamos paréntesis de tipo "XXXg" o "XXXkg" al final
                        m = re.search(r"\((\d+(?:\.\d+)?(?:g|kg))\)\s*$", articulo, re.IGNORECASE)
                        if m:
                            # Si encaja, es una fracción: separamos nombre y cantidad
                            frac = m.group(1)                           # e.g. "250g" o "1kg"
                            prod_name = articulo[:m.start()].strip()    # todo antes del paréntesis
                            # calculamos factor según fracción
                            if frac.lower().endswith("kg"):
                                factor = float(frac[:-2])
                            else:
                                factor = float(frac[:-1]) / 1000.0
                        else:
                            # No es una fracción, dejamos el nombre completo (incluyendo paréntesis)
                            prod_name = articulo
                            factor = 1.0

                        # antes de buscar:
                        prod_norm = prod_name.strip().lower()

                        # construimos la máscara normalizando la columna PRODUCTO:
                        serie_norm = (
                            df["PRODUCTO"]
                            .astype(str)
                            .str.strip()
                            .str.lower()
                        )

                        mask = serie_norm == prod_norm
                        if not mask.any():
                            raise ValueError(f"Producto no encontrado: '{prod_name}'")

                        fila = df[mask].iloc[0]

                        cost_base = float(fila["COSTO"])
                        costo_unitario = cost_base * factor

                        # Acumular costo de la línea
                        cantidad = item["Cantidad"]
                        costo_total += costo_unitario * cantidad

                    total_facturado = subtotal - discount_amount
                    ganancia = total_facturado - costo_total

                    remito_record = {
                        "ID CLIENTE":       client_data["ID CLIENTE"],
                        "NUMERO REMITO":    remito_number,
                        "FECHA":            remito_date.isoformat(),
                        "DESTINATARIO":     to_,
                        "SUBTOTAL":         subtotal,
                        "DESCUENTO":        discount_percent,
                        "DESCUENTO MONTO":  discount_amount,
                        "TOTAL FACTURADO":  subtotal - discount_amount,
                        "COSTO TOTAL":      round(costo_total, 2),   # o cálculo si lo tienes
                        "GANANCIA":         round(ganancia, 2),  # o cálculo si lo tienes
                        "NOTAS":            notes
                    }
                    conn.record_remito(remito_record)

                    conn.record_remito_items(
                        remito_number=remito_number,
                        fecha=remito_date.isoformat(),
                        client_id=client_data["ID CLIENTE"],
                        items=st.session_state["remito_items"]
                        )
                except Exception as e:
                    st.error(f"Error al generar el remito: {e}")
                    st.session_state["remito_pdf"] = None

        # ——————————————————————————
        # 7) Botón de descarga
        # ——————————————————————————
        if st.session_state.get("remito_pdf"):
            st.download_button(
                label="Descargar PDF",
                data=st.session_state["remito_pdf"],
                file_name=st.session_state["remito_file_name"],
                mime="application/pdf"
            )

        # ——————————————————————————
        # 8) Reiniciar remito
        # ——————————————————————————
        st.write("---")
        if st.button("Generar Remito Nuevo"):
            st.session_state["remito_items"]     = []
            st.session_state["remito_pdf"]       = None
            st.session_state["remito_file_name"] = None
            st.success("Listo para un nuevo remito.")

    with tab2:
        st.subheader("Historial de Remitos")

        # Opción para elegir acción principal
        accion = st.radio(
            "¿Qué deseas hacer?",
            ["Ver remitos", "Eliminar remito"],
            horizontal=True
        )

        df_remitos = connector.get_remitos()
        df_items = connector.get_remito_items()

        if df_remitos is None or df_remitos.empty:
            st.info("Aún no hay remitos registrados.")
        else:
            df_remitos["FECHA"] = pd.to_datetime(df_remitos["FECHA"], errors="coerce")

            if accion == "Ver remitos":
                # Paso 1: Seleccionar cliente
                clientes_unicos = df_remitos["DESTINATARIO"].dropna().unique().tolist()
                clientes_unicos.sort()
                cliente_seleccionado = st.selectbox(
                    "Selecciona el cliente",
                    options=clientes_unicos
                )

                # Paso 2: Filtro por rango de fechas
                fechas_cliente = df_remitos[df_remitos["DESTINATARIO"] == cliente_seleccionado]["FECHA"]
                if fechas_cliente.empty:
                    st.info("Este cliente no tiene remitos.")
                else:
                    min_date = fechas_cliente.min().date()
                    max_date = fechas_cliente.max().date()
                    fecha_ini, fecha_fin = st.date_input(
                        "Selecciona rango de fechas",
                        [min_date, max_date],
                        min_value=min_date,
                        max_value=max_date
                    )

                    # Paso 3: Filtrar remitos por cliente y fecha
                    mask = (
                        (df_remitos["DESTINATARIO"] == cliente_seleccionado) &
                        (df_remitos["FECHA"].dt.date >= fecha_ini) &
                        (df_remitos["FECHA"].dt.date <= fecha_fin)
                    )
                    remitos_cliente = df_remitos[mask].sort_values("FECHA", ascending=False).reset_index(drop=True)

                    if remitos_cliente.empty:
                        st.info("No hay remitos para ese cliente y ese rango de fechas.")
                    else:
                        st.write(f"Mostrando {len(remitos_cliente)} remitos para **{cliente_seleccionado}** entre {fecha_ini} y {fecha_fin}:")
                        for i, row in remitos_cliente.iterrows():
                            with st.expander(f"Remito {row['NUMERO REMITO']} - {row['FECHA'].date()}"):
                                # Podés mostrar los campos principales aquí
                                st.write({
                                    "Fecha": row["FECHA"].date(),
                                    "Número": row["NUMERO REMITO"],
                                    "Subtotal": row.get("SUBTOTAL"),
                                    "Total Facturado": row.get("TOTAL FACTURADO"),
                                    "Notas": row.get("NOTAS", "")
                                })

                                if st.button(f"Descargar PDF {row['NUMERO REMITO']}", key=f"pdf_{row['NUMERO REMITO']}"):
                                    # Buscar ítems de ese remito
                                    items = df_items[df_items["NUMERO REMITO"] == row["NUMERO REMITO"]]

                                    # Preparar datos para la API de PDF
                                    data = {
                                        "from": "Tres Senderos",
                                        "to": row["DESTINATARIO"],
                                        "ship_to": row.get("DIRECCION", ""),
                                        "logo": "https://i.ibb.co/Kzy83dbF/pixelcut-export.jpg",
                                        "number": row["NUMERO REMITO"],
                                        "date": row["FECHA"].strftime("%b %d, %Y"),
                                        "fields[discounts]": "true",
                                        "discounts": row.get("DESCUENTO MONTO", 0),
                                        "notes": row.get("NOTAS", ""),
                                        "terms": "Envío sin cargo",
                                        "header": "",
                                        "currency": "ARS",
                                        "unit_cost_header": "Importe",
                                        "amount_header": "TOTAL",
                                        "discounts_title": f"Descuento ({row.get('DESCUENTO', 0)}%)"
                                    }
                                    for idx, it in items.iterrows():
                                        data[f"items[{idx}][name]"] = it["ARTICULO"]
                                        data[f"items[{idx}][quantity]"] = it["CANTIDAD"]
                                        data[f"items[{idx}][unit_cost]"] = it["PRECIO_UNITARIO"]

                                    # Generar el PDF
                                    manager = InvoiceManager(api_key=st.secrets["invoice_api"]["key"])
                                    try:
                                        pdf_bytes = manager.generate_invoice_pdf(data)
                                        st.download_button(
                                            label="Descargar PDF",
                                            data=pdf_bytes,
                                            file_name=f"{row['NUMERO REMITO']} - {row['DESTINATARIO']}.pdf",
                                            mime="application/pdf"
                                        )
                                    except Exception as e:
                                        st.error(f"Error al generar el PDF: {e}")

            elif accion == "Eliminar remito":
                # Paso 1: Seleccionar cliente
                clientes_unicos = df_remitos["DESTINATARIO"].dropna().unique().tolist()
                clientes_unicos.sort()
                cliente_seleccionado = st.selectbox(
                    "Selecciona el cliente",
                    options=clientes_unicos
                )

                # Paso 2: Mostrar remitos de ese cliente, solo activos
                remitos_cliente = df_remitos[
                    (df_remitos["DESTINATARIO"] == cliente_seleccionado) &
                    ((df_remitos.get("ESTADO", "ACTIVO") == "ACTIVO") | df_remitos.get("ESTADO").isnull())
                ].reset_index(drop=True)

                if remitos_cliente.empty:
                    st.info("Este cliente no tiene remitos activos.")
                else:
                    for i, row in remitos_cliente.iterrows():
                        with st.expander(f"Remito {row['NUMERO REMITO']} - {row['FECHA'].date()}"):
                            st.write(row)
                            if st.button(f"Eliminar remito {row['NUMERO REMITO']}", key=f"del_{row['NUMERO REMITO']}"):
                                # Anular remito
                                df_full = connector.get_remitos()
                                idx_real = df_full[df_full["NUMERO REMITO"] == row["NUMERO REMITO"]].index
                                if len(idx_real):
                                    idx_real = idx_real[0]
                                    if "ESTADO" not in df_full.columns:
                                        df_full["ESTADO"] = "ACTIVO"
                                    df_full.at[idx_real, "ESTADO"] = "ANULADO"
                                    connector.update_data(df_full)
                                    st.success("Remito anulado correctamente.")
                                    st.experimental_rerun()
                                else:
                                    st.error("No se pudo encontrar el remito en la base de datos.")


if __name__ == "__main__":
    remito_integration_page()
