import streamlit as st
import pandas as pd
import datetime
from io import BytesIO
from invoice_manager import InvoiceManager  # Tu clase POO
from sheet_connector import SheetConnector
from config import SPREADSHEET_URL

def remito_integration_page():
    st.title("Generar Remito con Productos Existentes")

    if "df" not in st.session_state:
        st.error("No se encontró el DataFrame con productos. Carga los productos primero.")
        return

    # Lista de ítems del remito
    if "remito_items" not in st.session_state:
        st.session_state["remito_items"] = []

    # Para almacenar el PDF y su nombre
    if "remito_pdf" not in st.session_state:
        st.session_state["remito_pdf"] = None
    if "remito_file_name" not in st.session_state:
        st.session_state["remito_file_name"] = None

    df = st.session_state.df

    # 1) Selección de categoría y producto (fuera del form)
    st.subheader("Selecciona el producto")
    categorias = df["CATEGORIA"].astype(str).str.strip().unique().tolist()
    cat_selected = st.selectbox("Categoría", options=categorias, key="cat_selectbox")

    df_cat = df[df["CATEGORIA"].astype(str).str.strip() == cat_selected]
    if df_cat.empty:
        st.warning("No hay productos en esta categoría.")
        return

    productos_cat = df_cat["PRODUCTO"].astype(str).unique().tolist()
    prod_selected = st.selectbox("Producto", options=productos_cat, key="prod_selectbox")

    # Obtenemos los datos del producto seleccionado
    df_prod = df_cat[df_cat["PRODUCTO"].astype(str) == prod_selected].iloc[0]
    tipo = df_prod["KG / UNIDAD"]  # "KG" o "UNIDAD"
    precio_base = float(df_prod["PRECIO VENTA"])  # precio por kg o por unidad, según el producto

    # 2) Selección de fraccionamiento (también fuera del form para que sea dinámico)
    fraction_label = ""
    fraction_factor = 1.0

    if tipo.upper().strip() == "KG":
        st.write("El producto se vende por KG. Selecciona fraccionamiento:")
        fracc_options = ["100g", "250g", "500g", "1kg", "Personalizable"]
        fracc_selected = st.selectbox("Fraccionamiento", options=fracc_options, key="fracc_selectbox")

        if fracc_selected == "100g":
            fraction_label = "100g"
            fraction_factor = 0.1
        elif fracc_selected == "250g":
            fraction_label = "250g"
            fraction_factor = 0.25
        elif fracc_selected == "500g":
            fraction_label = "500g"
            fraction_factor = 0.5
        elif fracc_selected == "1kg":
            fraction_label = "1kg"
            fraction_factor = 1.0
        elif fracc_selected == "Personalizable":
            grams = st.number_input("Ingresa la cantidad de gramos", min_value=1, value=200)
            fraction_label = f"{grams}g"
            fraction_factor = grams / 1000.0

    else:
        st.write("El producto se vende por UNIDAD.")
        # En este caso, no hay fraccionamiento adicional
        fraction_label = ""  # no se usa

    # Calculamos el precio por “paquete” (fraccionamiento o unidad)
    fraction_price = precio_base * fraction_factor

    # 3) Formulario para confirmar cuántos “paquetes” o unidades agregar
    with st.form("add_item_form"):
        quantity = st.number_input("¿Cuántos paquetes de ese fraccionamiento?", min_value=1, value=1)
        add_submitted = st.form_submit_button("Añadir al remito")

        if add_submitted:
            total_line_price = fraction_price * quantity

            # Construimos el nombre a mostrar en la tabla de items
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

    # 4) Mostrar la tabla de ítems añadidos
    st.subheader("Artículos en el remito")
    if st.session_state["remito_items"]:
        df_items = pd.DataFrame(st.session_state["remito_items"])
        edited_df = st.data_editor(
            df_items,
            num_rows="dynamic",
            use_container_width=True,
            key="remito_data_editor"
        )

        if "Subtotal" in edited_df.columns:
            total_remito = edited_df["Subtotal"].sum()
        else:
            total_remito = 0

        st.write(f"**Total:** {total_remito:.2f} ARS")
        st.session_state["remito_items"] = edited_df.to_dict("records")
    else:
        st.info("Aún no hay artículos en el remito.")

    # (Resto del código para generar PDF, descargarlo, etc.)
    # 
    st.write("---")

    # 4) Formulario para generar el remito
    st.subheader("Generar PDF del remito")
    with st.form("generate_remito_form"):
        remito_number = st.text_input("Número de remito", value="REM-001")
        remito_date = st.date_input("Fecha", value=datetime.date.today())
        from_ = st.text_input("Remitente", value="Tres Senderos")
        to_ = st.text_input("Destinatario")
        address = st.text_area("Dirección del cliente")  # <-- NUEVO: dirección
        notes = st.text_area("Notas")
        terms = st.text_area("Términos", "Envío sin cargo")
        # Cambiamos a porcentaje
        discount_percent = st.number_input("Descuento global (%)", min_value=0, value=0)

        generate_submitted = st.form_submit_button("Generar Remito")
        if generate_submitted:
            date_str = remito_date.strftime("%b %d, %Y")

            # Recalcular el subtotal
            if st.session_state["remito_items"]:
                df_items = pd.DataFrame(st.session_state["remito_items"])
                subtotal = df_items["Subtotal"].sum()
            else:
                subtotal = 0

            # Calculamos el monto de descuento
            discount_amount = subtotal * discount_percent / 100
            total_final = subtotal - discount_amount

            # Para que aparezca "Descuento (10%)" en la línea de subtotales,
            # renombramos discounts_title con el porcentaje:
            discount_title_str = f"Descuento ({discount_percent}%)"

            data = {
                "from": from_,
                "to": to_,
                "ship_to": address,   # <-- NUEVO: Se mostrará como “Ship To” por defecto
                "logo": "https://i.ibb.co/Kzy83dbF/pixelcut-export.jpg",
                "number": remito_number,
                "date": date_str,
                "fields[discounts]": "true",
                "discounts": discount_amount,  
                "notes": notes,
                "terms": terms,
                "header": "",
                "currency": "ARS",
                "unit_cost_header": "Importe",
                "amount_header": "TOTAL",
                # Cambiamos discounts_title para que muestre el porcentaje
                "discounts_title": discount_title_str
            }

            # Agregar cada ítem
            for i, item in enumerate(st.session_state["remito_items"]):
                data[f"items[{i}][name]"] = item["Artículo"]
                data[f"items[{i}][quantity]"] = item["Cantidad"]
                data[f"items[{i}][unit_cost]"] = item["Precio"]

            api_key = st.secrets["invoice_api"]["key"]
            manager = InvoiceManager(api_key=api_key)
            try:
                pdf_bytes = manager.generate_invoice_pdf(data)
                st.session_state["remito_pdf"] = pdf_bytes
                st.session_state["remito_file_name"] = f"{remito_number}.pdf"
                st.success("¡Remito generado exitosamente!")

                invoice_record = {
                    "Number": remito_number,
                    "Date": remito_date.strftime("%Y-%m-%d"),
                    "Customer name": to_,
                    "Subtotal": subtotal,
                    "Discount": discount_amount,
                    "Total final": total_final,
                }
                connector = SheetConnector(SPREADSHEET_URL)
                connector.append_invoice_record(invoice_record)
            except Exception as e:
                st.error(f"Error al generar el remito: {e}")
                st.session_state["remito_pdf"] = None


    # 5) Botón de descarga (fuera del form)
    if st.session_state.get("remito_pdf") is not None:
        st.download_button(
            label="Descargar PDF",
            data=st.session_state["remito_pdf"],
            file_name=st.session_state["remito_file_name"],
            mime="application/pdf"
        )

    st.write("---")
    # Botón para reiniciar y generar un nuevo remito
    if st.button("Generar Remito Nuevo"):
        st.session_state["remito_items"] = []
        st.session_state["remito_pdf"] = None
        st.session_state["remito_file_name"] = None
        st.success("Se han reiniciado los datos. Ahora puedes generar un nuevo remito.")

if __name__ == "__main__":
    remito_integration_page()
