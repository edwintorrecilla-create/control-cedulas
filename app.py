import streamlit as st
import cv2
import numpy as np
from pyzbar.pyzbar import decode, ZBarSymbol
import sqlite3
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Scanner Profesional de Cédulas", layout="centered")

def conectar_db():
    conn = sqlite3.connect('base_conductores.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS registros 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, cedula TEXT, nombre TEXT, fecha TEXT)''')
    conn.commit()
    return conn

# --- MOTOR DE PROCESAMIENTO AVANZADO ---
def mejorar_y_leer(imagen_bytes):
    # Convertir bytes a imagen OpenCV
    nparr = np.frombuffer(imagen_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 1. Convertir a escala de grises
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Binarización de Otsu (encuentra el umbral óptimo de blanco/negro automáticamente)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 3. Intento de lectura en 3 variantes
    # Original, Grises, y Blanco/Negro puro
    for version in [img, gray, thresh]:
        lectura = decode(version, symbols=[ZBarSymbol.PDF417])
        if lectura:
            return lectura[0].data.decode('ISO-8859-1', errors='ignore'), version
            
    return None, thresh

# --- INTERFAZ ---
st.title("📸 Scanner de Cédula (Modo Foto)")
st.info("Tome la foto asegurándose de que el código PDF417 ocupe la mayor parte de la pantalla.")

# Widget de cámara
foto_capturada = st.camera_input("Enfoque el respaldo de la cédula")

if foto_capturada:
    with st.spinner("Procesando imagen con alta precisión..."):
        texto_detectado, imagen_procesada = mejorar_y_leer(foto_capturada.getvalue())
        
    if texto_detectado:
        st.success("✅ ¡Lectura exitosa!")
        # Mostramos la cadena para que veas qué extrajo
        st.code(texto_detectado)
        
        # Formulario de confirmación
        with st.form("confirmar_datos"):
            col1, col2 = st.columns(2)
            c_id = col1.text_input("Número de Cédula")
            c_nom = col2.text_input("Nombres y Apellidos")
            
            if st.form_submit_button("Guardar en Historial"):
                db = conectar_db()
                db.execute("INSERT INTO registros (cedula, nombre, fecha) VALUES (?,?,?)", 
                          (c_id, c_nom, datetime.now().strftime("%Y-%m-%d %H:%M")))
                db.commit()
                st.balloons()
    else:
        st.error("No se pudo decodificar el código de la foto.")
        st.subheader("Imagen analizada (para diagnóstico):")
        # Mostramos cómo vio el código el algoritmo para ver si estaba borroso
        st.image(imagen_procesada, caption="Esta es la versión blanco/negro que el sistema intentó leer.")
        st.info("Tip: Si la imagen se ve muy blanca o muy negra, cambie el ángulo de luz para evitar reflejos.")

