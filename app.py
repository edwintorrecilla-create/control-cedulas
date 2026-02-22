import streamlit as st
import cv2
import numpy as np
from pyzbar.pyzbar import decode, ZBarSymbol
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ESTÉTICA (CSS) ---
st.set_page_config(page_title="Control de Ingresos", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stDataFrame { background-color: white; border-radius: 10px; }
    div[data-testid="stMetricValue"] { font-size: 24px; }
    </style>
    """, unsafe_allow_html=True)

# --- BASE DE DATOS ---
def conectar_db():
    conn = sqlite3.connect('despachos.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS conductores 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, cedula TEXT, nombre TEXT, rh TEXT, fecha TEXT)''')
    conn.commit()
    return conn

# --- MEJORA DE LECTURA POR DIMENSIONES (7.5x1.5 cm) ---
def procesar_zoom_cedula(img):
    h, w, _ = img.shape
    # Recortamos una franja central (donde usualmente el usuario pone la cédula)
    # Esto simula un "Macro" digital para captar mejor el PDF417
    start_row, end_row = int(h*0.3), int(h*0.7)
    start_col, end_col = int(w*0.1), int(w*0.9)
    recorte = img[start_row:end_row, start_col:end_col]
    
    # Aumentamos el tamaño del recorte para mejorar resolución
    recorte_grande = cv2.resize(recorte, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(recorte_grande, cv2.COLOR_BGR2GRAY)
    # Filtro para resaltar barras negras
    sharpen_kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharp = cv2.filter2D(gray, -1, sharpen_kernel)
    return sharp

# --- INTERFAZ ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4006/4006511.png", width=100)
    st.title("Menú")
    opcion = st.radio("Navegación", ["🆕 Nuevo Registro", "📊 Ver Historial"])
    st.info("© 2024 Tu Empresa. Todos los derechos reservados.")

if opcion == "🆕 Nuevo Registro":
    st.markdown("## 42 Registro de Conductores 😊")
    st.write("Aproxime el código de la cédula al recuadro de la cámara.")
    
    col_cam, col_datos = st.columns([1, 1])

    with col_cam:
        st.subheader("Cámara")
        foto = st.camera_input("Scanner", label_visibility="collapsed")
        
    with col_datos:
        st.subheader("Datos Extraídos")
        if foto:
            file_bytes = np.asarray(bytearray(foto.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, 1)
            
            # Procesamiento con Zoom y Enfoque
            img_ready = procesar_zoom_cedula(img)
            lectura = decode(img_ready, symbols=[ZBarSymbol.PDF417])

            if lectura:
                st.success("✅ Cédula leída con éxito")
                texto_crudo = lectura[0].data.decode('ISO-8859-1', errors='ignore')
                
                # Campos automáticos (Simulados hasta que me pases el texto real)
                cedula_val = "10203040" 
                nombre_val = "JUAN PEREZ"
                
                cedula = st.text_input("Cédula:", value=cedula_val)
                nombre = st.text_input("Nombre:", value=nombre_val)
                rh = st.text_input("RH:", value="O+")
                
                if st.button("📥 Confirmar y Guardar"):
                    conn = conectar_db()
                    c = conn.cursor()
                    c.execute("INSERT INTO conductores (cedula, nombre, rh, fecha) VALUES (?,?,?,?)",
                             (cedula, nombre, rh, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit()
                    st.balloons()
                    st.success("¡Registro guardado!")
            else:
                st.warning("⚠️ No se detectó el código. Asegúrese de centrar la franja de barras.")
                st.info("Tip: Mantenga la cédula a 15 cm de la cámara.")

else:
    st.markdown("## 44 Historial de Ingresos 😍")
    conn = conectar_db()
    df = pd.read_sql_query("SELECT * FROM conductores ORDER BY id DESC", conn)
    
    st.dataframe(df, use_container_width=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("⬇️ Descargar Reporte CSV", df.to_csv(index=False), "reporte.csv", "text/csv")
    
