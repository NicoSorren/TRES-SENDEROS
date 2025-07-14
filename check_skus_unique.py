#!/usr/bin/env python3
"""
check_skus_unique.py

Lee tu Google Sheet "PRODUCTOS" y comprueba que ningún SKU (ni dentro de los conjuntos
separados por comas) se repita. Imprime una lista de duplicados o confirma que todo está OK.
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from collections import Counter

# Configura aquí tu URL y la ruta al JSON de servicio
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit?gid=0#gid=0" # reemplaza por la tuya
SERVICE_ACCOUNT_FILE  = "service_account.json"

def authenticate():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        SERVICE_ACCOUNT_FILE, scope
    )
    return gspread.authorize(creds)

def main():
    client = authenticate()
    sheet = client.open_by_url(SPREADSHEET_URL).worksheet("PRODUCTOS")
    records = sheet.get_all_records()

    # Extraer todos los SKUs
    all_skus = []
    for row in records:
        cell = row.get("SKU", "")
        # Cada celda puede tener varios SKUs separados por coma
        for sku in str(cell).split(","):
            sku = sku.strip()
            if sku:
                all_skus.append(sku)

    # Contar ocurrencias
    counts = Counter(all_skus)
    duplicates = {sku: cnt for sku, cnt in counts.items() if cnt > 1}

    if not duplicates:
        print("✅ Todos los SKUs son únicos.")
    else:
        print("⚠️ Se encontraron SKUs repetidos:")
        for sku, cnt in duplicates.items():
            print(f"  • {sku} → {cnt} veces")

if __name__ == "__main__":
    main()
