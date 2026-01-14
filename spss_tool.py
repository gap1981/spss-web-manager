import streamlit as st
import pandas as pd
import pyreadstat
import io
import os
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SPSS Master Flow", layout="wide", page_icon="🛡️")

# --- LOGOS Y ESTILO ---
LOGO_SPSS = "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/IBM_SPSS_Statistics_logo.svg/128px-IBM_SPSS_Statistics_logo.svg.png"
LOGO_KOBO = "https://get.kobotoolbox.org/favicon.png"

st.markdown("""
    <style>
    .status-card { padding: 20px; border-radius: 10px; border: 1px solid #ddd; background-color: #f9f9f9; }
    .stButton>button { border-radius: 20px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR DE ADN MEJORADO ---
def parse_sps_metadata_v5(sps_content):
    """Parser de 5ta generación: Maneja códigos alfanuméricos y discrepancias de nombres."""
    var_labels = {}
    value_labels = {}
    
    # Normalización total del texto
    text = sps_content.replace('\r', ' ').replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)

    # 1. VARIABLE LABELS
    var_match = re.search(r"VARIABLE LABELS (.*?)\.", text, re.IGNORECASE)
    if var_match:
        # Busca /nombre 'Etiqueta' o nombre 'Etiqueta'
        entries = re.findall(r"(?:/|^)\s*(\S+)\s+['\"](.*?)['\"]", var_match.group(1))
        for var_name, label in entries:
            clean_name = var_name.strip().replace('/', '_') # Normalizar para búsqueda
            var_labels[var_name] = label
            var_labels[clean_name] = label
            if "_" in var_name: var_labels[var_name.replace("_", "/")] = label

    # 2. VALUE LABELS (Soporta 'AEP', 'EZE' y números)
    val_blocks = re.findall(r"VALUE LABELS\s+(.*?)\.", text, re.IGNORECASE)
    for block in val_blocks:
        block = block.strip()
        first_quote = re.search(r"['\"]", block)
        if not first_quote: continue
        
        vars_part = block[:first_quote.start()].strip()
        labels_part = block[first_quote.start():].strip()
        
        var_names = re.split(r"[\s/]+", vars_part)
        pairs = re.findall(r"['\"]([^'\"]+)['\"]\s+['\"]([^'\"]+)['\"]", labels_part)
        
        if pairs:
            v_map = {p[0]: p[1] for p in pairs}
            for vn in var_names:
                if not vn: continue
                value_labels[vn] = v_map
                clean_vn = vn.strip().replace('/', '_')
                value_labels[clean_vn] = v_map
                if "_" in vn: value_labels[vn.replace("_", "/")] = v_map
        
    return var_labels, value_labels

def main():
    # --- HEADER VISUAL ---
    col_l1, col_l2, col_l3 = st.columns([1, 4, 1])
    with col_l1: st.image(LOGO_SPSS, width=80)
    with col_l2: 
        st.title("🛡️ SPSS Master Flow Pro")
        st.caption("Ecosistema de Validación y Planchado de Datos | Trendsity")
    with col_l3: st.image(LOGO_KOBO, width=60)

    # --- SIDEBAR: CHECKLIST ---
    with st.sidebar:
        st.header("📋 Check de Seguimiento")
        
        # Estados
        step1 = "✅" if st.session_state.get('meta_loaded') else "❌"
        step2 = "✅" if st.session_state.get('excel_downloaded') else "⏳"
        step3 = "✅" if st.session_state.get('apto') else "❌"
        
        st.markdown(f"""
        1. {step1} ADN Cargado  
        2. {step2} Pack Excel Generado  
        3. {step3} Aduana Superada  
        ---
        """)
        
        if st.button("🔄 REINICIAR PROYECTO", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # --- SELECTOR DE MODO ---
    mode = st.radio("Origen de la estructura de datos:", 
                    ["KoboToolbox (Excel + SPS)", "LimeSurvey (SAV ADN)"], horizontal=True)

    # --- PASO 1: CARGA ---
    if 'meta_loaded' not in st.session_state:
        st.subheader("1️⃣ Inyectar ADN de Variables")
        if mode == "KoboToolbox (Excel + SPS)":
            c1, c2 = st.columns(2)
            with c1: f_excel = st.file_uploader("📥 Subir Excel de Datos", type=["xlsx"])
            with c2: f_sps = st.file_uploader("📥 Subir Sintaxis .SPS", type=["sps"])
            
            if f_excel and f_sps:
                df = pd.read_excel(f_excel)
                sps_text = f_sps.read().decode("latin-1") # Usamos latin-1 para Kobo
                v_labels, val_labels = parse_sps_metadata_v5(sps_text)
                st.session_state.update({'df_orig': df, 'v_labels': v_labels, 'val_labels': val_labels, 'all_cols': list(df.columns), 'meta_loaded': True})
                st.rerun()
        else:
            f_sav = st.file_uploader("📥 Subir archivo .SAV base", type=["sav"])
            if f_sav:
                with open("temp.sav", "wb") as f: f.write(f_sav.getbuffer())
                df, meta = pyreadstat.read_sav("temp.sav")
                st.session_state.update({'df_orig': df, 'v_labels': meta.column_names_to_labels, 'val_labels': meta.variable_value_labels, 'all_cols': list(df.columns), 'meta_loaded': True})
                os.remove("temp.sav")
                st.rerun()
        return

    # --- TABS ---
    t1, t2, t3 = st.tabs(["🌳 ADN Y PACK", "🔍 ADUANA", "🚀 EXPORTAR"])

    with t1:
        st.markdown("### 🧬 Verificación de Diccionario")
        
        col_list, col_pack = st.columns([2, 1])
        with col_list:
            resumen = []
            for c in st.session_state.all_cols:
                label = st.session_state.v_labels.get(c, st.session_state.v_labels.get(c.replace('/', '_'), "❌ SIN ETIQUETA"))
                resumen.append({"Variable": c, "Etiqueta": label, "Diccionario": "✅ OK" if c in st.session_state.val_labels or c.replace('/', '_') in st.session_state.val_labels else "---"})
            st.dataframe(pd.DataFrame(resumen), height=400)
        
        with col_pack:
            st.info("Generar template para el cliente:")
            out_xlsx = io.BytesIO()
            st.session_state.df_orig.to_excel(out_xlsx, index=False)
            if st.download_button("📥 DESCARGAR EXCEL PARA CLIENTE", out_xlsx.getvalue(), "Pack_Trendsity_Cliente.xlsx", use_container_width=True):
                st.session_state.excel_downloaded = True

    with t2:
        st.markdown("### 🔍 Aduana de Validación")
        f_p = st.file_uploader("📤 Subir Excel Planchado", type=["xlsx"])
        if f_p:
            df_p = pd.read_excel(f_p)
            errores = []
            for col in df_p.columns:
                # Buscar labels en original o con barra/guion bajo
                lookup_col = col if col in st.session_state.val_labels else col.replace('/', '_')
                
                if lookup_col in st.session_state.val_labels:
                    valid_codes = set(str(k) for k in st.session_state.val_labels[lookup_col].keys())
                    for idx, val in df_p[col].items():
                        if pd.notnull(val) and str(val) not in valid_codes:
                            errores.append({"Fila": idx+2, "Variable": col, "Error": "Código no existe en ADN", "Valor": val})
            
            if errores:
                st.error(f"❌ Inconsistencias: {len(errores)}")
                st.dataframe(pd.DataFrame(errores).head(20))
                st.session_state.apto = False
            else:
                st.success("✅ Todo Ok. Los códigos coinciden con el ADN.")
                st.session_state.apto = True
                st.session_state.df_final = df_p

    with t3:
        if st.session_state.get('apto'):
            st.markdown("### 💾 Exportación Final")
            name = st.text_input("Nombre del SAV:", "Trendsity_Base_Limpia")
            if st.button("🚀 GENERAR SAV"):
                path = f"{name}.sav"
                pyreadstat.write_sav(
                    st.session_state.df_final, path,
                    column_labels=st.session_state.v_labels,
                    variable_value_labels=st.session_state.val_labels
                )
                with open(path, "rb") as f:
                    st.download_button("📥 Descargar SAV Final", f, path, use_container_width=True)
                st.balloons()
        else:
            st.warning("⚠️ Debes superar la Aduana de Validación.")

if __name__ == "__main__":
    main()
