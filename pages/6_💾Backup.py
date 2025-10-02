# pages/6_💾Backup.py
import streamlit as st
# from backup import guardar_backup, listar_backups   # <- quitar
from backup_local import guardar_backup, listar_backups  # <- usar este


def backup_page():
    st.title("Sistema de Backups")

    if st.button("Realizar Backup"):
        result = guardar_backup()
        if result["path"]:
            st.success(f"Backup local: {result['path']}")
        else:
            st.info("Entorno web: no hay Escritorio. Usá la descarga.")

        st.download_button(
            "Descargar backup (XLSX)",
            data=result["bytes"],
            file_name=result["filename"],
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        up = result.get("uploaded")
        if isinstance(up, dict) and up.get("ok"):
            if up.get("non_json"):
                st.info("Subido a Drive (respuesta no-JSON del Web App). Verificá la carpeta de Backups.")
            else:
                st.success(f"Subido a Drive: [{up['name']}]({up['url']})")
        elif up is None:
            st.info("Subida a Drive no configurada. Agregá [backup_upload] en secrets si querés automatizarlo.")
        else:
            st.warning(f"No pude subir automáticamente a Drive. Detalle: {up.get('error')}")




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
