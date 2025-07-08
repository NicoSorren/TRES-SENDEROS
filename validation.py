import re
import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat

def validate_client_data(data):
    """
    Valida los datos mínimos de un cliente:
      - NOMBRE y DIRECCION no vacíos
      - EMAIL con formato básico si se provee
    Retorna un dict de errores por campo.
    """
    errors = {}
    if not data.get("NOMBRE", "").strip():
        errors["NOMBRE"] = "El nombre es obligatorio."
    if not data.get("DIRECCION", "").strip():
        errors["DIRECCION"] = "La dirección no puede quedar vacía."
    #email = data.get("EMAIL", "").strip()
    #if email:
     #   pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
      #  if not re.match(pattern, email):
       #     errors["EMAIL"] = "Formato de email inválido."
    return errors


def normalize_phone(raw: str, default_region: str = "AR") -> str | None:
    """
    Convierte un teléfono crudo en formato E.164 (ej. +541161234567).
    Devuelve None si no es válido.
    """
    try:
        num = phonenumbers.parse(raw, default_region)
        if not phonenumbers.is_valid_number(num):
            return None
        return phonenumbers.format_number(num, PhoneNumberFormat.E164)
    except NumberParseException:
        return None
