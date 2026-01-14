import streamlit as st
import pandas as pd
import pyreadstat
import io
import os
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SPSS Master Flow", layout="wide", page_icon="🛡️")

# --- MOTOR DE ADN AVANZADO (PRO PARSER) ---
def parse_kobo_metadata_pro(sps_content):
    """Extrae etiquetas de variables y de valores (códigos) sincronizando nombres de Kobo."""
    var_labels = {}
    value_labels = {}
    
    # Normalizar texto: eliminar saltos de línea y excesos de espacios
    clean_text = re.sub(r'\s+', ' ', sps_content)

    # 1. VARIABLE LABELS: Captura "nombre 'etiqueta'"
    # Buscamos el bloque VARIABLE LABELS ... .
    var_match = re.search(r"VARIABLE LABELS (.*?)\.", clean_text, re.IGNORECASE)
    if var_match:
        content = var_match.group(1)
        # Regex para capturar /nombre 'etiqueta' o el primer nombre sin /
        entries = re.findall(r"(?:/|^)\s*(\S+)\s+'(.*?)'", content)
        for var_name, label in entries:
            var_labels[var_name] = label
            if "_" in var_name: var_labels[var_name.replace("_", "/")] = label

    # 2. VALUE LABELS: Captura "nombre 'cod' 'etiqueta' 'cod' 'etiqueta' ..."
    val_blocks = re.findall(r"VALUE LABELS\s+(\S+)(.*?)\.", clean_text, re.IGNORECASE)
    for var_name, content in val_blocks:
        pairs = re.findall(r"['\"]?(\d+)['\"]?\s+['\"](.*?)['\"]", content)
        if pairs:
            v_map = {float(p[0]): p[1] for p in pairs}
            value_labels[var_name] = v_map
            if "_" in var_name: value_labels[var_name.replace("_", "/")] = v_map
        
    return var_labels, value_labels

