# backup.py
from __future__ import annotations
import os
from pathlib import Path
import datetime as dt
import pandas as pd
import streamlit as st

# Usamos tu conector para leer TODAS las pestañas que interesan
from sheet_connector import SheetConnector

# ---------- Helpers de ruta ----------

def _desktop_dir() -> Path:
    """
    Devuelve la carpeta Escritorio del usuario de forma robusta:
    - Windows: Desktop / OneDrive/Desktop / OneDrive/Escritorio / Escritorio
    - macOS/Linux: ~/Desktop o ~/Escritorio si existe
    """
    home = Path.home()
    candidates = [
        home / "Desktop",
        home / "Escritorio",
        home / "OneDrive" / "Desktop",
        home / "OneDrive" / "Escritorio",
    ]
    for c in candidates:
        if c.exists():
            return c
    # fallback: home
    return home

def _backup_root() -> Path:
    """Carpeta final de backups en el Escritorio."""
    root = _desktop_dir() / "BACKUP TRES SENDEROS"
    root.mkdir(parents=True, exist_ok=True)
    return root

def _now_str() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def _master_url_from_secrets() -> str:
    """
    Tu SheetConnector recibe una URL completa.
    En secrets guardamos el ID: armamos la URL estándar con ese ID.
    """
    try:
        master_id = st.secrets["backup"]["master_spreadsheet_id"]
    except Exception as e:
        raise RuntimeError("No encuentro [backup].master_spreadsheet_id en secrets.toml") from e
    return f"https://docs.google.com/spreadsheets/d/{master_id}/edit#gid=0"

# ---------- API pública ----------

def guardar_backup(_df_ignorado=None) -> str:
    """
    Crea un archivo XLSX local con todas las pestañas clave del maestro.
    Devuelve la ruta absoluta del archivo creado.
    Compatibilidad: acepta un primer arg (df) pero lo ignora.
    """
    # 1) Dónde guardamos
    out_dir = _backup_root()
    out_path = out_dir / f"TS_MASTER_{_now_str()}.xlsx"

    # 2) Conectamos al maestro y leemos todas las hojas relevantes
    url = _master_url_from_secrets()
    conn = SheetConnector(url)

    # Preparamos getters de cada pestaña (se llaman si existen)
    getters = {
        "PRODUCTOS": getattr(conn, "get_products", None),
        "CLIENTES": getattr(conn, "get_clients", None),
        "REMITOS": getattr(conn, "get_remitos", None),
        "DETALLE_REMITOS": getattr(conn, "get_remito_items", None),
        "CATEGORIAS": getattr(conn, "get_categories", None),
        "SUBCATEGORIAS": getattr(conn, "get_subcategories", None),
    }

    # 3) Escribimos el XLSX con openpyxl
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        wrote_any = False
        for sheet_name, getter in getters.items():
            if getter is None:
                continue
            try:
                df = getter()
            except Exception:
                # Si hay una hoja que todavía no implementaste, seguimos
                df = None
            if df is None:
                df = pd.DataFrame()
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            wrote_any = True

        if not wrote_any:
            # Como mínimo respaldamos el df de sesión si existiera
            df_sess = st.session_state.get("df", pd.DataFrame())
            df_sess.to_excel(writer, sheet_name="PRODUCTOS", index=False)

    return str(out_path.resolve())


def listar_backups() -> list[str]:
    """
    Lista rutas absolutas de los archivos .xlsx en la carpeta de backups (ordenados desc por fecha).
    """
    root = _backup_root()
    files = sorted(root.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [str(p.resolve()) for p in files]
