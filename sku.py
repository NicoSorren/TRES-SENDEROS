#!/usr/bin/env python3
"""
sku.py

Script temporal: asigna SKUs únicos (incluyendo SUBCATEGORÍA) a los productos
que aún no tengan SKU en tu hoja 'PRODUCTOS'. Solo para uso único.
"""

import gspread
import pandas as pd
from collections import defaultdict
from oauth2client.service_account import ServiceAccountCredentials
from gspread import Cell

# IMPORTAMOS el módulo, no sólo la función
import sku_generator

# — CONFIGURA ESTO antes de ejecutar —
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit?gid=0#gid=0" # reemplaza por la tuya
SERVICE_ACCOUNT_FILE = "service_account.json"


def authenticate():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        SERVICE_ACCOUNT_FILE, scope
    )
    return gspread.authorize(creds)


def main():
    # 1) Leer hoja
    client = authenticate()
    sheet  = client.open_by_url(SPREADSHEET_URL).worksheet("PRODUCTOS")
    values = sheet.get_all_values()
    headers, data = values[0], values[1:]
    df = pd.DataFrame(data, columns=headers)

    # 2) Preparo mis contadores LOCALES
    used_skus    = defaultdict(int)
    cat_codes    = {}
    subcat_codes = {}

    # 3) Cuento los SKUs ya existentes
    for cell in df["SKU"].fillna("").astype(str):
        for sku in [s.strip() for s in cell.split(",") if s.strip()]:
            used_skus[sku] += 1

    # 4) Inyecto ESOS contadores a sku_generator
    sku_generator.used_skus    = used_skus
    sku_generator.cat_codes    = cat_codes
    sku_generator.subcat_codes = subcat_codes

    updates = []
    # 5) Generar nuevos SKUs donde falte
    for idx, row in df.iterrows():
        if not str(row["SKU"]).strip():
            nuevo = sku_generator.generar_sku(
                row["PRODUCTO"],
                row["CATEGORIA"],
                row.get("SUBCATEGORIA", ""),
                row.get("FRACCIONAMIENTO", ""),
                row.get("KG / UNIDAD", "")
            )
            df.at[idx, "SKU"] = nuevo
            updates.append((idx + 2, nuevo))  # +2 porque la hoja incluye header

    if not updates:
        print("No había SKUs vacíos. Nada que hacer.")
        return

    # 6) Batch update para no pasarnos de cuota
    col_idx = headers.index("SKU") + 1
    cells   = [Cell(r, col_idx, val) for r, val in updates]
    sheet.update_cells(cells, value_input_option="USER_ENTERED")

    print(f"Asigné {len(updates)} SKUs en total. ¡Listo!")


if __name__ == "__main__":
    main()
