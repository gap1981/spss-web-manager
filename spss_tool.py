import streamlit as st
import pandas as pd
import pyreadstat
import io
import re

# Configuración de interfaz estilo Jamovi
st.set_page_config(page_title="SPSS Web Manager Pro", layout="wide", page_icon="📊")

# --- MOTOR DE TRADUCCIÓN SPS ---

def parse_sps_syntax(sps_content):
    """
    Extrae etiquetas de variables y de valores desde un archivo .sps.
    """
    var_labels = {}
    value_labels = {}
    
    try:
        text = sps_content.decode('utf-8')
    except:
        text = sps_content.decode('latin-1')

    # VARIABLE LABELS: Captura nombres y etiquetas
    var_matches = re.findall(r'VARIABLE LABELS\s+([\w\./_]+)\s+[\'"](.+?)[\'"]', text, re.IGNORECASE)
    for var, label in var_matches:
        clean_var = var.split('/')[-1].replace('/', '_')
        var_labels[clean_var] = label

    # VALUE LABELS: Mapea códigos a etiquetas (Ej: 1 'Hombre')
    value_blocks = re.findall(r'VALUE LABELS\s+([\w\./_]+)\s+(.+?)\.', text, re.DOTALL | re.IGNORECASE)
    for var, labels_raw in value_blocks:
        clean_var = var.split('/')[-1].replace('/', '_')
        # Regex corregida para evitar el SyntaxError
        pairs = re.findall(r"['\"]?(\d+)['\"]?\s+['\"](.+?)['\"]", labels_raw)
        if pairs:
            value_labels[clean_var] = {float(k): v for k, v in pairs}

    return var_labels, value_labels

# --- COMPATIBILIZADOR DE COLUMNAS (MEJORADO) ---

def fix_kobo_columns(df):
    """
    Normaliza nombres de Kobo:
    1. Cambia / por _ para coincidir con SPS.
    2. Evita crear duplicados si ya existen columnas con _.
    """
    new_names = []
    # Primero identificamos qué nombres ya existen para no duplicar
    existing_names = set(df.columns)
    
    for col in df.columns:
        # Intentar normalizar: quitar grupo y cambiar / por _
        base_name = str(col).split('/')[-1]
        clean_name = base_name.replace('/', '_')
        
        # Si el nombre limpio es distinto al original pero YA EXISTE en el DF, 
        # mantenemos el original para no chocar.
        if clean_name != col and clean_name in existing_names:
            final_name = str(col)
        else:
            final_name = clean_name

        # Evitar palabra reservada _index de Streamlit
        if final_name == "_index":
            final_name = "id_kobo"
            
        new_names.append(final_name)
    
    df.columns = new_names
    return df

# --- INTERFAZ DE USUARIO ---

st.title("📊 SPSS Web Manager (Kobo & LimeSurvey)")
st.markdown("---")

with st.sidebar:
    st.header("📁 Carga de Archivos")
    origen = st.selectbox("Flujo de trabajo:", 
                          ["KoboToolbox (Excel/CSV + SPS)", 
                           "LimeSurvey (DAT/CSV + SPS)", 
                           "SAV Local (Arreglar Codificación)"])
    
    data_file = st.file_uploader("1. Archivo de DATOS", type=["xlsx", "csv", "dat", "sav", "txt"])
    sps_file = st.file_uploader("2. Archivo de SINTAXIS (.sps)", type=["sps"])

if data_file:
    try:
        # A. Lectura de datos
        if data_file.name.endswith('.sav'):
            raw_bytes = data_file.read()
            try:
                df, meta = pyreadstat.read_sav(io.BytesIO(raw_bytes), encoding="utf-8")
            except:
                df, meta = pyreadstat.read_sav(io.BytesIO(raw_bytes), encoding="latin-1")
            var_labels = dict(zip(df.columns, meta.column_labels))
            val_labels = meta.variable_value_labels
        elif data_file.name.endswith('.xlsx'):
            df = pd.read_excel(data_file)
            var_labels, val_labels = {}, {}
        else:
            df = pd.read_csv(data_file, sep=None, engine='python')
            var_labels, val_labels = {}, {}

        # B. Compatibilizar columnas
        df = fix_kobo_columns(df)

        # C. Procesar Sintaxis SPS
        if sps_file:
            sps_vars, sps_vals = parse_sps_syntax(sps_file.read())
            var_labels.update(sps_vars)
            val_labels.update(sps_vals)
            st.sidebar.success(f"✅ Metadatos vinculados")

        # D. Vista Estilo Jamovi
        tab1, tab2 = st.tabs(["📋 Hoja de Datos", "🔍 Vista de Variables"])

        with tab1:
            df_visual = df.copy()
            for col, mapping in val_labels.items():
                if col in df_visual.columns:
                    try:
                        # Mapeo de códigos numéricos a etiquetas de texto
                        df_visual[col] = df_visual[col].map(mapping).fillna(df_visual[col])
                    except: pass
            
            st.subheader("Editor de Datos")
            st.data_editor(df_visual, width="stretch", num_rows="dynamic")

        with tab2:
            st.subheader("Diccionario de Metadatos")
            meta_df = pd.DataFrame({
                "Variable": df.columns,
                "Etiqueta": [var_labels.get(c, "Sin etiqueta") for c in df.columns],
                "Valores": ["✅ Sí" if c in val_labels else "❌ No" for c in df.columns]
            })
            st.dataframe(meta_df, width="stretch")

        # E. Exportación
        if st.button("🚀 Generar y Descargar SAV"):
            output_name = "resultado_final.sav"
            labels_list = [var_labels.get(c, "") for c in df.columns]
            pyreadstat.write_sav(df, output_name, column_labels=labels_list, variable_value_labels=val_labels)
            with open(output_name, "rb") as f:
                st.download_button("⬇️ Descargar SAV", f, file_name="proyecto_final.sav")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("👋 Sube tu archivo de datos para comenzar.")
   
