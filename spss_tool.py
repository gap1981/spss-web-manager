import streamlit as st
import pandas as pd
import pyreadstat
import io
import os
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SPSS Master Flow", layout="wide", page_icon="🛡️")

# --- LOGOS ---
LOGO_SPSS = "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/IBM_SPSS_Statistics_logo.svg/128px-IBM_SPSS_Statistics_logo.svg.png"
LOGO_KOBO = "https://get.kobotoolbox.org/favicon.png"

# --- MOTOR DE ADN MEJORADO ---
def parse_sps_metadata_v6(sps_content):
    """Extrae etiquetas de variables y categorías (Value Labels) normalizando nombres."""
    var_labels = {}
    value_labels = {}
    
    # Normalización del texto del SPS
    text = sps_content.replace('\r', ' ').replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)

    # 1. VARIABLE LABELS
    var_match = re.search(r"VARIABLE LABELS (.*?)\.", text, re.IGNORECASE)
    if var_match:
        entries = re.findall(r"(?:/|^)\s*(\S+)\s+['\"](.*?)['\"]", var_match.group(1))
        for var_name, label in entries:
            # Normalizamos el nombre del SPS a formato estándar (con _)
            clean_name = var_name.strip().replace('/', '_')
            var_labels[clean_name] = label

    # 2. VALUE LABELS (Soporta códigos de texto y números)
    val_blocks = re.findall(r"VALUE LABELS\s+(.*?)\.", text, re.IGNORECASE)
    for block in val_blocks:
        block = block.strip()
        first_quote = re.search(r"['\"]", block)
        if not first_quote: continue
        
        vars_part = block[:first_quote.start()].strip()
        labels_part = block[first_quote.start():].strip()
        
        # Normalizar nombres de variables del bloque
        var_names = [v.replace('/', '_') for v in re.split(r"[\s/]+", vars_part) if v]
        pairs = re.findall(r"['\"]([^'\"]+)['\"]\s+['\"]([^'\"]+)['\"]", labels_part)
        
        if pairs:
            v_map = {p[0]: p[1] for p in pairs}
            for vn in var_names:
                value_labels[vn] = v_map
        
    return var_labels, value_labels

