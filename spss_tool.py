import streamlit as st
import pandas as pd
import pyreadstat
import io
import os
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SPSS Master Flow Pro", layout="wide", page_icon="🛡️")

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff; border-radius: 10px 10px 0px 0px; padding: 10px 20px; border: 1px solid #ddd;
    }
    .stTabs [aria-selected="true"] { background-color: #1f77b4 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR DE ADN (NORMALIZADO) ---
def parse_sps_metadata_v7(sps_content):
    var_labels = {}
    value_labels = {}
    
    # Normalización del texto
    text = sps_content.replace('\r', ' ').replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)

    # 1. VARIABLE LABELS
    var_match = re.search(r"VARIABLE LABELS (.*?)\.", text, re.IGNORECASE)
    if var_match:
        entries = re.findall(r"(?:/|^)\s*(\S+)\s+['\"](.*?)['\"]", var_match.group(1))
        for var_name, label in entries:
            # Aquí ya guardamos todo con guion bajo para que coincida con el Excel limpio
            clean_name = var_name.strip().replace('/', '_')
            var_labels[clean_name] = label

    # 2. VALUE LABELS
    val_blocks = re.findall(r"VALUE LABELS\s+(.*?)\.", text, re.IGNORECASE)
    for block in val_blocks:
        block = block.strip()
        first_quote = re.search(r"['\"]", block)
        if not first_quote: continue
        vars_part = block[:first_quote.start()].strip()
        labels_part = block[first_quote.start():].strip()
        
        var_names = [v.replace('/', '_') for v in re.split(r"[\s/]+", vars_part) if v]
        pairs = re.findall(r"['\"]([^'\"]+)['\"]\s+['\"]([^'\"]+)['\"]", labels_part)
        
        if pairs:
            v_map = {p[0]: p[1] for p in pairs}
            for vn in var_names:
                value_labels[vn] = v_map
        
    return var_labels, value_labels

