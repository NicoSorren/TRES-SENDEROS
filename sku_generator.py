# sku_generator.py
import re
from collections import defaultdict
from typing import Dict, Any

# — Globales para control de códigos y conteos —
used_skus: defaultdict = defaultdict(int)
cat_codes: Dict[str, str]    = {}
subcat_codes: Dict[Any, str] = {}

def init_existing_skus(df, sku_column: str = "SKU"):
    """
    Limpia e inicializa `used_skus` a partir de la columna de SKUs de un DataFrame.
    Cada vez que recargues tu catálogo (p.ej. al iniciar la app), llama a esta función:
        sku_generator.init_existing_skus(st.session_state.df)
    para que los contadores internos reflejen los SKUs ya persistidos.
    """
    used_skus.clear()
    for cell in df[sku_column].fillna("").astype(str):
        for sku in [s.strip() for s in cell.split(",") if s.strip()]:
            used_skus[sku] += 1

def get_duplicate_skus() -> Dict[str, int]:
    """
    Retorna un dict {sku: conteo} con los SKUs que aparecen más de una vez
    en el contador interno `used_skus`. Úsalo para mostrar advertencias
    si algo salió mal en la generación.
    """
    return {sku: cnt for sku, cnt in used_skus.items() if cnt > 1}


def generar_codigo_categoria(categoria: str) -> str:
    """
    Genera (y memo­riza) un código corto para la categoría,
    evitando colisiones con otros códigos de categoría.
    """
    cat_norm = re.sub(r"\s+", "", categoria.strip()).upper()
    # Si ya existe, lo reutilizamos
    if categoria in cat_codes:
        return cat_codes[categoria]
    # Buscamos la longitud mínima (3+) que no choque
    for L in range(3, len(cat_norm) + 1):
        candidato = cat_norm[:L]
        if candidato not in cat_codes.values():
            cat_codes[categoria] = candidato
            return candidato
    # Fallback: todo el nombre
    cat_codes[categoria] = cat_norm
    return cat_norm

def generar_codigo_subcategoria(categoria: str, subcat: str) -> str:
    """
    Genera (y memo­riza) un código corto para la subcategoría,
    evitando colisiones dentro de la misma categoría.
    """
    key = (categoria, subcat)
    sub_norm = re.sub(r"\s+", "", subcat.strip()).upper() or "SS"
    if key in subcat_codes:
        return subcat_codes[key]
    # Probamos longitudes crecientes (2+)
    for L in range(2, len(sub_norm) + 1):
        candidato = sub_norm[:L]
        if candidato not in subcat_codes.values():
            subcat_codes[key] = candidato
            return candidato
    subcat_codes[key] = sub_norm
    return sub_norm

def procesar_fraccionamientos(frac_str: str, tipo: str) -> list[str]:
    """
    Devuelve lista de sufijos de fracción (por ejemplo ["100G","250G","1KG","UNI"])
    según el tipo (KG vs UNIDAD).
    """
    t = str(tipo).strip().upper()
    s = str(frac_str or "").lower()

    if t in ("UNIDAD", "UNI", "UND") and not s:
        return ["UNI"]

    resultados = []
    for part in s.split(","):
        p = part.strip()
        if not p:
            continue
        # Ejemplo: "250g" → "250G", "1kg" → "1KG", "unidad" → "UNI"
        if p.endswith("kg"):
            resultados.append(p.replace("kg","KG").upper())
        elif p.endswith("g"):
            resultados.append(p.replace("g","G").upper())
        elif "unidad" in p:
            resultados.append("UNI")
        else:
            # cualquier número que quede lo tomamos como gramos
            num = re.sub(r"\D+", "", p)
            if num:
                resultados.append(f"{num}G")
    return resultados or [""]

def generar_sku(
    nombre_producto: str,
    categoria: str,
    subcategoria: str,
    fraccionamiento: str,
    tipo: str
) -> str:
    """
    Genera SKUs en forma de "CATE-SUBC-PROD-FRACC", añade sufijo numérico
    si el base ya existía. Antes de usarla, llama a init_existing_skus(df).
    """
    # 1) Inicializa códigos
    cate_code = generar_codigo_categoria(categoria)
    subc_code = generar_codigo_subcategoria(categoria, subcategoria or "")

    # 2) Normaliza producto
    prod_norm = re.sub(r"\s+", "", nombre_producto).upper()
    prod_code = prod_norm[:4] if len(prod_norm) >= 4 else prod_norm

    # 3) Calcula fracciones
    fracs = procesar_fraccionamientos(fraccionamiento, tipo)

    skus = []
    for frac in fracs:
        base = "-".join(p for p in [cate_code, subc_code, prod_code, frac] if p).rstrip("-")
        # 4) Incrementa contador y genera con sufijo si ya existía
        used_skus[base] += 1
        count = used_skus[base]
        sku_final = f"{base}{count}" if count > 1 else base
        skus.append(sku_final)

    # 5) (Opcional) Verifica duplicados tras generar
    dup = get_duplicate_skus()
    if dup:
        # podrías levantar una excepción, mostrar un warn o log
        print("⚠️ Duplicados detectados tras generar SKU:", dup)

    return ", ".join(skus)