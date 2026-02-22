import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image
import os
import sqlite3
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Registro OCR Frontal", layout="wide")

# Crear carpeta para fotos si no existe
if not os.path.exists('fotos_cedulas'):
    os.makedirs('fotos_cedulas')

def conectar_db():
    conn = sqlite3.connect('control_acceso.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS registros 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  cedula TEXT, nombre TEXT, fecha TEXT, ruta_foto TEXT)''')
    conn.commit()
    return conn

# --- FUNCIÓN OCR ---
def extraer_datos(imagen_cv):
    # Convertir a gris y mejorar contraste para OCR
    gray = cv2.cvtColor(imagen_cv, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    
    # Extraer todo el texto de la imagen
    texto = pytesseract.image_to_string(gray, lang='spa')
    return texto

# --- INTERFAZ ---
st.title("🪪 Registro por Cédula Frontal (OCR)")

col_cam, col_reg = st.columns([1, 1])

with col_cam:
    st.subheader("Paso 1: Tomar Foto Frontal")
    foto = st.camera_input("Enfoque la parte delantera de la cédula")

if foto:
    # Procesar imagen
    file_bytes = np.asarray(bytearray(foto.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    with st.spinner("Analizando documento..."):
        texto_extraido = extraer_datos(img)
    
    with col_reg:
        st.subheader("Paso 2: Confirmar Datos")
        
        # Intentamos buscar el número de cédula en el texto con lógica simple
        # (Buscamos secuencias de números largas)
        import re
        numeros = re.findall(r'\d+', texto_extraido)
        cedula_sugerida = max(numeros, key=len) if numeros else ""

        with st.form("datos_ocr"):
            num_cedula = st.text_input("Número de Cédula:", value=cedula_sugerida)
            nombre_completo = st.text_input("Nombre Completo (como aparece en la foto):")
            
            if st.form_submit_button("Guardar Registro"):
                # Guardar imagen físicamente
                nombre_archivo = f"fotos_cedulas/{num_cedula}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(nombre_archivo, img)
                
                # Guardar en DB
                db = conectar_db()
                db.execute("INSERT INTO registros (cedula, nombre, fecha, ruta_foto) VALUES (?,?,?,?)",
                          (num_cedula, nombre_completo, datetime.now().strftime("%Y-%m-%d %H:%M"), nombre_archivo))
                db.commit()
                st.success("✅ Registro guardado exitosamente.")

# --- HISTORIAL ---
st.markdown("---")
st.subheader("📋 Registros Recientes")
db = conectar_db()
df = pd.read_sql_query("SELECT * FROM registros ORDER BY id DESC", db)
st.dataframe(df, use_container_width=True)

