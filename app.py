import streamlit as st
import cv2
import numpy as np
import pytesseract
import os
import sqlite3
import pandas as pd
import re
from datetime import datetime
from PIL import Image

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Scanner Frontal Pro", layout="wide")

# Carpeta para guardar las evidencias
FOLDER_FOTOS = "registros_cedulas"
if not os.path.exists(FOLDER_FOTOS):
    os.makedirs(FOLDER_FOTOS)

# --- BASE DE DATOS ---
def conectar_db():
    conn = sqlite3.connect('logistica_conductores.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ingresos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  cedula TEXT, nombre TEXT, fecha_hora TEXT, ruta_foto TEXT)''')
    conn.commit()
    return conn

# --- MOTOR DE DIGITALIZACIÓN ACTIVA ---
def digitalizar_imagen(imagen_cv):
    # 1. Aumentar tamaño para mejorar resolución de letras pequeñas
    img_grande = cv2.resize(imagen_cv, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    # 2. Pasar a escala de grises
    gray = cv2.cvtColor(img_grande, cv2.COLOR_BGR2GRAY)
    
    # 3. Filtro Bilateral: quita ruido pero mantiene los bordes de las letras nítidos
    blur = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # 4. Umbralización Adaptativa: detecta texto incluso con sombras o mala luz
    digitalizada = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Intentar OCR con configuración optimizada para documentos
    # psm 6: Asume un bloque único de texto
    config_ocr = r'--oem 3 --psm 6'
    texto = pytesseract.image_to_string(digitalizada, lang='spa', config=config_ocr)
    
    return texto, digitalizada

# --- INTERFAZ DE USUARIO ---
st.title("🛡️ Sistema de Registro Digital")
st.markdown("#### Ubique la **PARTE FRONTAL** de la cédula frente a la cámara")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📸 Captura de Imagen")
    foto = st.camera_input("Scanner", label_visibility="collapsed")

if foto:
    # Convertir bytes a formato OpenCV
    file_bytes = np.asarray(bytearray(foto.read()), dtype=np.uint8)
    img_original = cv2.imdecode(file_bytes, 1)
    
    with st.spinner("Digitalizando y extrayendo información..."):
        texto_ocr, img_procesada = digitalizar_imagen(img_original)
    
    with col2:
        st.subheader("📝 Datos del Registro")
        
        # Lógica para encontrar el número de cédula (7 a 10 dígitos)
        numeros = re.findall(r'\d+', texto_ocr)
        cedula_sugerida = next((n for n in numeros if 7 <= len(n) <= 10), "")
        
        # Mostrar lo que el sistema "vio" para ayudar al usuario
        st.image(img_procesada, caption="Vista Digitalizada (Lo que el OCR analizó)", use_column_width=True)
        
        with st.form("formulario_registro"):
            val_cedula = st.text_input("Número de Cédula:", value=cedula_sugerida)
            val_nombre = st.text_input("Nombre Completo (como aparece):")
            
            confirmar = st.form_submit_button("📥 GUARDAR EN BASE DE DATOS")
            
            if confirmar:
                if val_cedula and val_nombre:
                    # Guardar foto a color como evidencia
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    ruta_img = f"{FOLDER_FOTOS}/ID_{val_cedula}_{timestamp}.jpg"
                    cv2.imwrite(ruta_img, img_original)
                    
                    # Guardar en DB
                    db = conectar_db()
                    cursor = db.cursor()
                    cursor.execute("INSERT INTO ingresos (cedula, nombre, fecha_hora, ruta_foto) VALUES (?,?,?,?)",
                                   (val_cedula, val_nombre, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ruta_archivo))
                    db.commit()
                    
                    st.success(f"¡Registro exitoso! Conductor: {val_nombre}")
                    st.balloons()
                else:
                    st.error("⚠️ Debe completar Cédula y Nombre antes de guardar.")

# --- HISTORIAL ---
st.markdown("---")
st.subheader("📋 Historial de Registros")
db = conectar_db()
df = pd.read_sql_query("SELECT id, cedula, nombre, fecha_hora FROM ingresos ORDER BY id DESC", db)
st.dataframe(df, use_container_width=True)
db.close()



