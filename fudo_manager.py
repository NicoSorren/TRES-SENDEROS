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

import unicodedata, re

def _norm_col(s: str) -> str:
    # normaliza: quita saltos de línea, colapsa espacios, quita acentos, minúsculas
    s = str(s).replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return s.lower()

def _find_col(df: pd.DataFrame, target: str) -> str | None:
    tgt = _norm_col(target)
    # 1) match exacto normalizado
    for c in df.columns:
        if _norm_col(c) == tgt:
            return c
    # 2) fallback específico para el ID interno (por si cambia formato)
    if tgt == _norm_col("ID (Uso interno)"):
        for c in df.columns:
            n = _norm_col(c)
            if "id" in n and "uso" in n and "interno" in n:
                return c
    return None

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
    df_fudo   = fudo_conn.get_products()

    # 2.a) Detecto nombres reales y estandarizo
    id_col   = _find_col(df_fudo, "ID (Uso interno)")
    code_col = _find_col(df_fudo, "Código")

    # Debug opcional
    # st.write("Encabezados Fudo:", list(df_fudo.columns))
    # st.write("ID detectada:", id_col, " — Código detectada:", code_col)

    if not id_col or not code_col:
        raise KeyError("No se encontraron columnas ‘ID (Uso interno)’ y/o ‘Código’ en la hoja de Fudo.")

    df_fudo_sub = df_fudo[[id_col, code_col]].rename(
        columns={id_col: "ID\n(Uso interno)", code_col: "Código"}
    )

    # 3) Merge para conservar IDs previos
    df_merge = (
        df_master
        .merge(df_fudo_sub, how="left", left_on="SKU", right_on="Código")
        .rename(columns={"ID\n(Uso interno)": "ID_prev"})
    )

    # 4) IDs finales como int o None
    def make_id(val):
        if pd.isna(val) or str(val).strip() == "":
            return None
        return int(float(val))

    df_merge["ID\n(Uso interno)"] = df_merge["ID_prev"].apply(make_id)

    # 5) Activo_Fudo (activo=SI y stock != "0")
    stock_str = df_merge.get("STOCK", "").astype(str).str.strip()
    activo    = df_merge.get("ACTIVO", "").astype(str).str.upper().str.strip()
    df_merge["Activo_Fudo"] = np.where(
        (activo == "SI") & (stock_str != "0"),
        "Si", "No"
    )

    # 6) Mapeo al template de Fudo
    df_export = pd.DataFrame({
        "ID\n(Uso interno)"              : df_merge["ID\n(Uso interno)"],
        "Categoría*"                     : df_merge.get("CATEGORIA", ""),
        "Subcategoría"                   : df_merge.get("SUBCATEGORIA", ""),
        "Código"                         : df_merge["SKU"],
        "Nombre*"                        : df_merge["PRODUCTO"],
        "Descripción"                    : df_merge.get("DESCRIPCION", ""),
        "Precio*"                        : df_merge["PRECIO VENTA"],
        "Costo"                          : df_merge["COSTO"],
        "Proveedor"                      : "",
        "Activo\n(SÍ / NO)"              : df_merge["Activo_Fudo"],
        "Favorito\n(SÍ / NO)"            : "No",
        "Controlar Stock\n(SÍ / NO)"     : "No",
        "Permitir vender solo\n(SÍ / NO)": "Si",
        "Posición"                       : df_merge.get("Posición", None)
    })

    # 7) Orden final
    return (
        df_export
        .sort_values(["Categoría*", "Subcategoría", "Nombre*"],
                     key=lambda col: col.map(clean_for_sort))
        .reset_index(drop=True)
    )

# fudo_manager.py
import time
import math
from typing import Optional

import numpy as np
import pandas as pd

from sheet_connector import SheetConnector


