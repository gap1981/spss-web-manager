import streamlit as st
import pandas as pd
import pyreadstat
import io
import os

# Configuración de la página para dispositivos móviles y escritorio
st.set_page_config(
    page_title="SPSS Web Tool Manager",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def main():
    # Estilo CSS personalizado para mejorar la visualización en Android
    st.markdown("""
        <style>
        .main {
            background-color: #f5f7f9;
        }
        .stButton>button {
            width: 100%;
            border-radius: 10px;
            height: 3em;
            background-color: #007bff;
            color: white;
        }
        .stTextInput>div>div>input {
            border-radius: 8px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🛠️ Herramienta SPSS para LimeSurvey")
    st.markdown("Edita la estructura, limpia columnas y exporta tus datos sin IBM SPSS.")

    # 1. CARGA DEL ARCHIVO .SAV
    uploaded_file = st.file_uploader("Carga tu archivo .sav aquí", type=["sav"])

    if uploaded_file is not None:
        # Guardamos temporalmente para que pyreadstat pueda leerlo por ruta de archivo
        input_path = "temp_input.sav"
        with open(input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        try:
            # Leemos el archivo conservando metadatos (etiquetas de variables y valores)
            df, meta = pyreadstat.read_sav(input_path)
            
            st.success(f"✅ Archivo cargado: {len(df.columns)} columnas y {len(df)} registros.")

            # Organizamos la App en Pestañas para que sea cómoda en Android
            tab_preview, tab_columns, tab_edit = st.tabs([
                "📊 Ver Datos", 
                "🗑️ Borrar Columnas", 
                "✏️ Editar Sintaxis"
            ])

            # --- PESTAÑA: VISTA PREVIA ---
            with tab_preview:
                st.subheader("Vista rápida de los datos")
                st.dataframe(df.head(20), use_container_width=True)

            # --- PESTAÑA: GESTIONAR COLUMNAS ---
            with tab_columns:
                st.subheader("Limpieza de variables")
                st.write("Selecciona únicamente las variables que deseas conservar.")
                
                # Botones de selección rápida
                col_btn1, col_btn2 = st.columns(2)
                all_cols = df.columns.tolist()
                
                selected_cols = st.multiselect(
                    "Columnas activas:",
                    options=all_cols,
                    default=all_cols,
                    key="col_selector"
                )
                
                # Filtramos el dataframe
                df_filtered = df[selected_cols]
                st.info(f"Se conservarán {len(selected_cols)} de {len(all_cols)} columnas.")

            # --- PESTAÑA: EDITAR ESTRUCTURA (SINTAXIS) ---
            with tab_edit:
                st.subheader("Editor de Etiquetas de Variable")
                st.markdown("Cambia la 'Sintaxis' o nombre descriptivo que aparece en SPSS.")
                
                modified_labels = {}
                # Formulario para editar etiquetas masivamente
                with st.form("edit_labels_form"):
                    # Dividimos en 2 columnas para no hacer el scroll tan largo en móvil
                    edit_col1, edit_col2 = st.columns(2)
                    
                    for i, col_name in enumerate(selected_cols):
                        # Obtener la etiqueta actual o el nombre si está vacía
                        current_label = meta.column_names_to_labels.get(col_name, col_name)
                        
                        target_col = edit_col1 if i % 2 == 0 else edit_col2
                        with target_col:
                            new_label = st.text_input(
                                f"Variable: {col_name}", 
                                value=current_label, 
                                key=f"label_{col_name}"
                            )
                            modified_labels[col_name] = new_label
                    
                    submitted = st.form_submit_button("Guardar Cambios de Estructura")
                    if submitted:
                        st.toast("Estructura actualizada correctamente.")

            # --- SECCIÓN DE EXPORTACIÓN ---
            st.divider()
            st.subheader("💾 Exportar y Descargar")
            
            exp1, exp2 = st.columns(2)

            with exp1:
                st.write("**Formato Excel**")
                # Opción para simplificar el encabezado de Excel
                excel_header = st.radio("Encabezados en Excel:", ["Nombres cortos (V1, V2)", "Etiquetas largas"], index=0)
                
                output_xlsx = io.BytesIO()
                df_excel = df_filtered.copy()
                
                if excel_header == "Etiquetas largas":
                    df_excel.columns = [modified_labels.get(c, c) for c in df_excel.columns]

                with pd.ExcelWriter(output_xlsx, engine='openpyxl') as writer:
                    df_excel.to_excel(writer, index=False)
                
                st.download_button(
                    label="Descargar en Excel (.xlsx)",
                    data=output_xlsx.getvalue(),
                    file_name="encuesta_exportada.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            with exp2:
                st.write("**Formato SPSS Limpio**")
                output_sav_path = "cleaned_data.sav"
                
                # Escribimos el nuevo SAV manteniendo etiquetas de valor y nuevas etiquetas de variable
                pyreadstat.write_sav(
                    df_filtered, 
                    output_sav_path, 
                    column_labels=modified_labels,
                    variable_value_labels=meta.variable_value_labels
                )
                
                with open(output_sav_path, "rb") as f:
                    st.download_button(
                        label="Descargar SPSS Editado (.sav)",
                        data=f,
                        file_name="encuesta_limpia.sav",
                        mime="application/octet-stream"
                    )

        except Exception as e:
            st.error(f"Hubo un problema al procesar el archivo: {str(e)}")
        
        finally:
            # Limpieza de archivos temporales del servidor de Streamlit
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists("cleaned_data.sav"):
                os.remove("cleaned_data.sav")

if __name__ == "__main__":
    main()
