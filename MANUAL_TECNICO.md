# 🛠️ Manual Técnico: SPSS Web Tool Manager

Este documento describe la arquitectura técnica, dependencias y lógica interna de la aplicación **SPSS Web Tool Manager**.

## 1. Arquitectura del Sistema

La aplicación está construida como una **Single Page Application (SPA)** utilizando el framework **Streamlit**.

*   **Frontend**: Streamlit (Components de UI reactivos).
*   **Backend**: Python 3.x.
*   **Data Processing**: Pandas y Pyreadstat (Wrapper de Readstat para archivos SPSS/SAS/Stata).
*   **Export**: OpenPyXML (Excel) y Pyreadstat (.sav).

### Estructura de Archivos
*   `spss_tool.py`: Punto de entrada principal. Contiene toda la lógica de presentación y negocio.
*   `requirements.txt`: Lista de dependencias.
*   `README.md`: Documentación general.
*   `temp_*.sav`: Archivos temporales generados durante la carga/descarga (se limpian automáticamente).

---

## 2. Dependencias Clave

| Librería | Propósito |
| :--- | :--- |
| `streamlit` | Framework web y gestión de estado (Session State). |
| `pandas` | Manipulación de DataFrames y análisis de datos. |
| `pyreadstat` | Lectura y escritura de archivos `.sav`, incluyendo metadatos (etiquetas). |
| `openpyxl` | Motor para leer y escribir archivos Excel (`.xlsx`). |

---

## 3. Módulos y Funciones Principales

El código en `spss_tool.py` se organiza en tres grandes funciones que corresponden a los módulos de la aplicación:

### A. `tool_manager_exporter()`
Maneja la carga inicial, visualización y exportación.
*   **Gestión de Estado**: Inicializa `st.session_state.df` y `.meta`.
*   **Vista de Estructura**: Itera sobre `df.columns` cruzando información con `meta` (etiquetas, formatos).
*   **Edición de Metadatos**: Permite modificar `meta.column_names_to_labels` sin alterar los datos todavía.
*   **Exportación**: Aplica las transformaciones y etiquetas al momento de generar el archivo de salida.

### B. `tool_advanced_editor()`
Proporciona capacidades de edición profunda.
*   **Data Editor**: Utiliza `st.data_editor` con `num_rows="dynamic"` para permitir edición tipo Excel.
*   **Metadata Editor**: Tabla editable separada para modificar etiquetas y *Value Labels* (JSON).
*   **Sincronización**: Detecta cambios en el editor y actualiza el `st.session_state` correspondiente.
*   **Lógica de Borrado**: Permite eliminar columnas tanto del DataFrame como de los diccionarios de metadatos asociados.

### C. `tool_audit_validator()` (Nuevo)
Módulo de auditoría de calidad.
*   **Input**: Recibe `.sav` (Patrón) y `.xlsx/.csv` (Target).
*   **Validación Estructural**:
    *   `Missing Columns`: `set(ref) - set(target)`
    *   `Extra Columns`: `set(target) - set(ref)`
*   **Validación de Tipos**:
    *   Verifica si columnas numéricas en patrón contienen strings en target usando `pd.to_numeric(errors='coerce')`.
*   **Validación de Valores (Value Labels)**:
    *   Extrae valores válidos de `meta.variable_value_labels`.
    *   Normaliza tipos (int vs float) para comparaciones robustas.
    *   Itera sobre valores únicos (`unique()`) para optimizar rendimiento.

---

## 4. Gestión de Estado (Session State)

La persistencia de datos entre recargas de la página (reruns) es crítica en Streamlit.

*   `st.session_state.df`: El DataFrame principal cargado con Pandas.
*   `st.session_state.meta`: Objeto de metadatos de Pyreadstat (contiene etiquetas originales).
*   `st.session_state.modified_labels`: Diccionario `{columna: nueva_etiqueta}` que almacena cambios del usuario.
*   `st.session_state.selected_cols`: Lista de columnas activas/seleccionadas.
*   `st.session_state.file_loaded`: Flag booleano para controlar la carga inicial.

## 5. Setup y Despliegue

### Instalación Local
```bash
pip install -r requirements.txt
```

### Ejecución
```bash
streamlit run spss_tool.py
```

### Configuración de Streamlit
El archivo utiliza `st.set_page_config` para:
*   Layout: `wide` (aprovecha todo el ancho de pantalla).
*   Sidebar: `collapsed` por defecto (mejor experiencia móvil).

## 6. Manejo de Errores y Seguridad
*   **Archivos Temporales**: Se utilizan nombres fijos (`temp_input.sav`) para evitar colisiones básicas y se aseguran bloques `try/finally` para su eliminación.
*   **Validación de Inputs**: Se chequean extensiones de archivo y consistencia de datos antes de procesar.
