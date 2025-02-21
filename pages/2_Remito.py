import streamlit as st
import pandas as pd

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
    cat_selected = st.selectbox("Categoría", options=categorias)

    df_cat = df[df["CATEGORIA"].astype(str).str.strip() == cat_selected]
    if df_cat.empty:
        st.warning("No hay productos en esta categoría.")
        return

    productos_cat = df_cat["PRODUCTO"].astype(str).unique().tolist()
    prod_selected = st.selectbox("Producto", options=productos_cat)

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
    # ...

if __name__ == "__main__":
    remito_integration_page()
