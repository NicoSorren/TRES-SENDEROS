# sku_generator.py
import re

def generar_codigo_categoria(categoria, cat_codes):
    """
    Genera un código de categoría evitando colisiones.
    - 'cat_codes' es un dict { nombre_categoria: codigo_generado } o un dict con { codigo_generado } usados.
    - Si la categoría ya tiene un código asignado, lo reutiliza.
    - Si no, comienza con las 3 primeras letras y expande hasta que no haya colisión.
    """
    # Normalizamos la categoría (sin espacios, en mayúsculas)
    cat_upper = re.sub(r"\s+", "", categoria.strip().upper())
    
    # Si ya asignamos un código antes a esta categoría, lo devolvemos
    for cat_name, code_asignado in cat_codes.items():
        if cat_name.strip().lower() == categoria.strip().lower():
            return code_asignado

    # Intentar con longitud creciente: 3, 4, 5...
    for length in range(3, len(cat_upper) + 1):
        candidate = cat_upper[:length]
        # Verificamos si candidate ya está en uso
        if candidate not in cat_codes.values():
            cat_codes[categoria] = candidate
            return candidate
    
    # Si no encontramos uno libre, usamos todo cat_upper
    cat_codes[categoria] = cat_upper
    return cat_upper

def procesar_fraccionamientos(fraccionamiento_str, tipo):
    """
    Devuelve una lista de códigos de fraccionamiento. 
    - Si 'tipo' es UNIDAD y no hay fraccionamiento, se usa ["UNI"].
    - Si 'tipo' es KG, se procesan valores como '100g, 250g' -> ['100G', '250G'].
    """
    # Si es UNIDAD y no hay fraccionamiento, asignamos 'UNI'
    if tipo.upper() == "UNIDAD":
        # Si el fraccionamiento está vacío, lo consideramos 'UNIDAD' o 'UNI'
        if not fraccionamiento_str.strip():
            return ["UNI"]
        else:
            # Si el usuario ingresó algo, se procesa igual
            return [fraccionamiento_str.strip().upper()]
    
    # Caso KG
    fracs = []
    for frac in fraccionamiento_str.split(","):
        frac = frac.strip().lower()
        if frac == '1kg':
            fracs.append("1KG")
        elif frac == 'unidad':
            fracs.append("UNI")  # Raro que un KG sea 'unidad', pero por si acaso
        else:
            # Extrae dígitos y añade 'G'
            num = re.sub(r'[^0-9]', '', frac)
            if num:
                fracs.append(num + "G")
    # Si no hay nada, retornamos [""] o []
    return fracs if fracs else [""]

def generar_sku(nombre_producto, categoria, fraccionamiento, tipo, used_skus, cat_codes):
    """
    Genera un SKU para cada fraccionamiento y los concatena con comas.
    Estructura de cada SKU: CATE-TIPO-FRACC
      - CATE: Código de la categoría (evita colisiones con generar_codigo_categoria)
      - TIPO: Primeras 4 letras del producto, sin espacios
      - FRACC: Código del fraccionamiento (p.ej. '100G', 'UNI')
    
    'used_skus' es un dict que lleva el conteo de SKUs base para asegurar unicidad (baseSKU, conteo).
    'cat_codes' es un dict que lleva {categoria: codigo_categoria_usado}.
    """
    # 1) Generar/obtener código de categoría sin colisiones
    cate_code = generar_codigo_categoria(categoria, cat_codes)
    
    # 2) Normalizar nombre producto (primeras 4 letras)
    nombre_norm = re.sub(r"\s+", "", nombre_producto).upper()
    tipo_code = nombre_norm[:4] if len(nombre_norm) >= 4 else nombre_norm
    
    # 3) Procesar fraccionamientos según tipo
    fracs = procesar_fraccionamientos(fraccionamiento, tipo)
    
    sku_list = []
    for frac_code in fracs:
        # Si frac_code está vacío, podría quedar "FRU-MANZ-" => no ideal, pero depende de tu preferencia
        base_sku = f"{cate_code}-{tipo_code}-{frac_code}".rstrip("-")  # si frac_code = "" => quita guion final
        used_skus[base_sku] += 1
        if used_skus[base_sku] > 1:
            sku_val = f"{base_sku}{used_skus[base_sku]}"
        else:
            sku_val = base_sku
        sku_list.append(sku_val)
    
    return ", ".join(sku_list)
