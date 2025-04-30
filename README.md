# Monitor de Sensores ADI 1030

Aplicación hecha con Streamlit para visualizar en tiempo real los datos de sensores conectados al equipo ADI 1030 de Applikon Systems a través de puerto serial.

## Características

- Lectura en tiempo real de sensores (pH, temperatura, oxígeno disuelto y nivel)
- Gráficas interactivas con Plotly
- Exportación de datos a CSV y Excel
- Interfaz amigable en Streamlit

## Requisitos

- Python 3.8 o superior
- Conexión a un puerto serial funcional

## Instalación

```bash
git clone https://github.com/tuusuario/adi1030-monitor.git
cd adi1030-monitor
pip install -r requirements.txt
streamlit run app.py
```

## Créditos y Licencia

Desarrollado por el **Laboratorio de Bioquímica, Edificio O**, del **Instituto Tecnológico de Morelia**, perteneciente al **Tecnológico Nacional de México (TecNM)**.

Consulta el archivo [LICENSE](LICENSE) para los términos de uso.
