"""
---
title: "🧾 Remito"
---
"""


import streamlit as st
import pandas as pd
import datetime
from io import BytesIO

from invoice_manager import InvoiceManager
from sheet_connector import SheetConnector  # reusa tu conector existente

# Copiamos la misma URL que definiste en Gestionar_Productos.py
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit?gid=0#gid=0"

def remito_integration_page():
    st.title("Generar Remito con Gestión de Clientes")

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
            telefono  = st.text_input("Teléfono", key="nuevo_telefono")
            email     = st.text_input("Email", key="nuevo_email")
            obs       = st.text_area("Observaciones", key="nuevo_obs")

            add_cli = st.form_submit_button("Agregar Cliente")

        if add_cli:
            client_data = {
                "ID CLIENTE":    cli_id,
                "NOMBRE":        nombre,
                "DIRECCION":     direccion,
                "TELEFONO":      telefono,
                "EMAIL":         email,
                "OBSERVACIONES": obs
            }
            connector.add_client(client_data)
            st.success(f"Cliente {cli_id} “{nombre}” agregado correctamente.")
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
            # Si es cliente nuevo, guardamos antes de generar  ← GUARDAR CLIENTE
            if modo_cliente == "Nuevo" and client_data["NOMBRE"].strip():
                connector.add_client(client_data)
                st.success(f"Cliente [{client_data['ID CLIENTE']}] '{client_data['NOMBRE']}' guardado.")

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
                    # Extraer nombre base y fracción (si la hay)
                    if "(" in articulo and articulo.endswith(")"):
                        prod_name, frac = articulo.rsplit(" (", 1)
                        frac = frac[:-1]  # quitar ) final
                        if frac.endswith("g"):
                            grams = float(frac.rstrip("g"))
                            factor = grams / 1000.0
                        else:
                            factor = 1.0
                    else:
                        prod_name = articulo
                        factor = 1.0

                    # Buscar costo de base en el catálogo
                    fila = df[df["PRODUCTO"] == prod_name].iloc[0]
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

if __name__ == "__main__":
    remito_integration_page()
