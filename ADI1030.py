import streamlit as st
import serial
import serial.tools.list_ports
import time
import pandas as pd
from datetime import datetime
import plotly.express as px
import threading
import sys

# Configuración inicial de la página
st.set_page_config(
    page_title="Monitor ADI 1030 - Applikon Systems",
    layout="wide",
    page_icon="📊"
)

# --- Constantes y Configuración ---
COMANDOS = {
    "pH": b'\x02F1.1.1C\r',
    "Temp": b'\x02F1.1.2C\r',
    "DO": b'\x02F1.1.3C\r',
    "Level": b'\x02F1.1.4C\r'
}

# --- Inicialización del Estado ---
def init_session_state():
    if 'datos' not in st.session_state:
        st.session_state.datos = pd.DataFrame(columns=["Tiempo", "pH", "Temp", "DO", "Level"])
    if 'lectura_activa' not in st.session_state:
        st.session_state.lectura_activa = False
    if 'ser' not in st.session_state:
        st.session_state.ser = None
    if 'intervalo_lectura' not in st.session_state:
        st.session_state.intervalo_lectura = 5  # Valor por defecto

init_session_state()

# --- Funciones Principales ---
def detectar_puertos():
    """Detecta puertos COM disponibles con manejo de errores."""
    try:
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            st.warning("No se detectaron puertos COM. Verifica:")
            st.markdown("- El cable está conectado correctamente")
            st.markdown("- Los drivers del adaptador están instalados")
        return [port.device for port in ports]
    except Exception as e:
        st.error(f"Error al detectar puertos: {e}")
        return []

def conectar_serial(puerto):
    """Establece conexión con el dispositivo."""
    try:
        if not puerto:
            st.error("Selecciona un puerto COM primero")
            return False

        ser = serial.Serial(
            port=puerto,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        time.sleep(2)  # Tiempo de inicialización
        st.session_state.ser = ser
        st.success(f"✅ Conectado a {puerto}")
        return True
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return False

def leer_datos():
    """Hilo principal para lectura continua de datos."""
    while st.session_state.lectura_activa and st.session_state.ser:
        try:
            nueva_fila = {"Tiempo": datetime.now()}
            
            for sensor, comando in COMANDOS.items():
                try:
                    st.session_state.ser.write(comando)
                    time.sleep(0.3)
                    respuesta = st.session_state.ser.readline().decode('utf-8', errors='ignore').strip()
                    nueva_fila[sensor] = respuesta.split('A')[-1] if 'A' in respuesta else None
                except Exception as e:
                    st.error(f"Error en sensor {sensor}: {e}")
                    nueva_fila[sensor] = None

            # Actualiza DataFrame
            st.session_state.datos = pd.concat([
                st.session_state.datos,
                pd.DataFrame([nueva_fila])
            ], ignore_index=True)

            time.sleep(st.session_state.intervalo_lectura)

        except Exception as e:
            st.error(f"Error crítico: {e}")
            st.session_state.lectura_activa = False
            break

# --- Interfaz de Usuario ---
st.title("📊 Monitor ADI 1030 - Applikon Systems")

# Sidebar - Configuración
with st.sidebar:
    st.header("⚙ Configuración")
    
    # Detección de puertos
    with st.spinner("Buscando puertos COM..."):
        puertos_disponibles = detectar_puertos()
    
    # Selector de puerto
    puerto_seleccionado = st.selectbox(
        "Seleccionar puerto COM",
        puertos_disponibles if puertos_disponibles else ["No detectados"],
        disabled=not puertos_disponibles
    )
    
    # Botón de conexión
    if st.button("🔌 Conectar", type="primary", disabled=not puertos_disponibles):
        if puertos_disponibles:
            conectar_serial(puerto_seleccionado)
    
    # Control de intervalo
    st.session_state.intervalo_lectura = st.slider(
        "⏱ Intervalo de lectura (segundos)",
        1, 60, st.session_state.intervalo_lectura
    )
    
    # Controles de lectura
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ Iniciar", 
                    disabled=not st.session_state.ser or st.session_state.lectura_activa,
                    help="Inicia la adquisición de datos"):
            st.session_state.lectura_activa = True
            threading.Thread(target=leer_datos, daemon=True).start()
            st.rerun()
    
    with col2:
        if st.button("⏹ Detener", 
                    disabled=not st.session_state.lectura_activa,
                    help="Detiene la adquisición de datos"):
            st.session_state.lectura_activa = False
            st.rerun()

# --- Visualización de Datos ---
if not st.session_state.datos.empty:
    # Últimos valores
    cols = st.columns(4)
    metricas = {
        "pH": "🌡 pH",
        "Temp": "🌡 Temp (°C)",
        "DO": "🫧 DO",
        "Level": "📶 Level"
    }
    
    for i, (sensor, label) in enumerate(metricas.items()):
        if sensor in st.session_state.datos.columns:
            ultimo_valor = st.session_state.datos[sensor].iloc[-1]
            cols[i].metric(label, ultimo_valor)

    # Pestañas principales
    tab1, tab2, tab3 = st.tabs(["📈 Gráficos", "📋 Datos", "💾 Exportar"])
    
    with tab1:
        sensores = st.multiselect(
            "Seleccionar sensores:",
            list(COMANDOS.keys()),
            default=["pH", "Temp"]
        )
        
        if sensores:
            fig = px.line(
                st.session_state.datos.melt(id_vars=["Tiempo"], value_vars=sensores),
                x="Tiempo", y="value", color="variable",
                labels={"value": "Valor", "variable": "Sensor"},
                title="Tendencias en Tiempo Real"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.dataframe(
            st.session_state.datos.sort_values("Tiempo", ascending=False),
            height=500,
            column_config={
                "Tiempo": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm:ss")
            }
        )
    
    with tab3:
        formato = st.radio("Formato de exportación:", ["CSV", "Excel"])
        
        if formato == "CSV":
            st.download_button(
                label="⬇️ Descargar CSV",
                data=st.session_state.datos.to_csv(index=False),
                file_name=f"ADI1030_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.download_button(
                label="⬇️ Descargar Excel",
                data=st.session_state.datos.to_excel(index=False),
                file_name=f"ADI1030_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
else:
    st.info("📭 No hay datos disponibles. Conecta el dispositivo e inicia la lectura.")

# Cierre seguro al finalizar
if st.session_state.ser and not st.session_state.lectura_activa:
    st.session_state.ser.close()
