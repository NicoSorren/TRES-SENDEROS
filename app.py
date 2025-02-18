
import streamlit as st
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

st.title("Conexión a Google Sheets con Streamlit Secrets")


scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]

# Leemos el bloque JSON desde st.secrets
raw_json = st.secrets["gcp_service_account"]["json"]
service_account_info = json.loads(raw_json)

# Creamos las credenciales
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# A partir de aquí, ya puedes usar 'client' para abrir tu spreadsheet


# URL de tu Spreadsheet (reemplaza con la URL real)
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit?gid=0#gid=0"
spreadsheet = client.open_by_url(spreadsheet_url)

# Selecciona la primera hoja o una específica
sheet = spreadsheet.sheet1

# Obtén los registros de la hoja
records = sheet.get_all_records()

# Convierte los datos a un DataFrame y muéstralo
df = pd.DataFrame(records)
st.write("Datos del Spreadsheet:")
st.dataframe(df)
