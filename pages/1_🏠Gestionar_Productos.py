import time
import streamlit as st
import pandas as pd
import concurrent.futures
from PIL import Image
from mix_manager import MixManager

from sheet_connector import get_data_from_sheet, update_spreadsheet
from product_editor import ProductEditor
from product_manager import ProductManager
from category_manager import CategoryManager
from mix_manager import MixManager

# Configuración general de la página
st.set_page_config(
    page_title="Tres Senderos",
    page_icon="🍃",       # un emoji de hoja, por ejemplo
    layout="wide"
)

# Carga y muestra tu logo en la sidebar
logo = Image.open("Logo_TRES_SENDEROS-.png")

# Opción A: en la sidebar
st.sidebar.image(logo, width=80)

st.title("Gestión de Productos")

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit?gid=0#gid=0"

df = get_data_from_sheet(SPREADSHEET_URL)

if "df" not in st.session_state:
    st.session_state.df = df.copy()

mix_manager = MixManager(st.session_state.df)

st.header("Datos Cargados desde Google Sheets")
st.subheader("Funcionalidades de Gestión de Productos")
tabs = st.tabs(["Editar Productos", "Agregar Producto", "Eliminar Producto", "Gestionar Categorías", "MIXES"])

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

with tabs[4]:
    mix_manager = MixManager(st.session_state.df)
    mix_manager.manage_mixes()

@st.cache_resource(show_spinner=False)
def get_executor():
    return concurrent.futures.ProcessPoolExecutor(max_workers=1)

st.write("---")
st.write("No olvidar presionar botón de debajo para confirmar TODOS los cambios")
st.write("No es necesario que sea luego de modificar, agregar o eliminar cada producto. Puede hacerse al FINAL de hacerse todos los cambios que uno quiera")
if st.button("CONFIRMAR CAMBIOS A BASE DE DATOS"):   
    with st.spinner("Actualizando la hoja de cálculo en segundo plano..."):
        executor = get_executor()
        future = executor.submit(update_spreadsheet, SPREADSHEET_URL, st.session_state.df)
        st.success("La actualización se inició en un proceso separado.")

