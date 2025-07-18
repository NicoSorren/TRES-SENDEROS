# pages/7_Exportar_a_FUDO.py
import pandas as pd
import streamlit as st
from io import BytesIO
from fudo_manager import build_export_df, upload_export_df, download_fudo_xlsx
import numpy as np
from datetime import datetime


st.set_page_config(page_title="Exportar a Fudo", layout="wide")
st.title("📤 Exportar productos a Fudo")

st.title("🔄 Sincronizar con Fudo")

# URLs y ID de tus Google Sheets
MASTER_URL = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit"
FUDO_URL   = "https://docs.google.com/spreadsheets/d/1xLmOA76L2xwnh0LUfLH813B35Md7cRXdmFCfPMKNxU8/edit"
FUDO_ID    = "1xLmOA76L2xwnh0LUfLH813B35Md7cRXdmFCfPMKNxU8"  # para la descarga

tab_export, tab_import = st.tabs(["🚀 Exportar a Fudo", "📥 Importar desde Fudo"])

# ———————— TAB: Exportar ————————
with tab_export:
    st.header("1️⃣ Exportar productos a Fudo")
    st.markdown(
        """
        – Lee tu hoja maestra, explota fracciones y genera el DataFrame de exportación.  
        – Sincroniza la pestaña **Productos** y descarga el XLSX listo para Fudo.
        """
    )

    # Siempre leer en vivo
    df_export = build_export_df(MASTER_URL, FUDO_URL)

    st.subheader("Vista previa del export")
    st.dataframe(df_export, use_container_width=True)

    if st.button("🔄 Sincronizar y descargar", key="export_sync"):
        with st.spinner("Preparando export…"):
            # Volver a generar para garantizar la última versión
            df_export = build_export_df(MASTER_URL, FUDO_URL)

            upload_export_df(df_export, FUDO_URL)
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            xlsx_bytes = download_fudo_xlsx(FUDO_ID, st.secrets["gcp_service_account"]["json"])
            filename = f"export_fudo_{now}.xlsx"

            st.success("✅ Google Sheet de Fudo actualizado.")
            st.download_button(
                "⬇️ Descargar XLSX para Fudo",
                data=xlsx_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_export"
            )

# … tus constantes y tabs …

with tab_import:
    st.header("2️⃣ Importar XLSX oficial de Fudo")
    st.markdown(
        """
        – Sube el archivo `.xlsx` que descargaste desde Fudo (pestaña Productos).  
        – Volcará **exactamente** esos valores a la hoja de Productos.
        """
    )

    uploaded_file = st.file_uploader("Selecciona el XLSX de Fudo", type=["xlsx"])
    if uploaded_file:
        # 1) Leemos TODO como texto
        df_import = pd.read_excel(uploaded_file, sheet_name="Productos", dtype=str)

        # 2) Limpiamos miles y convertimos SOLO ID, Precio* y Costo
        for col in ["ID\n(Uso interno)", "Precio*", "Costo"]:
            if col in df_import.columns:
                df_import[col] = (
                    df_import[col]
                      .str.replace(",", "", regex=False)  # quita separador de miles
                      .fillna("0")                         # vacíos → "0"
                )
                df_import[col] = pd.to_numeric(df_import[col], errors="coerce") \
                                    .fillna(0) \
                                    .astype(int)

        # 3) Para “Posición”, simplemente rellenamos vacíos con cadena
        if "Posición" in df_import.columns:
            df_import["Posición"] = df_import["Posición"].fillna("").astype(str)

        # 4) Vista previa
        st.subheader("Vista previa de la importación")
        st.dataframe(df_import, use_container_width=True)

        # 5) Subida final
        if st.button("🔄 Sincronizar y descargar", key="export_download"):
          with st.spinner("Actualizando Google Sheet de Fudo…"):
              try:
                  # 1) Hacemos una copia
                  df_to_upload = df_import.copy()

                  # 2) Convertimos ID, Precio* y Costo a int como ya tenías:
                  for col in ["ID\n(Uso interno)", "Precio*", "Costo"]:
                      if col in df_to_upload.columns:
                          df_to_upload[col] = df_to_upload[col].astype(str).fillna("")
                          # Ahora quitas comas y espacios
                          df_to_upload[col] = df_to_upload[col].str.replace(",", "", regex=False).str.strip()
                          # Finalmente conviertes a número
                          df_to_upload[col] = (
                              pd.to_numeric(df_to_upload[col], errors="coerce")
                                .fillna(0)
                                .astype(int)
                          )

                  # 3) Para “Posición”, lo dejamos en cadena vacía si es NaN
                  if "Posición" in df_to_upload.columns:
                      df_to_upload["Posición"] = df_to_upload["Posición"].fillna("").astype(str)

                  # 4) **Reemplazamos cualquier otro NaN** del DataFrame
                  df_to_upload = df_to_upload.fillna("")

                  # (Opcional, para verificar que ya no quede nada)
                  st.write("Nulos restantes:", df_to_upload.isna().sum())

                  # 5) Finalmente subimos
                  upload_export_df(df_to_upload, FUDO_URL)
                  st.success("✅ Google Sheet de Fudo sincronizado con éxito.")
              except Exception as e:
                  st.error(f"❌ Error en import: {e}")
                  
# —————— Bloque de Debug para dtypes de ID ——————
with st.expander("🔍 Debug: comparar dtype de ID interno", expanded=False):
    # 1) Subida de archivos
    fudo_file   = st.file_uploader("📥 XLSX oficial de Fudo", type=["xlsx"], key="dbg_fudo")
    export_file = st.file_uploader("📥 XLSX exportado por app", type=["xlsx"], key="dbg_export")

    if fudo_file and export_file:
        # 2) Leer ambas hojas como object
        df_fudo   = pd.read_excel(fudo_file,   sheet_name="Productos", dtype=object)
        df_export = pd.read_excel(export_file, sheet_name="Productos", dtype=object)

        # 3) Mostrar dtype y tipos únicos de la columna de ID
        st.write("**Original Fudo** — dtype:",
                 df_fudo["ID\n(Uso interno)"].dtype)
        st.write("**Original Fudo** — clases únicas:",
                 {type(x) for x in df_fudo["ID\n(Uso interno)"].unique()})

        st.write("---")

        st.write("**Export app** — dtype:",
                 df_export["ID\n(Uso interno)"].dtype)
        st.write("**Export app** — clases únicas:",
                 {type(x) for x in df_export["ID\n(Uso interno)"].unique()})
    elif fudo_file or export_file:
        st.info("Sube ambos archivos para comparar.")

