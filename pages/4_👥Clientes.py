# pages/5_Clientes.py

import streamlit as st
import pandas as pd
from sheet_connector import SheetConnector

# URL de tu spreadsheet (idéntica a la que usas en Remito y Productos)
SPREADSHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/"
    "edit?gid=0#gid=0"
)

def _rerun():
    """
    Helper que invoca la función de rerun según la versión de Streamlit.
    """
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

@st.cache_data(ttl=300, show_spinner=False)
def load_clients(spreadsheet_url: str) -> pd.DataFrame:
    """
    Cachea la lectura de la pestaña CLIENTES durante 5 minutos.
    """
    connector = SheetConnector(spreadsheet_url)
    df = connector.get_clients()
    return df if df is not None else pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def load_remitos(spreadsheet_url: str) -> pd.DataFrame:
    """
    Cachea la lectura de la pestaña REMITOS durante 5 minutos.
    """
    connector = SheetConnector(spreadsheet_url)
    df = connector.get_remitos()
    return df if df is not None else pd.DataFrame()

def clientes_page():
    st.title("Gestión de Clientes")
    connector = SheetConnector(SPREADSHEET_URL)

    # 1) Carga cacheada de clientes y remitos
    df_clients = load_clients(SPREADSHEET_URL)
    df_remitos = load_remitos(SPREADSHEET_URL)

    # 2) Mostrar/ocultar listado con buscador
    if st.checkbox("Mostrar lista de clientes"):
        if df_clients.empty:
            st.info("No hay clientes registrados aún.")
        else:
            q = st.text_input("🔍 Buscar cliente (ID, nombre o email)", "")
            if q:
                mask = (
                    df_clients["ID CLIENTE"].str.contains(q, case=False, na=False)
                    | df_clients["NOMBRE"].str.contains(q, case=False, na=False)
                    | df_clients["EMAIL"].str.contains(q, case=False, na=False)
                )
                df_display = df_clients[mask]
                if df_display.empty:
                    st.warning("No se encontraron clientes que coincidan.")
                else:
                    st.dataframe(df_display, use_container_width=True)
            else:
                st.dataframe(df_clients, use_container_width=True)

    st.markdown("---")

    # 3) Pestañas para cada operación
    tab_add, tab_edit, tab_del, tab_hist = st.tabs([
        "➕ Agregar Cliente",
        "✏️ Editar Cliente",
        "🗑️ Eliminar Cliente",
        "📜 Historial"
    ])

    # ——————————————————————————
    # 4A) Pestaña: Agregar Cliente
    # ——————————————————————————
    with tab_add:
        st.subheader("Agregar Cliente Nuevo")

        # Calcular próximo ID con prefijo CLI-###
        if not df_clients.empty and "ID CLIENTE" in df_clients.columns:
            nums = (
                df_clients["ID CLIENTE"]
                .str.replace(r"^CLI-", "", regex=True)
                .pipe(pd.to_numeric, errors="coerce")
                .dropna()
            )
            next_num = int(nums.max()) + 1 if not nums.empty else 1
        else:
            next_num = 1
        new_id = f"CLI-{next_num:03d}"

        with st.form("form_add_client", clear_on_submit=True):
            st.text_input("ID Cliente", value=new_id, disabled=True)
            nombre_n    = st.text_input("Nombre")
            direccion_n = st.text_input("Dirección")
            telefono_n  = st.text_input("Teléfono")
            email_n     = st.text_input("Email")
            obs_n       = st.text_area("Observaciones")
            submitted_n = st.form_submit_button("Agregar Cliente")

        if submitted_n:
            new_client = {
                "ID CLIENTE":    new_id,
                "NOMBRE":        nombre_n,
                "DIRECCION":     direccion_n,
                "TELEFONO":      telefono_n,
                "EMAIL":         email_n,
                "OBSERVACIONES": obs_n,
                "FECHA_ALTA":    pd.Timestamp("today").date().isoformat()
            }
            connector.add_client(new_client)
            st.success(f"Cliente {new_id} '{nombre_n}' agregado.")
            load_clients.clear()
            load_remitos.clear()
            if st.button("➕ Agregar otro cliente"):
                _rerun()

    # ——————————————————————————
    # 4B) Pestaña: Editar Cliente
    # ——————————————————————————
    with tab_edit:
        st.subheader("Editar Cliente Existente")

        if df_clients.empty:
            st.warning("No hay clientes para editar.")
        else:
            nombres = df_clients["NOMBRE"].tolist()
            selected_name = st.selectbox("Selecciona Nombre del cliente", nombres, key="edit_name")
            cliente = df_clients[df_clients["NOMBRE"] == selected_name].iloc[0]
            edit_id = cliente["ID CLIENTE"]

            with st.form("form_edit_client"):
                nombre_e    = st.text_input("Nombre", value=cliente["NOMBRE"])
                direccion_e = st.text_input("Dirección", value=cliente["DIRECCION"])
                telefono_e  = st.text_input("Teléfono", value=cliente["TELEFONO"])
                email_e     = st.text_input("Email", value=cliente["EMAIL"])
                obs_e       = st.text_area("Observaciones", value=cliente["OBSERVACIONES"])
                submitted_e = st.form_submit_button("Actualizar Cliente")

            if submitted_e:
                updated = {
                    "ID CLIENTE":    edit_id,
                    "NOMBRE":        nombre_e,
                    "DIRECCION":     direccion_e,
                    "TELEFONO":      telefono_e,
                    "EMAIL":         email_e,
                    "OBSERVACIONES": obs_e,
                    # FECHA_ALTA se conserva
                }
                connector.update_client(updated)
                st.success("Cliente actualizado.")
                load_clients.clear()
                if st.button("✏️ Editar otro cliente"):
                    _rerun()

    # ——————————————————————————
    # 4C) Pestaña: Eliminar Cliente
    # ——————————————————————————
    with tab_del:
        st.subheader("Eliminar Cliente")

        if df_clients.empty:
            st.warning("No hay clientes para eliminar.")
        else:
            nombres = df_clients["NOMBRE"].tolist()
            selected_name = st.selectbox("Selecciona Nombre a eliminar", nombres, key="del_name")
            if st.button(f"Eliminar {selected_name}", key="del_act"):
                client_row = df_clients[df_clients["NOMBRE"] == selected_name].iloc[0]
                connector.delete_client(client_row["ID CLIENTE"])
                st.success(f"Cliente {selected_name} eliminado.")
                load_clients.clear()
                load_remitos.clear()
                if st.button("🗑️ Eliminar otro cliente", key="del_again"):
                    _rerun()

    # ——————————————————————————
    # 4D) Pestaña: Historial de Remitos
    # ——————————————————————————
    with tab_hist:
        st.subheader("Historial de Remitos")
        if df_remitos.empty:
            st.info("Aún no hay remitos registrados.")
        else:
            nombres = df_clients["NOMBRE"].tolist()
            selected_name = st.selectbox("Selecciona Cliente", nombres, key="hist_name")
            client_id = df_clients.loc[df_clients["NOMBRE"] == selected_name, "ID CLIENTE"].iloc[0]
            df_client_rem = df_remitos[df_remitos["ID CLIENTE"] == client_id]
            if df_client_rem.empty:
                st.warning("No hay remitos para este cliente.")
            else:
                st.dataframe(df_client_rem, use_container_width=True)

if __name__ == "__main__":
    clientes_page()
