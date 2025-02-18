import pandas as pd
import re
from collections import defaultdict

# --------------------------
# CONFIGURACIÓN GENERAL
# --------------------------
INPUT_CSV = 'LISTA PRECIOS - PRODUCTOS.csv'   # Archivo de entrada
OUTPUT_CSV = 'productos_tiendanube.csv'       # Archivo de salida
ENCODING = 'utf-8'                            # Ajusta si tu archivo usa otro encoding

MOSTRAR_EN_TIENDA = 'SÍ'
ENVIO_SIN_CARGO = 'SÍ'
PRODUCTO_FISICO = 'SÍ'
SEXO = 'Unisex'
RANGO_EDAD = ''
ALTO = 0
ANCHO = 0
PROFUNDIDAD = 0

# --------------------------
# VARIABLES GLOBALES PARA CATE
# --------------------------
categoria_code_mapping = {}  # Mapea nombre de categoría a código único
used_categoria_codes = {}    # Mapea código usado a categoría

def generar_codigo_categoria(categoria):
    """
    Genera un código único para la categoría.
    Se parte de las primeras 3 letras (sin espacios, en mayúscula) y se extiende si ya existe.
    """
    cat = categoria.strip().upper().replace(" ", "")
    # Si ya está asignado para esta categoría, retornarlo.
    if categoria in categoria_code_mapping:
        return categoria_code_mapping[categoria]
    
    # Empezar con 3 letras (o lo que tenga si es más corto)
    length = 3 if len(cat) >= 3 else len(cat)
    code_candidate = cat[:length]
    
    # Extender el código si ya existe asignado a otra categoría.
    while True:
        if code_candidate not in used_categoria_codes:
            used_categoria_codes[code_candidate] = categoria
            categoria_code_mapping[categoria] = code_candidate
            return code_candidate
        else:
            # Si ya está asignado a esta misma categoría, retornarlo.
            if used_categoria_codes[code_candidate] == categoria:
                categoria_code_mapping[categoria] = code_candidate
                return code_candidate
            # Si se puede extender, aumentar la longitud.
            if length < len(cat):
                length += 1
                code_candidate = cat[:length]
            else:
                # Si ya usamos todo el nombre, agregar un sufijo numérico
                suffix = 1
                while f"{code_candidate}{suffix}" in used_categoria_codes:
                    suffix += 1
                new_code = f"{code_candidate}{suffix}"
                used_categoria_codes[new_code] = categoria
                categoria_code_mapping[categoria] = new_code
                return new_code

# --------------------------
# FUNCIONES DE UTILIDAD
# --------------------------

def parse_price(price_str):
    """
    Convierte la cadena de precio en float.
    - Elimina símbolos de moneda como '$'.
    - Elimina separadores de miles (p.ej. si "7.400" significa 7400).
    - Sustituye comas por puntos si existieran (ej. 7,4 -> 7.4).
    """
    price_str = price_str.replace('$', '').strip()
    price_str = price_str.replace('.', '')  # Asumiendo que "7.400" significa 7400
    # price_str = price_str.replace(',', '.')  # Descomenta si usas coma como decimal
    return float(price_str)

def generar_slug(nombre):
    """
    Genera un identificador de URL a partir del nombre del producto.
    Elimina acentos, signos y reemplaza espacios por guiones.
    """
    nombre = nombre.lower().strip()
    nombre = re.sub(r'[áàä]', 'a', nombre)
    nombre = re.sub(r'[éèë]', 'e', nombre)
    nombre = re.sub(r'[íìï]', 'i', nombre)
    nombre = re.sub(r'[óòö]', 'o', nombre)
    nombre = re.sub(r'[úùü]', 'u', nombre)
    nombre = re.sub(r'[^a-z0-9\s-]', '', nombre)
    nombre = re.sub(r'\s+', '-', nombre)
    return nombre

def generar_sku(nombre_producto, categoria, variante, used_skus):
    """
    Genera un SKU siguiendo la estructura:
    CATE-TIPO-FRACC
    Donde:
      - CATE: código único de la categoría (generado dinámicamente)
      - TIPO: primeras 4 letras significativas del nombre del producto
      - FRACC: código de fraccionamiento (250G, 500G, 1KG o UNI)
    Y asegura su unicidad en used_skus.
    """
    # Código de categoría único
    cate_code = generar_codigo_categoria(categoria)
    
    # Procesar nombre del producto: quitar espacios y tomar primeras 4 letras
    nombre_norm = re.sub(r'\s+', '', nombre_producto).upper()
    tipo_code = nombre_norm[:4] if len(nombre_norm) >= 4 else nombre_norm
    
    # Código de fraccionamiento
    if variante.lower() == '1kg':
        frac_code = '1KG'
    elif variante.lower() == 'unidad':
        frac_code = 'UNI'
    else:
        frac_code = re.sub(r'[^0-9]', '', variante) + 'G'
    
    # SKU base
    base_sku = f"{cate_code}-{tipo_code}-{frac_code}"
    
    # Asegurar unicidad
    used_skus[base_sku] += 1
    if used_skus[base_sku] > 1:
        return f"{base_sku}{used_skus[base_sku]}"
    else:
        return base_sku

def calcular_variantes(precio_base):
    """
    Para productos vendidos por KG, genera tres variantes:
    250g, 500g, 1kg, con su precio, peso y costo correspondientes.
    """
    variantes = []
    for frac, factor, peso in [('250g', 0.25, 0.250), ('500g', 0.50, 0.500), ('1kg', 1.0, 1.000)]:
        precio = round(precio_base * factor, 2)
        variantes.append({
            'fraccionamiento': frac,
            'precio': precio,
            'peso': peso,
            'costo': precio
        })
    return variantes

