import streamlit as st
import pandas as pd
import pyreadstat
import io
import re

# --- MOTOR UNIVERSAL DE ETIQUETADO ---

def parse_sps_syntax(sps_content):
    """Extrae metadatos de archivos .sps (Kobo o LimeSurvey)"""
    var_labels = {}
    value_labels = {}
    try:
        text = sps_content.decode('utf-8')
    except:
        text = sps_content.decode('latin-1')

    # Extraer VARIABLE LABELS
    var_matches = re.findall(r'VARIABLE LABELS\s+(\w+)\s+"(.+?)"', text, re.IGNORECASE)
    for var, label in var_matches:
        var_labels[var] = label

    # Extraer VALUE LABELS (Mapeo de códigos a texto)
    value_blocks = re.findall(r'VALUE LABELS\s+(\w+)\s+(.+?)\.', text, re.DOTALL | re.IGNORECASE)
    for var, labels_raw in value_blocks:
        pairs = re.findall(r'(\d+)\s+"(.+?)"', labels_raw)
        if pairs:
            value_labels[var] = {float(k): v for k, v in pairs}
            
    return var_labels, value_labels

# --- INTERFAZ MULTI-HERRAMIENTA ---

st.set_page_config(page_title="SPSS Web Manager Pro", layout="wide")
st.title("📊 Gestor SPSS Universal")

with st.sidebar:
    st.header("⚙️ Configuración de Entrada")
    tipo_flujo = st.selectbox("Selecciona el origen:", 
        ["Kobo (XLSX + SPS)", "LimeSurvey (DAT + SPS)", "Corregir SAV Existente"])
    
    uploaded_data = st.file_uploader("Cargar archivo de DATOS", type=["xlsx", "dat", "sav"])
    uploaded_sps = st.file_uploader("Cargar archivo de SINTAXIS (.sps)", type=["sps"])

if uploaded_data:
    df = pd.DataFrame()
    var_labels, val_labels = {}, {}
    
    # 1. CARGA DE DATOS SEGÚN ORIGEN
    if tipo_flujo == "Kobo (XLSX + SPS)":
        df = pd.read_excel(uploaded_data)
    elif tipo_flujo == "LimeSurvey (DAT + SPS)":
        # LimeSurvey suele usar CSV o TXT en el .dat
        df = pd.read_csv(uploaded_data, sep=None, engine='python')
    elif tipo_flujo == "Corregir SAV Existente":
        # Usamos la lógica de fallback de codificación que solicitaste
        bytes_data = uploaded_data.read()
        try:
            df, meta = pyreadstat.read_sav(io.BytesIO(bytes_data), encoding="utf-8")
        except:
            df, meta = pyreadstat.read_sav(io.BytesIO(bytes_data), encoding="latin-1")
        var_labels = dict(zip(meta.column_names, meta.column_labels))
        val_labels = meta.variable_value_labels

    # 2. APLICAR SINTAXIS SI EXISTE
    if uploaded_sps:
        sps_var_labels, sps_val_labels = parse_sps_syntax(uploaded_sps.read())
        var_labels.update(sps_var_labels)
        val_labels.update(sps_val_labels)
        st.sidebar.success("✅ Sintaxis aplicada")

    # --- VISTA ESTILO JAMOVI ---
    tab_data, tab_vars = st.tabs(["📋 Datos", "🔍 Variables"])

    with tab_data:
        # Aplicamos etiquetas de valor para que se vea el texto (ej. "Hombre")
        df_visual = df.copy()
        for col, mapping in val_labels.items():
            if col in df_visual.columns:
                df_visual[col] = df_visual[col].map(mapping).fillna(df_visual[col])
        
        st.subheader("Hoja de Datos (Jamovi Style)")
        st.data_editor(df_visual, use_container_width=True)

    with tab_vars:
        st.subheader("Diccionario de Metadatos")
        # Mostrar qué tiene etiqueta y qué no
        meta_df = pd.DataFrame({
            "Variable": df.columns,
            "Etiqueta": [var_labels.get(c, c) for c in df.columns],
            "Diccionario": ["✅ OK" if c in val_labels else "❌ No" for c in df.columns]
        })
        st.dataframe(meta_df, use_container_width=True)

    # 3. EXPORTACIÓN FINAL A SPSS (.sav)
    if st.button("💾 Exportar a .SAV (Formato IBM SPSS)"):
        # pyreadstat necesita etiquetas en orden de columnas
        labels_list = [var_labels.get(c, "") for c in df.columns]
        output = "archivo_final.sav"
        pyreadstat.write_sav(df, output, column_labels=labels_list, variable_value_labels=val_labels)
        
        with open(output, "rb") as f:
            st.download_button("⬇️ Descargar SAV Etiquetado", f, file_name="spss_listo.sav")
