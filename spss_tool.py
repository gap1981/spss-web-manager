import streamlit as st
import pandas as pd
import pyreadstat
import io
import re
import os

# Configuración de pantalla completa estilo Jamovi
st.set_page_config(page_title="SPSS Web Manager Pro", layout="wide", page_icon="📊")

# --- LÓGICA DE PROCESAMIENTO ---

def parse_sps_syntax(sps_content):
    """
    Extrae etiquetas de variables y de valores desde un archivo .sps.
    Maneja codificaciones mixtas para evitar caracteres rotos.
    """
    var_labels = {}
    value_labels = {}
    
    try:
        text = sps_content.decode('utf-8')
    except:
        text = sps_content.decode('latin-1')

    # VARIABLE LABELS: Extrae el nombre y la descripción
    var_matches = re.findall(r'VARIABLE LABELS\s+([\w\.]+)\s+"(.+?)"', text, re.IGNORECASE)
    for var, label in var_matches:
        # Limpieza de nombres de Kobo: grupo/pregunta -> pregunta
        clean_var = var.split('/')[-1]
        var_labels[clean_var] = label

    # VALUE LABELS: Mapea códigos numéricos a texto (ej: 1 -> "Sí")
    value_blocks = re.findall(r'VALUE LABELS\s+([\w\.]+)\s+(.+?)\.', text, re.DOTALL | re.IGNORECASE)
    for var, labels_raw in value_blocks:
        clean_var = var.split('/')[-1]
        pairs = re.findall(r'(\d+)\s+"(.+?)"', labels_raw)
        if pairs:
            # SPSS usa floats internamente para códigos numéricos
            value_labels[clean_var] = {float(k): v for k, v in pairs}

    return var_labels, value_labels

def clean_dataframe(df):
    """
    Limpia el dataframe de nombres reservados y prefijos de grupo.
    """
    # 1. Eliminar prefijos de grupos de Kobo en los nombres de columnas
    df.columns = [col.split('/')[-1] for col in df.columns]
    
    # 2. SOLUCIÓN AL ERROR: Renombrar '_index' porque Streamlit lo reserva
    if "_index" in df.columns:
        df = df.rename(columns={"_index": "id_fila_kobo"})
    
    return df

# --- INTERFAZ GRÁFICA ---

st.title("📊 SPSS Web Manager (Kobo & LimeSurvey)")
st.markdown("---")

with st.sidebar:
    st.header("📁 Carga de Archivos")
    tipo_origen = st.selectbox("Selecciona tu flujo:", 
                               ["KoboToolbox (XLSX + SPS)", 
                                "LimeSurvey (DAT + SPS)", 
                                "SAV Existente (Arreglar etiquetas)"])
    
    uploaded_data = st.file_uploader("1. Archivo de DATOS (.xlsx, .dat, .sav)", type=["xlsx", "dat", "sav", "csv"])
    uploaded_sps = st.file_uploader("2. Archivo de SINTAXIS (.sps)", type=["sps"])
    
    st.markdown("---")
    st.caption("v2.1 - Compatible con Android y PC")

if uploaded_data:
    df = pd.DataFrame()
    var_labels, val_labels = {}, {}
    
    # --- 1. CARGA SEGÚN ORIGEN ---
    try:
        if tipo_origen == "KoboToolbox (XLSX + SPS)":
            df = pd.read_excel(uploaded_data)
            df = clean_dataframe(df)
            
        elif tipo_origen == "LimeSurvey (DAT + SPS)":
            # Detectar si el .dat es CSV o ancho fijo (por defecto CSV/TSV)
            df = pd.read_csv(uploaded_data, sep=None, engine='python')
            df = clean_dataframe(df)
            
        elif tipo_origen == "SAV Existente (Arreglar etiquetas)":
            raw_bytes = uploaded_data.read()
            try:
                # Intento UTF-8 solicitado
                df, meta = pyreadstat.read_sav(io.BytesIO(raw_bytes), encoding="utf-8")
                # Si detectamos etiquetas rotas (Ã), forzamos fallback
                if any("Ã" in str(l) for l in meta.column_labels): raise Exception()
            except:
                # Fallback Latin-1 solicitado
                df, meta = pyreadstat.read_sav(io.BytesIO(raw_bytes), encoding="latin-1")
            
            df = clean_dataframe(df)
            var_labels = dict(zip(df.columns, meta.column_labels))
            val_labels = meta.variable_value_labels

        # --- 2. PROCESAR SINTAXIS (.SPS) ---
        if uploaded_sps:
            sps_var_labels, sps_val_labels = parse_sps_syntax(uploaded_sps.read())
            var_labels.update(sps_var_labels)
            val_labels.update(sps_val_labels)
            st.sidebar.success("✅ Sintaxis SPS cargada correctamente")

        # --- 3. VISTA JAMOVI (Pestañas) ---
        tab_data, tab_vars = st.tabs(["📋 Hoja de Datos", "🔍 Vista de Variables"])

        with tab_data:
            # Crear copia visual con etiquetas aplicadas (1 -> Sí)
            df_visual = df.copy()
            for col, mapping in val_labels.items():
                if col in df_visual.columns:
                    df_visual[col] = df_visual[col].map(mapping).fillna(df_visual[col])
            
            st.subheader("Editor de Datos")
            # Usando width="stretch" para evitar avisos de deprecación
            edited_df = st.data_editor(df_visual, width="stretch", num_rows="dynamic")

        with tab_vars:
            st.subheader("Diccionario de Metadatos")
            var_info = {
                "Variable": df.columns,
                "Etiqueta (Label)": [var_labels.get(c, "Sin etiqueta") for c in df.columns],
                "Diccionario de Valores": ["✅ Sí" if c in val_labels else "❌ No" for c in df.columns]
            }
            st.dataframe(pd.DataFrame(var_info), width="stretch")

        # --- 4. EXPORTACIÓN ---
        st.markdown("---")
        if st.button("🚀 Generar y Descargar archivo SPSS (.sav)"):
            output_path = "resultado_final.sav"
            
            # Reconstruimos la lista de etiquetas para pyreadstat
            labels_list = [var_labels.get(c, "") for c in df.columns]
            
            pyreadstat.write_sav(
                df, # Guardamos el original (numérico)
                output_path,
                column_labels=labels_list,
                variable_value_labels=val_labels
            )
            
            with open(output_path, "rb") as f:
                st.download_button("⬇️ Descargar SAV Etiquetado", f, file_name="spss_fix_final.sav")

    except Exception as e:
        st.error(f"Error al procesar los archivos: {e}")
        st.info("Asegúrate de que las columnas del archivo de datos coincidan con los nombres en el archivo .sps")

else:
    # Pantalla de bienvenida
    st.warning("⚠️ Esperando carga de archivos...")
    st.markdown("""
    ### Cómo usar esta herramienta:
    1. **Selecciona el origen** en la izquierda (Kobo, LimeSurvey o SAV).
    2. **Sube el archivo de datos** (Excel o DAT).
    3. **Sube el archivo .sps** (La sintaxis que contiene las etiquetas).
    4. **Revisa y edita** en la tabla central.
    5. **Descarga** tu archivo .sav listo para cualquier software estadístico.
    """)
