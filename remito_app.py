import streamlit as st
import datetime
from remito_script import cargar_productos, escribir_remito

# Cargar productos desde el archivo Excel
st.title("Generador de Remitos")

productos = cargar_productos()

st.header("Selecciona productos")

# Inicializar lista de productos seleccionados en la sesión
if 'seleccionados' not in st.session_state:
    st.session_state.seleccionados = []

def agregar_producto(producto_seleccionado, cantidad):
    index = int(producto_seleccionado.split('.')[0]) - 1
    cantidad_gr = int(cantidad.replace('kg', '000').replace('g', ''))

    producto = productos[index]
    if 'precio_100gr' in producto:
        precio_unitario = producto['precio_100gr']
        precio_total = (precio_unitario / 100) * cantidad_gr
    elif 'precio_250gr' in producto:
        precio_unitario = producto['precio_250gr'] / 2.5
        precio_total = (producto['precio_250gr'] / 250) * cantidad_gr
    elif 'precio_500gr' in producto:
        precio_unitario = producto['precio_500gr'] / 5
        precio_total = (producto['precio_500gr'] / 500) * cantidad_gr
    elif '1kg' in producto:
        precio_unitario = producto['1kg'] / 10
        precio_total = (producto['1kg'] / 1000) * cantidad_gr
    elif 'unidad' in producto:
        precio_unitario = producto['unidad']
        precio_total = precio_unitario * cantidad_gr

    st.session_state.seleccionados.append({
        "producto": producto['nombre'],
        "peso": cantidad_gr,
        "precio_por_100gr": precio_unitario,
        "precio_total": precio_total
    })

producto_seleccionado = st.selectbox("Elige un producto", [f"{prod['codigo']}. {prod['nombre']}" for prod in productos])
cantidad = st.text_input("Introduce la cantidad en gr o kg (ej: 1000g o 1kg), o cantidad de unidades")

if st.button("Añadir producto"):
    agregar_producto(producto_seleccionado, cantidad)

st.header("Productos seleccionados")
for item in st.session_state.seleccionados:
    st.write(f"{item['producto']} - {item['peso']}g - ${item['precio_total']:.2f}")

st.header("Detalles del cliente")
nombre = st.text_input("Nombre del cliente", key="nombre")
direccion = st.text_input("Dirección", key="direccion")
telefono = st.text_input("Teléfono", key="telefono")
localidad = st.text_input("Localidad", key="localidad")
observaciones = st.text_area("Observaciones", key="observaciones")

descuento_aplica = st.checkbox("¿Aplicar descuento?", key="descuento_aplica")
descuento = 0
if descuento_aplica:
    descuento = st.slider("Porcentaje de descuento", 0, 100, 0, key="descuento")

if st.button("Generar Remito"):
    fecha = datetime.datetime.now().strftime('%Y-%m-%d')
    subtotal = sum(item['precio_total'] for item in st.session_state.seleccionados)
    total_precio_con_descuento = subtotal - (subtotal * (descuento / 100))

    nombre_archivo_excel = escribir_remito(
        nombre, fecha, direccion, telefono, localidad, observaciones, 
        st.session_state.seleccionados, subtotal, descuento, total_precio_con_descuento
    )
    st.success(f"Remito generado para {nombre} con un total de ${total_precio_con_descuento:.2f}")
    
    with open(nombre_archivo_excel, "rb") as file:
        st.download_button(
            label="Descargar Remito",
            data=file,
            file_name=nombre_archivo_excel,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.session_state.seleccionados = []

