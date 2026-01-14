import streamlit as st
import pandas as pd
import pyreadstat
import io
import os
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SPSS Master Validator", layout="wide", page_icon="🛡️")

# --- ESTILOS PERSONALIZADOS (Buenas prácticas de diseño) ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stAlert { border-radius: 10px; }
    .step-header { color: #1f77b4; font-weight: bold; font-size: 1.5rem; margin-bottom: 0.5rem; }
    .instruction { color: #555; font-size: 0.95rem; margin-bottom: 1.5rem; }
    div[data-testid="stExpander"] { border: 1px solid #d1d9e0; border-radius: 10px; background-color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE SOPORTE ---
def parse_kobo_sps(sps_content):
    """Extrae metadatos del archivo .sps de KoboToolbox"""
    var_labels = {}
    value_labels = {}
    
    # 1. VARIABLE LABELS
    var_match = re.search(r"VARIABLE LABELS(.*?)\.", sps_content, re.DOTALL | re.IGNORECASE)
    if var_match:
        entries = var_match.group(1).split('/')
        for entry in entries:
            clean = entry.strip()
            if not clean: continue
            parts = clean.split(None, 1)
            if len(parts) == 2:
                var_labels[parts[0].strip()] = parts[1].strip().strip("'")

    # 2. VALUE LABELS
    val_matches = re.findall(r"VALUE LABELS\s+(\w+)(.*?)\.", sps_content, re.DOTALL | re.IGNORECASE)
    for var_name, values_block in val_matches:
        v_map = {}
        pairs = re.findall(r"['\"]?(\d+)['\"]?\s+['\"](.*?)['\"]", values_block)
        for val, lab in pairs:
            v_map[float(val)] = lab
        value_labels[var_name] = v_map
        
    return var_labels, value_labels

def detect_prohibited_chars(val):
    if not isinstance(val, str): return False
    return bool(re.search(r'[\r\n\x00-\x1f\x7f-\x9f]', val))

# --- INTERFAZ PRINCIPAL ---
def main():
    st.sidebar.title("🛠️ Centro de Control")
    mode = st.sidebar.radio(
        "Origen de Datos:",
        ["KoboToolbox (Excel + SPS)", "LimeSurvey (SAV ADN)"],
        help="Elija Kobo si tiene la sintaxis .sps y el Excel. Elija LimeSurvey si ya tiene un .sav generado."
    )
    
    if st.sidebar.button("🔄 REINICIAR PROYECTO"):
        st.session_state.clear()
        st.rerun()

    st.title("🛡️ SPSS Data Validator & Suite")
    st.markdown("---")

    # --- FLUJO DE CARGA ---
    if 'meta' not in st.session_state:
        st.markdown('<p class="step-header">Paso 0: Inyección de ADN (Metadatos)</p>', unsafe_allow_html=True)
        
        if mode == "KoboToolbox (Excel + SPS)":
            c1, c2 = st.columns(2)
            with c1:
                uploaded_excel = st.file_uploader("📥 1. Subir Excel de Datos (Kobo)", type=["xlsx", "csv"])
            with c2:
                uploaded_sps = st.file_uploader("📥 2. Subir Sintaxis (.Sps)", type=["sps"])
            
            if uploaded_excel and uploaded_sps:
                with st.spinner("Decodificando ADN de Kobo..."):
                    df = pd.read_excel(uploaded_excel) if ".xlsx" in uploaded_excel.name else pd.read_csv(uploaded_excel)
                    sps_text = uploaded_sps.read().decode("utf-8", errors="ignore")
                    v_labels, val_labels = parse_kobo_sps(sps_text)
                    
                    st.session_state.df_orig = df
                    st.session_state.meta_v_labels = v_labels
                    st.session_state.meta_val_labels = val_labels
                    st.session_state.all_cols = list(df.columns)
                    st.session_state.meta = True # Flag de carga
                    st.rerun()
        
        else: # MODO LIMESURVEY
            uploaded_sav = st.file_uploader("📥 Subir archivo .SAV base", type=["sav"])
            if uploaded_sav:
                with st.spinner("Extrayendo ADN del SAV..."):
                    with open("temp.sav", "wb") as f: f.write(uploaded_sav.getbuffer())
                    df, meta = pyreadstat.read_sav("temp.sav")
                    st.session_state.df_orig = df
                    st.session_state.meta_v_labels = meta.column_names_to_labels
                    st.session_state.meta_val_labels = meta.variable_value_labels
                    st.session_state.all_cols = list(df.columns)
                    st.session_state.meta = True
                    os.remove("temp.sav")
                    st.rerun()
        return

    # --- TABS DE TRABAJO (Flujo lógico para el analista) ---
    tab1, tab2, tab3 = st.tabs(["📋 1. DICCIONARIO", "🔍 2. ADUANA DE DATOS", "💾 3. EXPORTACIÓN"])

    # TAB 1: Revisión de ADN
    with tab1:
        st.markdown('<p class="step-header">Estructura detectada</p>', unsafe_allow_html=True)
        st.info("💡 Revise que las etiquetas se hayan cargado correctamente antes de proceder.")
        
        col_sel, col_info = st.columns([1, 2])
        with col_sel:
            cols_active = st.multiselect("Variables a incluir:", st.session_state.all_cols, default=st.session_state.all_cols)
        
        with col_info:
            with st.expander("Ver Diccionario de Etiquetas (ADN)"):
                df_dict = pd.DataFrame({
                    "Variable": list(st.session_state.meta_v_labels.keys()),
                    "Etiqueta": list(st.session_state.meta_v_labels.values())
                })
                st.table(df_dict.head(10))

    # TAB 2: La Aduana (Validación de Planchado)
    with tab2:
        st.markdown('<p class="step-header">Control de Calidad (Aduana)</p>', unsafe_allow_html=True)
        st.markdown('<p class="instruction">Sube el archivo que el cliente "planchó" o corrigió. El sistema verificará que no haya roto el ADN.</p>', unsafe_allow_html=True)
        
        planchado_file = st.file_uploader("📤 Subir Excel del Cliente", type=["xlsx"], key="planchado")
        
        if planchado_file:
            df_p = pd.read_excel(planchado_file)
            errores = []
            
            # Auditoría
            for col in df_p.columns:
                if col in st.session_state.meta_val_labels:
                    valid_codes = set(st.session_state.meta_val_labels[col].keys())
                    # Check de códigos fuera de rango
                    invalid = df_p[~df_p[col].isin(valid_codes) & df_p[col].notnull()]
                    for idx in invalid.index:
                        errores.append({"Fila": idx+2, "Variable": col, "Error": "Código no existe en ADN", "Valor": df_p.at[idx, col]})

            if errores:
                st.error(f"⚠️ Se detectaron {len(errores)} inconsistencias críticas.")
                st.dataframe(pd.DataFrame(errores))
                st.session_state.apto = False
            else:
                st.success("✅ Datos consistentes con el ADN. Listo para exportar.")
                st.session_state.apto = True
                st.session_state.df_ready = df_p

    # TAB 3: Exportación
    with tab3:
        if st.session_state.get('apto', False):
            st.markdown('<p class="step-header">Generación de Entregables</p>', unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                filename = st.text_input("Nombre del archivo:", "Data_Final_Trendsity")
            with c2:
                st.write("Presione para generar el archivo .sav oficial.")
                
            # Generar SAV
            buf = io.BytesIO()
            path_tmp = "export.sav"
            pyreadstat.write_sav(
                st.session_state.df_ready, 
                path_tmp,
                column_labels=st.session_state.meta_v_labels,
                variable_value_labels=st.session_state.meta_val_labels
            )
            with open(path_tmp, "rb") as f:
                st.download_button(
                    "💾 DESCARGAR SPSS (.SAV)",
                    f,
                    file_name=f"{filename}.sav",
                    use_container_width=True
                )
        else:
            st.warning("🔒 El flujo de exportación está bloqueado. Primero debe validar los datos en la pestaña 'Aduana'.")

if __name__ == "__main__":
    main()