def main():
    # --- BARRA LATERAL: CHECKLIST ---
    with st.sidebar:
        st.header("📋 PROGRESO")
        
        # Lógica de checks
        s1 = "✅" if st.session_state.get('meta_loaded') else "❌"
        s2 = "✅" if st.session_state.get('excel_downloaded') else "⏳"
        s3 = "✅" if st.session_state.get('apto') else "❌"
        
        st.info(f"""
        **PASO A PASO:**
        1. {s1} Estructura Cargada
        2. {s2} Excel Limpio Descargado
        3. {s3} Validación (Aduana)
        4. {'✅' if s3 == '✅' else '🔒'} Exportación SAV
        """)
        
        st.divider()
        if st.button("🔄 REINICIAR PROYECTO"):
            st.session_state.clear()
            st.rerun()

    # --- ENCABEZADO ---
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🛡️ SPSS Master Flow Pro")
        st.caption("Ecosistema de Validación de Datos | Trendsity")
    with col2:
        st.write("📊 **SPSS**")
        st.write("📈 **KOBO**")

    # --- SELECTOR DE ORIGEN ---
    mode = st.radio("Seleccione el origen de los datos:", 
                    ["KoboToolbox (Excel + SPS)", "LimeSurvey (Archivo SAV)"], horizontal=True)

    # --- PASO 0: CARGA Y LIMPIEZA AUTOMÁTICA ---
    if 'meta_loaded' not in st.session_state:
        if mode == "KoboToolbox (Excel + SPS)":
            c1, c2 = st.columns(2)
            with c1: f_excel = st.file_uploader("📥 Excel de Kobo", type=["xlsx"])
            with c2: f_sps = st.file_uploader("📥 Sintaxis SPS", type=["sps"])
            
            if f_excel and f_sps:
                with st.spinner("Limpiando cabeceras ( / -> _ ) y cargando ADN..."):
                    df = pd.read_excel(f_excel)
                    # LIMPIEZA AUTOMÁTICA INMEDIATA
                    df.columns = [str(c).replace('/', '_') for c in df.columns]
                    
                    sps_text = f_sps.read().decode("latin-1")
                    v_labels, val_labels = parse_sps_metadata_v7(sps_text)
                    
                    st.session_state.update({
                        'df_orig': df, 'v_labels': v_labels, 'val_labels': val_labels,
                        'all_cols': list(df.columns), 'meta_loaded': True
                    })
                    st.rerun()
        else:
            f_sav = st.file_uploader("📥 Subir archivo .SAV base", type=["sav"])
            if f_sav:
                with open("temp.sav", "wb") as f: f.write(f_sav.getbuffer())
                df, meta = pyreadstat.read_sav("temp.sav")
                st.session_state.update({
                    'df_orig': df, 'v_labels': meta.column_names_to_labels, 
                    'val_labels': meta.variable_value_labels, 
                    'all_cols': list(df.columns), 'meta_loaded': True
                })
                os.remove("temp.sav")
                st.rerun()
        return

    # --- TABS DE TRABAJO ---
    t1, t2, t3 = st.tabs(["🌳 1. ADN & PACK LIMPIO", "🔍 2. ADUANA", "🚀 3. SAV FINAL"])

    with t1:
        st.subheader("Paso 1: Diccionario y Preparación")
        st.write("El sistema ha corregido los nombres de las columnas automáticamente.")
        
        col_res, col_down = st.columns([2, 1])
        with col_res:
            resumen = []
            for c in st.session_state.all_cols:
                label = st.session_state.v_labels.get(c, "❌ NO ENCONTRADA EN SPS")
                resumen.append({"Columna Limpia": c, "Etiqueta": label, "Diccionario": "✅ OK" if c in st.session_state.val_labels else "---"})
            st.dataframe(pd.DataFrame(resumen), height=350)
            
        with col_down:
            st.info("Descarga este Excel corregido para dárselo al cliente:")
            out_xlsx = io.BytesIO()
            st.session_state.df_orig.to_excel(out_xlsx, index=False)
            if st.download_button("📥 DESCARGAR EXCEL PARA CLIENTE", out_xlsx.getvalue(), "Estructura_Limpia.xlsx", use_container_width=True):
                st.session_state.excel_downloaded = True

    with t2:
        st.subheader("Paso 2: Aduana de Calidad")
        f_p = st.file_uploader("📤 Subir Excel Planchado por Cliente", type=["xlsx"])
        if f_p:
            df_p = pd.read_excel(f_p)
            errores = []
            for col in df_p.columns:
                if col in st.session_state.val_labels:
                    valid_codes = set(str(k) for k in st.session_state.val_labels[col].keys())
                    for idx, val in df_p[col].items():
                        if pd.notnull(val) and str(val) not in valid_codes:
                            errores.append({"Fila": idx+2, "Variable": col, "Error": "Código inválido", "Valor": val})
            
            if errores:
                st.error(f"❌ Se encontraron {len(errores)} inconsistencias.")
                st.dataframe(pd.DataFrame(errores).head(50))
                st.session_state.apto = False
            else:
                st.success("✅ ¡Base impecable! Lista para exportar.")
                st.session_state.apto = True
                st.session_state.df_final = df_p

    with t3:
        if st.session_state.get('apto'):
            st.subheader("Paso 3: Exportación Final")
            name = st.text_input("Nombre del archivo:", "Base_Trendsity_Final")
            if st.button("🚀 GENERAR Y DESCARGAR SAV OFICIAL"):
                path_sav = f"{name}.sav"
                pyreadstat.write_sav(
                    st.session_state.df_final, path_sav,
                    column_labels=st.session_state.v_labels,
                    variable_value_labels=st.session_state.val_labels
                )
                with open(path_sav, "rb") as f:
                    st.download_button("📥 Bajar archivo .sav", f, path_sav, use_container_width=True)
                st.balloons()
        else:
            st.warning("🔒 Debes completar la validación en la pestaña 'Aduana' para habilitar la exportación.")

if __name__ == "__main__":
    main()
