import streamlit as st
import pandas as pd
import pyreadstat
import io
import os
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Trendsity Data Pro", layout="wide", page_icon="🛡️")

# --- LOGOS E INTERFAZ ---
st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: white; border: 1px solid #ddd; border-radius: 5px; padding: 5px 15px;
    }
    .check-box { background-color: #ffffff; padding: 12px; border-radius: 8px; border-left: 5px solid #007bff; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR DE ADN KOBO (ULTRA PRECISIÓN) ---
def parse_kobo_sps_v9(sps_content):
    var_labels = {}
    value_labels = {}
    
    # Limpieza previa del SPS: quitamos ruidos de formato
    text = sps_content.replace('\r', ' ').replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)

    # 1. VARIABLE LABELS: Extraer etiquetas de preguntas
    # Formato esperado: VARIABLE LABELS var1 'etiqueta' /var2 'etiqueta' .
    v_match = re.search(r"VARIABLE LABELS\s+(.*?)\s*\.", text, re.IGNORECASE)
    if v_match:
        content = v_match.group(1)
        # Regex para capturar tanto /var 'label' como var 'label'
        items = re.findall(r"(?:/|^)\s*(\S+)\s+['\"](.*?)['\"]", content)
        for var_name, label in items:
            clean_name = var_name.strip().replace('/', '_')
            var_labels[clean_name] = label

    # 2. VALUE LABELS: Extraer diccionarios de códigos
    # Formato: VALUE LABELS var1 '1' 'Label' '2' 'Label' .
    val_blocks = re.findall(r"VALUE LABELS\s+(.*?)\s*\.", text, re.IGNORECASE)
    for block in val_blocks:
        first_quote = re.search(r"['\"]", block)
        if not first_quote: continue
        
        vars_part = block[:first_quote.start()].strip()
        labels_part = block[first_quote.start():].strip()
        
        # Nombres de variables (pueden ser varios para un mismo bloque de etiquetas)
        var_names = [v.replace('/', '_') for v in re.split(r"[\s/]+", vars_part) if v]
        # Pares de códigos y etiquetas
        pairs = re.findall(r"['\"]([^'\"]+)['\"]\s+['\"]([^'\"]+)['\"]", labels_part)
        
        if pairs:
            v_map = {p[0]: p[1] for p in pairs}
            # Intentar convertir códigos a numérico si es posible para compatibilidad con SAV
            try:
                v_map_numeric = {float(k): v for k, v in v_map.items() if k.isdigit() or k.replace('.','',1).isdigit()}
                final_map = {**v_map, **v_map_numeric}
            except:
                final_map = v_map
                
            for vn in var_names:
                value_labels[vn] = final_map
        
    return var_labels, value_labels

