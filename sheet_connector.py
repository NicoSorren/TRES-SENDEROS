import json
import time
import random
import gspread
from gspread.exceptions import APIError
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import pandas as pd
import datetime

# ---------------- Robustez: backoff & helpers ----------------

RETRY_STATUS = {429, 500, 502, 503, 504}

def _status_code(api_error: APIError):
    try:
        return api_error.response.status_code
    except Exception:
        return None

def _with_retry(fn, *args, **kwargs):
    """
    Ejecuta 'fn' con reintentos exponenciales (con jitter) ante APIError 429/5xx.
    """
    backoff = 0.7
    last_err = None
    for _ in range(6):  # hasta 6 intentos ~ ~7-12s total
        try:
            return fn(*args, **kwargs)
        except APIError as e:
            last_err = e
            code = _status_code(e)
            if code not in RETRY_STATUS:
                raise
            # jitter 0-250ms para evitar thundering herd en cloud
            time.sleep(backoff + random.random() * 0.25)
            backoff *= 1.8
    raise last_err

def parse_price(price_str):
    s = str(price_str).strip().replace('$', '').replace('.', '')
    try:
        return float(s)
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
        self.client = self._authenticate()
        # Cache interno para evitar pedir metadatos del spreadsheet en cada llamada
        self._sh_cache = None
        self._sh_cache_ts = 0.0
        self._sh_cache_ttl = 30.0  # segundos

    # ---------------- Auth ----------------

    def _authenticate(self):
        raw_json = st.secrets["gcp_service_account"]["json"]
        service_account_info = json.loads(raw_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, self.scope)
        client = gspread.authorize(creds)
        return client

    # ---------------- Spreadsheet / Worksheet helpers con retry ----------------

    def _open_spreadsheet(self):
        """
        Devuelve el objeto Spreadsheet con cache y retry.
        """
        now = time.time()
        if self._sh_cache and (now - self._sh_cache_ts) < self._sh_cache_ttl:
            return self._sh_cache
        sh = _with_retry(self.client.open_by_url, self.spreadsheet_url)
        self._sh_cache = sh
        self._sh_cache_ts = now
        return sh

    def _ws(self, name: str):
        """
        Devuelve un Worksheet por nombre con retry.
        """
        sh = self._open_spreadsheet()
        return _with_retry(sh.worksheet, name)

    # ---------------- PRODUCTOS (sheet1 y hoja PRODUCTOS) ----------------

    def get_data(self):
        sh = self._open_spreadsheet()
        sheet = sh.sheet1
        try:
            records = _with_retry(sheet.get_all_records)
            df = pd.DataFrame(records)
        except APIError:
            values = _with_retry(sheet.get_all_values)
            df = pd.DataFrame(values[1:], columns=values[0]) if values else pd.DataFrame()

        if "PRECIO VENTA" in df.columns:
            df["PRECIO VENTA"] = df["PRECIO VENTA"].apply(parse_price)
        if "FACTOR" in df.columns:
            df["FACTOR"] = pd.to_numeric(df["FACTOR"], errors="coerce").round(2)
        if "STOCK" in df.columns:
            df["STOCK"] = df["STOCK"].astype(str).str.strip()
        return df

    def update_data(self, df):
        """
        Actualiza sheet1 con los datos del DataFrame (primera fila = headers).
        """
        sh = self._open_spreadsheet()
        sheet = sh.sheet1
        df_clean = df.copy().where(pd.notnull(df), "")
        if "FACTOR" in df_clean.columns:
            df_clean["FACTOR"] = df_clean["FACTOR"].map(lambda x: f"{float(x):.2f}" if str(x) != "" else "")
        data = [df_clean.columns.tolist()] + df_clean.values.tolist()
        _with_retry(sheet.update, 'A1', data)

    def get_products(self) -> pd.DataFrame:
        sh = self._open_spreadsheet()
        # Si detectás otra plantilla podés cambiar el nombre de hoja aquí
        sheet = _with_retry(sh.worksheet, "PRODUCTOS")
        values = _with_retry(sheet.get_all_values)
        if not values or len(values) < 2:
            return pd.DataFrame(columns=values[0] if values else [])
        headers, rows = values[0], values[1:]
        return pd.DataFrame(rows, columns=headers)

    # ---------------- CLIENTES ----------------

    def get_clients(self) -> pd.DataFrame:
        sheet = self._ws("CLIENTES")
        values = _with_retry(sheet.get_all_values)
        if not values:
            return pd.DataFrame()
        headers, rows = values[0], values[1:]
        return pd.DataFrame(rows, columns=headers)

    def add_client(self, client_data: dict):
        sheet = self._ws("CLIENTES")
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
        sheet = self._ws("CLIENTES")
        cell = _with_retry(sheet.find, client_data["ID CLIENTE"])
        row_idx = cell.row
        headers = _with_retry(sheet.row_values, 1)
        row = [client_data.get(h, "") for h in headers]
        _with_retry(sheet.update, f"A{row_idx}", [row])

    def delete_client(self, client_id: str):
        sheet = self._ws("CLIENTES")
        cell = _with_retry(sheet.find, client_id)
        _with_retry(sheet.delete_rows, cell.row)

    # ---------------- REMITOS ----------------

    def record_remito(self, remito_data: dict):
        """
        Inserta en 'REMITOS'. Si manejás ESTADO, incluí ese campo en headers.
        """
        sheet = self._ws("REMITOS")
        headers = _with_retry(sheet.row_values, 1)
        row = [remito_data.get(h, "") for h in headers]
        _with_retry(sheet.append_row, row)

    def get_remitos(self) -> pd.DataFrame:
        sheet = self._ws("REMITOS")
        values = _with_retry(sheet.get_all_values)
        if not values or len(values) < 2:
            return pd.DataFrame(columns=values[0] if values else [])
        headers, rows = values[0], values[1:]
        return pd.DataFrame(rows, columns=headers)

    # ---------------- DETALLE_REMITOS ----------------

    def record_remito_items(self, remito_number: str, fecha: str, client_id: str, items: list[dict]):
        """
        Inserta líneas en 'DETALLE_REMITOS'.
        """
        sheet = self._ws("DETALLE_REMITOS")
        _ = _with_retry(sheet.row_values, 1)  # asegura headers
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
        sheet = self._ws("DETALLE_REMITOS")
        values = _with_retry(sheet.get_all_values)
        if not values or len(values) < 2:
            return pd.DataFrame(columns=values[0] if values else [])
        headers, rows = values[0], values[1:]
        df = pd.DataFrame(rows, columns=headers)
        # Tipos
        if "FECHA" in df.columns:
            df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce")
        if "CANTIDAD" in df.columns:
            df["CANTIDAD"] = pd.to_numeric(df["CANTIDAD"], errors="coerce")
        if "SUBTOTAL" in df.columns:
            df["SUBTOTAL"] = pd.to_numeric(df["SUBTOTAL"], errors="coerce")
        if "PRECIO_UNITARIO" in df.columns:
            df["PRECIO_UNITARIO"] = pd.to_numeric(df["PRECIO_UNITARIO"], errors="coerce")
        return df

    # ---------------- HISTORIAL (si lo usás) ----------------

    def record_history(self, record: dict):
        sheet = self._ws("HISTORIAL")
        headers = _with_retry(sheet.row_values, 1)
        row = [record.get(h, "") for h in headers]
        _with_retry(sheet.append_row, row)

    def get_history(self) -> pd.DataFrame:
        sheet = self._ws("HISTORIAL")
        values = _with_retry(sheet.get_all_values)
        if not values or len(values) < 2:
            return pd.DataFrame()
        headers, rows = values[0], values[1:]
        return pd.DataFrame(rows, columns=headers)


# --------- Wrappers de alto nivel que ya usabas ---------

def get_data_from_sheet(spreadsheet_url):
    return SheetConnector(spreadsheet_url).get_data()

def update_spreadsheet(spreadsheet_url, df):
    SheetConnector(spreadsheet_url).update_data(df)

def get_clients_from_sheet(spreadsheet_url) -> pd.DataFrame:
    return SheetConnector(spreadsheet_url).get_clients()

def add_client_to_sheet(spreadsheet_url, client_data: dict):
    SheetConnector(spreadsheet_url).add_client(client_data)
