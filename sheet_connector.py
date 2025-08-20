import json
import time
import gspread
from gspread.exceptions import APIError
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import pandas as pd
import datetime

# ----- Utilidades de robustez -----
RETRY_STATUS = {429, 500, 502, 503, 504}

def _status_code(api_error: APIError):
    try:
        return api_error.response.status_code
    except Exception:
        return None

def _with_retry(fn, *args, **kwargs):
    """
    Ejecuta 'fn' con reintentos exponenciales si aparece APIError 429/5xx.
    """
    backoff = 0.8
    last_err = None
    for _ in range(5):  # hasta 5 intentos
        try:
            return fn(*args, **kwargs)
        except APIError as e:
            last_err = e
            code = _status_code(e)
            if code not in RETRY_STATUS:
                raise
            time.sleep(backoff)
            backoff *= 1.8
    # si agotamos reintentos, relanzamos
    raise last_err


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

    # ---------- GENERAL (sheet1: PRODUCTOS maestro) ----------
    def get_data(self):
        sheet = self.client.open_by_url(self.spreadsheet_url).sheet1
        try:
            records = _with_retry(sheet.get_all_records)
            df = pd.DataFrame(records)
        except APIError:
            values = _with_retry(sheet.get_all_values)
            df = pd.DataFrame(values[1:], columns=values[0])

        df["PRECIO VENTA"] = df["PRECIO VENTA"].apply(parse_price)
        df["FACTOR"] = pd.to_numeric(df["FACTOR"], errors="coerce").round(2)
        df["STOCK"] = df["STOCK"].astype(str).str.strip()
        return df

    def update_data(self, df):
        """
        Actualiza la hoja activa (sheet1) con los datos del DataFrame.
        """
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        sheet = spreadsheet.sheet1
        df_clean = df.copy().where(pd.notnull(df), "")
        if "FACTOR" in df_clean.columns:
            df_clean["FACTOR"] = df_clean["FACTOR"].map(lambda x: f"{x:.2f}")
        data = [df_clean.columns.tolist()] + df_clean.values.tolist()
        _with_retry(sheet.update, 'A1', data)

    # ---------- CLIENTES ----------
    def get_clients(self) -> pd.DataFrame:
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        sheet = spreadsheet.worksheet("CLIENTES")
        values = _with_retry(sheet.get_all_values)
        if not values:
            return pd.DataFrame()
        headers = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=headers)
        return df

    def add_client(self, client_data: dict):
        sheet = self.client.open_by_url(self.spreadsheet_url).worksheet("CLIENTES")
        headers = _with_retry(sheet.row_values, 1)
        if "FECHA_ALTA" not in headers:
            headers.append("FECHA_ALTA")
            _with_retry(sheet.update, "A1", [headers])
        row = []
        for h in headers:
            if h == "FECHA_ALTA":
                row.append(client_data.get(h, datetime.date.today().isoformat()))
            else:
                row.append(client_data.get(h, ""))
        _with_retry(sheet.append_row, row)

    def update_client(self, client_data: dict):
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        sheet = spreadsheet.worksheet("CLIENTES")
        cell = _with_retry(sheet.find, client_data["ID CLIENTE"])
        row_idx = cell.row
        headers = _with_retry(sheet.row_values, 1)
        row = [client_data.get(h, "") for h in headers]
        _with_retry(sheet.update, f"A{row_idx}", [row])

    def delete_client(self, client_id: str):
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        sheet = spreadsheet.worksheet("CLIENTES")
        cell = _with_retry(sheet.find, client_id)
        _with_retry(sheet.delete_rows, cell.row)

    # ---------- HISTORIAL (si lo usas) ----------
    def record_history(self, record: dict):
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        sheet = spreadsheet.worksheet('HISTORIAL')
        headers = _with_retry(sheet.row_values, 1)
        row = [record.get(h, "") for h in headers]
        _with_retry(sheet.append_row, row)

    def get_history(self) -> pd.DataFrame:
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        sheet = spreadsheet.worksheet('HISTORIAL')
        values = _with_retry(sheet.get_all_values)
        if not values or len(values) < 2:
            return pd.DataFrame()
        headers = values[0]
        data    = values[1:]
        return pd.DataFrame(data, columns=headers)

    # ---------- UTILIDAD borrado por categoría en sheet1 ----------
    def delete_category_rows(self, category_name):
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        sheet = spreadsheet.sheet1
        all_rows = _with_retry(sheet.get_all_values)
        if not all_rows:
            return
        header = all_rows[0]
        try:
            cat_index = header.index("CATEGORIA")
        except ValueError:
            st.error("No se encontró la columna 'CATEGORIA' en el spreadsheet.")
            return
        rows_to_delete = []
        for i, row in enumerate(all_rows[1:], start=2):
            if len(row) > cat_index and row[cat_index].strip().lower() == category_name.strip().lower():
                rows_to_delete.append(i)
        for row_num in sorted(rows_to_delete, reverse=True):
            _with_retry(sheet.delete_rows, row_num)

    # ---------- REMITOS ----------
    def record_remito(self, remito_data: dict):
        """
        Agrega una fila a la pestaña 'REMITOS' con encabezados:
        ['ID CLIENTE','NUMERO REMITO','FECHA','DESTINATARIO',
         'SUBTOTAL','DESCUENTO','DESCUENTO MONTO','TOTAL FACTURADO',
         'COSTO TOTAL','GANANCIA','NOTAS', 'ESTADO'(opcional)]
        """
        sheet = self.client.open_by_url(self.spreadsheet_url).worksheet("REMITOS")
        headers = _with_retry(sheet.row_values, 1)
        row = [remito_data.get(h, "") for h in headers]
        _with_retry(sheet.append_row, row)

    def get_remitos(self) -> pd.DataFrame:
        sheet = self.client.open_by_url(self.spreadsheet_url).worksheet("REMITOS")
        values = _with_retry(sheet.get_all_values)
        if not values or len(values) < 2:
            return pd.DataFrame(columns=values[0] if values else [])
        headers = values[0]
        data = values[1:]
        return pd.DataFrame(data, columns=headers)

    # ---------- DETALLE_REMITOS ----------
    def record_remito_items(self, remito_number: str, fecha: str, client_id: str, items: list[dict]):
        """
        Registra en DETALLE_REMITOS cada ítem de un remito.
        """
        sh = self.client.open_by_url(self.spreadsheet_url)
        sheet = sh.worksheet("DETALLE_REMITOS")
        _ = _with_retry(sheet.row_values, 1)  # asegura headers creados

        rows = []
        for it in items:
            rows.append([
                remito_number,
                fecha,
                client_id,
                it["Artículo"],
                it["Cantidad"],
                it["Precio"],
                it["Subtotal"]
            ])
        _with_retry(sheet.append_rows, rows)

    def get_remito_items(self) -> pd.DataFrame:
        sh = self.client.open_by_url(self.spreadsheet_url)
        sheet = sh.worksheet("DETALLE_REMITOS")
        values = _with_retry(sheet.get_all_values)
        if not values or len(values) < 2:
            return pd.DataFrame(columns=values[0] if values else [])
        headers = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=headers)
        # Convertir tipos
        df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce")
        df["CANTIDAD"] = pd.to_numeric(df["CANTIDAD"], errors="coerce")
        df["SUBTOTAL"] = pd.to_numeric(df["SUBTOTAL"], errors="coerce")
        df["PRECIO_UNITARIO"] = pd.to_numeric(df["PRECIO_UNITARIO"], errors="coerce")
        return df

    # ---------- PRODUCTOS ----------
    def get_products(self) -> pd.DataFrame:
        sh = self.client.open_by_url(self.spreadsheet_url)
        if "https://docs.google.com/spreadsheets/d/1xLmOA76L2xwnh0LUfLH813B35Md7cRXdmFCfPMKNxU8/edit" in self.spreadsheet_url:
            sheet_name = "Productos"
        else:
            sheet_name = "PRODUCTOS"
        sheet = sh.worksheet(sheet_name)
        all_vals = _with_retry(sheet.get_all_values)
        if not all_vals or len(all_vals) < 2:
            return pd.DataFrame(columns=all_vals[0] if all_vals else [])
        headers = all_vals[0]
        rows    = all_vals[1:]
        return pd.DataFrame(rows, columns=headers)


def update_spreadsheet(spreadsheet_url, df):
    connector = SheetConnector(spreadsheet_url)
    connector.update_data(df)

# Wrappers de alto nivel para clientes
def get_clients_from_sheet(spreadsheet_url) -> pd.DataFrame:
    return SheetConnector(spreadsheet_url).get_clients()

def add_client_to_sheet(spreadsheet_url, client_data: dict):
    SheetConnector(spreadsheet_url).add_client(client_data)
