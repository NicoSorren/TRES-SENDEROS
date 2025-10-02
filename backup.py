# backup.py
from __future__ import annotations
import os
from pathlib import Path
import datetime as dt
from io import BytesIO
import pandas as pd
import streamlit as st
from sheet_connector import SheetConnector

# ---------- Rutas locales (solo cuando hay escritorio) ----------
def _desktop_dir() -> Path:
    home = Path.home()
    for c in [home/"Desktop", home/"Escritorio", home/"OneDrive"/"Desktop", home/"OneDrive"/"Escritorio"]:
        if c.exists():
            return c
    return home  # fallback

def _backup_root() -> Path:
    root = _desktop_dir() / "BACKUP TRES SENDEROS"
    try:
        root.mkdir(parents=True, exist_ok=True)
    except Exception:
        # en la nube puede fallar (no hay escritorio); ignoramos
        pass
    return root

def _now_str() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def _master_url() -> str:
    master_id = st.secrets["backup"]["master_spreadsheet_id"]
    return f"https://docs.google.com/spreadsheets/d/{master_id}/edit#gid=0"

# ---------- Core ----------
def _collect_dataframes() -> dict[str, pd.DataFrame]:
    """Lee las hojas relevantes del maestro usando tu SheetConnector."""
    url = _master_url()
    conn = SheetConnector(url)
    dfs: dict[str, pd.DataFrame] = {}

    def safe(getter, name):
        try:
            df = getter()
        except Exception:
            df = pd.DataFrame()
        dfs[name] = df if df is not None else pd.DataFrame()

    if hasattr(conn, "get_products"):       safe(conn.get_products, "PRODUCTOS")
    if hasattr(conn, "get_clients"):        safe(conn.get_clients, "CLIENTES")
    if hasattr(conn, "get_remitos"):        safe(conn.get_remitos, "REMITOS")
    if hasattr(conn, "get_remito_items"):   safe(conn.get_remito_items, "DETALLE_REMITOS")
    if hasattr(conn, "get_categories"):     safe(conn.get_categories, "CATEGORIAS")
    if hasattr(conn, "get_subcategories"):  safe(conn.get_subcategories, "SUBCATEGORIAS")

    # fallback si no trajo nada
    if not dfs:
        dfs["PRODUCTOS"] = st.session_state.get("df", pd.DataFrame())
    return dfs

# ---------- API pública ----------
def guardar_backup(*_args, **_kwargs) -> dict:
    """
    Crea un backup y devuelve:
      {"path": <ruta_local_o_None>, "bytes": <xlsx_bytes>, "filename": <nombre.xlsx>}
    - Siempre produce bytes para descarga.
    - Si es posible, además guarda un .xlsx en Escritorio/BACKUP TRES SENDEROS.
    Acepta args/kwargs extra para ser compatible con llamadas anteriores.
    """
    dfs = _collect_dataframes()
    fname = f"TS_MASTER_{_now_str()}.xlsx"

    # 1) Siempre construimos el XLSX en memoria
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for sheet, df in dfs.items():
            df.to_excel(writer, sheet_name=sheet, index=False)
    buf.seek(0)
    xlsx_bytes = buf.getvalue()

    # 2) Intentamos guardar local (solo si hay escritorio/escritura)
    saved_path = None
    try:
        out_dir = _backup_root()
        out_path = out_dir / fname
        # puede fallar en cloud: carpeta no existe o es read-only
        with open(out_path, "wb") as f:
            f.write(xlsx_bytes)
        saved_path = str(out_path.resolve())
    except Exception:
        saved_path = None  # estamos probablemente en la nube; solo descarga

    return {"path": saved_path, "bytes": xlsx_bytes, "filename": fname}

def listar_backups() -> list[str]:
    """Lista backups locales (si existen). En cloud normalmente quedará vacío."""
    root = _backup_root()
    try:
        files = sorted(root.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [str(p.resolve()) for p in files]
    except Exception:
        return []