def main():
    # --- HEADER VISUAL ---
    c_img1, c_title, c_img2 = st.columns([1, 4, 1])
    with c_img1: st.image(LOGO_SPSS, width=80)
    with c_title: 
        st.title("🛡️ SPSS Master Flow Pro")
        st.caption("Trendsity | Limpieza automática de cabeceras Kobo ( / ➔ _ )")
    with c_img2: st.image(LOGO_KOBO, width=60)

    # --- SIDEBAR: CHECKLIST ---
    with st.sidebar:
        st.header("📋 Estado del Proyecto")
        s1 = "✅" if st.session_state.get('meta_loaded') else "❌"
        s2 = "✅" if st.session_state.get('excel_downloaded') else "⏳"
        s3 = "✅" if st.session_state.get('apto') else "❌"
        
        st.write(f"{s1} 1. ADN Inyectado")
        st.write(f"{s2} 2. Pack Excel Limpio")
        st.write(f"{s3} 3. Aduana Superada")
        
        st.divider()
        if st.button("🔄 REINICIAR TODO"):
            st.session_state.clear()
            st.rerun()

    # --- PASO 0: CARGA Y LIMPIEZA AUTOMÁTICA ---
    if 'meta_loaded' not in st.session_state:
        mode = st.radio("Estructura de origen:", ["KoboToolbox", "LimeSurvey"], horizontal=True)
        
        if mode == "KoboToolbox":
            st.info("### 1. Sube tus archivos de Kobo\nEl sistema reemplazará automáticamente las barras `/` de los nombres por `_`.")
            c1, c2 = st.columns(2)
            with c1: f_excel = st.file_uploader("📥 Datos Excel", type=["xlsx"])
            with c2: f_sps = st.file_uploader("📥 Sintaxis .SPS", type=["sps"])
            
            if f_excel and f_sps:
                with st.spinner("Limpiando cabeceras y cargando ADN..."):
                    df = pd.read_excel(f_excel)
                    # --- LIMPIEZA AUTOMÁTICA DE CABECERAS ---
                    df.columns = [c.replace('/', '_') for c in df.columns]
                    
                    sps_text = f_sps.read().decode("latin-1")
                    v_labels, val_labels = parse_sps_metadata_v6(sps_text)
                    
                    st.session_state.update({
                        'df_orig': df, 'v_labels': v_labels, 'val_labels': val_labels,
                        'all_cols': list(df.columns), 'meta_loaded': True, 'mode': 'kobo'
                    })
                    st.rerun()
        else:
            # [Modo LimeSurvey similar al anterior...]
            f_sav = st.file_uploader("📥 Archivo SAV", type=["sav"])
            if f_sav:
                with open("temp.sav", "wb") as f: f.write(f_sav.getbuffer())
                df, meta = pyreadstat.read_sav("temp.sav")
                st.session_state.update({
                    'df_orig': df, 'v_labels': meta.column_names_to_labels, 
                    'val_labels': meta.variable_value_labels, 'all_cols': list(df.columns), 
                    'meta_loaded': True, 'mode': 'limesurvey'
                })
                os.remove("temp.sav")
                st.rerun()
        return

    # --- TABS DE TRABAJO ---
    t1, t2, t3 = st.tabs(["🌳 ADN & PACK LIMPIO", "🔍 ADUANA", "🚀 EXPORTAR"])

    with t1:
        st.markdown("### 🧬 ADN y Template de Trabajo")
        st.write("Abajo puedes ver cómo quedaron los nombres de columna tras la limpieza.")
        
        col_res, col_pack = st.columns([2, 1])
        with col_res:
            resumen = []
            for c in st.session_state.all_cols:
                label = st.session_state.v_labels.get(c, "❌ NO ENCONTRADA EN SPS")
                dict_status = "✅ OK" if c in st.session_state.val_labels else "---"
                resumen.append({"Variable (Limpia)": c, "Etiqueta SPSS": label, "Diccionario": dict_status})
            st.dataframe(pd.DataFrame(resumen), height=350)
            
        with col_pack:
            st.success("✨ Cabeceras corregidas")
            out_xlsx = io.BytesIO()
            st.session_state.df_orig.to_excel(out_xlsx, index=False)
            if st.download_button("📥 DESCARGAR EXCEL PARA CLIENTE", out_xlsx.getvalue(), "Base_Limpia_Para_Planchado.xlsx", use_container_width=True):
                st.session_state.excel_downloaded = True
            st.caption("Este Excel ya tiene las cabeceras corregidas (ej: F9_1). Pídele al cliente que no las toque.")

    with t2:
        st.markdown("### 🔍 Aduana de Validación")
        f_p = st.file_uploader("📤 Subir Excel Planchado por Cliente", type=["xlsx"])
        if f_p:
            df_p = pd.read_excel(f_p)
            errores = []
            for col in df_p.columns:
                if col in st.session_state.val_labels:
                    valid_codes = set(str(k) for k in st.session_state.val_labels[col].keys())
                    for idx, val in df_p[col].items():
                        # Validar si el valor existe en el diccionario (como string para evitar líos de tipos)
                        if pd.notnull(val) and str(val) not in valid_codes:
                            errores.append({"Fila": idx+2, "Variable": col, "Error": "Código inválido", "Valor": val})
            
            if errores:
                st.error(f"❌ Errores detectados: {len(errores)}")
                st.dataframe(pd.DataFrame(errores).head(50))
                st.session_state.apto = False
            else:
                st.success("✅ Validación superada. Los datos son consistentes con el ADN.")
                st.session_state.apto = True
                st.session_state.df_final = df_p

    with t3:
        if st.session_state.get('apto'):
            st.subheader("🚀 Generación de SAV Final")
            name = st.text_input("Nombre del archivo:", "Trendsity_Data_Final")
            if st.button("GENERAR Y DESCARGAR"):
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
            st.warning("🔒 Debes completar la validación en la pestaña 'Aduana'.")

if __name__ == "__main__":
    main()
