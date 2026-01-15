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
    Normaliza los nombres para que coincidan con la limpieza del Excel.
    """
    var_labels = {}
    value_labels = {}
    
    try:
        text = sps_content.decode('utf-8')
    except:
        text = sps_content.decode('latin-1')

    # VARIABLE LABELS: Captura nombres y etiquetas
    # Usamos regex que tolera nombres de variables con puntos, barras y guiones
    var_matches = re.findall(r'VARIABLE LABELS\s+([\w\./_]+)\s+[\'"](.+?)[\'"]', text, re.IGNORECASE)
    for var, label in var_matches:
        # Normalización coherente: P2/1 -> P2_1
        clean_var = var.split('/')[-1].replace('/', '_')
        var_labels[clean_var] = label

    # VALUE LABELS: Mapea códigos a etiquetas (Ej: 1 'Hombre')
    value_blocks = re.findall(r'VALUE LABELS\s+([\w\./_]+)\s+(.+?)\.', text, re.DOTALL | re.IGNORECASE)
    for var, labels_raw in value_blocks:
        clean_var = var.split('/')[-1].replace('/', '_')
        pairs = re.findall(r"['\"]?(\d+)['\"]?\s+['\"](.+?)[\'"]", labels_raw)
        if pairs:
            # SPSS usa números como floats en pandas tras lectura
            value_labels[clean_var] = {float(k): v for k, v in pairs}

    return var_labels, value_labels

# --- COMPATIBILIZADOR DE COLUMNAS (ELIMINA DUPLICADOS) ---

def fix_kobo_columns(df):
    """
    1. Convierte / en _ (Compatibilidad con SPS).
    2. Quita prefijos de grupo.
    3. Asegura nombres ÚNICOS para que Streamlit no de error.
    """
    new_names = []
    seen = {}

    for col in df.columns:
        # Normalizar nombre
        clean_name = str(col).split('/')[-1].replace('/', '_')
        
        # Evitar palabra reservada _index
        if clean_name == "_index":
            clean_name = "id_kobo"

        # GESTIÓN DE DUPLICADOS: Si el nombre ya existe, lo marcamos
        if clean_name in seen:
            seen[clean_name] += 1
            final_name = f"{clean_name}_duplicada_{seen[clean_name]}"
        else:
            seen[clean_name] = 0
            final_name = clean_name
            
        new_names.append(final_name)
    
    df.columns = new_names
    return df

# --- INTERFAZ DE USUARIO ---

st.title("📊 SPSS Web Manager (Kobo & LimeSurvey)")
st.markdown("---")

with st.sidebar:
    st.header("📁 Cargar Archivos")
    origen = st.selectbox("Flujo de trabajo:", 
                          ["KoboToolbox (Excel/CSV + SPS)", 
                           "LimeSurvey (DAT/CSV + SPS)", 
                           "SAV Local (Arreglar Codificación)"])
    
    data_file = st.file_uploader("1. Archivo de DATOS", type=["xlsx", "csv", "dat", "sav", "txt"])
    sps_file = st.file_uploader("2. Archivo de SINTAXIS (.sps)", type=["sps"])
    st.markdown("---")
    st.caption("Compatible con Android y PC")

if data_file:
    try:
        # A. Lectura de datos según tipo
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
            # Para CSV o .dat de LimeSurvey
            df = pd.read_csv(data_file, sep=None, engine='python')
            var_labels, val_labels = {}, {}

        # B. Compatibilizar columnas (Fix de diagonales y nombres repetidos)
        df = fix_kobo_columns(df)

        # C. Procesar Sintaxis SPS si se subió
        if sps_file:
            sps_vars, sps_vals = parse_sps_syntax(sps_file.read())
            var_labels.update(sps_vars)
            val_labels.update(sps_vals)
            st.sidebar.success(f"✅ {len(sps_vars)} etiquetas vinculadas")

        # D. Vista Estilo Jamovi
        tab1, tab2 = st.tabs(["📋 Hoja de Datos", "🔍 Vista de Variables"])

        with tab1:
            st.subheader("Editor de Datos")
            # Crear copia visual con etiquetas (Ej: 1 -> 'Sí')
            df_visual = df.copy()
            for col, mapping in val_labels.items():
                if col in df_visual.columns:
                    try:
                        df_visual[col] = df_visual[col].map(mapping).fillna(df_visual[col])
                    except: pass
            
            # El editor ya no dará error de columnas repetidas
            edited_df = st.data_editor(df_visual, width="stretch", num_rows="dynamic")

        with tab2:
            st.subheader("Diccionario de Metadatos")
            meta_df = pd.DataFrame({
                "Variable": df.columns,
                "Etiqueta": [var_labels.get(c, "Sin etiqueta en SPS") for c in df.columns],
                "Valores": ["✅ Definidos" if c in val_labels else "❌ No" for c in df.columns]
            })
            st.dataframe(meta_df, width="stretch")

        # E. Exportación a SPSS (.sav)
        st.markdown("---")
        if st.button("🚀 Generar y Descargar SAV Profesional"):
            output_name = "datos_finales.sav"
            
            # Preparar etiquetas en el orden exacto de las columnas del DF
            final_labels = [var_labels.get(c, "") for c in df.columns]
            
            pyreadstat.write_sav(
                df, 
                output_name, 
                column_labels=final_labels, 
                variable_value_labels=val_labels
            )
            
            with open(output_name, "rb") as f:
                st.download_button("⬇️ Descargar SAV para IBM SPSS / Jamovi", 
                                   f, file_name="kobo_limesurvey_listo.sav")

    except Exception as e:
        st.error(f"Error en el procesamiento: {e}")
else:
    st.info("👋 Por favor, carga tu archivo de datos en el panel izquierdo.")
