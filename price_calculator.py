# price_calculator.py

def convertir_a_gramos(label: str) -> float:
    """
    Convierte un string como '100g' o '1kg' a su valor en gramos.
    Si no puede convertir, retorna None.
    """
    label = str(label).strip().lower()
    if label.endswith("kg"):
        try:
            return float(label.replace("kg", "")) * 1000
        except:
            return None
    elif label.endswith("g"):
        try:
            return float(label.replace("g", ""))
        except:
            return None
    return None

def compute_fraction_price(tipo: str, precio_base: float, frac_label: str) -> float:
    """
    Calcula el precio de un producto dado:
    - tipo: 'KG' o 'UNIDAD'
    - precio_base: precio por 1 kg (si es 'KG') o precio por 1 unidad (si es 'UNIDAD')
    - frac_label: por ejemplo '100g', '250g', '500g', '1kg' o vacío (si es UNIDAD)
    
    Retorna el precio correspondiente a ese fraccionamiento o None si no se pudo calcular.
    """
    tipo = tipo.upper().strip()
    if tipo == "UNIDAD":
        # Si el producto se vende por UNIDAD, no hay fraccionamiento
        return precio_base
    
    # Caso KG
    grams = convertir_a_gramos(frac_label)
    if grams is None:
        return None
    return precio_base * (grams / 1000.0)
