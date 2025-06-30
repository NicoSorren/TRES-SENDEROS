# pages/Backup.py
import streamlit as st
import os
from backup import guardar_backup, listar_backups

def backup_page():
    st.title("Sistema de Backups")

    # Opción para realizar un backup
    if st.button("Realizar Backup"):
        if "df" not in st.session_state:
            st.error("No hay datos para respaldar. Carga primero los productos.")
        else:
            filepath = guardar_backup(st.session_state.df)
            st.success(f"Backup guardado: {filepath}")

    st.markdown("---")
    st.subheader("Backups existentes")
    backups = listar_backups()
    if backups:
        # Mostrar la lista de backups con sus rutas relativas
        for backup_file in backups:
            st.write(backup_file)
    else:
        st.info("No se encontraron backups.")

if __name__ == "__main__":
    backup_page()
