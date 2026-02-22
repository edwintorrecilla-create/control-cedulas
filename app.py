import streamlit as st
import cv2
import numpy as np
from pyzbar.pyzbar import decode, ZBarSymbol
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA Y ESTILO CSS ---
st.set_page_config(page_title="Control de Ingresos Conductores", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { 
        width: 100%; 
        border-radius: 8px; 
        height: 3.5em; 
        background-color: #007bff; 
        color: white;
        font-weight: bold;
        border: none;
    }
    .stButton>button:hover { background-color: #0056b3; border: none; }
    .css-1r6slb0 { border-radius: 15px; background-color: white; padding: 20px; box-shadow: 0px 4px 12px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE BASE DE DATOS ---
def conectar_db():
    conn = sqlite3.connect('registro_empresa.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ingresos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  cedula TEXT, nombre TEXT, rh TEXT, fecha_hora TEXT)''')
    conn.commit()
    return conn

# --- MOTOR DE LECTURA MEJORADO (FUERZA BRUTA) ---
def procesar_lectura_extrema(img):
    # 1. Convertir a escala de grises
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Versión: Alto Contraste (Binarización Adaptativa)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY, 11, 2)
    
    # 3. Versión: Nitidez Extrema (Sharpening)
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharp = cv2.filter2D(gray, -1, kernel)
    
    # 4. Versión: Zoom Digital (Recorte central 7.5x1.5 cm aprox)
    h, w = gray.shape
    recorte = gray[int(h*0.3):int(h*0.7), int(w*0.1):int(w*0.9)]
    zoom = cv2.resize(recorte, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # Intentar decodificar en cada una de las versiones
    intentos = [gray, thresh, sharp, zoom, img]
    
    for version in intentos:
        # Buscamos específicamente el formato PDF417 de la cédula
        resultado = decode(version, symbols=[ZBarSymbol.PDF417])
        if resultado:
            return resultado
    return None

# --- ESTRUCTURA DE LA INTERFAZ ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4006/4006511.png", width=80)
    st.title("Gestión de Carga")
    st.markdown("---")
    menu = st.radio("Menú de Usuario", ["🆕 Registro de Ingreso", "📋 Historial de Despachos"])
    st.markdown("---")
    st.caption("v2.0 - Optimización de Scanner")

if menu == "🆕 Registro de Ingreso":
    st.header("42 Registro de Conductores 😊")
    st.write("Por favor, aproxime la cédula a la cámara. Evite reflejos de luz directa.")

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.subheader("📸 Cámara de Verificación")
        foto = st.camera_input("Scanner", label_visibility="collapsed")
        
    with col2:
        st.subheader("📄 Datos Extraídos")
        
        if foto:
            # Convertir foto a formato OpenCV con alta calidad
            file_bytes = np.asarray(bytearray(foto.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
            # Ejecutar lectura múltiple
            lectura = procesar_lectura_extrema(img)

            if lectura:
                st.success("✅ Código detectado con éxito")
                # Extraemos el texto crudo (ISO-8859-1 maneja tildes y ñ)
                datos_crudos = lectura[0].data.decode('ISO-8859-1', errors='ignore')
                
                # ÁREA DE PRUEBA: Mostramos el texto para que nos ayudes a parsearlo
                st.code(datos_crudos, language=None)
                
                # Por ahora, llenado manual asistido mientras pulimos el extractor automático
                with st.form("form_registro"):
                    c_ced = st.text_input("Número de Cédula:", placeholder="Escaneado o manual...")
                    c_nom = st.text_input("Nombre Completo:", placeholder="Nombre del conductor...")
                    c_rh = st.selectbox("RH:", ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"])
                    
                    if st.form_submit_button("📥 CONFIRMAR Y GUARDAR"):
                        db = conectar_db()
                        cursor = db.cursor()
                        ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
                        cursor.execute("INSERT INTO ingresos (cedula, nombre, rh, fecha_hora) VALUES (?,?,?,?)",
                                       (c_ced, c_nom, c_rh, ahora))
                        db.commit()
                        st.balloons()
                        st.success("¡Registro almacenado en la base de datos!")
            else:
                st.error("❌ No se pudo leer el código PDF417.")
                st.info("""
                **Sugerencias para una lectura exitosa:**
                1. Mantenga la cédula a unos **15-20 cm** de la cámara.
                2. Incline levemente la cédula para **evitar el reflejo** de las luces del techo.
                3. Asegúrese de que el código de barras se vea **nítido** en la pantalla.
                """)
        else:
            st.warning("Esperando captura de imagen...")

else:
    st.header("44 Historial de Ingresos 😍")
    db = conectar_db()
    df = pd.read_sql_query("SELECT * FROM ingresos ORDER BY id DESC", db)
    db.close()

    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        # Botones de descarga
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Descargar Reporte CSV",
            data=csv,
            file_name=f'reporte_ingresos_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv',
        )
    else:
        st.info("Aún no hay registros de conductores el día de hoy.")

