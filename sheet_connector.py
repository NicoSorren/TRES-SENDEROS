import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import pandas as pd
import concurrent.futures

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

    def delete_category_rows(self, category_name):
        """
        Elimina del spreadsheet todas las filas cuyo valor en la columna "CATEGORIA"
        coincida (ignorando mayúsculas y espacios) con category_name.
        """
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        sheet = spreadsheet.sheet1

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

    def append_invoice_record(self, record: dict, sheet_name="Remitos"):
        """Append an invoice/remito record to the specified worksheet.

        If the worksheet does not exist, it will be created and the keys of
        ``record`` will be written as the header in the first row.
        """
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)

        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=sheet_name, rows="1", cols=str(len(record))
            )
            worksheet.append_row(list(record.keys()))

        worksheet.append_row(list(record.values()))

def update_spreadsheet(spreadsheet_url, df):
    connector = SheetConnector(spreadsheet_url)
    connector.update_data(df)
