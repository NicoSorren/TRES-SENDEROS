import streamlit as st
import pandas as pd
import unicodedata
import re
from io import BytesIO

st.set_page_config(page_title="Actualizar todos los productos Fudo", layout="wide")
st.title("✏️ Actualizar archivo Fudo para TODOS los productos donde hay cambios")

fudo_file = st.file_uploader("Subí el archivo Fudo original (.xlsx, hoja 'Productos')", type=["xlsx"])

if "df_fudo" not in st.session_state:
    st.error("No está inicializada tu hoja 'copia Fudo' en la app (st.session_state.df_fudo).")
    st.stop()

df_template = st.session_state.df_fudo.copy()

def limpiar_sku(s):
    s = str(s)
    s = s.replace('\n','').replace('\r','').replace('\t','').replace('\xa0', '')
    s = s.strip().upper().replace("–", "-").replace("—", "-")
    return s

def buscar_columna(df, base):
    def normalizar_col(c):
        c = unicodedata.normalize('NFKC', c)
        c = c.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        c = re.sub(r'\s+', ' ', c)
        c = c.lower().replace("í", "i")
        return c.strip()
    base_norm = normalizar_col(base)
    for col in df.columns:
        if base_norm in normalizar_col(col):
            return col
    return None

if fudo_file:
    xls = pd.ExcelFile(fudo_file)
    hojas = xls.sheet_names
    if "Productos" not in hojas:
        st.error("El archivo no tiene la hoja 'Productos'.")
        st.stop()
    df_fudo = pd.read_excel(xls, sheet_name="Productos")

    if "Código" not in df_fudo.columns or "Código" not in df_template.columns:
        st.error("Faltan la columna 'Código' en alguna hoja.")
        st.stop()

    df_fudo["Código"] = df_fudo["Código"].apply(limpiar_sku)
    df_template["Código"] = df_template["Código"].apply(limpiar_sku)
    df_fudo = df_fudo.set_index("Código")
    df_template = df_template.set_index("Código")
    df_fudo = df_fudo[~df_fudo.index.duplicated(keep='first')]
    df_template = df_template[~df_template.index.duplicated(keep='first')]

    # Buscar nombres reales de columna "Activo"
    col_activo_fudo = buscar_columna(df_fudo, "activo")
    col_activo_template = buscar_columna(df_template, "activo")

    # Campos a modificar
    campos_a_modificar = ["Precio*", "Costo", col_activo_fudo]

    productos_cambiados = []

    # --- ACTUALIZA TODOS LOS PRODUCTOS EN COMÚN ---
    for sku in set(df_fudo.index) & set(df_template.index):
        for campo in campos_a_modificar:
            valor_fudo = df_fudo.at[sku, campo] if campo in df_fudo.columns else ""
            # Usá el nombre correcto en df_template
            if campo == col_activo_fudo:
                valor_app = df_template.at[sku, col_activo_template] if col_activo_template in df_template.columns else ""
            else:
                valor_app = df_template.at[sku, campo] if campo in df_template.columns else ""
            if pd.notnull(valor_app) and str(valor_fudo) != str(valor_app):
                dtype_original = df_fudo[campo].dtype
                if pd.api.types.is_integer_dtype(dtype_original):
                    if pd.isna(valor_app) or valor_app == "":
                        valor_app_cast = pd.NA
                    else:
                        valor_app_cast = int(float(valor_app))
                elif pd.api.types.is_float_dtype(dtype_original):
                    valor_app_cast = float(valor_app) if not pd.isna(valor_app) and valor_app != "" else float("nan")
                else:
                    valor_app_cast = valor_app
                productos_cambiados.append({
                    "SKU": sku,
                    "Campo": campo,
                    "Valor Fudo (antes)": valor_fudo,
                    "Valor App (nuevo)": valor_app
                })
                df_fudo.at[sku, campo] = valor_app_cast

    # ---- MOSTRAR RESUMEN DE CAMBIOS ----
    if productos_cambiados:
        st.success(f"Se actualizaron {len(productos_cambiados)} campos en total.")
        df_cambios = pd.DataFrame(productos_cambiados)
        st.dataframe(df_cambios, use_container_width=True)
        # Botón para descargar el reporte de cambios
        csv = df_cambios.to_csv(index=False).encode('utf-8')
        st.download_button("Descargar cambios (.csv)", data=csv, file_name="cambios_actualizados.csv", mime="text/csv")
    else:
        st.info("No hay cambios en precios, costos ni estado activo entre Fudo y tu spreadsheet.")

    # ----------- LIMPIEZA Y EXPORTACIÓN -----------
    if st.button("Descargar archivo Fudo actualizado (.xlsx)"):
        output = BytesIO()

        # Código como columna
        if df_fudo.index.name == "Código":
            df_fudo = df_fudo.reset_index()
        if "Código" not in df_fudo.columns:
            st.error("La columna 'Código' no existe en el DataFrame antes de exportar.")
            st.stop()

        # Limpiar y dejar únicos los Códigos de producto
        def limpiar_codigo(s):
            s = str(s).strip().upper().replace("–", "-").replace("—", "-")
            s = s.replace('\n','').replace('\r','').replace('\t','').replace('\xa0', '')
            return s
        df_fudo["Código"] = df_fudo["Código"].apply(limpiar_codigo)
        df_fudo = df_fudo.drop_duplicates(subset=["Código"], keep="first")

        # Limpiar IDs internos (deben ser int o vacío)
        def limpiar_id(val):
            if pd.isna(val) or str(val).strip().lower() in ["", "nan", "none"]:
                return ""
            try:
                n = float(val)
                if n.is_integer():
                    return int(n)
                else:
                    return int(round(n))
            except:
                return ""
        if "ID\n(Uso interno)" in df_fudo.columns:
            df_fudo["ID\n(Uso interno)"] = df_fudo["ID\n(Uso interno)"].apply(limpiar_id)

        # Limpiar y dejar únicos los nombres (sin espacios extra)
        if "Nombre*" in df_fudo.columns:
            df_fudo["Nombre*"] = df_fudo["Nombre*"].astype(str).str.strip()
            df_fudo = df_fudo.drop_duplicates(subset=["Nombre*"], keep="first")

        # Convertir Precios y Costos a numérico (int si es posible, sino float, sino vacío)
        for col in ["Precio*", "Costo"]:
            if col in df_fudo.columns:
                df_fudo[col] = pd.to_numeric(df_fudo[col], errors="coerce").fillna("")

        columnas_texto = ["Categoría*", "Subcategoría", "Nombre*", "Descripción", "Proveedor"]
        for col in columnas_texto:
            if col in df_fudo.columns:
                df_fudo[col] = df_fudo[col].astype(str).str.strip()
                df_fudo[col] = df_fudo[col].replace("nan", "")
                df_fudo[col] = df_fudo[col].astype(object)
        df_fudo = df_fudo.fillna("")

        # Orden final de columnas
        columnas_orden_fudo = [
            "ID\n(Uso interno)", "Categoría*", "Subcategoría", "Código", "Nombre*",
            "Descripción", "Precio*", "Costo", "Proveedor", col_activo_fudo,
            "Favorito\n(SÍ / NO)", "Controlar Stock\n(SÍ / NO)",
            "Permitir vender solo\n(SÍ / NO)", "Posición"
        ]
        # Agregar columnas vacías si faltan
        for col in columnas_orden_fudo:
            if col not in df_fudo.columns:
                df_fudo[col] = ""
        df_fudo = df_fudo[columnas_orden_fudo if set(columnas_orden_fudo).issubset(df_fudo.columns) else [col for col in columnas_orden_fudo if col in df_fudo.columns]]

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for hoja in hojas:
                if hoja == "Productos":
                    df_fudo.to_excel(writer, sheet_name=hoja, index=False)
                else:
                    df_temp = pd.read_excel(xls, sheet_name=hoja)
                    df_temp.to_excel(writer, sheet_name=hoja, index=False)
        output.seek(0)
        st.download_button(
            label="Descargar archivo .xlsx actualizado",
            data=output,
            file_name="fudo_actualizado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Subí el archivo Fudo para actualizar todos los productos.")