def upload_export_df(
    df_export: pd.DataFrame,
    fudo_url: str,
    worksheet_name: str = "Productos",
    batch_rows: int = 500,          # tamaño de bloque por update
    max_retries: int = 5,           # reintentos ante APIError o timeouts
    backoff_sec: float = 1.0,       # espera base entre reintentos
    progress_cb: Optional[callable] = None,  # opcional: función(progress: float)
):
    """
    Sube df_export a la hoja 'worksheet_name' del Google Sheet Fudo en forma robusta e idempotente.

    1) Sanitiza valores (sin NaN/Inf/np types/NaT).
    2) Escribe encabezado en A1.
    3) Escribe filas en lotes (A{row} anclado).
    4) Limpia el 'tail' sobrante al final (idempotente).
    5) Reintenta con backoff si hay rate-limit/errores transitorios.

    Parámetros:
      - df_export: DataFrame final con las columnas exactas requeridas por Fudo.
      - fudo_url: URL del Google Sheet de Fudo.
      - worksheet_name: nombre de la pestaña destino (por defecto "Productos").
      - batch_rows: filas por bloque (500–1000 es razonable).
      - max_retries: cantidad de reintentos por bloque.
      - backoff_sec: segundos base de espera entre reintentos.
      - progress_cb: función opcional para reportar progreso (0.0–1.0).
    """

    # -------- 0) Preparación/saneamiento --------
    df = df_export.copy()

    # Recomendado: unicidad por Código antes de escribir
    if "Código" in df.columns:
        df = df.drop_duplicates(subset=["Código"], keep="first")

    # Reemplazar inf/-inf por NaN y luego NaN -> ""
    df = df.replace([np.inf, -np.inf], np.nan).where(pd.notnull(df), "")

    # Asegurar que no queden 'nan' string en textos
    for col in df.columns:
        if pd.api.types.is_object_dtype(df[col].dtype):
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("nan", "", regex=False)
                .str.replace("NaT", "", regex=False)
            )

    # Convertir valores a tipos JSON-seguros (primitivos de Python)
    def to_primitive(x):
        # None -> ""
        if x is None:
            return ""
        # pandas NA/NaN -> ""
        if pd.isna(x):
            return ""
        # pandas Timestamp -> ISO
        if isinstance(x, pd.Timestamp):
            return x.isoformat()
        # numpy -> python
        if isinstance(x, (np.integer,)):
            return int(x)
        if isinstance(x, (np.floating,)):
            # por las dudas, ya mapeamos NaN arriba, pero re-chequeamos
            return float(x)
        if isinstance(x, (np.bool_, bool)):
            return bool(x)
        # resto: dejar como string/plano
        return x

    header = [str(c) for c in df.columns.tolist()]
    rows = [[to_primitive(v) for v in row] for row in df.astype(object).values.tolist()]

    # -------- 1) Abrir worksheet destino --------
    conn = SheetConnector(fudo_url)
    sh = conn.client.open_by_url(fudo_url)
    try:
        ws = sh.worksheet(worksheet_name)
    except Exception:
        # fallback: segunda hoja (como en tu lógica anterior)
        ws = sh.worksheets()[1]

    # -------- 2) Escribir encabezado en A1 --------
    _retry_update(ws, [header], "A1", max_retries=max_retries, backoff_sec=backoff_sec)

    # -------- 3) Escribir filas en lotes --------
    total = len(rows)
    if total == 0:
        # si no hay filas, limpiar todo debajo de encabezado
        try:
            ws.batch_clear([f"A2:ZZ100000"])
        except Exception:
            pass
        if progress_cb:
            progress_cb(1.0)
        return

    start_row = 2
    blocks = math.ceil(total / batch_rows)

    for b in range(blocks):
        i0 = b * batch_rows
        i1 = min(total, i0 + batch_rows)
        block = rows[i0:i1]

        # rango de inicio del bloque
        range_anchor = f"A{start_row}"
        _retry_update(ws, block, range_anchor, max_retries=max_retries, backoff_sec=backoff_sec)

        start_row += len(block)

        if progress_cb:
            progress_cb((i1) / total)

    # -------- 4) Limpiar tail sobrante (idempotente) --------
    # limpia desde la fila siguiente al último bloque hasta un tope alto
    try:
        ws.batch_clear([f"A{start_row}:ZZ100000"])
    except Exception:
        # si falla la limpieza, no abortamos: ya escribimos lo necesario
        pass

    if progress_cb:
        progress_cb(1.0)


