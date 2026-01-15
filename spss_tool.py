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
    Normaliza los nombres con la misma lógica que el Excel.
    """
    var_labels = {}
    value_labels = {}
    
    try:
        text = sps_content.decode('utf-8')
    except:
        text = sps_content.decode('latin-1')

    # VARIABLE LABELS
    var_matches = re.findall(r'VARIABLE LABELS\s+([\w\./_]+)\s+[\'"](.+?)[\'"]', text, re.IGNORECASE)
    for var, label in var_matches:
        # Aplicamos la lógica de normalización solicitada
        clean_var = var.replace('/', '_')
        if '/' in var:
            clean_var = 'P' + var.split('/')[-1]
        var_labels[clean_var] = label

    # VALUE LABELS
    value_blocks = re.findall(r'VALUE LABELS\s+([\w\./_]+)\s+(.+?)\.', text, re.DOTALL | re.IGNORECASE)
    for var, labels_raw in value_blocks:
        clean_var = var.replace('/', '_')
        if '/' in var:
            clean_var = 'P' + var.split('/')[-1]
            
        pairs = re.findall(r"['\"]?(\d+)['\"]?\s+['\"](.+?)['\"]", labels_raw)
        if pairs:
            value_labels[clean_var] = {float(k): v for k, v in pairs}

    return var_labels, value_labels

# --- COMPATIBILIZADOR DE COLUMNAS (Lógica de Doble P) ---

def fix_kobo_columns(df):
    """
    1. Convierte / en _ (Compatibilidad con SPS).
    2. Si hay un grupo, antepone una 'P' al nombre (P1 -> PP1) para evitar duplicados.
    3. Asegura nombres únicos.
    """
    new_names = []
    seen = {}

    for col in df.columns:
        col_str = str(col)
        
        # Lógica solicitada: Si tiene barra, es de grupo.
        if '/' in col_str:
            # P1 dentro de grupo se vuelve PP1
            clean_name = 'P' + col_str.split('/')[-1].replace('/', '_')
        else:
            # Si no tiene barra, solo cambiamos posibles / internos por _
            clean_name = col_str.replace('/', '_')
        
        # Evitar palabra reservada _index
        if clean_name == "_index":
            clean_name = "id_kobo"

        # Verificación final de unicidad (Parche de seguridad)
        if clean_name in seen:
            seen[clean_name] += 1
            clean_name = f"{clean_name}_{seen[clean_name]}"
        else:
            seen[clean_name] = 0
            
        new_names.append(clean_name)
    
    df.columns = new_names
    return df

# --- INTERFAZ DE USUARIO ---

st.title("📊 SPSS Universal Manager")
st.markdown("### Flujo optimizado para Kobo (Excel + SPS) y LimeSurvey")

with st.sidebar:
    st.header("📁 Cargar Archivos")
    data_file = st.file_uploader("1. Archivo de DATOS (.xlsx, .csv, .dat)", type=["xlsx", "csv", "dat", "txt", "sav"])
    sps_file = st.file_uploader("2. Archivo de SINTAXIS (.sps)", type=["sps"])

if data_file:
    try:
        # Carga de datos
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

        # Aplicar compatibilización de nombres (Doble P para grupos)
        df = fix_kobo_columns(df)

        # Procesar Sintaxis
        if sps_file:
            s_vars, s_vals = parse_sps_syntax(sps_file.read())
            var_labels.update(s_vars)
            val_labels.update(s_vals)
            st.sidebar.success("✅ Metadatos vinculados con éxito")

        # Pestañas Jamovi
        tab1, tab2 = st.tabs(["📋 Vista de Datos", "🔍 Vista de Variables"])

        with tab1:
            # Mapeo visual de etiquetas
            df_visual = df.copy()
            for col, mapping in val_labels.items():
                if col in df_visual.columns:
                    try:
                        df_visual[col] = df_visual[col].map(mapping).fillna(df_visual[col])
                    except: pass
            
            st.data_editor(df_visual, width="stretch", num_rows="dynamic")

        with tab2:
            st.subheader("Diccionario de Metadatos")
            meta_df = pd.DataFrame({
                "Variable": df.columns,
                "Etiqueta": [var_labels.get(c, "No encontrada en SPS") for c in df.columns],
                "Valores": ["✅ Sí" if c in val_labels else "❌ No" for c in df.columns]
            })
            st.dataframe(meta_df, width="stretch")

        # Exportar
        if st.button("🚀 Descargar Archivo SAV"):
            labels_list = [var_labels.get(c, "") for c in df.columns]
            output = "datos_finales_etiquetados.sav"
            pyreadstat.write_sav(df, output, column_labels=labels_list, variable_value_labels=val_labels)
            with open(output, "rb") as f:
                st.download_button("⬇️ Descargar SAV", f, file_name="kobo_processed.sav")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Sube tus archivos para comenzar.")
