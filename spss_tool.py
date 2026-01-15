import streamlit as st
import pandas as pd
import pyreadstat
import io
import re

# Configuración estilo Jamovi
st.set_page_config(page_title="SPSS Universal Manager", layout="wide", page_icon="📊")

# --- MOTOR DE TRADUCCIÓN SPS ---

def parse_sps_syntax(sps_content):
    var_labels = {}
    value_labels = {}
    try:
        text = sps_content.decode('utf-8')
    except:
        text = sps_content.decode('latin-1')

    # VARIABLE LABELS
    var_matches = re.findall(r'VARIABLE LABELS\s+([\w\./_]+)\s+[\'"](.+?)[\'"]', text, re.IGNORECASE)
    for var, label in var_matches:
        # Lógica Doble P: si tiene barra en el SPS, buscamos la columna PP
        clean_var = 'P' + var.split('/')[-1] if '/' in var else var
        var_labels[clean_var] = label

    # VALUE LABELS
    value_blocks = re.findall(r'VALUE LABELS\s+([\w\./_]+)\s+(.+?)\.', text, re.DOTALL | re.IGNORECASE)
    for var, labels_raw in value_blocks:
        clean_var = 'P' + var.split('/')[-1] if '/' in var else var
        # REGEX CORREGIDA:
        pairs = re.findall(r"['\"](\d+)['\"]\s+['\"](.+?)['\"]", labels_raw)
        if not pairs: # Intento para códigos sin comillas
            pairs = re.findall(r"(\d+)\s+['\"](.+?)['\"]", labels_raw)
        
        if pairs:
            value_labels[clean_var] = {float(k): v for k, v in pairs}

    return var_labels, value_labels

# --- COMPATIBILIZADOR DE COLUMNAS ---

def process_columns(df):
    """
    Aplica la regla de la Doble P de forma conservadora para evitar duplicados.
    """
    new_names = []
    for col in df.columns:
        col_str = str(col)
        if '/' in col_str:
            # Caso grupo: seccion/P1 -> PP1
            clean_name = 'P' + col_str.split('/')[-1]
        else:
            # Caso normal: P5_1 -> se queda igual
            clean_name = col_str
        
        # Streamlit reserva '_index', lo evitamos
        if clean_name == "_index":
            clean_name = "id_kobo"
            
        new_names.append(clean_name)
    
    df.columns = new_names
    return df

# --- INTERFAZ ---

st.title("📊 SPSS Universal Manager")
st.subheader("Cuesta Blanca 2025 - Flujo Seguro")

with st.sidebar:
    st.header("📁 Carga de Archivos")
    data_file = st.file_uploader("1. Datos (Excel/CSV)", type=["xlsx", "csv", "dat", "sav"])
    sps_file = st.file_uploader("2. Sintaxis (.sps)", type=["sps"])

if data_file:
    try:
        # Carga
        if data_file.name.endswith('.csv'):
            df = pd.read_csv(data_file)
        elif data_file.name.endswith('.xlsx'):
            df = pd.read_excel(data_file)
        elif data_file.name.endswith('.sav'):
            raw_bytes = data_file.read()
            df, meta = pyreadstat.read_sav(io.BytesIO(raw_bytes))
        else:
            df = pd.read_csv(data_file, sep=None, engine='python')

        # Procesar columnas con la lógica de la Doble P
        df = process_columns(df)
        
        var_labels, val_labels = {}, {}
        if sps_file:
            var_labels, val_labels = parse_sps_syntax(sps_file.read())
            st.sidebar.success("✅ Sintaxis vinculada")

        tab1, tab2 = st.tabs(["📋 Hoja de Datos", "🔍 Vista de Variables"])

        with tab1:
            df_visual = df.copy()
            # Mapeo visual de etiquetas (1 -> Sí)
            for col, mapping in val_labels.items():
                if col in df_visual.columns:
                    try:
                        df_visual[col] = df_visual[col].map(mapping).fillna(df_visual[col])
                    except: pass
            
            st.data_editor(df_visual, width="stretch")

        with tab2:
            st.subheader("Diccionario de Variables")
            meta_df = pd.DataFrame({
                "Columna": df.columns,
                "Etiqueta": [var_labels.get(c, "No definida en SPS") for c in df.columns]
            })
            st.dataframe(meta_df, width="stretch")

        if st.button("🚀 Generar Archivo SPSS (.sav)"):
            output = "datos_finales.sav"
            labels_list = [var_labels.get(c, "") for c in df.columns]
            pyreadstat.write_sav(df, output, column_labels=labels_list, variable_value_labels=val_labels)
            with open(output, "rb") as f:
                st.download_button("⬇️ Descargar SAV", f, file_name="Cuesta_Blanca_Etiquetado.sav")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Carga tus archivos para comenzar.")
