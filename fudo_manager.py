# fudo_manager.py
import re
import pandas as pd
import gspread
import json
from io import BytesIO
from typing import Union
from sheet_connector import get_data_from_sheet, SheetConnector
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import AuthorizedSession
import streamlit as st
from typing import List
from pandas.api.types import CategoricalDtype
import numpy as np

def strip_parenthesis(text: str) -> str:
    """
    Elimina cualquier '(...)' del texto, incluyendo espacios previos.
    Ej: 'Granola (sin azúcar)' -> 'Granola'
    """
    return re.sub(r"\s*\([^)]*\)", "", text).strip()

def explode_fracciones(df: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for _, row in df.iterrows():
        kg_unidad = str(row.get("KG / UNIDAD", "")).strip().upper()
        fracs     = str(row.get("FRACCIONAMIENTO", "")).strip()
        if kg_unidad == "KG" and fracs:
            sku_list = [s.strip() for s in str(row["SKU"]).split(",")]
            for sku_i in sku_list:
                # sku_i es el SKU completo, p.ej. "FRU-AL-ALME-100G2"
                suffix_raw = sku_i.rsplit("-", 1)[-1]  
                m = re.match(r"^(\d+)(KG|G)", suffix_raw, re.IGNORECASE)
                if not m:
                    # si no encaja, saltamos
                    continue
                num  = int(m.group(1))
                unit = m.group(2).upper()
                # factor de kg
                factor = num if unit == "KG" else num / 1000.0

                # precios y costos redondeados al 10 más cercano
                precio_i = int(round((row["PRECIO VENTA"] * factor) / 10.0) * 10)
                costo_i  = int(round((row["COSTO"]        * factor) / 10.0) * 10)

                # formateo del sufijo para el nombre: 100g o 1kg
                suffix_name = f"{num}{unit.lower()}"

                new = row.copy()
                new["SKU"]           = sku_i  # conserva el dígito diferenciador
                base_name = strip_parenthesis(row["PRODUCTO"])
                new["PRODUCTO"] = f"{base_name} {suffix_name}"
                new["PRECIO VENTA"]  = precio_i
                new["COSTO"]         = costo_i
                new["STOCK"]         = row["STOCK"]
                filas.append(new)
        else:
            filas.append(row)

    df_out = pd.DataFrame(filas).reset_index(drop=True)
    df_out["PRODUCTO"] = df_out["PRODUCTO"].apply(strip_parenthesis)
    return df_out

# Función para limpiar puntuación y paréntesis
def clean_for_sort(text: str) -> str:
    # 1) quitar (…)
    no_paren = re.sub(r"\s*\([^)]*\)", "", text)
    # 2) quitar comas y otros símbolos que no sean letras, números o espacios
    no_punct = re.sub(r"[^\w\s]", "", no_paren)
    return no_punct.strip().lower()

def build_export_df(master_url: str, fudo_url: str) -> pd.DataFrame:
    # 1) Cargo y exploto tu hoja maestra
    df_master = get_data_from_sheet(master_url)
    df_master = explode_fracciones(df_master)

    # 2) Leo el sheet actual de Fudo (IDs ya existentes)
    fudo_conn = SheetConnector(fudo_url)
    df_fudo   = fudo_conn.get_products()[["ID\n(Uso interno)", "Código"]]

    # 3) Hago merge para conservar IDs previos
    df_merge = df_master.merge(
        df_fudo,
        how="left",
        left_on="SKU",
        right_on="Código"
    ).rename(columns={"ID\n(Uso interno)": "ID_prev"})

    # 4) Construyo la columna FINAL de IDs como ints o None
    def make_id(val):
        if pd.isna(val):
            return None           # celdas vacías → None
        return int(val)           # valores existentes → enteros

    df_merge["ID\n(Uso interno)"] = df_merge["ID_prev"].apply(make_id)

    st.write("▶️ STOCK dtype:", df_merge["STOCK"].dtype)
    st.write("▶️ STOCK valores únicos:", df_merge["STOCK"].unique())
    st.write("▶️ Ejemplo filas relevantes:", 
            df_merge.loc[df_merge["SKU"].str.contains("AL-ALME"), 
                        ["SKU","STOCK","ACTIVO"]])
    
    df_merge["Activo_Fudo"] = np.where(
        (df_merge["ACTIVO"].str.upper() == "SI") &
        (df_merge["STOCK"]               != "0"),
        "Si",
        "No"
    )

    # 5) Mapeo al template de Fudo
    df_export = pd.DataFrame({
        "ID\n(Uso interno)"             : df_merge["ID\n(Uso interno)"],
        "Categoría*"                    : df_merge["CATEGORIA"],
        "Subcategoría"                  : df_merge["SUBCATEGORIA"],
        "Código"                        : df_merge["SKU"],
        "Nombre*"                       : df_merge["PRODUCTO"],
        "Descripción"                   : df_merge.get("DESCRIPCION", ""),
        "Precio*"                       : df_merge["PRECIO VENTA"],
        "Costo"                         : df_merge["COSTO"],
        "Proveedor"                     : "",
        "Activo\n(SÍ / NO)"             : df_merge["Activo_Fudo"],
        "Favorito\n(SÍ / NO)"           : "No",
        "Controlar Stock\n(SÍ / NO)"    : "No",
        "Permitir vender solo\n(SÍ / NO)": "Si",
        "Posición"                      : df_merge.get("Posición", None)
    })

    # 6) Ordeno y devuelvo
    return (
        df_export
        .sort_values(
            ["Categoría*", "Subcategoría", "Nombre*"],
            key=lambda col: col.map(clean_for_sort)
        )
        .reset_index(drop=True)
    )

def upload_export_df(df_export: pd.DataFrame, fudo_url: str):
    """
    Limpia y escribe df_export en la pestaña Productos (índice 1)
    de tu Google Sheet de Fudo.
    """
    fudo_conn = SheetConnector(fudo_url)
    sh = fudo_conn.client.open_by_url(fudo_url)
    prod_ws = sh.worksheets()[1]
    prod_ws.clear()
    data = [df_export.columns.tolist()] + df_export.values.tolist()
    prod_ws.update(values=data, range_name="A1")

def download_fudo_xlsx(fudo_id: str, creds_json: Union[dict, str]) -> bytes:
    """
    Descarga directamente el .xlsx de Google Sheets vía la API de Drive.
    """
    # parse JSON si hace falta
    if isinstance(creds_json, str):
        creds_info = json.loads(creds_json)
    else:
        creds_info = creds_json

    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    sess = AuthorizedSession(creds)
    export_url = f"https://docs.google.com/spreadsheets/d/{fudo_id}/export?format=xlsx"
    resp = sess.get(export_url)
    resp.raise_for_status()
    return resp.content


def get_unique_categories(df_export: pd.DataFrame) -> List[str]:
    """
    Devuelve la lista de categorías únicas, en el orden en que aparecen.
    """
    return df_export["Categoría*"].drop_duplicates().tolist()

def apply_category_order_and_position(
    df_export: pd.DataFrame, order_list: List[str]
) -> pd.DataFrame:
    """
    Reordena el DataFrame según order_list de categorías,
    luego por Subcategoría y Nombre*, y asigna una columna
    'Posición' global de 1 a N.
    """
    # 1) Forzar el orden de categorías
    cat_type = CategoricalDtype(categories=order_list, ordered=True)
    df = df_export.copy()
    df["Categoría*"] = df["Categoría*"].astype(cat_type)

    # 2) Ordenamiento final
    df = df.sort_values(
        by=["Categoría*", "Subcategoría", "Nombre*"],
        key=lambda col: col.str.lower()
    ).reset_index(drop=True)

    # 3) Asignar posición global
    df.insert(0, "Posición", range(1, len(df) + 1))
    return df

def build_export_df_from_dfs(df_master: pd.DataFrame, df_template: pd.DataFrame) -> pd.DataFrame:
    """
    Igual que build_export_df, pero usando los DataFrames que ya tienes en sesión:
    - df_master: tu hoja maestra raw
    - df_template: df de Productos de Fudo con IDs asignados
    """
    # 1) Exploto fracciones
    df_master_exp = explode_fracciones(df_master.copy())

    
        # 2) Merge para heredar IDs
    df_merge = (
        df_master_exp
        .merge(
            df_template[["ID\n(Uso interno)", "Código"]],
            how="left",
            left_on="SKU",
            right_on="Código"
        )
        .rename(columns={"ID\n(Uso interno)": "ID_prev"})
    )

    st.write("▶️ [DEBUG builder] STOCK dtype:",   df_merge["STOCK"].dtype)
    st.write("▶️ [DEBUG builder] STOCK únicos:",   df_merge["STOCK"].unique())
    st.write("▶️ [DEBUG builder] filas AL-ALME:",
             df_merge[df_merge["SKU"].str.contains("AL-ALME")][["SKU","STOCK","ACTIVO"]])
    
    stock_str = df_merge["STOCK"].astype(str).str.strip()

    # 3) Asigno la columna final de IDs (enteros o None)
    def make_id(x):
        return int(x) if pd.notna(x) else None

    df_merge["ID\n(Uso interno)"] = df_merge["ID_prev"].apply(make_id)

    df_merge["Activo_Fudo"] = np.where(
        (df_merge["ACTIVO"].str.upper()=="SI") & (stock_str != "0"),
        "Si",
         "No"
    )

    st.write("▶️ [DEBUG builder] Activo_Fudo únicos:", 
         df_merge["Activo_Fudo"].unique())
    
    st.write("▶️ [DEBUG builder] filas AL-ALME con Activo_Fudo:", 
         df_merge
           .loc[df_merge["SKU"].str.contains("AL-ALME"), 
                ["SKU","STOCK","ACTIVO","Activo_Fudo"]])


    # 4) Mapeo al formato Fudo
    df_export = pd.DataFrame({
        "ID\n(Uso interno)"             : df_merge["ID\n(Uso interno)"],
        "Categoría*"                    : df_merge["CATEGORIA"],
        "Subcategoría"                  : df_merge["SUBCATEGORIA"],
        "Código"                        : df_merge["SKU"],
        "Nombre*"                       : df_merge["PRODUCTO"],
        "Descripción"                   : df_merge.get("DESCRIPCION", ""),
        "Precio*"                       : df_merge["PRECIO VENTA"],
        "Costo"                         : df_merge["COSTO"],
        "Proveedor"                     : "",
        "Activo\n(SÍ / NO)"             : df_merge["Activo_Fudo"],
        "Favorito\n(SÍ / NO)"           : "No",
        "Controlar Stock\n(SÍ / NO)"    : "No",
        "Permitir vender solo\n(SÍ / NO)": "Si",
        "Posición"                      : df_merge.get("Posición", None)
    })

    

    # 5) Ordeno y limpio índice
    return (
        df_export
        .sort_values(
            ["Categoría*", "Subcategoría", "Nombre*"],
            key=lambda col: col.map(clean_for_sort)
        )
        .reset_index(drop=True)
    )