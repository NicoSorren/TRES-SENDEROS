# sheet_connector.py
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import pandas as pd

def parse_price(price_str):
    # Asegurarte de que es string
    price_str = str(price_str).strip()
    # Eliminar símbolo de dólar
    price_str = price_str.replace('$', '')
    # Si tu hoja usa punto como separador de miles y coma como decimal:
    #  "20.200" => "20200"  y  "20,20" => "20.20"
    # Ajusta según tu caso:
    price_str = price_str.replace('.', '')  # Quita separador de miles
    # Convertir a float
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

        # Convertir la columna "PRECIO VENTA" usando parse_price
        df["PRECIO VENTA"] = df["PRECIO VENTA"].apply(parse_price)

        return df
