# backup_local.py
from __future__ import annotations
import os
import datetime as dt
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests
import streamlit as st

from sheet_connector import SheetConnector


# ================== Helpers básicos ==================

def _now_str() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _desktop_dir() -> Path:
    """
    Detecta el Escritorio (Windows/Mac/OneDrive/español). Si no existe, usa el home.
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
    return home


def _backup_root() -> Path:
    """
    Carpeta de backups locales:
      - override opcional por env var TRES_SENDEROS_BACKUP_DIR
      - por defecto: Escritorio / BACKUPS TRES SENDEROS
    """
    custom = os.getenv("TRES_SENDEROS_BACKUP_DIR", "").strip()
    root = Path(custom) if custom else (_desktop_dir() / "BACKUPS TRES SENDEROS")
    try:
        root.mkdir(parents=True, exist_ok=True)
    except Exception:
        # En entorno web puede no poder crear; está bien.
        pass
    return root


def _master_url() -> str:
    try:
        master_id = st.secrets["backup"]["master_spreadsheet_id"]
    except Exception as e:
        raise RuntimeError("Falta [backup].master_spreadsheet_id en secrets.toml") from e
    return f"https://docs.google.com/spreadsheets/d/{master_id}/edit#gid=0"


def _keep_last_n() -> int:
    """
    Rotación local opcional. En secrets.toml:
      [backup_local]
      keep_last = 30
    """
    try:
        return int(st.secrets.get("backup_local", {}).get("keep_last", 0))
    except Exception:
        return 0


# ================== Lectura de datos ==================

def _collect_dataframes() -> Dict[str, pd.DataFrame]:
    url = _master_url()
    conn = SheetConnector(url)
    dfs: Dict[str, pd.DataFrame] = {}

    def safe(getter, name: str):
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


# ================== Rotación local ==================

def _rotate_local_backups(directory: Path, keep_last: int) -> None:
    files = sorted(
        directory.glob("TS_MASTER_*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for p in files[keep_last:]:
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass


# ================== Upload a Drive via Apps Script ==================

def _upload_to_drive_via_webapp(xlsx_bytes: bytes, filename: str) -> Optional[dict]:
    conf = st.secrets.get("backup_upload", {})
    url = conf.get("url"); token = conf.get("token")
    if not url or not token:
        return None

    params = {"token": token, "filename": filename}
    headers = {"Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
    r = requests.post(url, params=params, data=xlsx_bytes, headers=headers, timeout=60)

    # Si no es 2xx -> error con cuerpo
    r.raise_for_status()

    # Intento parsear JSON
    try:
        return r.json()
    except ValueError:
        # 🟡 Apps Script devolvió HTML pero igual subió el archivo.
        # Podemos reportar “subido sin confirmar” y que mires la carpeta.
        return {"ok": True, "non_json": True, "hint": "Respuesta no-JSON pero HTTP 200; verificá Drive."}




# ================== API pública ==================

def guardar_backup(*_args, **_kwargs) -> dict:
    """
    Genera backup XLSX y devuelve:
      {
        "path": <ruta local o None>,
        "bytes": <xlsx en bytes para descargar>,
        "filename": <nombre del archivo>,
        "uploaded": <dict con info de Drive o None>
      }
    - En local: además guarda bajo Escritorio/BACKUPS TRES SENDEROS (si es posible).
    - En web: te da descarga y sube a Drive si configuraste el Web App.
    """
    dfs = _collect_dataframes()
    fname = f"TS_MASTER_{_now_str()}.xlsx"

    # 1) Construir XLSX en memoria (XlsxWriter)
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        for sheet, df in dfs.items():
            df.to_excel(w, sheet_name=sheet, index=False)
    buf.seek(0)
    xlsx_bytes = buf.getvalue()

    # 2) Guardado local (si existe escritorio / permisos)
    saved_path = None
    try:
        out_dir = _backup_root()
        out_path = out_dir / fname
        with open(out_path, "wb") as f:
            f.write(xlsx_bytes)
        saved_path = str(out_path.resolve())

        keep = _keep_last_n()
        if keep > 0:
            _rotate_local_backups(out_dir, keep)
    except Exception:
        saved_path = None  # en web suele fallar, y está bien

    # 3) Subir automáticamente a tu Drive vía Web App (si está configurado)
    uploaded = None
    try:
        uploaded = _upload_to_drive_via_webapp(xlsx_bytes, fname)
    except Exception as e:
        uploaded = {"ok": False, "error": str(e)}

    return {"path": saved_path, "bytes": xlsx_bytes, "filename": fname, "uploaded": uploaded}


def listar_backups() -> List[str]:
    """
    Lista backups locales (si existen). En web probablemente no haya escritorio.
    """
    root = _backup_root()
    try:
        files = sorted(root.glob("TS_MASTER_*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [str(p.resolve()) for p in files]
    except Exception:
        return []
