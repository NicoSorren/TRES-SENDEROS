import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import pandas as pd
import concurrent.futures

def get_data_from_sheet(spreadsheet_url, worksheet_name=None):
    connector = SheetConnector(spreadsheet_url, worksheet_name)
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
    def __init__(self, spreadsheet_url, worksheet_name=None):
        self.spreadsheet_url = spreadsheet_url
        self.worksheet_name = worksheet_name
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

    def _get_sheet(self):
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        if self.worksheet_name:
            return spreadsheet.worksheet(self.worksheet_name)
        return spreadsheet.sheet1

    def get_data(self):
        sheet = self._get_sheet()
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        if "PRECIO VENTA" in df.columns:
            df["PRECIO VENTA"] = df["PRECIO VENTA"].apply(parse_price)
        if "STOCK" in df.columns:
            df["STOCK"] = df["STOCK"].astype(str).str.strip()
        return df

    def update_data(self, df):
        """
        Actualiza la hoja de cálculo con los datos del DataFrame.
        Se asume que la primera fila de la hoja contiene los encabezados.
        """
        sheet = self._get_sheet()
        # Limpiar el DataFrame: reemplazar NaN por cadena vacía
        df_clean = df.copy()
        df_clean = df_clean.where(pd.notnull(df_clean), "")
        # Convertir el DataFrame a lista de listas (incluyendo encabezados)
        data = [df_clean.columns.tolist()] + df_clean.values.tolist()
        # Actualizar la hoja, a partir de la celda A1
        sheet.update('A1', data)

    def delete_category_rows(self, category_name):
        """
        Elimina del spreadsheet todas las filas cuyo valor en la columna "CATEGORIA"
        coincida (ignorando mayúsculas y espacios) con category_name.
        """
        sheet = self._get_sheet()

        # Obtener todas las filas de la hoja
        all_rows = sheet.get_all_values()
        if not all_rows:
            return

        # Se asume que la primera fila es el encabezado.
        header = all_rows[0]
        try:
            cat_index = header.index("CATEGORIA")
        except ValueError:
            st.error("No se encontró la columna 'CATEGORIA' en el spreadsheet.")
            return

        # Recorrer las filas (a partir de la fila 2) y almacenar las filas que coinciden
        rows_to_delete = []
        for i, row in enumerate(all_rows[1:], start=2):  # start=2: fila 1 es el encabezado
            if len(row) > cat_index and row[cat_index].strip().lower() == category_name.strip().lower():
                rows_to_delete.append(i)

        # Ordenar en orden descendente para borrar sin afectar los índices
        rows_to_delete.sort(reverse=True)
        for row_num in rows_to_delete:
            sheet.delete_rows(row_num)

    def append_row(self, row_values):
        sheet = self._get_sheet()
        sheet.append_row(row_values, value_input_option="USER_ENTERED")

def update_spreadsheet(spreadsheet_url, df, worksheet_name=None):
    connector = SheetConnector(spreadsheet_url, worksheet_name)
    connector.update_data(df)
