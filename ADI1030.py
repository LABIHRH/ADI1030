import streamlit as st
import serial
import serial.tools.list_ports
import time
import pandas as pd
from datetime import datetime
import plotly.express as px
import threading
import sys

# Configuración de la página
st.set_page_config(page_title="Monitor ADI 1030", layout="wide")

# Comandos para sensores canal 1
COMANDOS = {
    "pH": b'\x02F1.1.1C\r',
    "Temp": b'\x02F1.1.2C\r',
    "DO": b'\x02F1.1.3C\r',
    "Level": b'\x02F1.1.4C\r'
}

# Función mejorada para detectar puertos
def detectar_puertos():
    """Detecta puertos seriales disponibles con manejo de errores mejorado"""
    try:
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            st.warning("⚠ No se detectaron puertos COM. Conecta el dispositivo y verifica:")
            st.markdown("- El cable está bien conectado")
            st.markdown("- Los drivers están instalados")
            st.markdown("- El dispositivo está encendido")
        return [port.device for port in ports]
    except Exception as e:
        st.error(f"❌ Error crítico al detectar puertos: {str(e)}")
        return []

# Estado de la aplicación
if 'datos' not in st.session_state:
    st.session_state.datos = pd.DataFrame(columns=["Tiempo", "pH", "Temp", "DO", "Level"])
if 'lectura_activa' not in st.session_state:
    st.session_state.lectura_activa = False
if 'ser' not in st.session_state:
    st.session_state.ser = None

# Función mejorada para conectar al puerto serial
def conectar_serial(puerto):
    try:
        if not puerto:
            st.error("🔌 No se seleccionó ningún puerto")
            return False
            
        ser = serial.Serial(
            port=puerto,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        time.sleep(2)
        st.session_state.ser = ser
        st.success(f"✅ Conectado correctamente a {puerto}")
        return True
    except serial.SerialException as e:
        error_msg = f"❌ Error al conectar a {puerto}: {str(e)}"
        if "Permission denied" in str(e):
            error_msg += "\n🔒 Posible solución: Cierra otros programas que usen este puerto"
        elif "FileNotFoundError" in str(e):
            error_msg += "\n🔍 Posible solución: Verifica que el puerto existe"
        st.error(error_msg)
        return False
    except Exception as e:
        st.error(f"❌ Error inesperado: {str(e)}")
        return False

# Función para leer datos del sensor
def leer_dato(ser, comando):
    try:
        ser.write(comando)
        time.sleep(0.3)
        respuesta = ser.readline().decode('utf-8', errors='ignore').strip()
        if 'A' in respuesta:
            return respuesta.split('A')[-1]
        return None
    except Exception as e:
        st.error(f"📡 Error de lectura: {str(e)}")
        return None

# Función principal de lectura
def leer_datos():
    while (st.session_state.lectura_activa and 
           st.session_state.ser and 
           st.session_state.ser.is_open):
        try:
            nueva_fila = {"Tiempo": datetime.now()}
            
            for sensor, comando in COMANDOS.items():
                valor = leer_dato(st.session_state.ser, comando)
                if valor is not None:
                    nueva_fila[sensor] = valor
            
            st.session_state.datos = pd.concat([
                st.session_state.datos, 
                pd.DataFrame([nueva_fila])
            ], ignore_index=True)
            
            time.sleep(st.session_state.intervalo_lectura)
            
        except Exception as e:
            st.error(f"🔴 Error en hilo de lectura: {str(e)}")
            st.session_state.lectura_activa = False
            break

# Interfaz de usuario
st.title("📊 Monitor ADI 1030 de Applikon Systems")

# Sidebar para configuración
with st.sidebar:
    st.header("⚙ Configuración")
    
    # Detección de puertos con feedback visual
    with st.spinner("Buscando puertos COM..."):
        puertos_disponibles = detectar_puertos()
    
    if puertos_disponibles:
        puerto_seleccionado = st.selectbox(
            "Seleccionar puerto COM", 
            puertos_disponibles,
            key="puerto_selected"
        )
    else:
        puerto_seleccionado = None
        st.error("No hay puertos disponibles")
    
    if st.button("🔌 Conectar", key="btn_conectar"):
        if puerto_seleccionado:
            conectar_serial(puerto_seleccionado)
        else:
            st.error("Selecciona un puerto primero")
    
    st.session_state.intervalo_lectura = st.slider(
        "⏱ Intervalo de lectura (segundos)", 
        1, 60, 5,
        key="intervalo_lectura"
    )
    
    if st.session_state.ser and st.session_state.ser.is_open:
        if st.button("▶ Iniciar Lectura", disabled=st.session_state.lectura_activa):
            st.session_state.lectura_activa = True
            threading.Thread(target=leer_datos, daemon=True).start()
            st.experimental_rerun()
        
        if st.button("⏹ Detener Lectura", disabled=not st.session_state.lectura_activa):
            st.session_state.lectura_activa = False
            st.experimental_rerun()
    else:
        st.warning("Conecta el puerto serial primero")

# Visualización de datos
if not st.session_state.datos.empty:
    # Mostrar últimos valores
    cols = st.columns(4)
    for i, sensor in enumerate(["pH", "Temp", "DO", "Level"]):
        if sensor in st.session_state.datos.columns:
            ultimo_valor = st.session_state.datos[sensor].iloc[-1] if not st.session_state.datos.empty else "--"
            cols[i].metric(label=sensor, value=ultimo_valor)

    # Gráficos en tiempo real
    tab1, tab2, tab3 = st.tabs(["📈 Gráficos Combinados", "📋 Datos en Tiempo Real", "💾 Exportar Datos"])
    
    with tab1:
        sensores_graficar = st.multiselect(
            "Seleccionar sensores para graficar",
            ["pH", "Temp", "DO", "Level"],
            default=["pH", "Temp", "DO"],
            key="sensores_graficar"
        )
        
        if sensores_graficar:
            fig = px.line(
                st.session_state.datos.melt(
                    id_vars=["Tiempo"], 
                    value_vars=sensores_graficar,
                    var_name="Sensor", 
                    value_name="Valor"
                ),
                x="Tiempo", 
                y="Valor", 
                color="Sensor",
                title="Datos de Sensores en Tiempo Real",
                labels={"Valor": "Valor del Sensor"},
                height=500
            )
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.dataframe(
            st.session_state.datos.sort_values("Tiempo", ascending=False), 
            height=500,
            column_config={
                "Tiempo": st.column_config.DatetimeColumn(
                    "Hora",
                    format="YYYY-MM-DD HH:mm:ss"
                )
            }
        )
    
    with tab3:
        st.download_button(
            label="📥 Descargar datos como CSV",
            data=st.session_state.datos.to_csv(index=False).encode('utf-8'),
            file_name=f"datos_adi1030_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime='text/csv'
        )
        
        st.download_button(
            label="📊 Descargar datos como Excel",
            data=st.session_state.datos.to_excel(excel_writer=bytes(), index=False),
            file_name=f"datos_adi1030_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime='application/vnd.ms-excel'
        )
else:
    st.info("📭 No hay datos disponibles. Conecta el dispositivo e inicia la lectura.")

# Cerrar conexión al finalizar
if (st.session_state.ser and 
    st.session_state.ser.is_open and 
    not st.session_state.lectura_activa):
    st.session_state.ser.close()
    