def main():
    # --- SIDEBAR: CHECKLIST DE PROGRESO ---
    with st.sidebar:
        st.title("🛡️ Estado del Proyecto")
        
        # Lógica de indicadores
        dna_status = "✅" if st.session_state.get('meta_loaded') else "❌"
        excel_status = "✅" if st.session_state.get('excel_downloaded') else "⏳"
        audit_status = "✅" if st.session_state.get('apto') else "❌"
        
        st.markdown(f"""
        **Paso a Paso:**
        * {dna_status} 1. ADN Cargado
        * {excel_status} 2. Excel Crudo Descargado
        * {audit_status} 3. Validación (Aduana)
        * {"✅" if audit_status == "✅" else "🔒"} 4. Exportación SAV
        """)
        
        st.divider()
        if st.button("🔄 REINICIAR TODO"):
            st.session_state.clear()
            st.rerun()

    st.title("🛡️ SPSS Validator & Analytics Suite")
    
    # --- SELECTOR DE HERRAMIENTA ---
    mode = st.radio("Seleccione el origen de la estructura:", 
                    ["KoboToolbox (Excel + SPS)", "LimeSurvey (SAV Original)"], horizontal=True)

    # --- FASE 0: CARGA ---
    if 'meta_loaded' not in st.session_state:
        st.info("### 1️⃣ Paso 1: Inyección de ADN\nSuba los archivos base para extraer la inteligencia de datos.")
        
        if mode == "KoboToolbox (Excel + SPS)":
            c1, c2 = st.columns(2)
            with c1: f_excel = st.file_uploader("📥 Excel de Datos (Kobo)", type=["xlsx"])
            with c2: f_sps = st.file_uploader("📥 Sintaxis .SPS (Etiquetas)", type=["sps"])
            
            if f_excel and f_sps:
                df = pd.read_excel(f_excel)
                sps_text = f_sps.read().decode("utf-8", errors="ignore")
                v_labels, val_labels = parse_kobo_metadata_pro(sps_text)
                st.session_state.update({'df_orig': df, 'v_labels': v_labels, 'val_labels': val_labels, 'all_cols': list(df.columns), 'meta_loaded': True})
                st.rerun()
        else:
            f_sav = st.file_uploader("📥 Archivo .SAV base", type=["sav"])
            if f_sav:
                with open("temp.sav", "wb") as f: f.write(f_sav.getbuffer())
                df, meta = pyreadstat.read_sav("temp.sav")
                st.session_state.update({'df_orig': df, 'v_labels': meta.column_names_to_labels, 'val_labels': meta.variable_value_labels, 'all_cols': list(df.columns), 'meta_loaded': True})
                os.remove("temp.sav")
                st.rerun()
        return

    # --- TABS CON INSTRUCCIONES ---
    t1, t2, t3 = st.tabs(["🌳 1. ADN & PACK CLIENTE", "🔍 2. ADUANA (CONTROL)", "💾 3. EXPORTAR"])

    with t1:
        st.markdown("""
        ### 📋 Gestión de ADN
        **¿Qué hace este paso?** Extrae todas las etiquetas del SPS y las vincula a las columnas. Aquí preparas el archivo que el cliente debe "planchar" (limpiar o corregir).
        """)
        
        col_list, col_pack = st.columns([2, 1])
        with col_list:
            cols = st.multiselect("Variables a incluir:", st.session_state.all_cols, default=st.session_state.all_cols)
            df_client = st.session_state.df_orig[cols]
        
        with col_pack:
            st.success("ADN Sincronizado")
            out_xlsx = io.BytesIO()
            df_client.to_excel(out_xlsx, index=False)
            if st.download_button("📥 DESCARGAR EXCEL PARA CLIENTE", out_xlsx.getvalue(), "Base_Para_Trabajar.xlsx", use_container_width=True):
                st.session_state.excel_downloaded = True

    with t2:
        st.markdown("""
        ### 🔍 Aduana de Datos
        **¿Qué hace este paso?**
        Verifica que el Excel que devuelve el cliente sea consistente. 
        - Chequea que los códigos (1, 2, 3...) existan en el SPS original.
        - Detecta textos donde debería haber números.
        """)
        
        f_p = st.file_uploader("📤 Subir Excel Planchado por el Cliente", type=["xlsx"])
        if f_p:
            df_p = pd.read_excel(f_p)
            errores = []
            for col in df_p.columns:
                if col in st.session_state.val_labels:
                    # Validar si los códigos en el excel existen en el diccionario
                    valid_codes = set(st.session_state.val_labels[col].keys())
                    invalid_rows = df_p[~df_p[col].isin(valid_codes) & df_p[col].notnull()]
                    for idx in invalid_rows.index:
                        errores.append({"Fila": idx+2, "Variable": col, "Error": "Código inválido", "Valor": df_p.at[idx, col]})
            
            if errores:
                st.error(f"❌ Se encontraron {len(errores)} errores de consistencia.")
                st.table(pd.DataFrame(errores).head(10))
                st.session_state.apto = False
            else:
                st.success("✅ ¡Validación Exitosa! Los datos coinciden con el ADN.")
                st.session_state.apto = True
                st.session_state.df_final = df_p

    with t3:
        st.markdown("""
        ### 💾 Exportación Final
        **¿Qué hace este paso?**
        Genera el archivo `.sav` definitivo. Lo más importante: **Inyecta las etiquetas de texto** (ej: 1 -> "Hombre") dentro del archivo para que al abrirlo en SPSS ya esté todo configurado.
        """)
        
        if st.session_state.get('apto'):
            name = st.text_input("Nombre del archivo:", "Base_Final_Trendsity")
            if st.button("🚀 GENERAR SPSS (.SAV)"):
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
            st.warning("🔒 Bloqueado: Primero debe pasar la validación en la pestaña 'Aduana'.")

if __name__ == "__main__":
    main()
