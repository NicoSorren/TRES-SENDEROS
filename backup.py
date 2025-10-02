# backup.py
import datetime
from typing import List, Dict, Optional
import json
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# ===== Helpers de autenticación =====
def _drive_service():
    # 👇 Tomamos el string JSON desde secrets y lo convertimos a dict
    raw = st.secrets["gcp_service_account"].get("json")
    if not raw:
        raise RuntimeError("Falta gcp_service_account.json en secrets.toml")

    creds_info = json.loads(raw)  # <-- clave del fix
    scopes = ["https://www.googleapis.com/auth/drive"]
    credentials = service_account.Credentials.from_service_account_info(
        creds_info, scopes=scopes
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)

def _now_str():
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# ===== API =====
def guardar_backup() -> Dict:
    """
    Crea una copia del Spreadsheet maestro dentro de la carpeta de backups.
    Devuelve dict con id, name y webViewLink.
    """
    drive = _drive_service()
    master_id = st.secrets["backup"]["master_spreadsheet_id"]
    folder_id = st.secrets["backup"]["folder_id"]

    # Nombre tipo: TS_MASTER_YYYY-MM-DD_HH-MM-SS
    new_name = f"TS_MASTER_{_now_str()}"

    body = {
        "name": new_name,
        "parents": [folder_id],   # ubicación: carpeta de backups
    }

    try:
        # files.copy mantiene el tipo nativo (Google Sheets)
        new_file = (
            drive.files()
            .copy(fileId=master_id, body=body, fields="id, name, webViewLink, createdTime")
            .execute()
        )
    except HttpError as e:
        # Burbujea con mensaje claro para la UI
        raise RuntimeError(f"Error al copiar el Spreadsheet maestro: {e}")

    # Opcional: limpieza de backups antiguos
    _auto_cleanup(drive)

    return {
        "id": new_file["id"],
        "name": new_file["name"],
        "link": new_file.get("webViewLink", ""),
        "createdTime": new_file.get("createdTime", ""),
    }


def listar_backups(max_items: int = 100) -> List[Dict]:
    """
    Lista los archivos en la carpeta de backups (solo Google Sheets), ordenados por fecha desc.
    Devuelve una lista de dicts con {id, name, createdTime, webViewLink}.
    """
    drive = _drive_service()
    folder_id = st.secrets["backup"]["folder_id"]

    query = (
        f"'{folder_id}' in parents and "
        f"mimeType = 'application/vnd.google-apps.spreadsheet' and "
        f"trashed = false"
    )

    results = (
        drive.files()
        .list(
            q=query,
            orderBy="createdTime desc",
            pageSize=max_items,
            fields="files(id, name, createdTime, webViewLink)",
        )
        .execute()
    )

    return results.get("files", [])


def _auto_cleanup(drive) -> None:
    """
    Si backup.keep_last está definido, mantiene solo los N más recientes.
    Borra silenciosamente el resto.
    """
    keep_last = int(st.secrets["backup"].get("keep_last", 0) or 0)
    if keep_last <= 0:
        return

    folder_id = st.secrets["backup"]["folder_id"]
    query = (
        f"'{folder_id}' in parents and "
        f"mimeType = 'application/vnd.google-apps.spreadsheet' and "
        f"trashed = false"
    )
    res = (
        drive.files()
        .list(
            q=query,
            orderBy="createdTime desc",
            pageSize=1000,
            fields="files(id)",
        )
        .execute()
    )
    files = res.get("files", [])
    to_delete = files[keep_last:]  # del (keep_last+1) en adelante

    for f in to_delete:
        try:
            drive.files().delete(fileId=f["id"]).execute()
        except HttpError:
            # no frenamos el flujo por un fallo de limpieza
            pass
