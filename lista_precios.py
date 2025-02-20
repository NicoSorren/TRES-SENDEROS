import pandas as pd

def parse_price(price_str):
    """
    Convierte un string con formato "$19.400" a un valor numérico.
    Se elimina el signo "$" y los separadores de miles (puntos).
    """
    price_str = price_str.replace("$", "").strip()
    price_str = price_str.replace(".", "")
    try:
        return float(price_str)
    except Exception as e:
        print(f"Error al parsear el precio '{price_str}': {e}")
        return 0.0

def convertir_a_gramos(label):
    """
    Convierte una etiqueta de fraccionamiento (ej. "100g" o "1kg")
    a su valor en gramos.
    """
    label = label.lower().strip()
    if label.endswith("kg"):
        try:
            return float(label.replace("kg", "").strip()) * 1000
        except:
            return None
    elif label.endswith("g"):
        try:
            return float(label.replace("g", "").strip())
        except:
            return None
    else:
        return None

def calcular_precio(frac_label, precio_base):
    """
    Calcula el precio para un fraccionamiento dado el precio base (por kg).
    """
    gramos = convertir_a_gramos(frac_label)
    if gramos is None:
        return None
    return int(round((gramos / 1000) * precio_base))

def generar_lista_precios(csv_path, encoding='latin1'):
    # Leer el CSV
    df = pd.read_csv(csv_path, encoding=encoding)
    required_cols = ["CATEGORIA", "PRODUCTO", "KG / UNIDAD", "PRECIO VENTA", "FRACCIONAMIENTO"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Falta la columna {col} en el CSV.")

    output_rows = []
    # Agrupar por categoría (manteniendo el orden del CSV)
    grouped = df.groupby("CATEGORIA", sort=False)
    for cat, group in grouped:
        # Determinar los tipos presentes en la categoría
        tipos = group["KG / UNIDAD"].astype(str).str.strip().str.upper().unique().tolist()
        is_mixed = ("KG" in tipos) and ("UNIDAD" in tipos)
        is_pure_kg = (len(tipos) == 1 and tipos[0] == "KG")
        is_pure_unidad = (len(tipos) == 1 and tipos[0] == "UNIDAD")
        
        # Para productos KG de la categoría, se obtiene la unión de los fraccionamientos
        kg_fracs = []
        for idx, row in group.iterrows():
            tipo = str(row["KG / UNIDAD"]).strip().upper()
            if tipo == "KG":
                frac_raw = row["FRACCIONAMIENTO"]
                frac_str = str(frac_raw).strip() if pd.notna(frac_raw) else ""
                if frac_str:
                    for frac in frac_str.split(","):
                        frac = frac.strip()
                        if frac and frac not in kg_fracs:
                            kg_fracs.append(frac)
        # Ordenar los fraccionamientos de menor a mayor según su valor en gramos
        kg_fracs_sorted = sorted(kg_fracs, key=lambda x: convertir_a_gramos(x) if convertir_a_gramos(x) is not None else 0)

        # Definir la cantidad de columnas disponibles para fraccionamientos de KG
        # En categoría mixta se usan 2 columnas (B y C); en categoría pura KG se usan 3 (B, C y D)
        allowed_kg = 2 if is_mixed else 3

        if len(kg_fracs_sorted) > allowed_kg:
            print(f"ADVERTENCIA: En la categoría '{cat}' se encontraron más de {allowed_kg} fraccionamientos para productos KG: {kg_fracs_sorted}. Se utilizarán los primeros {allowed_kg}.")
            kg_fracs_sorted = kg_fracs_sorted[:allowed_kg]

        # Construir la fila de encabezado para la categoría
        header = [cat, "", "", ""]
        if is_pure_unidad:
            header[3] = "UNIDAD"
        elif is_pure_kg:
            # Para categoría pura KG, asignamos de acuerdo a la cantidad
            if len(kg_fracs_sorted) == 1:
                header[3] = kg_fracs_sorted[0]
            elif len(kg_fracs_sorted) == 2:
                header[2] = kg_fracs_sorted[0]
                header[3] = kg_fracs_sorted[1]
            elif len(kg_fracs_sorted) >= 3:
                header[1] = kg_fracs_sorted[0]
                header[2] = kg_fracs_sorted[1]
                header[3] = kg_fracs_sorted[2]
        elif is_mixed:
            # En categoría mixta: columnas B y C para KG, columna D para UNIDAD
            if len(kg_fracs_sorted) == 1:
                header[2] = kg_fracs_sorted[0]
            elif len(kg_fracs_sorted) == 2:
                header[1] = kg_fracs_sorted[0]
                header[2] = kg_fracs_sorted[1]
            header[3] = "UNIDAD"
        else:
            header[3] = ""
        output_rows.append(header)

        # Procesar cada producto en la categoría
        for idx, row in group.iterrows():
            prod = row["PRODUCTO"]
            tipo = str(row["KG / UNIDAD"]).strip().upper()
            precio_base = parse_price(str(row["PRECIO VENTA"]))
            prod_row = [prod, "", "", ""]  # Inicializar la fila con el nombre del producto en la columna A

            if tipo == "UNIDAD":
                # Precio en columna D para productos de UNIDAD
                prod_row[3] = str(int(round(precio_base)))
            elif tipo == "KG":
                frac_raw = row["FRACCIONAMIENTO"]
                frac_str = str(frac_raw).strip() if pd.notna(frac_raw) else ""
                if not frac_str:
                    print(f"ADVERTENCIA: El producto '{prod}' (categoría '{cat}') no tiene fraccionamiento.")
                else:
                    # Extraer, ordenar y limitar los fraccionamientos según el tipo de categoría
                    fracs = [x.strip() for x in frac_str.split(",") if x.strip()]
                    if is_mixed and len(fracs) > 2:
                        print(f"ADVERTENCIA: El producto '{prod}' (categoría '{cat}') tiene más de 2 fraccionamientos: {fracs}.")
                        fracs = fracs[:2]
                    elif is_pure_kg and len(fracs) > 3:
                        print(f"ADVERTENCIA: El producto '{prod}' (categoría '{cat}') tiene más de 3 fraccionamientos: {fracs}.")
                        fracs = fracs[:3]
                    fracs_sorted = sorted(fracs, key=lambda x: convertir_a_gramos(x) if convertir_a_gramos(x) is not None else 0)
                    # Calcular los precios para cada fraccionamiento
                    precios = [calcular_precio(frac, precio_base) for frac in fracs_sorted]
                    if tipo == "KG":
                        if is_mixed:
                            # En categoría mixta: se usan las columnas B y C para KG
                            if len(precios) == 1:
                                prod_row[2] = str(precios[0])
                            elif len(precios) >= 2:
                                prod_row[1] = str(precios[0])
                                prod_row[2] = str(precios[1])
                        else:
                            # En categoría pura KG: se usan columnas B, C y D
                            if len(precios) == 1:
                                prod_row[3] = str(precios[0])
                            elif len(precios) == 2:
                                prod_row[2] = str(precios[0])
                                prod_row[3] = str(precios[1])
                            elif len(precios) >= 3:
                                prod_row[1] = str(precios[0])
                                prod_row[2] = str(precios[1])
                                prod_row[3] = str(precios[2])
            else:
                # Si el tipo no es reconocido, se deja la fila sin cambios
                pass

            output_rows.append(prod_row)

    df_out = pd.DataFrame(output_rows, columns=["CATEGORIA / PRODUCTO", "COL B", "COL C", "COL D"])
    return df_out

if __name__ == "__main__":
    archivo_csv = "LISTA PRECIOS - PRODUCTOS (4).csv"
    df_resultado = generar_lista_precios(archivo_csv, encoding="latin1")
    print(df_resultado)
    df_resultado.to_csv("estructura_listaprecios.csv", index=False, encoding="utf-8-sig")
