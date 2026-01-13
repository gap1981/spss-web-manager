# spss-web-manager
EDITOR BASICO DE SPSS ONLINE
📊 SPSS Web Tool Manager

Esta es una herramienta web optimizada para dispositivos móviles (Android/iOS) y escritorio, diseñada para manipular archivos de datos de SPSS (.sav) sin necesidad de tener instalado el software de IBM.

Es especialmente útil para procesar exportaciones de LimeSurvey, permitiendo limpiar la estructura de los datos, editar etiquetas de variables (sintaxis) y exportar los resultados a formatos más amigables como Excel.

🚀 Características principales

Carga de archivos .sav: Lectura directa de archivos SPSS preservando metadatos.

Gestión de Columnas: Elimina fácilmente columnas innecesarias o metadatos internos de encuestas.

Editor de Sintaxis/Etiquetas: Modifica las etiquetas de las variables en tiempo real.

Exportación Versátil:

Exporta a Excel (.xlsx) para análisis rápido.

Exporta a un nuevo SPSS (.sav) limpio y con etiquetas actualizadas.

Interfaz Responsiva: Diseñada para funcionar perfectamente en navegadores de Android como una App (PWA).

🛠️ Instalación y Despliegue

Opción 1: Streamlit Cloud (Recomendado para Android)

Sube los archivos spss_tool.py y requirements.txt a un repositorio de GitHub.

Entra en Streamlit Community Cloud.

Conecta tu repositorio y despliega la aplicación.

Una vez desplegada, abre la URL en tu Android y selecciona "Añadir a la pantalla de inicio" en Chrome para usarla como una App nativa.

Opción 2: Ejecución Local (PC)

Si prefieres correrlo en tu computadora, asegúrate de tener Python instalado y sigue estos pasos:

# Clonar el repositorio
git clone <tu-url-de-github>
cd <nombre-del-repo>

# Instalar dependencias
pip install -r requirements.txt

# Correr la aplicación
streamlit run spss_tool.py


📋 Requisitos

Las librerías necesarias están detalladas en el archivo requirements.txt:

streamlit: Para la interfaz web.

pandas: Para el manejo de estructuras de datos.

pyreadstat: Para la lectura/escritura de archivos SPSS (es el motor que reemplaza a IBM SPSS).

openpyxl: Para la generación de archivos Excel.

🔐 Privacidad y Seguridad

La herramienta procesa los archivos de forma local en el contenedor temporal de Streamlit. No se almacenan datos de forma permanente en ningún servidor; una vez que cierras la sesión o termina el procesamiento, los archivos temporales son eliminados.

Creado para la gestión eficiente de datos estadísticos.
