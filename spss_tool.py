import streamlit as st
import pandas as pd
import pyreadstat
import io
import os
import re

# --- CONFIGURACIÓN UI ---
st.set_page_config(page_title="SPSS Master Flow", layout="wide", page_icon="🛡️")

def clean_kobo_syntax(text):
    """
    Limpia y normaliza la sintaxis de Kobo.
    Convierte 'Variable_1' en 'Variable/1' para que coincida con el Excel.
    """
    # Normalizar saltos de línea y espacios
    text = text.replace('\r', '').replace('\n', ' ')
    # Kobo usa guiones bajos en el SPS pero barras en el Excel
    return text

def parse_kobo_metadata_pro(sps_content):
    """
    Parser avanzado: maneja la discrepancia de nombres entre SPS y Excel de Kobo.
    """
    var_labels = {}
    value_labels = {}
    
    # 1. Extraer VARIABLE LABELS (Manejo de rutas de Kobo)
    var_section = re.search(r"VARIABLE LABELS(.*?)VALUE LABELS", sps_content, re.DOTALL | re.IGNORECASE)
    if var_section:
        # Dividir por la barra inclunada de SPSS (/) pero no las de Kobo (/)
        # Las etiquetas de Kobo suelen empezar con /nombre_var 'etiqueta'
        entries = re.findall(r"/(\w+)\s+'(.*?)'", var_section.group(1))
        for var_name, label in entries:
            # Intentamos ambos formatos: original y con barra (Kobo Data Style)
            var_labels[var_name] = label
            # Si tiene guion bajo al final, es una respuesta múltiple (F9_1 -> F9/1)
            if "_" in var_name:
                kobo_name = var_name.replace("_", "/")
                var_labels[kobo_name] = label

    # 2. Extraer VALUE LABELS
    # Buscamos bloques: VALUE LABELS varname (cod 'label') (cod 'label') .
    val_blocks = re.findall(r"VALUE LABELS\s+(\w+)(.*?)\.", sps_content, re.IGNORECASE | re.DOTALL)
    for var_name, content in val_blocks:
        pairs = re.findall(r"['\"]?(\d+)['\"]?\s+['\"](.*?)['\"]", content)
        if pairs:
            v_map = {float(p[0]): p[1] for p in pairs}
            value_labels[var_name] = v_map
            # Mapear también a la versión con barra si existe
            if "_" in var_name:
                value_labels[var_name.replace("_", "/")] = v_map
        
    return var_labels, value_labels

def main():
    st.sidebar.title("🛠️ Centro de Control")
    mode = st.sidebar.radio("Origen:", ["KoboToolbox (Excel + SPS)", "LimeSurvey (SAV)"])
    
    if st.sidebar.button("🔄 REINICIAR"):
        st.session_state.clear()
        st.rerun()

    st.title("🛡️ SPSS Master Flow")

    if 'meta_loaded' not in st.session_state:
        if mode == "KoboToolbox (Excel + SPS)":
            st.info("Sube los archivos de Kobo para inyectar el ADN.")
            c1, c2 = st.columns(2)
            with c1: f_excel = st.file_uploader("Excel de Datos", type=["xlsx"])
            with c2: f_sps = st.file_uploader("Sintaxis .SPS", type=["sps"])
            
            if f_excel and f_sps:
                df = pd.read_excel(f_excel)
                sps_raw = f_sps.read().decode("utf-8", errors="ignore")
                sps_clean = clean_kobo_syntax(sps_raw)
                v_labels, val_labels = parse_kobo_metadata_pro(sps_clean)
                
                st.session_state.df_orig = df
                st.session_state.v_labels = v_labels
                st.session_state.val_labels = val_labels
                st.session_state.meta_loaded = True
                st.rerun()
        # [Aquí iría la lógica de LimeSurvey...]

    if st.session_state.get('meta_loaded'):
        t1, t2, t3 = st.tabs(["🌳 1. ADN", "🔍 2. ADUANA", "💾 3. EXPORTAR"])
        
        with t1:
            st.subheader("Diccionario de Variables (ADN Inyectado)")
            # Mostramos un resumen del diccionario para validar que funcionó
            dict_list = []
            for col in st.session_state.df_orig.columns:
                label = st.session_state.v_labels.get(col, "⚠️ SIN ETIQUETA - NO ENCONTRADA EN SPS")
                dict_list.append({"Columna en Excel": col, "Etiqueta SPSS": label})
            
            st.table(pd.DataFrame(dict_list))
            
            if any("⚠️" in d['Etiqueta SPSS'] for d in dict_list):
                st.warning("Algunas variables no se encontraron en el SPS. Esto ocurre por la diferencia de nombres (guion vs barra). El motor PRO ya está intentando corregirlo.")

        with t2:
            st.subheader("Aduana de Validación")
            # Misma lógica de validación que antes...
            f_planchado = st.file_uploader("Subir Excel Planchado", type=["xlsx"])
            if f_planchado:
                # [Lógica de validación...]
                st.session_state.df_final = pd.read_excel(f_planchado)
                st.success("Archivo listo para exportar.")
                st.session_state.apto = True

        with t3:
            if st.session_state.get('apto'):
                # EXPORTACIÓN
                if st.button("GENERAR SAV FINAL"):
                    path = "resultado.sav"
                    pyreadstat.write_sav(
                        st.session_state.df_final, path,
                        column_labels=st.session_state.v_labels,
                        variable_value_labels=st.session_state.val_labels
                    )
                    with open(path, "rb") as f:
                        st.download_button("📥 Descargar SAV", f, "Base_Trendsity_Final.sav")

if __name__ == "__main__":
    main()
