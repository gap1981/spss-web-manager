import streamlit as st
import pandas as pd
import pyreadstat
import io
import re

# Configuración de página estilo Jamovi
st.set_page_config(page_title="SPSS Universal Manager", layout="wide", page_icon="📊")

# --- MOTOR DE TRADUCCIÓN ---

def parse_sps_syntax(sps_content):
    """
    Extrae etiquetas de variables y valores. 
    Limpia nombres (quita grupos y cambia / por _) para que coincidan con el Excel.
    """
    var_labels = {}
    value_labels = {}
    
    try:
        text = sps_content.decode('utf-8')
    except:
        text = sps_content.decode('latin-1')

    # VARIABLE LABELS: Captura nombres incluso con puntos o barras
    # Ajuste para Kobo/LimeSurvey: P2/1 -> P2_1
    var_matches = re.findall(r'VARIABLE LABELS\s+([\w\./_]+)\s+"(.+?)"', text, re.IGNORECASE)
    for var, label in var_matches:
        clean_var = var.split('/')[-1].replace('/', '_')
        var_labels[clean_var] = label

    # VALUE LABELS: Mapea códigos (1 -> "Sí")
    # Soporta formatos con comillas simples o dobles
    value_blocks = re.findall(r'VALUE LABELS\s+([\w\./_]+)\s+(.+?)\.', text, re.DOTALL | re.IGNORECASE)
    for var, labels_raw in value_blocks:
        clean_var = var.split('/')[-1].replace('/', '_')
        pairs = re.findall(r"['\"]?(\d+)['\"]?\s+['\"](.+?)['\"]", labels_raw)
        if pairs:
            # Los códigos en SPSS suelen ser números (float en pandas)
            value_labels[clean_var] = {float(k): v for k, v in pairs}

    return var_labels, value_labels

def compatibilize_data(df):
    """
    Normaliza los nombres de las columnas:
    1. Elimina prefijos de grupo.
    2. Convierte P1/1 en P1_1 (Crucial para Kobo).
    3. Evita errores de nombres reservados.
    """
    new_cols = {}
    for col in df.columns:
        # Quitamos grupos y cambiamos / por _
        clean_name = str(col).split('/')[-1].replace('/', '_')
        
        # Evitar el error de Streamlit con '_index'
        if clean_name == "_index":
            clean_name = "id_registro"
            
        new_cols[col] = clean_name
    
    return df.rename(columns=new_cols)

# --- INTERFAZ ---

st.title("📊 SPSS Web Manager")
st.caption("Compatible con archivos de LimeSurvey (ExportSPSS) y KoboToolbox")

with st.sidebar:
    st.header("📁 Cargar Archivos")
    origen = st.radio("Tipo de proyecto:", ["Kobo (Excel/CSV + SPS)", "LimeSurvey (.dat + .sps)"])
    
    # Adaptamos el uploader según el origen
    if origen == "LimeSurvey (.dat + .sps)":
        data_file = st.file_uploader("Subir archivo .dat o .csv", type=["dat", "csv", "txt"])
    else:
        data_file = st.file_uploader("Subir Excel/CSV de Kobo", type=["xlsx", "csv"])
        
    sps_file = st.file_uploader("Subir archivo de Sintaxis (.sps)", type=["sps"])

if data_file:
    # 1. Leer Datos (Lógica para LimeSurvey .dat y Kobo .xlsx)
    try:
        if data_file.name.endswith('.xlsx'):
            df = pd.read_excel(data_file)
        else:
            # Los .dat de LimeSurvey suelen ser CSV con coma o tabulación
            df = pd.read_csv(data_file, sep=None, engine='python')
        
        # 2. Aplicar compatibilización (Diagonal por Guion Bajo)
        df = compatibilize_data(df)
        
        var_labels, val_labels = {}, {}
        
        # 3. Procesar Sintaxis si existe
        if sps_file:
            var_labels, val_labels = parse_sps_syntax(sps_file.read())
            st.sidebar.success(f"✅ Sintaxis vinculada: {len(var_labels)} variables.")

        # --- VISTA ESTILO JAMOVI ---
        tab1, tab2 = st.tabs(["📋 Hoja de Datos", "🔍 Vista de Variables"])

        with tab1:
            st.subheader("Datos Editables")
            # Copia visual con etiquetas de valor (Ej: 1 -> Hombre)
            df_visual = df.copy()
            for col, mapping in val_labels.items():
                if col in df_visual.columns:
                    # Intentamos mapear, si no es numérico lo dejamos igual
                    try:
                        df_visual[col] = df_visual[col].map(mapping).fillna(df_visual[col])
                    except:
                        pass
            
            # st.data_editor permite editar celdas como en una app de escritorio
            edited_df = st.data_editor(df_visual, width="stretch")

        with tab2:
            st.subheader("Diccionario de Metadatos")
            meta_summary = []
            for col in df.columns:
                meta_summary.append({
                    "Variable": col,
                    "Etiqueta": var_labels.get(col, "Sin etiqueta en SPS"),
                    "Diccionario": "✅ Sí" if col in val_labels else "❌ No"
                })
            st.dataframe(pd.DataFrame(meta_summary), width="stretch")

        # --- EXPORTACIÓN ---
        st.markdown("---")
        if st.button("🚀 Exportar a SAV Profesional"):
            output = "archivo_final_etiquetado.sav"
            
            # Preparar lista de etiquetas en orden
            labels_list = [var_labels.get(c, "") for c in df.columns]
            
            # Guardamos el archivo .sav real (con números + diccionario)
            # Esto es lo que lee SPSS, Jamovi, R o Stata.
            pyreadstat.write_sav(
                df, 
                output, 
                column_labels=labels_list, 
                variable_value_labels=val_labels
            )
            
            with open(output, "rb") as f:
                st.download_button("⬇️ Descargar SAV para IBM SPSS / Jamovi", f, file_name="datos_finales.sav")

    except Exception as e:
        st.error(f"Error al procesar: {e}")
else:
    st.info("Por favor, sube el archivo de datos para comenzar.")
