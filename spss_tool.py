import streamlit as st
import pandas as pd
import pyreadstat
import io
import os
import datetime

# --- CONFIGURACIÓN DE INTERFAZ ESTILO SPSS ---
st.set_page_config(page_title="SPSS Cloud Manager Pro", layout="wide", page_icon="📊")

def generate_spss_syntax(df, meta):
    """Genera un archivo de sintaxis .sps básico para reconstruir etiquetas."""
    syntax = ["* Sintaxis generada por SPSS Web Manager Pro.\n"]
    
    # Variable Labels
    syntax.append("VARIABLE LABELS")
    for var, label in meta.column_names_to_labels.items():
        if var in df.columns:
            syntax.append(f"  {var} '{label}'")
    syntax.append(".\n")
    
    # Value Labels
    if meta.variable_value_labels:
        syntax.append("VALUE LABELS")
        for var, labels in meta.variable_value_labels.items():
            if var in df.columns:
                syntax.append(f"  / {var}")
                for val, lab in labels.items():
                    val_str = f"'{val}'" if isinstance(val, str) else str(val)
                    syntax.append(f"    {val_str} '{lab}'")
        syntax.append(".\n")
    
    syntax.append("EXECUTE.")
    return "\n".join(syntax)

def main():
    # --- ESTILOS CSS PARA ANDROID/WEB ---
    st.markdown("""
        <style>
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #f0f2f6; border-radius: 4px 4px 0px 0px; padding: 10px;
        }
        .stTabs [aria-selected="true"] { background-color: #007bff !important; color: white !important; }
        </style>
    """, unsafe_allow_html=True)

    st.title("📊 SPSS Web Manager Pro")
    st.info("Herramienta para procesar exportaciones de LimeSurvey y revisiones de clientes.")

    # --- BARRA LATERAL: CARGA DE ARCHIVOS ---
    with st.sidebar:
        st.header("1. Carga de Archivos")
        uploaded_sav = st.file_uploader("Subir SAV Original (Metadatos)", type=["sav"])
        uploaded_excel = st.file_uploader("Subir Excel Revisado (Datos)", type=["xlsx"])
        
        st.divider()
        if st.button("🗑️ Borrar Todo y Reiniciar"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

    if not uploaded_sav:
        st.warning("👈 Por favor, carga el archivo .sav original para empezar.")
        return

    # --- PROCESAMIENTO DE ARCHIVOS ---
    # Leer SAV original para extraer el "ADN" (etiquetas, tipos, etc.)
    with open("temp_orig.sav", "wb") as f:
        f.write(uploaded_sav.getbuffer())
    df_sav, meta = pyreadstat.read_sav("temp_orig.sav")
    
    # Cargar datos desde Excel o desde el SAV si no hay Excel aún
    if uploaded_excel:
        df_final = pd.read_excel(uploaded_excel)
        st.success("✅ Datos del Excel del cliente cargados.")
    else:
        df_final = df_sav.copy()
        st.info("💡 Usando datos del SAV (aún no has subido el Excel revisado).")

    # --- VALIDACIÓN DE COMPATIBILIDAD ---
    missing_in_excel = [c for c in df_sav.columns if c not in df_final.columns]
    if missing_in_excel and uploaded_excel:
        st.error(f"⚠️ El Excel no contiene estas columnas necesarias: {', '.join(missing_in_excel)}")
        if not st.checkbox("Continuar ignorando columnas faltantes"):
            return

    # --- PESTAÑAS PRINCIPALES (INTERFACE SPSS) ---
    tab_data, tab_vars, tab_export = st.tabs(["📑 Vista de Datos", "🗂️ Vista de Variables", "📥 Exportar Entregables"])

    with tab_data:
        st.subheader("Data View")
        # st.data_editor permite editar celdas como en SPSS
        df_final = st.data_editor(df_final, use_container_width=True, height=500)

    with tab_vars:
        st.subheader("Variable View")
        var_data = []
        for col in df_final.columns:
            var_data.append({
                "Nombre": col,
                "Etiqueta": meta.column_names_to_labels.get(col, "Sin etiqueta"),
                "Tipo": "Numérica" if col in meta.variable_value_labels else "Cadena/Texto",
                "Medida": meta.variable_measure.get(col, "unknown"),
                "Valores": str(meta.variable_value_labels.get(col, ""))
            })
        st.table(pd.DataFrame(var_data))

    with tab_export:
        st.subheader("Generación de Archivos para el Cliente")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🛠️ Configuración")
            file_name = st.text_input("Nombre del proyecto:", "Estudio_Revisado")
            
        with col2:
            st.markdown("### 📦 Entregables")
            
            # 1. Generar SAV "Planchado"
            try:
                # Sincronizamos metadatos: solo los de las columnas presentes en df_final
                clean_labels = {k: v for k, v in meta.column_names_to_labels.items() if k in df_final.columns}
                clean_values = {k: v for k, v in meta.variable_value_labels.items() if k in df_final.columns}
                
                sav_buffer = io.BytesIO()
                pyreadstat.write_sav(
                    df_final, 
                    "temp_output.sav", 
                    column_labels=clean_labels,
                    variable_value_labels=clean_values,
                    variable_measure=meta.variable_measure
                )
                with open("temp_output.sav", "rb") as f:
                    st.download_button("📥 Descargar .SAV (SPSS)", f, file_name=f"{file_name}.sav")
            except Exception as e:
                st.error(f"Error al generar SAV: {e}")

            # 2. Libro de Códigos (Excel de códigos)
            codebook_list = []
            for var, labels in clean_values.items():
                for code, label in labels.items():
                    codebook_list.append({"Variable": var, "Código": code, "Etiqueta de Valor": label})
            
            df_codes = pd.DataFrame(codebook_list)
            output_codes = io.BytesIO()
            with pd.ExcelWriter(output_codes, engine='openpyxl') as writer:
                df_codes.to_excel(writer, index=False)
            st.download_button("📥 Descargar Libro de Códigos (Excel)", output_codes.getvalue(), file_name=f"{file_name}_codigos.xlsx")

            # 3. Sintaxis .SPS
            syntax_content = generate_spss_syntax(df_final, meta)
            st.download_button("📥 Descargar Sintaxis (.SPS)", syntax_content, file_name=f"{file_name}.sps")

    # Limpieza
    if os.path.exists("temp_orig.sav"): os.remove("temp_orig.sav")
    if os.path.exists("temp_output.sav"): os.remove("temp_output.sav")

if __name__ == "__main__":
    main()
