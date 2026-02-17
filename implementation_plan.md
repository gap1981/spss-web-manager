# Plan de Implementación: Módulo de Data Storytelling

Este plan detalla la creación de un nuevo módulo en `spss_tool.py` enfocado en la visualización automatizada y narrativa de datos electorales y demográficos.

## Objetivo
Implementar una interfaz "inteligente" donde el usuario asigne roles semánticos a sus variables (ej: "Esta columna es Género", "Esta es Intención de Voto") y el sistema genere automáticamente un set de gráficos estandarizados y profesionales.

## User Review Required
> [!IMPORTANT]
> **Nuevas Dependencias**: Se requiere la librería `plotly` para gráficos interactivos avanzados. Se deberá agregar a `requirements.txt`.

## Proposed Changes

### 1. Nueva Función: `tool_visualizer()` en `spss_tool.py`
Se creará una cuarta herramienta principal.

#### Flujo de Usuario:
1.  **Carga de Datos**: Usa el archivo cargado en memoria (`st.session_state.df`).
2.  **Mapeo de Variables (Role Assignment)**:
    *   El usuario selecciona qué columnas corresponden a conceptos clave:
        *   **Género** (Categórica)
        *   **Edad** (Numérica)
        *   **Nivel Educativo** (Ordinal/Categórica)
        *   **Variable de Interés** (Intención de Voto, Imagen Candidato, etc.)
3.  **Generación de Dashboard**:
    *   Al confirmar el mapeo, se despliegan pestañas con análisis temáticos.

### 2. Tipos de Gráficos (Data Storytelling)

#### A. Demográficos (Univariado)
*   **Distribución de Género**: Gráfico de Donut con porcentajes.
*   **Histograma de Edad**: Con curva de densidad y métricas clave (Media, Mediana).
*   **Nivel Educativo**: Gráfico de barras horizontales ordenadas.

#### B. Escenarios Electorales (Univariado)
*   **Intención de Voto General**: Gráfico de barras verticales con etiquetas de valor.
*   **Imagen de Candidatos**: Stacked Bar Chart (Muy Buena, Buena, Regular, Mala, Muy Mala).

#### C. Análisis de Cuotas (Frecuencias Clave)
*   **Tabla de Control de Muestra**: Generación automática de una tabla de frecuencias cruzadas para variables de control:
    *   Género
    *   Rango de Edad
    *   Zona / Localidad
    *   *Objetivo*: Verificar rápidamente si la muestra recolectada cumple con las cuotas teóricas.

#### D. Cruces (Bivariado - Data Crossings)
*   **Voto por Género**: Gráfico de barras agrupadas (Grouped Bar Chart). Permite ver diferencias de preferencia por sexo.
*   **Voto por Rango Etario**: El sistema crea automáticamente rangos de edad (16-30, 31-50, 50+) si se provee la edad numérica, y cruza con la intención de voto.
*   **Mapa de Calor (Heatmap)**: Para cruces densos (ej: Educativo vs Voto).

### 3. Integración en `spss_tool.py`
*   Modificar el menú lateral para incluir "📊 Data Storytelling (Beta)".
*   Asegurar que `tool_visualizer` acceda al `session_state` compartido.

## Verification Plan

### Automated Tests
*   No aplican tests unitarios automatizados para la UI de Streamlit en este entorno.

### Manual Verification
1.  **Carga de Datos**: Iniciar la app, cargar un `.sav` de encuesta real.
2.  **Mapeo**: Ir al módulo "Data Storytelling". Seleccionar las variables de Género, Edad y Voto.
3.  **Visualización**:
    *   Verificar que el gráfico de Género muestre porcentajes correctos.
    *   Verificar que el Histograma de Edad tenga sentido.
    *   **Prueba de Cruce**: Verificar el gráfico "Voto por Género". ¿Suman 100% los grupos? ¿Los colores son distintos?
4.  **Interaccion**: Probar filtros dinámicos (si se implementan) y tooltips de Plotly.
