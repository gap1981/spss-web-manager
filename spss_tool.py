import streamlit as st
import pandas as pd
import pyreadstat
import io
import os
import re

# Configuración de la plataforma
st.set_page_config(page_title="SPSS Validator Flow", layout="wide", page_icon="🛡️")

# --- FUNCIONES DE CONTROL DE CALIDAD ---
def detect_prohibited_chars(val):
    if not isinstance(val, str): return False
    return bool(re.search(r'[\r\n\x00-\x1f\x7f-\x9f]', val))

def main():
    st.title("🛡️ Auditoría SPSS: ADN -> Planchado -> Validación")
    
    # 1. CARGA DEL ADN ORIGINAL
    with st.sidebar:
        st.header("1. Carga de Estructura")
        uploaded_sav = st.file_uploader("Subir SAV Original (LimeSurvey)", type=["sav"])
        if st.button("🔄 Reiniciar Todo"):
            st.session_state.clear()
            st.rerun()

    if not uploaded_sav:
        st.info("👈 Sube el archivo base para definir las reglas de las variables.")
        return

    # Procesar archivo base una sola vez
    if 'meta' not in st.session_state:
        input_path = "meta_base.sav"
        with open(input_path, "wb") as f:
            f.write(uploaded_sav.getbuffer())
        df_orig, meta = pyreadstat.read_sav(input_path)
        st.session_state.df_orig = df_orig
        st.session_state.meta = meta
        st.session_state.all_cols = list(df_orig.columns)
        if os.path.exists(input_path): os.remove(input_path)

    # TABS DEL FLUJO LINEAL
    t1, t2, t3 = st.tabs(["🌳 Paso 1: ADN & Entrega Cliente", "🔍 Paso 2: Validación de Planchado", "💾 Paso 3: Exportación Final"])

    # --- TAB 1: DEFINICIÓN DE ESTRUCTURA Y ENTREGA AL CLIENTE ---
    with t1:
        st.subheader("Configuración de la Base para el Cliente")
        cols_to_keep = st.multiselect(
            "Seleccione las columnas que enviará al cliente:", 
            options=st.session_state.all_cols, 
            default=st.session_state.all_cols
        )
        
        df_for_client = st.session_state.df_orig[cols_to_keep]
        st.session_state.cols_active = cols_to_keep 

        st.write(f"Variables seleccionadas: {len(cols_to_keep)}")
        
        st.info("📢 **Descarga para el Cliente:** Entregue estos archivos. El Excel es el que deberá devolver editado.")
        
        col_down1, col_down2 = st.columns(2)
        
        with col_down1:
            # DESCARGA EXCEL (Lo que ellos realmente usan)
            output_xlsx = io.BytesIO()
            df_for_client.to_excel(output_xlsx, index=False)
            st.download_button(
                label="📥 Descargar EXCEL para Cliente",
                data=output_xlsx.getvalue(),
                file_name="Estructura_Para_Completar.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        with col_down2:
            # DESCARGA SAV (Lo que ellos piden por protocolo)
            f_labels = {k: v for k, v in st.session_state.meta.column_names_to_labels.items() if k in cols_to_keep}
            f_values = {k: v for k, v in st.session_state.meta.variable_value_labels.items() if k in cols_to_keep}
            
            temp_sav = "base_cliente.sav"
            pyreadstat.write_sav(df_for_client, temp_sav, column_labels=f_labels, variable_value_labels=f_values)
            with open(temp_sav, "rb") as f:
                st.download_button(
                    label="📥 Descargar SPSS para Cliente",
                    data=f,
                    file_name="Estructura_Cliente.sav",
                    mime="application/octet-stream",
                    use_container_width=True
                )
            if os.path.exists(temp_sav): os.remove(temp_sav)

    # --- TAB 2: CICLO DE PLANCHADO Y RECHAZO ---
    with t2:
        st.subheader("Auditoría del Excel de Planchado")
        excel_file = st.file_uploader("Subir el Excel que devolvió el cliente (editado)", type=["xlsx"])
        
        if excel_file:
            df_excel = pd.read_excel(excel_file)
            st.write("⌛ Iniciando escaneo de integridad...")

            # Detección de Teléfonos Repetidos
            phone_cols = [c for c in df_excel.columns if any(x in c.lower() for x in ['tel', 'cel', 'phone'])]
            sel_phone = st.selectbox("Columna de Teléfono (Opcional):", [None] + phone_cols)

            # --- MOTOR DE AUDITORÍA ---
            log_errores = []
            style_map = pd.DataFrame('', index=df_excel.index, columns=df_excel.columns)

            for col in df_excel.columns:
                if col in st.session_state.cols_active:
                    is_numeric_dna = pd.api.types.is_numeric_dtype(st.session_state.df_orig[col])
                    
                    for idx, val in df_excel[col].items():
                        # Error 1: Caracteres prohibidos
                        if detect_prohibited_chars(val):
                            log_errores.append({"Fila": idx+2, "Columna": col, "Error": "Caracteres Prohibidos (Saltos de línea)", "Valor": val})
                            style_map.at[idx, col] = 'background-color: #ff9800; color: white'

                        # Error 2: Tipo de dato (Se esperaba número)
                        if is_numeric_dna and pd.notnull(val):
                            try:
                                float(val)
                            except:
                                log_errores.append({"Fila": idx+2, "Columna": col, "Error": "Dato NO numérico", "Valor": val})
                                style_map.at[idx, col] = 'background-color: #f44336; color: white'

            # Error 3: Teléfonos duplicados
            if sel_phone:
                mask_dups = df_excel[sel_phone].duplicated(keep=False) & df_excel[sel_phone].notnull()
                for idx in df_excel.index[mask_dups]:
                    log_errores.append({"Fila": idx+2, "Columna": sel_phone, "Error": "Teléfono REPETIDO", "Valor": df_excel.at[idx, sel_phone]})
                    style_map.at[idx, sel_phone] = 'background-color: #ffff00; color: black'

            # --- GESTIÓN DE LA DEVOLUCIÓN ---
            if log_errores:
                st.session_state.apto = False
                df_log = pd.DataFrame(log_errores)
                st.error(f"❌ ARCHIVO RECHAZADO: Se encontraron {len(log_errores)} errores.")
                
                output_audit = io.BytesIO()
                with pd.ExcelWriter(output_audit, engine='openpyxl') as writer:
                    df_excel.style.apply(lambda x: style_map, axis=None).to_excel(writer, sheet_name='CORREGIR_AQUI', index=False)
                    df_log.to_excel(writer, sheet_name='INFORME_DE_ERRORES', index=False)
                
                st.download_button(
                    label="📥 DESCARGAR EXCEL CON ERRORES MARCADOS",
                    data=output_audit.getvalue(),
                    file_name="DEVOLVER_AL_CLIENTE_CON_ERRORES.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                st.dataframe(df_log, use_container_width=True)
            else:
                st.success("✅ ARCHIVO VALIDADO: El Excel está perfecto para generar la base final.")
                st.session_state.apto = True
                st.session_state.df_final = df_excel
        else:
            st.info("Suba el Excel editado por el cliente para validarlo.")

    # --- TAB 3: EXPORTACIÓN FINAL ---
    with t3:
        if st.session_state.get('apto', False):
            st.subheader("💾 Exportación de Base Final")
            final_name = st.text_input("Nombre del archivo:", value="Base_Limpia_Analisis")
            
            output_sav = "final_clean.sav"
            pyreadstat.write_sav(
                st.session_state.df_final, 
                output_sav, 
                column_labels={k: v for k, v in st.session_state.meta.column_names_to_labels.items() if k in st.session_state.df_final.columns},
                variable_value_labels={k: v for k, v in st.session_state.meta.variable_value_labels.items() if k in st.session_state.df_final.columns}
            )
            
            with open(output_sav, "rb") as f:
                st.download_button("📥 Descargar SAV Final para Procesamiento", f, f"{final_name}.sav", use_container_width=True)
            
            if os.path.exists(output_sav): os.remove(output_sav)
        else:
            st.warning("Debe validar el Excel en el Paso 2 para habilitar esta descarga.")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
