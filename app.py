#app.py
import streamlit as st
import pandas as pd
from sheet_connector import SheetConnector
from product_editor import ProductEditor
from product_manager import ProductManager
from category_manager import CategoryManager  # Nueva clase para gestionar categorías
from category_reorder import reorder_categories



st.set_page_config(page_title="Gestión de Productos")

st.title("Gestión de Productos")

# URL de tu Spreadsheet (reemplaza con la URL real)
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit?gid=0#gid=0"

# Conectar a Google Sheets y obtener datos
connector = SheetConnector(SPREADSHEET_URL)
df = connector.get_data()

# Almacenar el DataFrame en session_state (si aún no está)
if "df" not in st.session_state:
    st.session_state.df = df.copy()

st.header("Datos Cargados desde Google Sheets")
#st.dataframe(st.session_state.df)

st.subheader("Funcionalidades de Gestión de Productos")
tabs = st.tabs(["Editar Productos", "Agregar Producto", "Eliminar Producto", "Gestionar Categorías"])

with tabs[0]:
    st.header("Editar Productos")
    editor = ProductEditor(st.session_state.df)
    editor.edit_products_by_category()
    #editor.show_data()

with tabs[1]:
    st.header("Agregar Producto")
    manager = ProductManager(st.session_state.df)
    manager.add_product()
   # st.dataframe(st.session_state.df)

with tabs[2]:
    st.header("Eliminar Producto")
    manager = ProductManager(st.session_state.df)
    manager.delete_product()
    #st.dataframe(st.session_state.df)

with tabs[3]:
    st.header("Gestionar Categorías")
    cat_manager = CategoryManager()
    cat_manager.manage_categories()


if st.button("Actualizar Spreadsheet"):
    connector.update_data(st.session_state.df)
    st.success("Spreadsheet actualizado correctamente.")

if st.button("Generar CSV"):
    st.success("CSV generado (funcionalidad a implementar en siguientes pasos).")