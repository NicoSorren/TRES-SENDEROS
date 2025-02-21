import streamlit as st
import pandas as pd
import datetime
from io import BytesIO
from invoice_manager import InvoiceManager  # Tu clase POO

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

    # 1) Selección de categoría y producto (FUERA de un formulario)
    st.subheader("Selecciona el producto")
    categorias = df["CATEGORIA"].astype(str).str.strip().unique().tolist()
    cat_selected = st.selectbox("Categoría", options=categorias)

    # Filtrar productos según la categoría elegida
    df_cat = df[df["CATEGORIA"].astype(str).str.strip() == cat_selected]
    if df_cat.empty:
        st.warning("No hay productos en esta categoría.")
        return

    # Mostrar productos de la categoría
    productos_cat = df_cat["PRODUCTO"].astype(str).unique().tolist()
    prod_selected = st.selectbox("Producto", options=productos_cat)

    # 2) Formulario para definir cantidad / fraccionamiento y añadir ítem
    st.subheader("Define cantidad / fraccionamiento")
    with st.form("add_item_form"):
        df_prod = df_cat[df_cat["PRODUCTO"].astype(str) == prod_selected].iloc[0]
        tipo = df_prod["KG / UNIDAD"]  # "KG" o "UNIDAD"
        precio_base = df_prod["PRECIO VENTA"]

        fraction_price = precio_base
        fraction_label = ""
        total_line_price = 0
        quantity = 1

        if tipo.upper().strip() == "KG":
            st.write("El producto se vende por KG. Selecciona fraccionamiento:")
            fracc_options = ["100g", "250g", "500g", "1kg", "Personalizado"]
            fracc_selected = st.selectbox("Fraccionamiento", options=fracc_options)

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
            else:
                grams = st.number_input("Ingresa gramos", min_value=1, value=200)
                fraction_label = f"{grams}g"
                fraction_factor = grams / 1000.0

            fraction_price = precio_base * fraction_factor
            quantity = st.number_input("¿Cuántos paquetes de ese fraccionamiento?", min_value=1, value=1)
            total_line_price = fraction_price * quantity
        else:
            st.write("El producto se vende por UNIDAD.")
            quantity = st.number_input("Cantidad de unidades", min_value=1, value=1)
            total_line_price = precio_base * quantity

        add_submitted = st.form_submit_button("Añadir al remito")
        if add_submitted:
            if tipo.upper().strip() == "KG":
                item_name = f"{prod_selected} ({fraction_label})"
                unit_cost = fraction_price
            else:
                item_name = prod_selected
                unit_cost = precio_base

            st.session_state["remito_items"].append({
                "Artículo": item_name,
                "Cantidad": quantity,
                "Precio": unit_cost,
                "Subtotal": total_line_price
            })
            st.success(f"Artículo '{item_name}' agregado al remito.")

    # 3) Mostrar la tabla de ítems añadidos
    st.subheader("Artículos en el remito")

    if st.session_state["remito_items"]:
        df_items = pd.DataFrame(st.session_state["remito_items"])

        # Mostramos la tabla editable
        edited_df = st.data_editor(
            df_items,
            num_rows="dynamic",           # Permite agregar o eliminar filas
            use_container_width=True,     # Para que se ajuste al ancho
            key="remito_data_editor"
        )

        # Calcular total
        if "Subtotal" in edited_df.columns:
            total_remito = edited_df["Subtotal"].sum()
        else:
            total_remito = 0

        st.write(f"**Total:** {total_remito:.2f} ARS")

        # Almacenar los cambios en session_state
        # Convertimos edited_df a diccionarios para re-guardar en la lista "remito_items"
        st.session_state["remito_items"] = edited_df.to_dict("records")

    else:
        st.info("Aún no hay artículos en el remito.")


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

# Llamada top-level
remito_integration_page()
