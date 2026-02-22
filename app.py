import streamlit as st
import cv2
import numpy as np
from pyzbar.pyzbar import decode, ZBarSymbol
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN DE BASE DE DATOS ---
# Esto garantiza que el archivo sea único y se actualice
def inicializar_db():
    conn = sqlite3.connect('base_datos_conductores.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ingresos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  cedula TEXT, 
                  nombre_completo TEXT, 
                  rh TEXT, 
                  fecha_hora TEXT)''')
    conn.commit()
    return conn

# --- 2. LÓGICA DE PROCESAMIENTO DE TEXTO ---
def procesar_texto_cedula(texto_crudo):
    """
    Aquí extraeremos los datos. La cadena de la cédula colombiana 
    suele ser compleja, por ahora haremos una limpieza básica.
    """
    # Intentamos una limpieza simple de caracteres no deseados
    limpio = "".join(char for char in texto_crudo if char.isprintable())
    
    # Nota: El parseo exacto depende de si la cédula es nueva o vieja.
    # Por ahora, guardamos el bloque de texto para que tú veas cómo llega.
    return {
        "cedula": "Pendiente Procesar", 
        "datos": limpio[:50] + "..." # Muestra una parte
    }

# --- 3. INTERFAZ DE USUARIO ---
st.set_page_config(page_title="Control de Carga - Empresa", layout="wide")

st.title("🚛 Sistema de Registro de Conductores")
st.sidebar.header("Opciones")
modo = st.sidebar.radio("Ir a:", ["Registrar Ingreso", "Consultar Histórico"])

if modo == "Registrar Ingreso":
    st.header("📸 Escaneo de Documento")
    
    # Captura de foto
    foto = st.camera_input("Enfoque el código PDF417 de la cédula")

    if foto:
        # Convertir imagen para que OpenCV la entienda
        file_bytes = np.asarray(bytearray(foto.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        
        # Intentar leer el código
        objetos = decode(img, symbols=[ZBarSymbol.PDF417])

        if objetos:
            texto_detectado = objetos[0].data.decode('ISO-8859-1', errors='ignore')
            st.success("✅ Código detectado")
            
            # Mostramos el contenido para que verifiques qué llega
            st.info(f"Contenido leído: {texto_detectado}")
            
            # Formulario para confirmar datos
            with st.form("confirmar_registro"):
                st.write("### Confirmación de Datos")
                # Por ahora pedimos confirmar manualmente mientras pulimos el extractor automático
                cedula = st.text_input("Número de Cédula")
                nombre = st.text_input("Nombre Completo")
                
                enviado = st.form_submit_button("Guardar en Base de Datos")
                
                if enviado:
                    conn = inicializar_db()
                    cursor = conn.cursor()
                    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("INSERT INTO ingresos (cedula, nombre_completo, fecha_hora) VALUES (?, ?, ?)",
                                   (cedula, nombre, ahora))
                    conn.commit()
                    conn.close()
                    st.success("¡Registro guardado con éxito!")
        else:
            st.warning("⚠️ No se pudo leer el código. Intenta con más luz o acercando más el documento.")

elif modo == "Consultar Histórico":
    st.header("📋 Registros Almacenados")
    
    conn = inicializar_db()
    df = pd.read_sql_query("SELECT * FROM ingresos ORDER BY id DESC", conn)
    conn.close()

    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        # Botón para descargar como Excel/CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar Reporte (CSV)",
            data=csv,
            file_name=f'reporte_conductores_{datetime.now().date()}.csv',
            mime='text/csv',
        )
    else:
        st.write("No hay registros en la base de datos.")