import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import pandas as pd

@st.cache_data(show_spinner=False)
def get_data_from_sheet(spreadsheet_url):
    connector = SheetConnector(spreadsheet_url)
    return connector.get_data()

def parse_price(price_str):
    price_str = str(price_str).strip()
    price_str = price_str.replace('$', '')
    price_str = price_str.replace('.', '')
    try:
        return float(price_str)
    except ValueError:
        return 0.0

class SheetConnector:
    def __init__(self, spreadsheet_url):
        self.spreadsheet_url = spreadsheet_url
        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file"
        ]
        self.client = self.authenticate()

    def authenticate(self):
        raw_json = st.secrets["gcp_service_account"]["json"]
        service_account_info = json.loads(raw_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, self.scope)
        client = gspread.authorize(creds)
        return client

    def get_data(self):
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        sheet = spreadsheet.sheet1
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        df["PRECIO VENTA"] = df["PRECIO VENTA"].apply(parse_price)
        df["STOCK"] = df["STOCK"].astype(str).str.strip()
        return df

    def update_data(self, df):
        """
        Actualiza la hoja de cálculo con los datos del DataFrame.
        Se asume que la primera fila de la hoja contiene los encabezados.
        """
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        sheet = spreadsheet.sheet1
        # Limpiar el DataFrame: reemplazar NaN por cadena vacía
        df_clean = df.copy()
        df_clean = df_clean.where(pd.notnull(df_clean), "")
        # Convertir el DataFrame a lista de listas (incluyendo encabezados)
        data = [df_clean.columns.tolist()] + df_clean.values.tolist()
        # Actualizar la hoja, a partir de la celda A1
        sheet.update('A1', data)