def main():
    # --- BARRA LATERAL (CHECKLIST) ---
    with st.sidebar:
        st.header("📊 Estatus del Flujo")
        meta_ok = st.session_state.get('meta_loaded', False)
        excel_ok = st.session_state.get('excel_downloaded', False)
        apto = st.session_state.get('apto', False)

        st.markdown(f"""
        <div class="check-box">{'✅' if meta_ok else '❌'} 1. Estructura Kobo/SPSS</div>
        <div class="check-box">{'✅' if excel_ok else '⏳'} 2. Descarga para Cliente</div>
        <div class="check-box">{'✅' if apto else '❌'} 3. Aduana de Planchado</div>
        """, unsafe_allow_html=True)
        
        st.divider()
        if st.button("🔄 REINICIAR TODO"):
            st.session_state.clear()
            st.rerun()

    st.title("🛡️ Trendsity SPSS Master Validator")
    st.caption("Herramienta Profesional de Gestión de Datos")

    # --- PASO 0: CARGA ---
    if not st.session_state.get('meta_loaded'):
        mode = st.radio("Origen de estructura:", ["KoboToolbox (Excel+SPS)", "LimeSurvey (SAV)"], horizontal=True)
        
        if mode == "KoboToolbox (Excel+SPS)":
            c1, c2 = st.columns(2)
            with c1: f_excel = st.file_uploader("📥 Subir Datos (Excel)", type=["xlsx"])
            with c2: f_sps = st.file_uploader("📥 Subir Sintaxis (SPS)", type=["sps"])
            
            if f_excel and f_sps:
                with st.spinner("Limpiando cabeceras y extrayendo ADN..."):
                    df = pd.read_excel(f_excel)
                    # LIMPIEZA AUTOMÁTICA DE CABECERAS
                    df.columns = [str(c).replace('/', '_') for c in df.columns]
                    
                    sps_raw = f_sps.read().decode("latin-1")
                    v_labels, val_labels = parse_kobo_sps_v9(sps_raw)
                    
                    # Rellenar datos de sistema
                    sys_vars = {'start':'Fecha Inicio', 'end':'Fecha Fin', 'deviceid':'ID Dispositivo'}
                    for k,v in sys_vars.items(): 
                        if k not in v_labels: v_labels[k] = v

                    st.session_state.update({
                        'df_orig': df, 'v_labels': v_labels, 'val_labels': val_labels,
                        'all_cols': list(df.columns), 'meta_loaded': True
                    })
                    st.rerun()
        else:
            # Flujo LimeSurvey (ya estabilizado)
            f_sav = st.file_uploader("Subir SAV ADN", type=["sav"])
            if f_sav:
                with open("t.sav","wb") as f: f.write(f_sav.getbuffer())
                df, meta = pyreadstat.read_sav("t.sav")
                st.session_state.update({'df_orig':df, 'v_labels':meta.column_names_to_labels, 'val_labels':meta.variable_value_labels, 'all_cols':list(df.columns), 'meta_loaded':True})
                st.rerun()
        return

    # --- TABS ---
    t1, t2, t3 = st.tabs(["📋 1. ADN & EXPORTAR TEMPLATE", "🔍 2. ADUANA", "🚀 3. SPSS FINAL"])

    with t1:
        st.subheader("Verificación de Diccionario y Nombres")
        st.write("A continuación se muestran las variables tras la limpieza automática (`/` convertido en `_`).")
        
        col_table, col_actions = st.columns([2, 1])
        with col_table:
            resumen = []
            for c in st.session_state.all_cols:
                lbl = st.session_state.v_labels.get(c, "❌ SIN ETIQUETA EN SPS")
                resumen.append({"Variable (Limpia)": c, "Etiqueta": lbl, "Diccionario": "✅ OK" if c in st.session_state.val_labels else "---"})
            st.dataframe(pd.DataFrame(resumen), height=400)
            
        with col_actions:
            st.success("✅ Estructura Sincronizada")
            out = io.BytesIO()
            st.session_state.df_orig.to_excel(out, index=False)
            if st.download_button("📥 DESCARGAR EXCEL PARA CLIENTE", out.getvalue(), "Template_Planchado_Trendsity.xlsx", use_container_width=True):
                st.session_state.excel_downloaded = True
            st.caption("Este Excel tiene las columnas corregidas para SPSS. Pide al cliente que no edite la primera fila.")

    with t2:
        st.subheader("Aduana de Validación de Datos")
        f_p = st.file_uploader("📤 Subir Excel del Cliente", type=["xlsx"])
        if f_p:
            df_p = pd.read_excel(f_p)
            errores = []
            for col in df_p.columns:
                if col in st.session_state.val_labels:
                    # Validar que los códigos ingresados sean válidos en el ADN
                    valid_codes = set(str(k) for k in st.session_state.val_labels[col].keys())
                    for idx, val in df_p[col].items():
                        if pd.notnull(val) and str(val) not in valid_codes:
                            # Permitimos que códigos numéricos pasen si el diccionario es de texto
                            try:
                                if str(int(float(val))) in valid_codes: continue
                            except: pass
                            errores.append({"Fila": idx+2, "Variable": col, "Error": "Código no existe", "Valor": val})
            
            if errores:
                st.error(f"❌ Inconsistencias: {len(errores)}")
                st.dataframe(pd.DataFrame(errores).head(30))
                st.session_state.apto = False
            else:
                st.success("✅ ¡Todo impecable! Datos consistentes.")
                st.session_state.apto = True
                st.session_state.df_final = df_p

    with t3:
        if st.session_state.get('apto'):
            st.subheader("Exportación Profesional")
            fname = st.text_input("Nombre del archivo:", "Base_Final_Procesada")
            if st.button("🚀 GENERAR SAV OFICIAL"):
                path = f"{fname}.sav"
                pyreadstat.write_sav(st.session_state.df_final, path, column_labels=st.session_state.v_labels, variable_value_labels=st.session_state.val_labels)
                with open(path, "rb") as f:
                    st.download_button("📥 Descargar .SAV", f, path, use_container_width=True)
                st.balloons()
        else:
            st.warning("⚠️ Debes subir y validar el archivo en 'Aduana' primero.")

if __name__ == "__main__":
    main()