def procesar_stock(stock_val):
    """
    - '-' => stock ilimitado (dejar en blanco)
    - '0' => sin stock
    - Otro número => stock específico
    """
    stock_val = str(stock_val).strip()
    if stock_val == '-':
        return '-'  # Tienda Nube interpreta vacío como stock ilimitado
    else:
        return stock_val

# --------------------------
# PROCESAMIENTO PRINCIPAL
# --------------------------

def procesar_producto(producto, used_skus):
    """
    Genera registros (filas) para un producto según sea KG o UNIDAD,
    usando la nueva generación de SKU que incorpora el código de categoría
    y asegurando unicidad con used_skus.
    """
    registros = []

    nombre = str(producto['PRODUCTO']).strip()
    precio_str = str(producto['PRECIO VENTA']).strip()
    tipo = str(producto['KG / UNIDAD']).strip().upper()  # 'KG' o 'UNIDAD'
    categoria = str(producto['CATEGORIA']).strip()
    marca = str(producto.get('MARCA', '')).strip()
    stock_str = str(producto.get('STOCK', '')).strip()

    # Convertir precio a float
    precio_base = parse_price(precio_str)

    # Procesar stock
    stock_final = procesar_stock(stock_str)

    # Slug y descripciones
    slug = generar_slug(nombre)
    descripcion = f"Descripción corta de {nombre}"
    tags = generar_slug(nombre).replace('-', ' ')

    if tipo == 'KG':
        variantes = calcular_variantes(precio_base)
        for var in variantes:
            frac = var['fraccionamiento']
            precio = var['precio']
            peso = var['peso']
            costo = var['costo']

            # Generar SKU con la nueva estructura
            sku = generar_sku(nombre, categoria, frac, used_skus)

            registro = [
                slug,                          # Identificador de URL
                nombre,                        # Nombre
                categoria,                     # Categorías
                "Fraccionamiento",             # Nombre de propiedad 1
                frac,                          # Valor de propiedad 1
                "", "", "", "",                # Propiedades 2 y 3 vacías
                precio,                        # Precio
                "",                            # Precio promocional
                peso,                          # Peso (kg)
                ALTO,                          # Alto (cm)
                ANCHO,                         # Ancho (cm)
                PROFUNDIDAD,                   # Profundidad (cm)
                stock_final,                   # Stock
                sku,                           # SKU único
                "",                            # Código de barras
                MOSTRAR_EN_TIENDA,
                ENVIO_SIN_CARGO,
                descripcion,
                tags,
                f"{nombre} {frac} - {categoria}",
                f"Compra {nombre} en presentación de {frac}. Envío sin cargo.",
                marca,
                PRODUCTO_FISICO,
                "",
                SEXO,
                RANGO_EDAD,
                costo
            ]
            registros.append(registro)

    elif tipo == 'UNIDAD':
        sku = generar_sku(nombre, categoria, 'Unidad', used_skus)
        precio = round(precio_base, 2)
        registro = [
            slug,
            nombre,
            categoria,
            "Presentación",
            "Unidad",
            "", "", "", "",
            precio,
            "",
            1,  # Peso (kg) -> ajusta si corresponde
            ALTO,
            ANCHO,
            PROFUNDIDAD,
            stock_final,
            sku,
            "",
            MOSTRAR_EN_TIENDA,
            ENVIO_SIN_CARGO,
            descripcion,
            tags,
            f"{nombre} - {categoria}",
            f"Compra {nombre}. Envío sin cargo.",
            marca,
            PRODUCTO_FISICO,
            "",
            SEXO,
            RANGO_EDAD,
            precio
        ]
        registros.append(registro)

    else:
        print(f"Tipo no reconocido: {tipo} para producto '{nombre}'")

    return registros

def main():
    # Leer el CSV de entrada
    df = pd.read_csv(INPUT_CSV, encoding=ENCODING)

    # Diccionario para controlar SKUs usados
    used_skus = defaultdict(int)

    csv_registros = []

    for _, row in df.iterrows():
        producto_valor = str(row.get('PRODUCTO', '')).strip()
        if producto_valor:
            registros = procesar_producto(row, used_skus)
            csv_registros.extend(registros)

    # Columnas requeridas por Tienda Nube (de A a AD)
    columnas = [
        "Identificador de URL",
        "Nombre",
        "Categorías",
        "Nombre de propiedad 1",
        "Valor de propiedad 1",
        "Nombre de propiedad 2",
        "Valor de propiedad 2",
        "Nombre de propiedad 3",
        "Valor de propiedad 3",
        "Precio",
        "Precio promocional",
        "Peso (kg)",
        "Alto (cm)",
        "Ancho (cm)",
        "Profundidad (cm)",
        "Stock",
        "SKU",
        "Código de barras",
        "Mostrar en tienda",
        "Envío sin cargo",
        "Descripción",
        "Tags",
        "Título para SEO",
        "Descripción para SEO",
        "Marca",
        "Producto Físico",
        "MPN (Número de pieza del fabricante)",
        "Sexo",
        "Rango de edad",
        "Costo"
    ]

    df_csv = pd.DataFrame(csv_registros, columns=columnas)
    df_csv.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
    print(f"Archivo CSV generado: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
