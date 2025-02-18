import streamlit as st
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

st.title("Edición de Productos: Precio y Marca")

# Conexión a Google Sheets (mismo código que en main.py)
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]

raw_json = st.secrets["gcp_service_account"]["json"]
service_account_info = json.loads(raw_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit?gid=0#gid=0"
spreadsheet = client.open_by_url(spreadsheet_url)
sheet = spreadsheet.sheet1
records = sheet.get_all_records()
df = pd.DataFrame(records)

# Almacenar el DataFrame en la sesión para preservar cambios
if "df" not in st.session_state:
    st.session_state.df = df.copy()
else:
    df = st.session_state.df

st.sidebar.header("Filtro de Categoría")
categorias = df["CATEGORIA"].unique()
selected_categories = st.sidebar.multiselect("Selecciona las categorías a editar", options=categorias, default=list(categorias))

st.write("### Edición de Precio y Marca por Categoría")
for cat in selected_categories:
    with st.expander(f"Categoría: {cat}"):
        # Filtra productos de la categoría seleccionada
        df_cat = df[df["CATEGORIA"] == cat]
        for index, row in df_cat.iterrows():
            st.write(f"**Producto:** {row['PRODUCTO']}")
            col1, col2 = st.columns(2)
            with col1:
                new_price = st.number_input(
                    f"Precio Venta para {row['PRODUCTO']}",
                    value=float(row["PRECIO VENTA"]),
                    step=1,
                    key=f"precio_{index}"
                )
            with col2:
                new_brand = st.text_input(
                    f"Marca para {row['PRODUCTO']}",
                    value=row["MARCA"],
                    key=f"marca_{index}"
                )
            # Actualizar los valores en el DataFrame almacenado en sesión
            st.session_state.df.at[index, "PRECIO VENTA"] = new_price
            st.session_state.df.at[index, "MARCA"] = new_brand

st.write("### Vista Actualizada de los Datos")
st.dataframe(st.session_state.df)

if st.button("Guardar Cambios"):
    st.success("Los cambios se han guardado en la aplicación. (Implementa la actualización en Google Sheets en el siguiente paso)")
