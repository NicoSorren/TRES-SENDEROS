import streamlit as st
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from sheet_connector import SheetConnector
from product_editor import ProductEditor

st.title("Gestión de Productos - Edición por Categoría")

# URL de tu Spreadsheet (reemplaza con la URL real)
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit?gid=0#gid=0"

# Conectar a Google Sheets y obtener datos
connector = SheetConnector(SPREADSHEET_URL)
df = connector.get_data()

st.write("### Datos Cargados desde Google Sheets")
st.dataframe(df)

# Crear instancia de ProductEditor para editar los datos
editor = ProductEditor(df)
editor.edit_products_by_category()
editor.show_data()

if st.button("Generar CSV"):
    st.success("CSV generado (funcionalidad a implementar en siguientes pasos).")
