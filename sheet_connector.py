import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import pandas as pd

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
        # Lee el bloque JSON de credenciales desde st.secrets
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
        return df
