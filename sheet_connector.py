# sheet_connector.py
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import pandas as pd

def parse_price(value):
        # Convertir a cadena por seguridad
        value_str = str(value).strip()
        # Eliminar símbolo $
        value_str = value_str.replace('$', '')
        # Eliminar separador de miles (.)
        value_str = value_str.replace('.', '')
        # Si tuvieras comas decimales (ej. 7,40) -> value_str = value_str.replace(',', '.')
        try:
            return float(value_str)
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

        # Convertir la columna "PRECIO VENTA" usando parse_price
        df["PRECIO VENTA"] = df["PRECIO VENTA"].apply(parse_price)

        return df
