# pages/6_💾Backup.py
import streamlit as st
# from backup import guardar_backup, listar_backups   # <- quitar
from backup_local import guardar_backup, listar_backups  # <- usar este


def backup_page():
    st.title("Sistema de Backups")

    if st.button("Realizar Backup"):
        try:
            result = guardar_backup()
            if result["path"]:
                st.success(f"Backup guardado en: {result['path']}")
            else:
                st.info("Backup generado en memoria (entorno web). Descargalo abajo.")
            st.download_button(
                "Descargar backup (XLSX)",
                data=result["bytes"],
                file_name=result["filename"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(str(e))


    st.markdown("---")
    st.subheader("Backups existentes")
    try:
        backups = listar_backups()
        if backups:
            for p in backups:
                st.write(p)
        else:
            st.info("No se encontraron backups locales (en entorno web no hay Escritorio).")
    except Exception as e:
        st.error(f"No se pudieron listar los backups: {e}")

if __name__ == "__main__":
    backup_page()
