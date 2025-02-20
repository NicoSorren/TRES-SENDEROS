import requests
from io import BytesIO

class InvoiceManager:
    """
    Clase que maneja la generación de facturas (o remitos) 
    usando la Invoice Generator API.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = 'https://invoice-generator.com'
        # Por defecto, configuramos el locale para Argentina (es-AR)
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept-Language': 'es-AR'
        }

    def generate_invoice_pdf(self, data: dict) -> BytesIO:
        """
        Llama a la API para generar un PDF de factura y 
        retorna el contenido en un objeto BytesIO.
        """
        response = requests.post(self.url, data=data, headers=self.headers)
        if response.status_code == 200:
            return BytesIO(response.content)  # PDF en memoria
        else:
            raise Exception(f"Error al generar la factura: {response.text}")
