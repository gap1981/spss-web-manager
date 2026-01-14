import streamlit as st
import pandas as pd
import pyreadstat
import io
import os
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SPSS Master Flow Pro", layout="wide", page_icon="🛡️")

# --- ESTILOS VISUALES Y LOGOS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stAlert { border-radius: 12px; }
    .css-1kyx60w { font-size: 1.2rem; font-weight: bold; }
    .check-list { background: white; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR DE ADN (NORMALIZADO Y ROBUSTO) ---
def parse_sps_metadata_v8(sps_content):
    var_labels = {}
    value_labels = {}
    
    # Normalización total del texto (quitar saltos de línea y excesos de espacios)
    text = sps_content.replace('\r', ' ').replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)

    # 1. VARIABLE LABELS: Captura "nombre 'etiqueta'"
    var_match = re.search(r"VARIABLE LABELS (.*?)\.", text, re.IGNORECASE)
    if var_match:
        content = var_match.group(1)
        # Capturamos /NombreVar 'Etiqueta'
        entries = re.findall(r"(?:/|^)\s*(\S+)\s+['\"](.*?)['\"]", content)
        for var_name, label in entries:
            clean_name = var_name.strip().replace('/', '_')
            var_labels[clean_name] = label

    # 2. VALUE LABELS: Captura bloques de códigos
    val_blocks = re.findall(r"VALUE LABELS\s+(.*?)\.", text, re.IGNORECASE)
    for block in val_blocks:
        block = block.strip()
        first_quote = re.search(r"['\"]", block)
        if not first_quote: continue
        
        vars_part = block[:first_quote.start()].strip()
        labels_part = block[first_quote.start():].strip()
        
        var_names = [v.replace('/', '_') for v in re.split(r"[\s/]+", vars_part) if v]
        # Capturamos pares: '1' 'Etiqueta'
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
        
        # Estados
        meta_ok = st.session_state.get('meta_loaded', False)
        excel_ok = st.session_state.get('excel_downloaded', False)
        audit_ok = st.session_state.get('apto', False)
        
        st.markdown(f"""
        <div class="check-list">
        {'✅' if meta_ok else '❌'} 1. Estructura Cargada<br>
        {'✅' if excel_ok else '⏳'} 2. Excel Limpio Generado<br>
        {'✅' if audit_ok else '❌'} 3. Validación (Aduana)<br>
        {'✅' if audit_ok else '🔒'} 4. Exportación SAV
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        if st.button("🔄 REINICIAR PROYECTO", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # --- HEADER ---
    st.title("🛡️ SPSS Master Flow Pro")
    st.caption("Ecosistema de Validación de Datos | Trendsity")

    # Selector de origen
    mode = st.radio("Origen de los datos:", ["KoboToolbox (Excel + SPS)", "LimeSurvey (SAV)"], horizontal=True)

    # --- PASO 0: CARGA Y LIMPIEZA ---
    if not st.session_state.get('meta_loaded'):
        st.info("### 📥 Paso 1: Carga de Archivos")
        if mode == "KoboToolbox (Excel + SPS)":
            c1, c2 = st.columns(2)
            with c1: f_excel = st.file_uploader("Subir Datos Excel", type=["xlsx"])
            with c2: f_sps = st.file_uploader("Subir Sintaxis SPS", type=["sps"])
            
            if f_excel and f_sps:
                with st.spinner("Procesando..."):
                    df = pd.read_excel(f_excel)
                    # --- LIMPIEZA AUTOMÁTICA DE CABECERAS ---
                    df.columns = [str(c).replace('/', '_') for c in df.columns]
                    
                    sps_text = f_sps.read().decode("latin-1")
                    v_labels, val_labels = parse_sps_metadata_v8(sps_text)
                    
                    # Rellenar etiquetas de sistema si faltan
                    sys_vars = {'start': 'Fecha de inicio', 'end': 'Fecha de fin', 'deviceid': 'ID del dispositivo'}
                    for k, v in sys_vars.items():
                        if k not in v_labels: v_labels[k] = v

                    st.session_state.update({
                        'df_orig': df, 'v_labels': v_labels, 'val_labels': val_labels,
                        'all_cols': list(df.columns), 'meta_loaded': True
                    })
                    st.rerun()
        else:
            # Lógica LimeSurvey
            f_sav = st.file_uploader("Subir archivo SAV base", type=["sav"])
            if f_sav:
                with open("temp.sav", "wb") as f: f.write(f_sav.getbuffer())
                df, meta = pyreadstat.read_sav("temp.sav")
                st.session_state.update({'df_orig': df, 'v_labels': meta.column_names_to_labels, 'val_labels': meta.variable_value_labels, 'all_cols': list(df.columns), 'meta_loaded': True})
                os.remove("temp.sav")
                st.rerun()
        return

    # --- TABS ---
    t1, t2, t3 = st.tabs(["🌳 1. ADN & PACK LIMPIO", "🔍 2. ADUANA", "🚀 3. EXPORTAR"])

    with t1:
        st.subheader("Diccionario y Template de Trabajo")
        st.markdown("**Nota:** El sistema ha convertido automáticamente todas las barras `/` en `_` para que coincidan con SPSS.")
        
        col_res, col_down = st.columns([2, 1])
        with col_res:
            resumen = []
            for c in st.session_state.all_cols:
                label = st.session_state.v_labels.get(c, "❌ NO ENCONTRADA EN SPS")
                resumen.append({"Columna Limpia": c, "Etiqueta SPSS": label, "Valores": "✅" if c in st.session_state.val_labels else "---"})
            st.dataframe(pd.DataFrame(resumen), height=400)
            
        with col_down:
            st.warning("⚠️ DESCARGUE ESTE EXCEL PARA EL CLIENTE:")
            out_xlsx = io.BytesIO()
            st.session_state.df_orig.to_excel(out_xlsx, index=False)
            if st.download_button("📥 DESCARGAR EXCEL LIMPIO", out_xlsx.getvalue(), "Base_Para_Trabajar.xlsx", use_container_width=True):
                st.session_state.excel_downloaded = True
            st.caption("Este archivo ya tiene los nombres corregidos. Evite que el cliente los modifique.")

    with t2:
        st.subheader("Aduana de Validación")
        f_p = st.file_uploader("📤 Subir Excel del Cliente", type=["xlsx"])
        if f_p:
            df_p = pd.read_excel(f_p)
            errores = []
            for col in df_p.columns:
                if col in st.session_state.val_labels:
                    valid_codes = set(str(k) for k in st.session_state.val_labels[col].keys())
                    for idx, val in df_p[col].items():
                        if pd.notnull(val) and str(val) not in valid_codes:
                            errores.append({"Fila": idx+2, "Variable": col, "Error": "Código no existe en ADN", "Valor": val})
            
            if errores:
                st.error(f"❌ Inconsistencias: {len(errores)}")
                st.table(pd.DataFrame(errores).head(20))
                st.session_state.apto = False
            else:
                st.success("✅ ¡Base validada! No hay inconsistencias de códigos.")
                st.session_state.apto = True
                st.session_state.df_final = df_p

    with t3:
        if st.session_state.get('apto'):
            st.subheader("Generación de Archivo Final")
            name = st.text_input("Nombre del SAV:", "Base_Trendsity_Validada")
            if st.button("🚀 GENERAR SAV OFICIAL"):
                path = f"{name}.sav"
                pyreadstat.write_sav(st.session_state.df_final, path, column_labels=st.session_state.v_labels, variable_value_labels=st.session_state.val_labels)
                with open(path, "rb") as f:
                    st.download_button("📥 Descargar .SAV", f, path, use_container_width=True)
                st.balloons()
        else:
            st.warning("🔒 Debes subir el Excel en la pestaña 'Aduana' primero.")

if __name__ == "__main__":
    main()
