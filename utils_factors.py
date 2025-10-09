# utils_factors.py
def parse_factor(value):
    """
    Parsea el factor a float SIN corregirlo.
    Acepta '1,50', '1.50', '150%', 1.5, etc.
    Devuelve float o None si no puede parsear.
    """
    if value is None:
        return None

    # ya float/int
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except Exception:
            return None

    # texto
    s = str(value).strip().replace("$", "").replace(" ", "")
    if not s:
        return None

    is_percent = s.endswith("%")
    if is_percent:
        s = s[:-1]

    # normalizar solo separadores, NUNCA escalar
    if "," in s and "." in s:
        # '1.234,56' -> '1234.56'
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    # si no hay coma, dejamos '.' como separador decimal

    try:
        x = float(s)
    except ValueError:
        return None

    if is_percent:
        x = x / 100.0

    return x


def is_factor_valid(x, min_ok=1.0, max_ok=2.0):
    """
    True si x está en [min_ok, max_ok]
    """
    try:
        xf = float(x)
    except Exception:
        return False
    return (min_ok <= xf <= max_ok)
