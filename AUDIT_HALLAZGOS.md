# Documentación Técnica: Módulo de Auditoría y Validación de Datos

## Descripción General
El módulo de **Auditoria y Validación de Datos** (`tool_audit_validator`) es una nueva funcionalidad integrada en `spss_tool.py` diseñada para asegurar la calidad de los datos recolectados en campo (Excel/CSV) contrastándolos contra un diccionario de datos maestro (SPSS .sav).

## Arquitectura y Flujo de Datos

1.  **Input 1: Archivo Maestro (.sav)**
    *   Actúa como la "fuente de verdad" (Single Source of Truth).
    *   Se extraen:
        *   **Metadata Estructural**: Nombres de variables obligatorias y sus tipos.
        *   **Value Labels**: Diccionario de valores permitidos (ej. `{1: "Hombre", 2: "Mujer"}`).

2.  **Input 2: Datos de Campo (Excel/CSV)**
    *   Archivo plano que contiene los datos recolectados.
    *   Puede contener errores de tipo, estructura o consistencia.

3.  **Motor de Validación**
    *   Implementado en Python usando `pandas` y `pyreadstat`.
    *   Ejecuta validaciones secuenciales (ver sección "Lógica de Validación").

4.  **Output: Reporte de Auditoría (.xlsx)**
    *   Genera un archivo Excel con múltiples pestañas para facilitar la corrección.

## Lógica de Validación Implementada

El sistema realiza tres niveles de validación:

### 1. Validación Estructural
*   **Columnas Faltantes (CRITICIDAD ALTA)**:
    *   Verifica si todas las variables del `.sav` existen en el archivo de datos.
    *   Es crucial para asegurar que no se haya perdido información.
*   **Columnas Extra (CRITICIDAD BAJA)**:
    *   Detecta columnas en el Excel que no están en el `.sav`.
    *   Útil para identificar campos temporales o errores de digitación en los nombres de variables.

### 2. Validación de Tipos de Datos (Type Checking)
*   **Detección de Texto en Campos Numéricos (CRITICIDAD ALTA)**:
    *   Si una variable es numérica en SPSS, el sistema verifica que todos los valores en el Excel sean convertibles a número.
    *   Detecta errores comunes como "No sabe", "N/A" o errores de tipeo en campos de edad o ingresos.
    *   Utiliza `pd.to_numeric(errors='coerce')` para una detección robusta.

### 3. Validación de Rango y Valores (Value Logic)
*   **Consistencia con Value Labels (CRITICIDAD MEDIA)**:
    *   Para variables categóricas definidas en SPSS (con `value_labels`), se verifica que los valores en los datos coincidan **exactamente** con:
        *   El **código** numérico (ej: `1`).
        *   O la **etiqueta** de texto (ej: `"Hombre"`).
    *   Cualquier valor fuera de este conjunto (ej: `3`, `0`, `"Otro"`) se reporta como error.
    *   **Manejo de Tipos**: Se normalizan enteros y flotantes (ej: `1.0` es válido para el código `1`) para evitar falsos positivos técnicos.

## Estructura del Reporte de Salida

El archivo Excel generado (`Reporte_Auditoria_Calidad.xlsx`) contiene:

| Pestaña | Contenido | Propósito |
| :--- | :--- | :--- |
| **Resumen** | Métricas generales, fecha de ejecución, nombres de archivos. | Visión general del estado de calidad. |
| **AUDIT_LOG** | Tabla detallada con cada error encontrado: Fila, Variable, Valor, Mensaje. | Guía "To-Do" para corregir los datos. |
| **DATA** | Copia fiel de los datos originales cargados (Excel/CSV). | Referencia cruzada inmediata sin abrir otro archivo. |
| **METADATA_REF**| Diccionario de variables y valores válidos del SPSS. | Consulta rápida de reglas sin abrir SPSS. |

## Hallazgos Técnicos y Mejoras Realizadas

Durante la implementación se identificaron y resolvieron los siguientes puntos clave:

*   **Robustez ante Formatos Numéricos**: Excel a menudo guarda números enteros como flotantes (`5.0`). El validador fue ajustado para tratar `5.0` y `5` como equivalentes al validar contra códigos enteros del SPSS.
*   **Performance**: La validación de rangos se realiza sobre los valores únicos (`unique()`) de cada columna en lugar de iterar fila por fila, lo que mejora drásticamente el rendimiento en archivos grandes.
*   **Feedback Visual**: Se implementaron barras de progreso y métricas en tiempo real en la UI de Streamlit para mejorar la experiencia de usuario durante procesos largos.
