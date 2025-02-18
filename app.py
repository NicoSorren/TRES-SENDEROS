import streamlit as st
from sheet_connector import SheetConnector
from product_editor import ProductEditor

st.title("Gestión de Productos - Streamlit App")

# Define la URL del Spreadsheet 
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit?gid=0#gid=0"

# Conectar a Google Sheets y obtener datos
connector = SheetConnector(SPREADSHEET_URL)
df = connector.get_data()

st.write("### Datos Cargados desde Google Sheets")
st.dataframe(df)

# Crear instancia de ProductEditor para editar los datos
editor = ProductEditor(df)
filtered_df = editor.filter_by_category()
editor.edit_products(filtered_df)
editor.show_data()

if st.button("Generar CSV"):
    # Aquí, en un siguiente paso, integraríamos la lógica de generación del CSV
    st.success("CSV generado (esta funcionalidad se implementará en pasos posteriores).")
