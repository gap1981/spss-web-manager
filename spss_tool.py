import streamlit as st
import pandas as pd
import pyreadstat
import io
import os

# Configuración de página estilo Jamovi (Ancho completo)
st.set_page_config(page_title="SPSS Web Manager", layout="wide", page_icon="📊")

# --- FUNCIONES DE LÓGICA DE DATOS ---

def load_spss_file(file_content, encoding=None):
    """
    Carga robusta con fallback automático para evitar errores de codificación
    especialmente útil para archivos provenientes de KoboToolbox.
    """
    try:
        # Intento 1: UTF-8 (Estándar moderno y Kobo)
        df, meta = pyreadstat.read_sav(io.BytesIO(file_content), encoding=encoding or "utf-8")
        
        # Validación: Si detectamos caracteres rotos típicos de UTF-8 leído como Latin-1
        if any("Ã" in str(l) for l in meta.column_labels if l):
             raise UnicodeDecodeError("utf-8", b"", 0, 1, "Etiquetas corruptas detectadas")
        return df, meta
    except Exception:
        # Fallback a Latin-1 (Archivos antiguos o mal codificados)
        df, meta = pyreadstat.read_sav(io.BytesIO(file_content), encoding="latin-1")
        return df, meta

def apply_kobo_labels(df, meta, xlsform_file):
    """
    Toma un XLSForm y aplica las etiquetas correctas al DataFrame de SPSS.
    Resuelve el problema de nombres de columnas largos y etiquetas rotas.
    """
    try:
        xls = pd.ExcelFile(xlsform_file)
        survey = pd.read_excel(xls, 'survey')
        # Limpieza básica de nombres de columnas de Kobo (quita prefijos de grupos)
        # Ejemplo: 'datos_personales/nombre' -> 'nombre'
        clean_names = {col: col.split('/')[-1] for col in df.columns}
        df = df.rename(columns=clean_names)
        
        # Mapeo de etiquetas desde el XLSForm
        label_map = dict(zip(survey['name'], survey['label']))
        new_labels = [label_map.get(col, col) for col in df.columns]
        
        return df, new_labels
    except Exception as e:
        st.error(f"Error procesando XLSForm: {e}")
        return df, meta.column_labels

# --- INTERFAZ DE USUARIO ---

st.title("📊 SPSS Data Manager & Kobo Fixer")
st.markdown("---")

# Barra lateral: Carga de Archivos
with st.sidebar:
    st.header("📁 Carga de Archivos")
    source = st.radio("Fuente de datos:", ["Archivo SAV Estándar", "KoboToolbox (SAV + XLSForm)", "LimeSurvey (.dat + .sps)"])
    
    uploaded_sav = st.file_uploader("Cargar archivo .sav", type=["sav"])
    
    xlsform = None
    if source == "KoboToolbox (SAV + XLSForm)":
        xlsform = st.file_uploader("Cargar XLSForm (Diseño)", type=["xlsx"])

# Lógica Principal de Visualización
if uploaded_sav:
    # 1. Cargar el archivo con la lógica de fallback solicitada
    sav_bytes = uploaded_sav.read()
    df, meta = load_spss_file(sav_bytes)
    
    # 2. Si es Kobo, intentar mejorar las etiquetas
    column_labels = meta.column_labels
    if xlsform:
        df, column_labels = apply_kobo_labels(df, meta, xlsform)
        st.sidebar.success("✅ XLSForm aplicado con éxito")

    # --- PESTAÑAS ESTILO JAMOVI ---
    tab_data, tab_vars = st.tabs(["📋 Hoja de Datos", "🔍 Vista de Variables"])

    with tab_data:
        st.subheader("Editor de Datos")
        # El data_editor permite editar celdas directamente
        edited_df = st.data_editor(
            df, 
            use_container_width=True, 
            num_rows="dynamic",
            key="main_editor"
        )

    with tab_vars:
        st.subheader("Diccionario de Variables (Metadatos)")
        # Creamos una tabla similar a la de Jamovi/SPSS Variable View
        var_info = {
            "Variable": edited_df.columns,
            "Etiqueta de Variable": column_labels if len(column_labels) == len(edited_df.columns) else ["N/A"] * len(edited_df.columns),
            "Medida": [meta.variable_measure.get(c, "unknown") for c in meta.column_names],
            "Tipo": [meta.original_variable_types.get(c, "unknown") for c in meta.column_names]
        }
        st.dataframe(pd.DataFrame(var_info), use_container_width=True)

    # --- BOTONES DE ACCIÓN (EXPORTACIÓN) ---
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Generar nuevo archivo SPSS (.sav)"):
            output_name = "datos_corregidos.sav"
            # Guardamos con las etiquetas (labels) que extrajimos/corregimos
            pyreadstat.write_sav(
                edited_df, 
                output_name, 
                column_labels=column_labels,
                variable_value_labels=meta.variable_value_labels
            )
            with open(output_name, "rb") as f:
                st.download_button(
                    label="⬇️ Descargar SAV Corregido",
                    data=f,
                    file_name=output_name,
                    mime="application/octet-stream"
                )
    
    with col2:
        # Opción extra rápida para Excel
        csv = edited_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "⬇️ Exportar a CSV (Excel)",
            csv,
            "data_output.csv",
            "text/csv"
        )
else:
    # Pantalla de bienvenida
    st.info("👋 Bienvenida/o. Por favor, carga un archivo .sav en el panel izquierdo para comenzar.")
    st.image("https://www.jamovi.org/assets/img/jamovi-preview.png", caption="Interfaz inspirada en jamovi", width=600)

# Footer responsivo para Android
st.sidebar.markdown("---")
st.sidebar.caption("SPSS Web Manager v2.0 | Optimizada para PC y Android")
