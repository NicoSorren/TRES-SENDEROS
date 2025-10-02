# pages/6_💾Backup.py
import streamlit as st
from backup import guardar_backup, listar_backups

def backup_page():
    st.title("Sistema de Backups")

    if st.button("Realizar Backup"):
        try:
            info = guardar_backup()
            st.success(f"Backup creado: [{info['name']}]({info['link']})")
        except Exception as e:
            st.error(str(e))

    st.markdown("---")
    st.subheader("Backups existentes")

    try:
        backups = listar_backups()
        if backups:
            for f in backups:
                st.write(f"• [{f['name']}]({f.get('webViewLink','')}) — {f.get('createdTime','')}")
        else:
            st.info("No se encontraron backups.")
    except Exception as e:
        st.error(f"No se pudieron listar los backups: {e}")

if __name__ == "__main__":
    backup_page()
