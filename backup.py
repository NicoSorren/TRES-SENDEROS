# backup.py
import os
import datetime
import pandas as pd

def crear_directorio_backup(directorio="backups"):
    """
    Crea el directorio de backups si no existe y lo retorna.
    """
    if not os.path.exists(directorio):
        os.makedirs(directorio)
    return directorio

def guardar_backup(df, directorio="backups"):
    """
    Guarda el DataFrame 'df' en un archivo CSV dentro del directorio de backups.
    El nombre del archivo se genera usando la fecha y hora actuales.
    Retorna la ruta completa del archivo generado.
    """
    backup_dir = crear_directorio_backup(directorio)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{timestamp}.csv"
    filepath = os.path.join(backup_dir, filename)
    df.to_csv(filepath, index=False)
    return filepath

def listar_backups(directorio="backups"):
    """
    Lista y retorna los nombres de archivo de todos los backups existentes en el directorio.
    """
    backup_dir = crear_directorio_backup(directorio)
    archivos = [f for f in os.listdir(backup_dir) if f.endswith(".csv")]
    return sorted(archivos)
