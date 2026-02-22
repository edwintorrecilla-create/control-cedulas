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

# --- NUEVO MOTOR DE DIGITALIZACIÓN (NITIDEZ EXTREMA) ---
def digitalizar_imagen(imagen_cv):
    # 1. Súper Resolución: Aumentamos el tamaño 3 veces para definir bordes
    img_grande = cv2.resize(imagen_cv, None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4)
    
    # 2. Convertir a gris
    gray = cv2.cvtColor(img_grande, cv2.COLOR_BGR2GRAY)
    
    # 3. Aplicar un filtro de nitidez (Sharpening) para marcar más las letras
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharp = cv2.filter2D(gray, -1, kernel)
    
    # 4. Umbralización de Otsu (Blanco y Negro sólido)
    _, digitalizada = cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 5. Engrosar letras (Cerrar los puntos blancos que viste en tu imagen)
    kernel_morf = np.ones((2,2), np.uint8)
    digitalizada = cv2.erode(digitalizada, kernel_morf, iterations=1)
    
    # Configuración OCR para lectura de bloques densos
    config_ocr = r'--oem 3 --psm 6'
    texto = pytesseract.image_to_string(digitalizada, lang='spa', config=config_ocr)
    
    return texto, digitalizada

# --- INTERFAZ DE USUARIO ---
st.title("🛡️ Sistema de Registro Digital")
st.markdown("#### Ubique la **PARTE FRONTAL** de la cédula a unos 20cm de la cámara")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📸 Captura de Imagen")
    foto = st.camera_input("Scanner", label_visibility="collapsed")

if foto:
    # Convertir a formato OpenCV
    file_bytes = np.asarray(bytearray(foto.read()), dtype=np.uint8)
    img_color = cv2.imdecode(file_bytes, 1)
    
    with st.spinner("Procesando nitidez..."):
        texto_ocr, img_procesada = digitalizar_imagen(img_color)
    
    with col2:
        st.subheader("📝 Datos del Registro")
        
        # Extraer número de cédula (eliminando puntos y comas)
        texto_limpio = texto_ocr.replace(".", "").replace(",", "")
        numeros = re.findall(r'\d+', texto_limpio)
        cedula_sugerida = next((n for n in numeros if 7 <= len(n) <= 10), "")
        
        # MOSTRAR FOTO A COLOR COMO SOLICITASTE
        st.image(img_color, caption="Captura Real (Evidencia a Color)", use_container_width=True)
        
        with st.expander("Ver análisis técnico (Blanco y Negro)"):
            st.image(img_procesada, caption="Imagen mejorada para el motor OCR")

        with st.form("formulario_registro"):
            val_cedula = st.text_input("Número de Cédula:", value=cedula_sugerida)
            val_nombre = st.text_input("Nombre Completo (Verifique en la imagen):")
            
            confirmar = st.form_submit_button("📥 GUARDAR EN BASE DE DATOS")
            
            if confirmar:
                if val_cedula and val_nombre:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    ruta_img = f"{FOLDER_FOTOS}/ID_{val_cedula}_{timestamp}.jpg"
                    cv2.imwrite(ruta_img, img_color)
                    
                    db = conectar_db()
                    cursor = db.cursor()
                    cursor.execute("INSERT INTO ingresos (cedula, nombre, fecha_hora, ruta_foto) VALUES (?,?,?,?)",
                                   (val_cedula, val_nombre, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ruta_img))
                    db.commit()
                    
                    st.success(f"Registro guardado: {val_nombre}")
                    st.balloons()
                else:
                    st.error("⚠️ Complete los campos antes de guardar.")

# --- HISTORIAL ---
st.markdown("---")
st.subheader("📋 Historial de Registros")
db = conectar_db()
df = pd.read_sql_query("SELECT id, cedula, nombre, fecha_hora FROM ingresos ORDER BY id DESC", db)
st.dataframe(df, use_container_width=True)
db.close()





