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

# --- MOTOR DE PROCESAMIENTO MEJORADO ---
def digitalizar_imagen(imagen_cv):
    # 1. Escalar para que las letras sean más grandes
    img_grande = cv2.resize(imagen_cv, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_LANCZOS4)
    
    # 2. Convertir a escala de grises
    gray = cv2.cvtColor(img_grande, cv2.COLOR_BGR2GRAY)
    
    # 3. Aplicar un leve desenfoque para suavizar el "ruido" de la cámara
    blur = cv2.GaussianBlur(gray, (3,3), 0)
    
    # 4. Umbralización simple (evita que las letras se vean "huecas")
    # Ajustamos para que el texto negro resalte mejor sobre el fondo claro
    _, digitalizada = cv2.threshold(blur, 100, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Intentar OCR con configuración para bloques de texto
    config_ocr = r'--oem 3 --psm 4'
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
    # Convertir bytes a formato OpenCV (Color)
    file_bytes = np.asarray(bytearray(foto.read()), dtype=np.uint8)
    img_color = cv2.imdecode(file_bytes, 1)
    
    with st.spinner("Procesando información..."):
        texto_ocr, img_procesada = digitalizar_imagen(img_color)
    
    with col2:
        st.subheader("📝 Datos del Registro")
        
        # Intentar extraer el número de cédula (secuencia de 7 a 10 dígitos)
        # Limpiamos el texto de puntos para facilitar la búsqueda
        texto_limpio = texto_ocr.replace(".", "").replace(",", "")
        numeros = re.findall(r'\d+', texto_limpio)
        cedula_sugerida = next((n for n in numeros if 7 <= len(n) <= 10), "")
        
        # 1. MOSTRAR LA FOTO A COLOR para confirmación visual
        st.image(img_color, caption="Captura Real (Evidencia)", use_column_width=True)
        
        # Opcional: Mostrar la versión procesada pequeña para diagnóstico
        with st.expander("Ver análisis del sistema (OCR)"):
            st.image(img_procesada, caption="Versión optimizada para lectura de texto")

        with st.form("formulario_registro"):
            val_cedula = st.text_input("Número de Cédula:", value=cedula_sugerida)
            val_nombre = st.text_input("Nombre Completo (como aparece):")
            
            confirmar = st.form_submit_button("📥 GUARDAR EN BASE DE DATOS")
            
            if confirmar:
                if val_cedula and val_nombre:
                    # Guardar foto A COLOR como evidencia
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    ruta_img = f"{FOLDER_FOTOS}/ID_{val_cedula}_{timestamp}.jpg"
                    cv2.imwrite(ruta_img, img_color)
                    
                    # Guardar en DB
                    db = conectar_db()
                    cursor = db.cursor()
                    cursor.execute("INSERT INTO ingresos (cedula, nombre, fecha_hora, ruta_foto) VALUES (?,?,?,?)",
                                   (val_cedula, val_nombre, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ruta_img))
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



