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
        os.remove(input_path)

    # TABS DEL FLUJO LINEAL
    t1, t2, t3 = st.tabs(["🌳 Paso 1: ADN & Estructura", "🔍 Paso 2: Validación de Planchado", "💾 Paso 3: Exportación Final"])

    # --- TAB 1: DEFINICIÓN DE ESTRUCTURA Y ENTREGA AL CLIENTE ---
    with t1:
        st.subheader("Configuración de la Base para el Cliente")
        cols_to_keep = st.multiselect(
            "Seleccione/Filtre las columnas para el cliente:", 
            options=st.session_state.all_cols, 
            default=st.session_state.all_cols
        )
        
        df_for_client = st.session_state.df_orig[cols_to_keep]
        st.session_state.cols_active = cols_to_keep # Guardamos para el planchado

        st.write(f"Variables activas: {len(cols_to_keep)}")
        
        # Botón para descargar el SAV que el cliente debe llenar/corregir
        st.info("💡 Descarga este SAV para entregárselo al cliente. El cliente debe devolver este archivo convertido en Excel.")
        
        buf_base = io.BytesIO()
        # Mantenemos metadatos originales solo de las columnas elegidas
        f_labels = {k: v for k, v in st.session_state.meta.column_names_to_labels.items() if k in cols_to_keep}
        f_values = {k: v for k, v in st.session_state.meta.variable_value_labels.items() if k in cols_to_keep}
        
        pyreadstat.write_sav(df_for_client, "base_cliente.sav", column_labels=f_labels, variable_value_labels=f_values)
        with open("base_cliente.sav", "rb") as f:
            st.download_button("📥 Descargar SAV para Cliente", f, "Estructura_Cliente.sav", use_container_width=True)

    # --- TAB 2: CICLO DE PLANCHADO Y RECHAZO ---
    with t2:
        st.subheader("Auditoría del Excel de Planchado")
        excel_file = st.file_uploader("Subir el Excel que devolvió el cliente", type=["xlsx"])
        
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
                    # ADN de la variable: ¿Es numérica en el SAV original?
                    is_numeric_dna = pd.api.types.is_numeric_dtype(st.session_state.df_orig[col])
                    
                    for idx, val in df_excel[col].items():
                        # Error 1: Caracteres prohibidos (Naranja)
                        if detect_prohibited_chars(val):
                            log_errores.append({"Fila": idx+2, "Columna": col, "Error": "Caracteres Prohibidos/Saltos de Línea", "Valor": val})
                            style_map.at[idx, col] = 'background-color: #ff9800; color: white'

                        # Error 2: Tipo de dato (Rojo)
                        if is_numeric_dna and pd.notnull(val):
                            try:
                                float(val)
                            except:
                                log_errores.append({"Fila": idx+2, "Columna": col, "Error": "Se esperaba NÚMERO y hay TEXTO", "Valor": val})
                                style_map.at[idx, col] = 'background-color: #f44336; color: white'

            # Error 3: Teléfonos duplicados (Amarillo)
            if sel_phone:
                mask_dups = df_excel[sel_phone].duplicated(keep=False) & df_excel[sel_phone].notnull()
                for idx in df_excel.index[mask_dups]:
                    log_errores.append({"Fila": idx+2, "Columna": sel_phone, "Error": "Teléfono DUPLICADO", "Valor": df_excel.at[idx, sel_phone]})
                    style_map.at[idx, sel_phone] = 'background-color: #ffff00; color: black'

            # --- GESTIÓN DE LA DEVOLUCIÓN ---
            if log_errores:
                st.session_state.apto = False
                df_log = pd.DataFrame(log_errores)
                st.error(f"❌ ARCHIVO RECHAZADO: Se encontraron {len(log_errores)} incidencias.")
                
                # Crear Excel de Devolución
                output_audit = io.BytesIO()
                with pd.ExcelWriter(output_audit, engine='openpyxl') as writer:
                    df_excel.style.apply(lambda x: style_map, axis=None).to_excel(writer, sheet_name='DATOS_A_CORREGIR', index=False)
                    df_log.to_excel(writer, sheet_name='INFORME_DE_ERRORES', index=False)
                
                st.download_button(
                    label="📥 DESCARGAR INFORME DE ERRORES PARA EL CLIENTE",
                    data=output_audit.getvalue(),
                    file_name="RECHAZO_POR_CALIDAD.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                st.dataframe(df_log, use_container_width=True)
            else:
                st.success("✅ ARCHIVO VALIDADO: El Excel cumple con la sintaxis y reglas del ADN.")
                st.session_state.apto = True
                st.session_state.df_final = df_excel
        else:
            st.info("Esperando el Excel del cliente para iniciar el ciclo de validación.")

    # --- TAB 3: EXPORTACIÓN FINAL (BLOQUEADA HASTA VALIDACIÓN) ---
    with t3:
        if st.session_state.get('apto', False):
            st.subheader("💾 Exportación de Productos Finales")
            final_name = st.text_input("Nombre del Proyecto:", value="Estudio_Final_Limpio")
            
            # Exportar SAV con ADN inyectado
            output_sav = "final_clean.sav"
            pyreadstat.write_sav(
                st.session_state.df_final, 
                output_sav, 
                column_labels={k: v for k, v in st.session_state.meta.column_names_to_labels.items() if k in st.session_state.df_final.columns},
                variable_value_labels={k: v for k, v in st.session_state.meta.variable_value_labels.items() if k in st.session_state.df_final.columns}
            )
            
            with open(output_sav, "rb") as f:
                st.download_button("📥 Descargar SAV Final (Inteligente)", f, f"{final_name}.sav", use_container_width=True)
        else:
            st.warning("⚠️ Pestaña Bloqueada. Debe validar el Excel en el paso anterior y resolver todos los errores antes de exportar.")

if __name__ == "__main__":
    main()
