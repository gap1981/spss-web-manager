import streamlit as st
import pandas as pd
import pyreadstat
import io
import os
import re

# --- CONFIGURACIÓN DE UI PARA DISPOSITIVOS MÓVILES Y TABLETS ---
st.set_page_config(
    page_title="SPSS Master Validator",
    layout="wide", # Aprovecha el ancho de la Galaxy Tab y la Dell
    page_icon="🛡️"
)

# Estilo CSS extra para botones grandes en Android (Pixel 6)
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        height: 3em;
        font-weight: bold;
        border-radius: 10px;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE AUDITORÍA LÓGICA ---
def detect_prohibited_chars(val):
    if not isinstance(val, str): return False
    return bool(re.search(r'[\r\n\x00-\x1f\x7f-\x9f]', val))

def main():
    st.title("🛡️ SPSS Master Flow")
    st.caption("Estructura ADN ➔ Validación de Planchado ➔ Triple Exportación")

    # --- SIDEBAR: CONTROL CENTRAL ---
    with st.sidebar:
        st.header("⚙️ Configuración")
        uploaded_sav = st.file_uploader("📥 Subir SAV Original (ADN)", type=["sav"])
        if st.button("🔄 REINICIAR SISTEMA"):
            st.session_state.clear()
            st.rerun()
        st.divider()
        st.info("Dispositivo detectado: Optimizado para táctil y escritorio.")

    if not uploaded_sav:
        st.info("👈 Por favor, sube el archivo .sav base (el que generaste de LimeSurvey) para extraer las reglas del ADN de datos.")
        return

    # --- LÓGICA DE SESIÓN (PERSISTENCIA) ---
    if 'df_orig' not in st.session_state:
        with st.spinner("Extrayendo ADN de variables..."):
            input_path = "meta_base_temp.sav"
            with open(input_path, "wb") as f:
                f.write(uploaded_sav.getbuffer())
            df_orig, meta = pyreadstat.read_sav(input_path)
            st.session_state.df_orig = df_orig
            st.session_state.meta = meta
            st.session_state.all_cols = list(df_orig.columns)
            if os.path.exists(input_path): os.remove(input_path)

    # --- FLUJO POR PESTAÑAS (TABS) ---
    t1, t2, t3 = st.tabs(["🌳 1. ADN & Estructura", "🔍 2. Auditoría de Planchado", "💾 3. Exportación Final"])

    # --- PASO 1: DEFINICIÓN DE ADN Y ENTREGA ---
    with t1:
        st.subheader("Paso 1: Filtrado de ADN")
        st.write("Seleccione qué columnas formarán parte del proyecto.")
        
        cols_to_keep = st.multiselect(
            "Variables activas (puedes borrar las que no necesites):", 
            options=st.session_state.all_cols, 
            default=st.session_state.all_cols
        )
        st.session_state.cols_active_step1 = cols_to_keep
        
        df_for_client = st.session_state.df_orig[cols_to_keep]

        st.success("✅ Estructura definida. Ahora descarga el pack para trabajar.")
        
        c1, c2 = st.columns(2)
        with c1:
            # EXCEL para el cliente (Uso táctil mejorado)
            out_xlsx = io.BytesIO()
            df_for_client.to_excel(out_xlsx, index=False)
            st.download_button(
                label="📥 DESCARGAR EXCEL (Para el cliente)",
                data=out_xlsx.getvalue(),
                file_name="Estructura_Para_Cliente.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with c2:
            # SAV para el protocolo
            temp_sav = "base_cliente.sav"
            f_labels = {k: v for k, v in st.session_state.meta.column_names_to_labels.items() if k in cols_to_keep}
            f_values = {k: v for k, v in st.session_state.meta.variable_value_labels.items() if k in cols_to_keep}
            pyreadstat.write_sav(df_for_client, temp_sav, column_labels=f_labels, variable_value_labels=f_values)
            with open(temp_sav, "rb") as f:
                st.download_button("📥 DESCARGAR SPSS (Protocolo)", f, "Estructura_Cliente.sav", use_container_width=True)

    # --- PASO 2: EL CICLO DE LA "ADUANA" (PLANCHADO) ---
    with t2:
        st.subheader("Paso 2: Aduana de Validación")
        st.write("Sube el Excel que devolvió el cliente para pasar los controles de calidad.")
        
        excel_file = st.file_uploader("📤 Subir Excel del Cliente", type=["xlsx"])
        
        if excel_file:
            df_excel = pd.read_excel(excel_file)
            
            # Selector de teléfono para duplicados (automático si detecta 'tel' o 'cel')
            phone_cols = [c for c in df_excel.columns if any(x in c.lower() for x in ['tel', 'cel', 'phone'])]
            sel_phone = st.selectbox("Columna de Teléfono (Opcional):", [None] + phone_cols)

            # --- MOTOR DE AUDITORÍA PROFUNDO ---
            log_errores = []
            style_map = pd.DataFrame('', index=df_excel.index, columns=df_excel.columns)

            for col in df_excel.columns:
                if col in st.session_state.all_cols:
                    is_numeric_dna = pd.api.types.is_numeric_dtype(st.session_state.df_orig[col])
                    
                    for idx, val in df_excel[col].items():
                        # Control 1: Caracteres raros / Saltos de línea
                        if detect_prohibited_chars(val):
                            log_errores.append({"Fila": idx+2, "Columna": col, "Error": "Caracter prohibido", "Valor": val})
                            style_map.at[idx, col] = 'background-color: #ff9800; color: white'

                        # Control 2: Sintaxis de Tipo (Número vs Texto)
                        if is_numeric_dna and pd.notnull(val):
                            try: float(val)
                            except:
                                log_errores.append({"Fila": idx+2, "Columna": col, "Error": "Texto en columna numérica", "Valor": val})
                                style_map.at[idx, col] = 'background-color: #f44336; color: white'

            # Control 3: Duplicados de teléfono
            if sel_phone:
                dups = df_excel[df_excel[sel_phone].duplicated(keep=False) & df_excel[sel_phone].notnull()]
                for idx in dups.index:
                    log_errores.append({"Fila": idx+2, "Columna": sel_phone, "Error": "Teléfono DUPLICADO", "Valor": df_excel.at[idx, sel_phone]})
                    style_map.at[idx, sel_phone] = 'background-color: #ffff00; color: black'

            # --- GESTIÓN DE DEVOLUCIÓN ---
            if log_errores:
                st.session_state.apto = False
                st.error(f"❌ ARCHIVO RECHAZADO: Se encontraron {len(log_errores)} errores.")
                
                # Crear Excel de Devolución con dos hojas
                out_audit = io.BytesIO()
                with pd.ExcelWriter(out_audit, engine='openpyxl') as writer:
                    df_excel.style.apply(lambda x: style_map, axis=None).to_excel(writer, sheet_name='CORREGIR_AQUI', index=False)
                    pd.DataFrame(log_errores).to_excel(writer, sheet_name='INFORME_DE_ERRORES', index=False)
                
                st.download_button(
                    label="📥 DESCARGAR EXCEL DE RECHAZO (Enviar al cliente)",
                    data=out_audit.getvalue(),
                    file_name="RECHAZO_POR_ERRORES.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                with st.expander("Ver detalle de errores en pantalla"):
                    st.table(pd.DataFrame(log_errores))
            else:
                st.success("✅ ¡TODO PERFECTO! El archivo ha pasado la validación. Ve al Paso 3.")
                st.session_state.apto = True
                st.session_state.df_planchado = df_excel
        else:
            st.info("Esperando carga del archivo del cliente...")

    # --- PASO 3: CONFIGURACIÓN FINAL Y TRIPLE DESCARGA ---
    with t3:
        if st.session_state.get('apto', False):
            st.subheader("Paso 3: Exportación Maestra")
            st.write("Filtre columnas finales si es necesario y genere sus archivos.")
            
            # Borrado final (Post-planchado)
            cols_final = st.multiselect(
                "Desactive columnas que NO desee en el SAV final:", 
                options=list(st.session_state.df_planchado.columns), 
                default=list(st.session_state.df_planchado.columns)
            )
            df_final = st.session_state.df_planchado[cols_final]
            
            proj_name = st.text_input("Nombre del Proyecto:", "Resultado_Validado")
            st.divider()

            # Triple columna de exportación
            col_a, col_b, col_c = st.columns(3)

            with col_a:
                st.write("📊 **SPSS SAV**")
                st.caption("DNA e Inteligencia inyectada.")
                path_sav = "final_output.sav"
                pyreadstat.write_sav(
                    df_final, path_sav, 
                    column_labels={k: v for k, v in st.session_state.meta.column_names_to_labels.items() if k in df_final.columns},
                    variable_value_labels={k: v for k, v in st.session_state.meta.variable_value_labels.items() if k in df_final.columns}
                )
                with open(path_sav, "rb") as f:
                    st.download_button("📥 Descargar SAV", f, f"{proj_name}.sav", use_container_width=True)

            with col_b:
                st.write("📖 **Excel LECTURA**")
                st.caption("Códigos traducidos a texto.")
                df_human = df_final.copy()
                for col in df_human.columns:
                    if col in st.session_state.meta.variable_value_labels:
                        df_human[col] = df_human[col].map(st.session_state.meta.variable_value_labels[col]).fillna(df_human[col])
                out_h = io.BytesIO()
                df_human.to_excel(out_h, index=False)
                st.download_button("📥 Descargar Excel Texto", out_h.getvalue(), f"{proj_name}_Lectura.xlsx", use_container_width=True)

            with col_c:
                st.write("🔢 **Excel CÓDIGOS**")
                st.caption("Puros números para análisis.")
                out_c = io.BytesIO()
                df_final.to_excel(out_c, index=False)
                st.download_button("📥 Descargar Excel Números", out_c.getvalue(), f"{proj_name}_Codigos.xlsx", use_container_width=True)
            
            st.balloons() # Pequeña celebración al terminar con éxito

        else:
            st.warning("⚠️ ACCESO RESTRINGIDO: El Paso 3 se activará automáticamente cuando subas un Excel sin errores en el Paso 2.")

if __name__ == "__main__":
    main()
