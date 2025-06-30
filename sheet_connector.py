import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import pandas as pd
import datetime

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
        sheet = self.client.open_by_url(self.spreadsheet_url).sheet1
        try:
            records = sheet.get_all_records()
            df = pd.DataFrame(records)
        except Exception:
            values = sheet.get_all_values()
            df = pd.DataFrame(values[1:], columns=values[0])

        df["PRECIO VENTA"] = df["PRECIO VENTA"].apply(parse_price)

        #st.write("Tipo raw de FACTOR:", df["FACTOR"].dtype)
        #st.write("Primeros valores raw:", df["FACTOR"].head(10).tolist())
        df["FACTOR"] = pd.to_numeric(df["FACTOR"], errors="coerce").round(2)
        #st.write("🔍 Después, dtype:", df["FACTOR"].dtype)
        #st.write("🔍 Después, head:", df["FACTOR"].head(10))

        df["STOCK"] = df["STOCK"].astype(str).str.strip()
        return df

    def update_data(self, df):
        """
        Actualiza la hoja de cálculo con los datos del DataFrame.
        Se asume que la primera fila de la hoja contiene los encabezados.
        """
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        sheet = spreadsheet.sheet1
        df_clean = df.copy().where(pd.notnull(df), "")
        if "FACTOR" in df_clean.columns:
            df_clean["FACTOR"] = df_clean["FACTOR"].map(lambda x: f"{x:.2f}")
            
        data = [df_clean.columns.tolist()] + df_clean.values.tolist()
        sheet.update('A1', data)

    # ← NUEVO
    def get_clients(self) -> pd.DataFrame:
        """Lee la pestaña 'CLIENTES', incluso si solo hay header."""
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        sheet = spreadsheet.worksheet("CLIENTES")
        values = sheet.get_all_values()
        if not values:
            return pd.DataFrame()
        headers = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=headers)
        return df

    # ← NUEVO
    def add_client(self, client_data: dict):
        sheet = self.client.open_by_url(self.spreadsheet_url).worksheet("CLIENTES")
        headers = sheet.row_values(1)
        # Aseguramos FECHA_ALTA en headers
        if "FECHA_ALTA" not in headers:
            headers.append("FECHA_ALTA")
            sheet.update("A1", [headers])
        # Construimos la fila
        row = []
        for h in headers:
            if h == "FECHA_ALTA":
                row.append(client_data.get(h, datetime.date.today().isoformat()))
            else:
                row.append(client_data.get(h, ""))
        sheet.append_row(row)

    def record_history(self, record: dict):
        """
        Agrega un registro de remito en la hoja 'HISTORIAL'.
        Se asume que existe una pestaña llamada HISTORIAL con cabecera:
        ['ID CLIENTE','NÚMERO_REMITO','FECHA_REMITO','TOTAL']
        """
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        sheet       = spreadsheet.worksheet('HISTORIAL')
        headers     = sheet.row_values(1)
        row = [record.get(h, "") for h in headers]
        sheet.append_row(row)

    def get_history(self) -> pd.DataFrame:
        """
        Lee toda la hoja 'HISTORIAL' y devuelve un DataFrame.
        """
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        sheet = spreadsheet.worksheet('HISTORIAL')
        values = sheet.get_all_values()
        if not values or len(values) < 2:
            return pd.DataFrame()
        headers = values[0]
        data    = values[1:]
        return pd.DataFrame(data, columns=headers)

    def delete_category_rows(self, category_name):
        """
        Elimina del spreadsheet todas las filas cuyo valor en la columna 'CATEGORIA'
        coincida (ignorando mayúsculas y espacios) con category_name.
        """
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        sheet = spreadsheet.sheet1
        all_rows = sheet.get_all_values()
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
            sheet.delete_rows(row_num)

    def update_client(self, client_data: dict):
        """
        Actualiza un cliente existente en 'CLIENTES' buscando por ID CLIENTE.
        client_data debe incluir todas las columnas: ID CLIENTE, NOMBRE, DIRECCION, TELEFONO, EMAIL, OBSERVACIONES.
        """
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        sheet = spreadsheet.worksheet("CLIENTES")
        # Encuentro la fila donde está el ID
        cell = sheet.find(client_data["ID CLIENTE"])
        row_idx = cell.row
        headers = sheet.row_values(1)
        row = [client_data.get(h, "") for h in headers]
        # Actualizo esa fila
        sheet.update(f"A{row_idx}", [row])

    def delete_client(self, client_id: str):
        """
        Elimina la fila del cliente cuyo ID CLIENTE coincida.
        """
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        sheet = spreadsheet.worksheet("CLIENTES")
        cell = sheet.find(client_id)
        sheet.delete_rows(cell.row)

    def record_remito(self, remito_data: dict):
        """
        Agrega una fila a la pestaña 'REMITOS' con encabezados:
        ['ID CLIENTE','NUMERO REMITO','FECHA', 'DESTINATARIO',
         'SUBTOTAL','DESCUENTO','DESCUENTO MONTO','TOTAL FACTURADO',
         'COSTO TOTAL','GANANCIA','NOTAS']
        """
        sheet = self.client.open_by_url(self.spreadsheet_url).worksheet("REMITOS")
        headers = sheet.row_values(1)
        row = [ remito_data.get(h, "") for h in headers ]
        sheet.append_row(row)

    def get_remitos(self) -> pd.DataFrame:
        """
        Lee toda la pestaña 'REMITOS' y devuelve un DataFrame.
        """
        sheet = self.client.open_by_url(self.spreadsheet_url).worksheet("REMITOS")
        values = sheet.get_all_values()
        if not values or len(values) < 2:
            return pd.DataFrame(columns=values[0] if values else [])
        headers = values[0]
        data = values[1:]
        return pd.DataFrame(data, columns=headers)
    
    def record_remito_items(self, remito_number: str, fecha: str, client_id: str, items: list[dict]):
        """
        Registra en DETALLE_REMITOS cada ítem de un remito.
        items = [
          {"Artículo": "...", "Cantidad": 2, "Precio": 150.0, "Subtotal": 300.0},
          …
        ]
        """
        sh = self.client.open_by_url(self.spreadsheet_url)
        sheet = sh.worksheet("DETALLE_REMITOS")
        headers = sheet.row_values(1)

        rows = []
        for it in items:
            row = [
                remito_number,
                fecha,
                client_id,
                it["Artículo"],
                it["Cantidad"],
                it["Precio"],
                it["Subtotal"]
            ]
            rows.append(row)
        # Apendemos todas las filas de golpe:
        sheet.append_rows(rows)

    def get_remito_items(self) -> pd.DataFrame:
        """
        Lee todo DETALLE_REMITOS y lo devuelve como DataFrame.
        """
        sh = self.client.open_by_url(self.spreadsheet_url)
        sheet = sh.worksheet("DETALLE_REMITOS")
        values = sheet.get_all_values()
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
    
    def get_products(self) -> pd.DataFrame:
        """
        Lee la pestaña 'PRODUCTOS' y devuelve un DataFrame con todas sus columnas,
        incluida 'CATEGORIA'.
        """
        sh    = self.client.open_by_url(self.spreadsheet_url)
        sheet = sh.worksheet("PRODUCTOS")
        all_vals = sheet.get_all_values()
        if not all_vals or len(all_vals) < 2:
            return pd.DataFrame(columns=all_vals[0] if all_vals else [])
        headers = all_vals[0]
        rows    = all_vals[1:]
        return pd.DataFrame(rows, columns=headers)

def update_spreadsheet(spreadsheet_url, df):
    connector = SheetConnector(spreadsheet_url)
    connector.update_data(df)

# ← NUEVO: Wrappers de alto nivel para clientes
def get_clients_from_sheet(spreadsheet_url) -> pd.DataFrame:
    """
    Función auxiliar que devuelve el DataFrame de clientes.
    """
    return SheetConnector(spreadsheet_url).get_clients()

def add_client_to_sheet(spreadsheet_url, client_data: dict):
    """
    Función auxiliar que agrega un cliente dado un dict con sus datos.
    """
    SheetConnector(spreadsheet_url).add_client(client_data)

