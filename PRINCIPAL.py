# Bienvenida.py

import streamlit as st
from PIL import Image
from datetime import date

# PRINCIPAL.py (arriba del todo, tras los imports)  
from sheet_connector import get_data_from_sheet  
from fudo_manager import SheetConnector  # o, si prefieres, importa get_products directo  

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1i4kafAJQvVkKbkVIo5LldsN7R-ApeWhHDKZjBvsguoo/edit"
FUDO_URL       = "https://docs.google.com/spreadsheets/d/1xLmOA76L2xwnh0LUfLH813B35Md7cRXdmFCfPMKNxU8/edit"  

# 1) Cargar hoja MAESTRA una única vez en sesión
if "df" not in st.session_state:
    df_master = get_data_from_sheet(SPREADSHEET_URL)
    st.session_state.df = df_master.copy()

# 2) Cargar hoja de FUDO una única vez en sesión
if "df_fudo" not in st.session_state:
    fudo_conn = SheetConnector(FUDO_URL)
    st.session_state.df_fudo = fudo_conn.get_products().copy()
    
# 1) Configuración de la página
st.set_page_config(
    page_title="Tres Senderos – Bienvenida",
    page_icon="🍃",
    layout="centered"
)

# 2) Estilos CSS para la cita
st.markdown(
    """
    <style>
    .main > div.block-container {
        max-width: 800px; margin: auto; padding-top: 2rem;
    }
    .quote-container {
        background-color: #f7f7f7; padding: 1.5rem;
        border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem;
    }
    .quote-text { font-size:1.75rem; font-weight:500; color:#333; line-height:1.3; margin-bottom:0.5rem; }
    .quote-author { font-size:1.2rem; color:#555; text-align:right; font-style:italic; }
    .stButton>button { background-color:#2E8B57; color:white; border:none; }
    .stButton>button:hover { background-color:#276746; }
    </style>
    """,
    unsafe_allow_html=True
)

# 3) Logo y título
logo = Image.open("Logo TRES SENDEROS.jpg")
st.image(logo, width=120)
st.title("¡Bienvenido a Tres Senderos!")

# 4) Lista de 25 citas motivacionales en español
QUOTES_ES = [
    ("El único modo de hacer un gran trabajo es amar lo que haces.", "Steve Jobs"),
    ("No dejes para mañana lo que puedas hacer hoy.", "Benjamin Franklin"),
    ("Nunca sueñes tu vida, vive tu sueño.", "Mark Twain"),
    ("La única forma de alcanzar lo imposible es creer que es posible.", "Charles Kingsleigh"),
    ("Cuanto más duro trabajo, más suerte tengo.", "Thomas Jefferson"),
    ("El éxito es caminar de fracaso en fracaso sin perder el entusiasmo.", "Winston Churchill"),
    ("Cree que puedes y ya estás a mitad de camino.", "Theodore Roosevelt"),
    ("La disciplina es el puente entre metas y logros.", "Jim Rohn"),
    ("Sin riesgo no hay recompensa.", "Anonimo"),
    ("Tu futuro se crea con lo que haces hoy, no mañana.", "Robert Kiyosaki"),
    ("No cuentes los días, haz que los días cuenten.", "Muhammad Ali"),
    ("La vida comienza donde termina tu zona de confort.", "Neale Donald Walsch"),
    ("Si quieres volar, renuncia a todo aquello que te pese.", "Toni Morrison"),
    ("El éxito no es la clave de la felicidad; la felicidad es la clave del éxito.", "Albert Schweitzer"),
    ("No es lo que tienes, sino lo que haces con lo que tienes.", "Zig Ziglar"),
    ("La creatividad es inteligencia divirtiéndose.", "Albert Einstein"),
    ("El fracaso es la oportunidad de comenzar de nuevo con más inteligencia.", "Henry Ford"),
    ("No esperes. El tiempo nunca será justo.", "Napoleon Hill"),
    ("Lo que no te mata te hace más fuerte.", "Friedrich Nietzsche"),
    ("La mejor venganza es un éxito rotundo.", "Frank Sinatra"),
    ("Haz de tu vida un sueño, y de tu sueño una realidad.", "Antoine de Saint-Exupéry"),
    ("Donde una puerta se cierra, otra se abre.", "Miguel de Cervantes"),
    ("Si crees que puedes o que no puedes, tienes razón.", "Henry Ford"),
    ("La persistencia es la cualidad de vencer.", "Napoleon Hill"),
    ("Convierte los obstáculos en peldaños hacia tus metas.", "Anonimo")
]

# 5) Selección según la fecha
idx = date.today().toordinal() % len(QUOTES_ES)
quote, author = QUOTES_ES[idx]

# 6) Mostrar la cita estilizada
st.markdown("### ✨ Cita del Día")
st.markdown(f"""
<div class="quote-container">
  <div class="quote-text">“{quote}”</div>
  <div class="quote-author">— {author}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# 7) Botón para ir a Gestión de Productos
if st.button("➡️ Ir a Gestión de Productos"):
    st.experimental_set_query_params(page="Gestionar_Productos")
