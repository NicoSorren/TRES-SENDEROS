import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

st.title("Conexión a Google Sheets con Streamlit Secrets")

# Configura el alcance (scope) requerido
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]

# Accede a las credenciales desde st.secrets
service_account_info = st.secrets["gcp_service_account"]

# Crea las credenciales a partir del contenido JSON en secrets
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)

# Autorización con gspread
client = gspread.authorize(creds)

# URL de tu Spreadsheet (reemplaza con la URL real)
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit?usp=sharing"
spreadsheet = client.open_by_url(spreadsheet_url)

# Selecciona la primera hoja o una específica
sheet = spreadsheet.sheet1

# Obtén los registros de la hoja
records = sheet.get_all_records()

# Convierte los datos a un DataFrame y muéstralo
df = pd.DataFrame(records)
st.write("Datos del Spreadsheet:")
st.dataframe(df)
