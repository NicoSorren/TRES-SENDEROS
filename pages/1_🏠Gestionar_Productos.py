import time
import streamlit as st
import pandas as pd
from PIL import Image
from mix_manager import MixManager

from sheet_connector import update_spreadsheet
from product_editor import ProductEditor
from product_manager import ProductManager
from category_manager import CategoryManager
from descripcion import edit_descriptions
from fudo_manager import build_export_df, upload_export_df

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
FUDO_URL       = "https://docs.google.com/spreadsheets/d/1xLmOA76L2xwnh0LUfLH813B35Md7cRXdmFCfPMKNxU8/edit"

# ————— 1️⃣ Datos en sesión (cargados en PRINCIPAL.py) —————
df_master = st.session_state.df          # tu hoja maestra
df_fudo   = st.session_state.df_fudo     # el sheet Productos de Fudo

# 1.a) Inicializar/filtrar activos en el master (igual que antes)
if "ACTIVO" not in df_master.columns:
    df_master["ACTIVO"] = "Si"

df_master = df_master[
    df_master["ACTIVO"].astype(str).str.upper() == "SI"
].reset_index(drop=True)

# Refresco la instancia local
st.session_state.df = df_master


import sku_generator

sku_generator.init_existing_skus(st.session_state.df)

mix_manager = MixManager(st.session_state.df)

st.header("Datos Cargados desde Google Sheets")
st.subheader("Funcionalidades de Gestión de Productos")
tabs = st.tabs(["Editar Productos", "Agregar Producto", "Eliminar Producto", "Gestionar Categorías", "MIXES", "Descripción de Productos"])

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

with tabs[5]:
    st.header("Descripción de Productos")
    edit_descriptions()


st.write("---")
st.write("No olvidar presionar botón de debajo para confirmar TODOS los cambios")
st.write("No es necesario que sea luego de modificar, agregar o eliminar cada producto. Puede hacerse al FINAL de hacerse todos los cambios que uno quiera")
if st.button("CONFIRMAR CAMBIOS A BASE DE DATOS", key="confirm_changes"):
    with st.spinner("Sincronizando Maestro y Fudo..."):
        # a) Actualizar Google Sheet maestro
        update_spreadsheet(SPREADSHEET_URL, st.session_state.df)

        # b) Generar DataFrame de exportación y subir al Sheet de Fudo
        df_export = build_export_df(SPREADSHEET_URL, FUDO_URL)
        upload_export_df(df_export, FUDO_URL)

        # c) Refrescar preview en sesión
        st.session_state.df_fudo = df_export.copy()

    st.success("✅ Maestro y Fudo sincronizados correctamente.")
