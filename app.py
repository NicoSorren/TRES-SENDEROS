import streamlit as st
import pandas as pd

st.title("Edición de Productos por Categoría")

# Leer el CSV (ajusta la ruta o nombre de archivo según corresponda)
df = pd.read_csv("LISTA PRECIOS - PRODUCTOS (3).csv", encoding="utf-8")

# Opcional: Mostrar los datos completos para verificar
# st.dataframe(df)

# Asegurarse de que las columnas críticas estén limpias
df["CATEGORIA"] = df["CATEGORIA"].astype(str).str.strip()
df["PRODUCTO"] = df["PRODUCTO"].astype(str).str.strip()
df["PRECIO VENTA"] = pd.to_numeric(df["PRECIO VENTA"], errors="coerce").fillna(0)
df["MARCA"] = df["MARCA"].astype(str).str.strip()

# Obtener la lista única de categorías
categorias = df["CATEGORIA"].unique()

# Para cada categoría, crear un expander con los productos
for cat in categorias:
    with st.expander(f"Categoría: {cat}"):
        df_cat = df[df["CATEGORIA"] == cat]
        for index, row in df_cat.iterrows():
            st.markdown(f"**Producto:** {row['PRODUCTO']}")
            col1, col2 = st.columns(2)
            with col1:
                new_price = st.number_input(
                    f"Precio Venta",
                    value=float(row["PRECIO VENTA"]),
                    step=1.0,
                    key=f"precio_{index}"
                )
            with col2:
                new_brand = st.text_input(
                    f"Marca",
                    value=row["MARCA"],
                    key=f"marca_{index}"
                )
            # Actualizar los valores en el DataFrame si se quiere persistir
            df.at[index, "PRECIO VENTA"] = new_price
            df.at[index, "MARCA"] = new_brand

st.write("### Datos Actualizados")
st.dataframe(df)
