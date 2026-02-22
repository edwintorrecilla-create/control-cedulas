import streamlit as st
import cv2
import numpy as np
import pytesseract
import os
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Registro Frontal de Cédula", layout="wide")

# Carpeta de almacenamiento
FOLDER_FOTOS = "evidencias_cedula"
if not os.path.exists(FOLDER_FOTOS):
    os.makedirs(FOLDER_FOTOS)

def conectar_db():
    conn = sqlite3.connect('base_datos_empresa.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS registros 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  cedula TEXT, nombre TEXT, fecha_hora TEXT, ruta_foto TEXT)''')
    conn.commit()
    return conn

# --- MOTOR OCR OPTIMIZADO ---
def procesar_ocr_frontal(imagen_color):
    # Convertimos a gris para el análisis
    gray = cv2.cvtColor(imagen_color, cv2.COLOR_BGR2GRAY)
    # Aplicamos un filtro para eliminar ruido y resaltar letras
    gray = cv2.medianBlur(gray, 3)
    # Binarización para que el OCR lea mejor (Solo para análisis interno)
    umbral = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    
    # Extraer texto (español)
    texto = pytesseract.image_to_string(umbral, lang='spa')
    return texto, umbral

# --- INTERFAZ ---
st.title("🪪 Registro de Personal")
st.markdown("### Por favor, ubique la parte frontal de la cédula frente a la cámara.")

col_izq, col_der = st.columns([1, 1])

with col_izq:
    st.subheader("📸 Captura de Documento")
    foto = st.camera_input("Enfoque la cédula", label_visibility="collapsed")

if foto:
    # Convertir foto recibida
    file_bytes = np.asarray(bytearray(foto.read()), dtype=np.uint8)
    img_color = cv2.imdecode(file_bytes, 1)
    
    # Procesar texto
    with st.spinner("Analizando información..."):
        texto_crudo, img_analisis = procesar_ocr_frontal(img_color)
    
    with col_der:
        st.subheader("📝 Datos Detectados")
        
        # Lógica de limpieza rápida (buscar números largos para la cédula)
        import re
        numeros = re.findall(r'\d+', texto_crudo)
        # Filtramos números que tengan entre 7 y 10 dígitos (típico de cédula)
        cedula_posible = next((n for n in numeros if 7 <= len(n) <= 10), "")

        with st.form("confirmacion_datos"):
            st.info("Verifique y corrija si es necesario:")
            cedula_final = st.text_input("Número de Documento:", value=cedula_posible)
            nombre_final = st.text_input("Nombre Completo (como aparece en el documento):")
            
            if st.form_submit_button("📥 GUARDAR REGISTRO"):
                if cedula_final and nombre_final:
                    # Guardar la foto A COLOR como evidencia
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    ruta_archivo = f"{FOLDER_FOTOS}/CED_{cedula_final}_{timestamp}.jpg"
                    cv2.imwrite(ruta_archivo, img_color)
                    
                    # Guardar en Base de Datos
                    db = conectar_db()
                    cursor = db.cursor()
                    cursor.execute("INSERT INTO registros (cedula, nombre, fecha_hora, ruta_foto) VALUES (?,?,?,?)",
                                   (cedula_final, nombre_final, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ruta_archivo))
                    db.commit()
                    
                    st.success(f"Registro de {nombre_final} guardado con éxito.")
                    st.balloons()
                else:
                    st.error("Por favor, complete ambos campos antes de guardar.")

# --- SECCIÓN DE HISTORIAL ---
st.markdown("---")
st.subheader("📊 Historial de Registros")
db = conectar_db()
df = pd.read_sql_query("SELECT cedula, nombre, fecha_hora FROM registros ORDER BY id DESC", db)
st.table(df)
db.close()



