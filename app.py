import time
import streamlit as st
import pandas as pd
from sheet_connector import get_data_from_sheet  # Usamos la función cacheada
from product_editor import ProductEditor
from product_manager import ProductManager
from category_manager import CategoryManager
from category_reorder import reorder_categories

st.set_page_config(page_title="Gestión de Productos")
st.title("Gestión de Productos")

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit?gid=0#gid=0"

# Medimos el tiempo de carga de datos
start_time = time.perf_counter()
df = get_data_from_sheet(SPREADSHEET_URL)
end_time = time.perf_counter()
st.write(f"Tiempo de carga de datos: {end_time - start_time:.3f} segundos")

if "df" not in st.session_state:
    st.session_state.df = df.copy()

st.header("Datos Cargados desde Google Sheets")
st.subheader("Funcionalidades de Gestión de Productos")
tabs = st.tabs(["Editar Productos", "Agregar Producto", "Eliminar Producto", "Gestionar Categorías"])

with tabs[0]:
    st.header("Editar Productos")
    editor = ProductEditor(st.session_state.df)
    editor.edit_products_by_category()

with tabs[1]:
    st.header("Agregar Producto")
    manager = ProductManager(st.session_state.df)
    manager.add_product()

with tabs[2]:
    st.header("Eliminar Producto")
    manager = ProductManager(st.session_state.df)
    manager.delete_product()

with tabs[3]:
    st.header("Gestionar Categorías")
    cat_manager = CategoryManager()
    cat_manager.manage_categories()

if st.button("Actualizar Spreadsheet"):
    from sheet_connector import SheetConnector
    connector = SheetConnector(SPREADSHEET_URL)
    connector.update_data(st.session_state.df)
    st.success("Spreadsheet actualizado correctamente.")

if st.button("Generar CSV"):
    st.success("CSV generado (funcionalidad a implementar en siguientes pasos).")
