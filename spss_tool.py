import streamlit as st
import pandas as pd
import pyreadstat
import io
import os
import re

# Configuración profesional para Web y Móvil
st.set_page_config(page_title="SPSS Master Validator", layout="wide", page_icon="🛡️")

# --- FUNCIONES DE APOYO ---
def detect_prohibited_chars(val):
    if not isinstance(val, str): return False
    return bool(re.search(r'[\r\n\x00-\x1f\x7f-\x9f]', val))

def main():
    st.title("🛡️ Auditoría SPSS: ADN -> Validación -> Triple Exportación")
    
    # 1. CARGA DEL ADN ORIGINAL
    with st.sidebar:
        st.header("1. Estructura Base")
        uploaded_sav = st.file_uploader("Subir SAV Original (LimeSurvey)", type=["sav"])
        if st.button("🔄 Reiniciar Aplicación"):
            st.session_state.clear()
            st.rerun()

    if not uploaded_sav:
        st.info("👈 Sube el archivo base para definir las reglas y etiquetas.")
        return

    # Procesar archivo base una sola vez
    if 'df_orig' not in st.session_state:
        input_path = "meta_base.sav"
        with open(input_path, "wb") as f:
            f.write(uploaded_sav.getbuffer())
        df_orig, meta = pyreadstat.read_sav(input_path)
        st.session_state.df_orig = df_orig
        st.session_state.meta = meta
        st.session_state.all_cols = list(df_orig.columns)
        if os.path.exists(input_path): os.remove(input_path)

    # TABS DEL FLUJO
    t1, t2, t3 = st.tabs(["🌳 Paso 1: Filtro & Entrega", "🔍 Paso 2: Auditoría de Planchado", "💾 Paso 3: Exportación Final"])

    # --- TAB 1: FILTRO INICIAL Y ENTREGA AL CLIENTE ---
    with t1:
        st.subheader("Selección de Variables")
        cols_to_keep = st.multiselect(
            "Variables que el cliente debe trabajar:", 
            options=st.session_state.all_cols, 
            default=st.session_state.all_cols
        )
        st.session_state.cols_active_step1 = cols_to_keep
        df_for_client = st.session_state.df_orig[cols_to_keep]

        st.info("📦 **Pack de Inicio:** Descarga los archivos para enviar al cliente.")
        c1, c2 = st.columns(2)
        with c1:
            out_xlsx = io.BytesIO()
            df_for_client.to_excel(out_xlsx, index=False)
            st.download_button("📥 Descargar EXCEL para completar", out_xlsx.getvalue(), "Estructura_Cliente.xlsx", use_container_width=True)
        with c2:
            temp_sav = "base_cliente.sav"
            pyreadstat.write_sav(df_for_client, temp_sav, 
                                 column_labels={k: v for k, v in st.session_state.meta.column_names_to_labels.items() if k in cols_to_keep},
                                 variable_value_labels={k: v for k, v in st.session_state.meta.variable_value_labels.items() if k in cols_to_keep})
            with open(temp_sav, "rb") as f:
                st.download_button("📥 Descargar SPSS para protocolo", f, "Estructura_Cliente.sav", use_container_width=True)

    # --- TAB 2: AUDITORÍA Y CICLO DE RECHAZO ---
    with t2:
        st.subheader("🔍 Monitor de Calidad")
        excel_file = st.file_uploader("Subir el Excel que devolvió el cliente", type=["xlsx"])
        
        if excel_file:
            df_excel = pd.read_excel(excel_file)
            log_errores = []
            style_map = pd.DataFrame('', index=df_excel.index, columns=df_excel.columns)
            
            phone_cols = [c for c in df_excel.columns if any(x in c.lower() for x in ['tel', 'cel', 'phone'])]
            sel_phone = st.selectbox("Detección de duplicados en columna:", [None] + phone_cols)

            for col in df_excel.columns:
                if col in st.session_state.all_cols:
                    is_numeric_dna = pd.api.types.is_numeric_dtype(st.session_state.df_orig[col])
                    for idx, val in df_excel[col].items():
                        # Error 1: Chars prohibidos (Naranja)
                        if detect_prohibited_chars(val):
                            log_errores.append({"Fila": idx+2, "Columna": col, "Error": "Caracter prohibido", "Valor": val})
                            style_map.at[idx, col] = 'background-color: #ff9800'
                        # Error 2: Tipo de dato (Rojo)
                        if is_numeric_dna and pd.notnull(val):
                            try: float(val)
                            except:
                                log_errores.append({"Fila": idx+2, "Columna": col, "Error": "Texto en columna numérica", "Valor": val})
                                style_map.at[idx, col] = 'background-color: #f44336'

            if sel_phone:
                dups = df_excel[df_excel[sel_phone].duplicated(keep=False) & df_excel[sel_phone].notnull()]
                for idx in dups.index:
                    log_errores.append({"Fila": idx+2, "Columna": sel_phone, "Error": "Teléfono DUPLICADO", "Valor": df_excel.at[idx, sel_phone]})
                    style_map.at[idx, sel_phone] = 'background-color: #ffff00'

            if log_errores:
                st.error(f"❌ RECHAZADO: {len(log_errores)} errores encontrados.")
                out_audit = io.BytesIO()
                with pd.ExcelWriter(out_audit, engine='openpyxl') as writer:
                    df_excel.style.apply(lambda x: style_map, axis=None).to_excel(writer, sheet_name='CORREGIR_AQUI', index=False)
                    pd.DataFrame(log_errores).to_excel(writer, sheet_name='ERRORES', index=False)
                st.download_button("📥 DESCARGAR EXCEL DE RECHAZO", out_audit.getvalue(), "ERRORES_DETECTADOS.xlsx", use_container_width=True)
                st.session_state.apto = False
            else:
                st.success("✅ VALIDADO: El archivo es apto.")
                st.session_state.apto = True
                st.session_state.df_planchado = df_excel

    # --- TAB 3: EXPORTACIÓN FINAL (TRIPLE SALIDA) ---
    with t3:
        if st.session_state.get('apto', False):
            st.subheader("💾 Generación Final de Resultados")
            
            # Posibilidad de borrar más columnas al final
            cols_final = st.multiselect("Filtro final (Borrar sobrantes):", 
                                        options=list(st.session_state.df_planchado.columns), 
                                        default=list(st.session_state.df_planchado.columns))
            
            df_final = st.session_state.df_planchado[cols_final]
            name = st.text_input("Nombre del Proyecto:", "Resultado_Final")

            st.divider()
            c1, c2, c3 = st.columns(3)

            with c1:
                st.write("📊 **Formato SPSS**")
                st.caption("SAV con códigos y etiquetas")
                path_sav = "final.sav"
                pyreadstat.write_sav(df_final, path_sav, 
                                     column_labels={k: v for k, v in st.session_state.meta.column_names_to_labels.items() if k in df_final.columns},
                                     variable_value_labels={k: v for k, v in st.session_state.meta.variable_value_labels.items() if k in df_final.columns})
                with open(path_sav, "rb") as f:
                    st.download_button("Descargar SAV", f, f"{name}.sav", use_container_width=True)

            with c2:
                st.write("📖 **Excel Lectura**")
                st.caption("Traducido a Texto (Para Cliente)")
                df_human = df_final.copy()
                for col in df_human.columns:
                    if col in st.session_state.meta.variable_value_labels:
                        df_human[col] = df_human[col].map(st.session_state.meta.variable_value_labels[col]).fillna(df_human[col])
                out_h = io.BytesIO()
                df_human.to_excel(out_h, index=False)
                st.download_button("Descargar Excel Texto", out_h.getvalue(), f"{name}_Lectura.xlsx", use_container_width=True)

            with c3:
                st.write("🔢 **Excel Datos**")
                st.caption("Solo códigos (Para Analista)")
                out_c = io.BytesIO()
                df_final.to_excel(out_c, index=False)
                st.download_button("Descargar Excel Códigos", out_c.getvalue(), f"{name}_Codigos.xlsx", use_container_width=True)
        else:
            st.warning("⚠️ Debe validar el Excel en el paso anterior.")

if __name__ == "__main__":
    main()
