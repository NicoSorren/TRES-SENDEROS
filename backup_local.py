# backup_local.py
from __future__ import annotations
import datetime as dt
from io import BytesIO
from pathlib import Path
import pandas as pd
import streamlit as st
from sheet_connector import SheetConnector

def _now_str() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def _desktop_dir() -> Path:
    home = Path.home()
    for c in [home/"Desktop", home/"Escritorio", home/"OneDrive"/"Desktop", home/"OneDrive"/"Escritorio"]:
        if c.exists():
            return c
    return home

def _backup_root() -> Path:
    root = _desktop_dir() / "BACKUP TRES SENDEROS"
    try:
        root.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return root

def _master_url() -> str:
    master_id = st.secrets["backup"]["master_spreadsheet_id"]
    return f"https://docs.google.com/spreadsheets/d/{master_id}/edit#gid=0"

def _collect_dataframes() -> dict[str, pd.DataFrame]:
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

    if not dfs:
        dfs["PRODUCTOS"] = st.session_state.get("df", pd.DataFrame())
    return dfs

def guardar_backup(*_args, **_kwargs) -> dict:
    dfs = _collect_dataframes()
    fname = f"TS_MASTER_{_now_str()}.xlsx"

    # XLSX en memoria para descarga
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for sheet, df in dfs.items():
            df.to_excel(w, sheet_name=sheet, index=False)
    buf.seek(0)
    xlsx_bytes = buf.getvalue()

    # Intento guardar local (si existe escritorio)
    saved_path = None
    try:
        out_dir = _backup_root()
        out_path = out_dir / fname
        with open(out_path, "wb") as f:
            f.write(xlsx_bytes)
        saved_path = str(out_path.resolve())
    except Exception:
        saved_path = None

    return {"path": saved_path, "bytes": xlsx_bytes, "filename": fname}

def listar_backups() -> list[str]:
    root = _backup_root()
    try:
        files = sorted(root.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [str(p.resolve()) for p in files]
    except Exception:
        return []
