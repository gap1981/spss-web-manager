5# 📘 Manual de Usuario: SPSS Web Tool Manager

Bienvenido al **SPSS Web Tool Manager**, una herramienta integral diseñada para gestionar, editar y auditar archivos de datos SPSS (`.sav`) directamente desde tu navegador, sin necesidad de licencias de software propietario.

## 🚀 Inicio Rápido

La aplicación se divide en tres módulos principales, accesibles desde el menú lateral (si está desplegado) o mediante las opciones de navegación:

1.  **Herramienta SPSS (Manager/Exporter)**: Para visualización rápida, edición ligera de metadatos y exportación.
2.  **Editor Avanzado**: Para modificar datos celda por celda, agregar/borrar variables y ediciones profundas.
3.  **Auditoría y Validación**: Para asegurar la calidad de los datos comparando archivos de campo (Excel) contra un patrón (SPSS).

---

## 1. Herramienta SPSS (Manager/Exporter)

Este módulo es ideal para revisar la estructura de un archivo y prepararlo para análisis o entrega.

### 📥 Carga de Archivos
*   Arrastra tu archivo `.sav` al área de carga o haz clic en "Browse files".
*   Una vez cargado, verás una confirmación con el número de columnas y registros.

### 👁️ Visualización y Estructura
*   **Pestaña "Ver Datos"**: Muestra una vista previa de las primeras 20 filas.
*   **Pestaña "Ver Estructura"**: Tabla detallada con:
    *   Tipo de variable (Numérica/Texto).
    *   Formato y Ancho.
    *   Etiquetas de Variable y Valores.
    *   *Tip:* Usa el buscador para encontrar variables específicas rápidamente.

### ✏️ Edición de Etiquetas y Selección
En la pestaña **"Editar Variables"**:
1.  **Selección**: Usa el panel izquierdo para elegir qué columnas conservar. Puedes "Seleccionar Todas" o buscar específicas.
2.  **Edición**: En el panel derecho, cambia las **Etiquetas de Variable** directamente.
3.  Haz clic en **"Guardar Etiquetas"** para aplicar los cambios.

### 📖 Libro de Códigos
Genera un diccionario de datos automático en Excel.
*   Ve a la pestaña **"Libro de Códigos"**.
*   Configura si deseas incluir estadísticas (válidos/perdidos).
*   Haz clic en **"Descargar Libro de Códigos"** para obtener un Excel detallado.

### 💾 Exportación
En la barra lateral (izquierda):
*   **Excel**: Elige si quieres encabezados con "Nombres cortos" (ej: `P1`) o "Etiquetas largas" (ej: `Pregunta 1: Edad`).
*   **SPSS**: Descarga una versión limpia y optimizada de tu archivo `.sav`.

---

## 2. Editor Avanzado

Usa este módulo cuando necesites intervenir los datos a nivel de celda o estructura profunda.

### 🛠️ Funciones Principales
*   **Carga Independiente**: Puedes cargar un archivo diferente al del módulo anterior.
*   **Barra de Herramientas**:
    *   **➕ Nueva Variable**: Crea una columna nueva (se llena con 0 por defecto).
    *   **🗑️ Borrar**: Elimina múltiples variables seleccionadas de forma permanente.
    *   **💾 Guardar**: Descarga el archivo `.sav` modificado.

### 📝 Edición de Datos
*   **Pestaña "Vista de Datos"**: Funciona como una hoja de cálculo. Haz doble clic en cualquier celda para editar su valor.
*   **Pestaña "Vista de Variables"**: Edita las etiquetas y los *Value Labels* (en formato JSON) de forma masiva.
*   *Nota*: La interfaz incluye bloques informativos contextuales en cada pestaña para facilitar su uso.

---

## 3. Auditoría y Validación de Datos 🛡️

Este módulo asegura que los datos recolectados en campo (Excel/CSV) cumplan con el estándar definido en tu archivo SPSS.

### ⚙️ Cómo Funciona
Requieres dos archivos:
1.  **Patrón (SPSS)**: El archivo que define cómo *deberían* ser los datos (variables obligatorias, tipos, valores válidos).
2.  **Datos (Excel/CSV)**: El archivo que recibes del equipo de campo o proveedor.

### 🚦 Proceso de Auditoría
1.  Carga ambos archivos en sus respectivas áreas.
2.  Haz clic en **"Ejecutar Validación Completa"**.
3.  El sistema verificará:
    *   **Estructura**: Que no falten variables obligatorias.
    *   **Tipos**: Que no haya texto en campos numéricos.
    *   **Rangos**: Que los valores coincidan con las etiquetas definidas en el SPSS (mostrando el mensaje "Dato no definido dentro de las etiquetas").
    *   **Orden de ID**: Valida que columnas tipo "id" o "encuesta" estén ordenadas.
    *   **Teléfonos Duplicados**: Advierte si encuentra números repetidos en campos tipo "tel" o "celular".

### 📊 Resultados y Exportación Avanzada
*   Verás métricas en pantalla (Errores Críticos, Advertencias) y una tabla interactiva resumida.
*   **Selección de Eliminación**: Si hay columnas en el Excel original que ya no deseas en la base final, puedes seleccionarlas en un menú desplegable para eliminarlas *antes* de exportar.
*   **Descarga de Resultados (Sin Limitaciones)**:
    *   **Reporte de Hallazgos (.xlsx)**: Exporta una lista exacta de errores, los datos validados y los metadatos para referencia.
    *   **Datos + Estructura (.sav)**: Genera y descarga instantáneamente tu nuevo archivo SPSS combinando los datos del proveedor (Excel) con las reglas y estructura de tu padrón original, integrando los ajustes realizados en el acto. Esta opción siempre está disponible independientemente de la cantidad de errores encontrados.

---

## 4. Data Storytelling (Beta) 📈

Convierte tus datos en narrativa visual de forma automática. Ideal para presentaciones rápidas de encuestas.

### 🎯 Mapeo de Variables
Al ingresar, debes asignar qué columna de tu archivo cumple cada rol semántico:
*   **Género**: Variable categórica (Hombre/Mujer).
*   **Edad**: Variable numérica (la herramienta creará rangos automáticamente).
*   **Zona**: Variable geográfica para control de cuotas.
*   **Variables de Interés**: Las preguntas de intención de voto o imagen que quieres graficar.

### 🧩 Pestañas de Análisis
1.  **Control de Muestra**: Tabla cruzada (Zona x Género x Rango Edad) para verificar si cumples con las cuotas del diseño muestral. Exportable a CSV.
2.  **Demográficos**: Gráficos pre-diseñados de distribución de género y edad.
3.  **Escenarios**: Gráficos de barras para cada variable de voto seleccionada, con porcentajes calculados automáticamente.
4.  **Cruces**: La función más potente. Elige una variable de corte (ej: Género) y mira cómo votan los distintos segmentos (Hombres vs Mujeres).

