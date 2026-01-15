import streamlit as st
import pandas as pd
import pyreadstat
import io
import re

# Configuración estilo Jamovi
st.set_page_config(page_title="SPSS Web Manager Pro", layout="wide", page_icon="📊")

# --- MOTOR DE TRADUCCIÓN SPS ---

def parse_sps_syntax(sps_content):
    var_labels = {}
    value_labels = {}
    try:
        text = sps_content.decode('utf-8')
    except:
        text = sps_content.decode('latin-1')

    # VARIABLE LABELS: Captura exacta del nombre tal cual aparece tras el '/'
    var_matches = re.findall(r'VARIABLE LABELS\s+([\w\./_]+)\s+[\'"](.+?)[\'"]', text, re.IGNORECASE)
    for var, label in var_matches:
        # Si tiene grupo en el SPS, aplicamos la regla de la Doble P
        clean_var = 'P' + var.split('/')[-1] if '/' in var else var
        var_labels[clean_var] = label

    # VALUE LABELS
    value_blocks = re.findall(r'VALUE LABELS\s+([\w\./_]+)\s+(.+?)\.', text, re.DOTALL | re.IGNORECASE)
    for var, labels_raw in value_blocks:
        clean_var = 'P' + var.split('/')[-1] if '/' in var else var
        pairs = re.findall(r"['\"]?(\d+)['\"]?\s+['\"](.+?)[\'"]", labels_raw)
        if pairs:
            value_labels[clean_var] = {float(k): v for k, v in pairs}

    return var_labels, value_labels

# --- COMPATIBILIZADOR DE EXCEL ---

def process_kobo_columns(df):
    """
    Aplica la regla de la Doble P: 
    Si la columna tiene '/', se vuelve 'P' + nombre.
    Si NO tiene '/', se queda EXACTAMENTE igual.
    """
    new_names = []
    for col in df.columns:
        col_str = str(col)
        if '/' in col_str:
            # Caso grupo: encuesta/P1 -> PP1
            clean_name = 'P' + col_str.split('/')[-1]
        else:
            # Caso normal: P5_1 -> se queda como P5_1
            clean_name = col_str
        
        # Evitar el nombre reservado de Streamlit
        if clean_name == "_index":
            clean_name = "id_kobo"
            
        new_names.append(clean_name)
    
    df.columns = new_names
    return df

# --- INTERFAZ ---

st.title("📊 SPSS Universal Manager")
st.subheader("Cuesta Blanca 2025 - Flujo Optimizado")

with st.sidebar:
    st.header("📁 Carga")
    data_file = st.file_uploader("1. Subir Datos (Excel/CSV)", type=["xlsx", "csv", "dat"])
    sps_file = st.file_uploader("2. Subir Sintaxis (.sps)", type=["sps"])

if data_file:
    # Cargar el archivo (CSV o Excel)
    if data_file.name.endswith('.csv'):
        df = pd.read_csv(data_file)
    elif data_file.name.endswith('.xlsx'):
        df = pd.read_excel(data_file)
    else:
        df = pd.read_csv(data_file, sep=None, engine='python')

    # PROCESO: Cambiamos nombres según tu regla
    df = process_kobo_columns(df)
    
    var_labels, val_labels = {}, {}
    if sps_file:
        var_labels, val_labels = parse_sps_syntax(sps_file.read())
        st.sidebar.success(f"✅ Sintaxis vinculada")

    tab1, tab2 = st.tabs(["📋 Hoja de Datos", "🔍 Vista de Variables"])

    with tab1:
        # Mapeo visual de etiquetas para el usuario
        df_visual = df.copy()
        for col, mapping in val_labels.items():
            if col in df_visual.columns:
                try:
                    df_visual[col] = df_visual[col].map(mapping).fillna(df_visual[col])
                except: pass
        
        st.data_editor(df_visual, width="stretch")

    with tab2:
        st.subheader("Diccionario extraído")
        meta_summary = pd.DataFrame({
            "Variable": df.columns,
            "Etiqueta": [var_labels.get(c, "No definida") for c in df.columns]
        })
        st.dataframe(meta_summary, width="stretch")

    if st.button("🚀 Descargar SAV Final"):
        output = "cuesta_blanca_etiquetado.sav"
        labels_list = [var_labels.get(c, "") for c in df.columns]
        pyreadstat.write_sav(df, output, column_labels=labels_list, variable_value_labels=val_labels)
        with open(output, "rb") as f:
            st.download_button("⬇️ Descargar SAV", f, file_name="cuesta_blanca_2025.sav")
else:
    st.info("Sube tus archivos para iniciar.")
