import streamlit as st
import pandas as pd
import pyreadstat
import io
import os
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SPSS Master Flow", layout="wide", page_icon="🛡️")

# --- MOTOR DE ADN (PARSER ULTRA-ROBUSTO) ---
def parse_sps_metadata_ultra(sps_content):
    """Extrae etiquetas de variables y valores (numéricos y texto) de Kobo."""
    var_labels = {}
    value_labels = {}
    
    # Limpiar y normalizar (SPSS usa puntos para cerrar bloques)
    text = sps_content.replace('\r', '').replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)

    # 1. VARIABLE LABELS
    var_section = re.search(r"VARIABLE LABELS (.*?)\.", text, re.IGNORECASE)
    if var_section:
        # Captura pares: /NombreVar 'Etiqueta'
        entries = re.findall(r"/(\S+)\s+'(.*?)'", var_section.group(1))
        for var_name, label in entries:
            var_labels[var_name] = label
            if "_" in var_name: var_labels[var_name.replace("_", "/")] = label

    # 2. VALUE LABELS (Maneja códigos de texto como 'AEP' y números como '1')
    val_blocks = re.findall(r"VALUE LABELS\s+(.*?)\.", text, re.IGNORECASE)
    for block in val_blocks:
        block = block.strip()
        # Separar nombres de variables de los pares de etiquetas
        first_quote = re.search(r"['\"]", block)
        if not first_quote: continue
        
        vars_part = block[:first_quote.start()].strip()
        labels_part = block[first_quote.start():].strip()
        
        var_names = re.split(r"[\s/]+", vars_part)
        # Captura pares de comillas: 'codigo' 'etiqueta'
        pairs = re.findall(r"['\"]([^'\"]+)['\"]\s+['\"]([^'\"]+)['\"]", labels_part)
        
        if pairs:
            # Diccionario: { 'AEP': 'AEP - Aeroparque', '1': 'Si' }
            v_map = {p[0]: p[1] for p in pairs}
            for vn in var_names:
                if not vn: continue
                value_labels[vn] = v_map
                if "_" in vn: value_labels[vn.replace("_", "/")] = v_map
        
    return var_labels, value_labels