def _retry_update(ws, values, range_anchor, max_retries=5, backoff_sec=1.0):
    """
    Envuelve ws.update con reintentos y espera incremental ante errores transitorios de la API.
    """
    attempt = 0
    while True:
        try:
            # Importante: values puede ser list[list] (bloque) o list (una fila)
            # gspread espera list[list] para múltiples filas
            payload = values if (values and isinstance(values[0], list)) else [values]
            ws.update(payload, range_anchor)
            return
        except Exception as e:
            attempt += 1
            if attempt > max_retries:
                # Re-lanzamos el último error
                raise
            # Espera incremental (1x, 2x, 3x, …)
            time.sleep(backoff_sec * attempt)

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
    Igual que build_export_df, pero usando los DataFrames ya cargados en sesión:
    - df_master: hoja maestra raw
    - df_template: DataFrame de la hoja Fudo (pestaña Productos) con IDs asignados
    """
    # 1) Exploto fracciones
    df_master_exp = explode_fracciones(df_master.copy())

    # 2) Detecto nombres reales en el template y estandarizo
    id_col   = _find_col(df_template, "ID (Uso interno)")
    code_col = _find_col(df_template, "Código")
    if not id_col or not code_col:
        raise KeyError("No se encontraron columnas ‘ID (Uso interno)’ y/o ‘Código’ en el template de Fudo.")

    df_temp_sub = df_template[[id_col, code_col]].rename(
        columns={id_col: "ID\n(Uso interno)", code_col: "Código"}
    )

    # 3) Merge para heredar IDs
    df_merge = (
        df_master_exp
        .merge(df_temp_sub, how="left", left_on="SKU", right_on="Código")
        .rename(columns={"ID\n(Uso interno)": "ID_prev"})
    )

    # 4) IDs finales como int o None
    def make_id(x):
        return int(float(x)) if pd.notna(x) and str(x).strip() != "" else None

    df_merge["ID\n(Uso interno)"] = df_merge["ID_prev"].apply(make_id)

    # 5) Activo_Fudo (activo=SI y stock != "0")
    stock_str = df_merge.get("STOCK", "").astype(str).str.strip()
    activo    = df_merge.get("ACTIVO", "").astype(str).str.upper().str.strip()
    df_merge["Activo_Fudo"] = np.where(
        (activo == "SI") & (stock_str != "0"),
        "Si", "No"
    )

    # 6) Mapeo al formato Fudo
    df_export = pd.DataFrame({
        "ID\n(Uso interno)"              : df_merge["ID\n(Uso interno)"],
        "Categoría*"                     : df_merge.get("CATEGORIA", ""),
        "Subcategoría"                   : df_merge.get("SUBCATEGORIA", ""),
        "Código"                         : df_merge["SKU"],
        "Nombre*"                        : df_merge["PRODUCTO"],
        "Descripción"                    : df_merge.get("DESCRIPCION", ""),
        "Precio*"                        : df_merge["PRECIO VENTA"],
        "Costo"                          : df_merge["COSTO"],
        "Proveedor"                      : "",
        "Activo\n(SÍ / NO)"              : df_merge["Activo_Fudo"],
        "Favorito\n(SÍ / NO)"            : "No",
        "Controlar Stock\n(SÍ / NO)"     : "No",
        "Permitir vender solo\n(SÍ / NO)": "Si",
        "Posición"                       : df_merge.get("Posición", None)
    })

    # 7) Orden final
    return (
        df_export
        .sort_values(["Categoría*", "Subcategoría", "Nombre*"],
                     key=lambda col: col.map(clean_for_sort))
        .reset_index(drop=True)
    )