def main():
    # --- BARRA LATERAL: CHECKLIST DE ESTADO ---
    with st.sidebar:
        st.title("🛡️ Estado del Proyecto")
        
        s1 = "✅" if st.session_state.get('meta_loaded') else "❌"
        s2 = "✅" if st.session_state.get('excel_downloaded') else "⏳"
        s3 = "✅" if st.session_state.get('apto') else "❌"
        
        st.markdown(f"**Progreso:**")
        st.write(f"{s1} 1. ADN del Proyecto")
        st.write(f"{s2} 2. Pack entregado al Cliente")
        st.write(f"{s3} 3. Validación de Planchado")
        st.write(f"{'✅' if s3 == '✅' else '🔒'} 4. Exportación Final")
        
        st.divider()
        if st.button("🔄 REINICIAR SISTEMA"):
            st.session_state.clear()
            st.rerun()

    st.title("🛡️ SPSS Validator & Analytics Flow")
    
    # Selector de origen
    mode = st.radio("Origen de Estructura:", ["KoboToolbox (Excel + SPS)", "LimeSurvey (SAV)"], horizontal=True)

    # --- PASO 0: CARGA INICIAL ---
    if 'meta_loaded' not in st.session_state:
        st.info("### 1️⃣ Paso 1: Carga de Archivos Base\nSuba los archivos originales para inyectar el ADN de datos.")
        
        if mode == "KoboToolbox (Excel + SPS)":
            c1, c2 = st.columns(2)
            with c1: f_excel = st.file_uploader("📥 Datos Crudos (.xlsx)", type=["xlsx"])
            with c2: f_sps = st.file_uploader("📥 Sintaxis Etiquetas (.sps)", type=["sps"])
            
            if f_excel and f_sps:
                df = pd.read_excel(f_excel)
                sps_text = f_sps.read().decode("utf-8", errors="ignore")
                v_labels, val_labels = parse_sps_metadata_ultra(sps_text)
                st.session_state.update({'df_orig': df, 'v_labels': v_labels, 'val_labels': val_labels, 'all_cols': list(df.columns), 'meta_loaded': True})
                st.rerun()
        else:
            f_sav = st.file_uploader("📥 Archivo SAV Original", type=["sav"])
            if f_sav:
                with open("temp.sav", "wb") as f: f.write(f_sav.getbuffer())
                df, meta = pyreadstat.read_sav("temp.sav")
                st.session_state.update({'df_orig': df, 'v_labels': meta.column_names_to_labels, 'val_labels': meta.variable_value_labels, 'all_cols': list(df.columns), 'meta_loaded': True})
                os.remove("temp.sav")
                st.rerun()
        return

    # --- TABS DE FLUJO ---
    t1, t2, t3 = st.tabs(["📋 1. ADN Y PACK TRABAJO", "🔍 2. ADUANA (REVISIÓN)", "💾 3. SPSS FINAL"])

    with t1:
        st.markdown("### 🧬 ADN Detectado\nEste es el diccionario que se aplicará. Verifique que las etiquetas de variable y valor coincidan.")
        
        col_vars, col_down = st.columns([2, 1])
        with col_vars:
            # Mostrar tabla de ADN
            resumen = []
            for c in st.session_state.all_cols:
                resumen.append({"Variable": c, "Etiqueta": st.session_state.v_labels.get(c, "⚠️ Sin etiqueta"), "Códigos": "✅ Sí" if c in st.session_state.val_labels else "---"})
            st.dataframe(pd.DataFrame(resumen), height=300)
        
        with col_down:
            st.success("✅ Estructura Lista")
            # Restaurada la descarga del Excel para el cliente
            out_xlsx = io.BytesIO()
            st.session_state.df_orig.to_excel(out_xlsx, index=False)
            if st.download_button("📥 DESCARGAR EXCEL PARA CLIENTE", out_xlsx.getvalue(), "Base_Para_Planchado.xlsx", use_container_width=True):
                st.session_state.excel_downloaded = True

    with t2:
        st.markdown("### 🔍 Aduana de Validación\nSube el archivo que el cliente editó. El sistema verificará si rompió los códigos (ej. puso texto donde van números).")
        f_p = st.file_uploader("📤 Subir Excel Planchado", type=["xlsx"])
        
        if f_p:
            df_p = pd.read_excel(f_p)
            errores = []
            for col in df_p.columns:
                if col in st.session_state.val_labels:
                    # Obtenemos los códigos válidos (pueden ser '1', '2' o 'AEP', 'EZE')
                    valid_codes = set(str(k) for k in st.session_state.val_labels[col].keys())
                    # Validar cada fila
                    for idx, val in df_p[col].items():
                        if pd.notnull(val) and str(val) not in valid_codes:
                            errores.append({"Fila": idx+2, "Variable": col, "Error": "Código inválido", "Valor": val})
            
            if errores:
                st.error(f"❌ Se encontraron {len(errores)} errores de consistencia.")
                st.write("El cliente debe usar los códigos definidos en el ADN (ej: '1' en lugar de 'Si', o 'AEP' en lugar de 'AEROPARQUE').")
                st.table(pd.DataFrame(errores).head(15))
                st.session_state.apto = False
            else:
                st.success("✅ ¡PERFECTO! Los datos son 100% consistentes con el ADN.")
                st.session_state.apto = True
                st.session_state.df_final = df_p

    with t3:
        if st.session_state.get('apto'):
            st.markdown("### 💾 Exportación Profesional\nSe inyectarán todos los metadatos (etiquetas de variable y de valor) en el archivo SAV.")
            name = st.text_input("Nombre del archivo:", "Base_Final_Trendsity")
            if st.button("🚀 GENERAR SAV FINAL"):
                path = f"{name}.sav"
                pyreadstat.write_sav(
                    st.session_state.df_final, path,
                    column_labels=st.session_state.v_labels,
                    variable_value_labels=st.session_state.val_labels
                )
                with open(path, "rb") as f:
                    st.download_button("📥 Descargar SAV Oficial", f, path, use_container_width=True)
                st.balloons()
        else:
            st.warning("⚠️ Paso Bloqueado: Primero debe corregir los errores en la pestaña 'Aduana'.")

if __name__ == "__main__":
    main()
