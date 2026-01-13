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
    # Inicializar session_state para persistir datos entre reruns
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'meta' not in st.session_state:
        st.session_state.meta = None
    if 'selected_cols' not in st.session_state:
        st.session_state.selected_cols = []
    if 'modified_labels' not in st.session_state:
        st.session_state.modified_labels = {}
    if 'file_loaded' not in st.session_state:
        st.session_state.file_loaded = False
    
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
            # Solo cargar si es un archivo nuevo o no hay datos en session_state
            if not st.session_state.file_loaded or st.session_state.df is None:
                # Leemos el archivo conservando metadatos (etiquetas de variables y valores)
                df, meta = pyreadstat.read_sav(input_path)
                
                # Guardar en session_state
                st.session_state.df = df
                st.session_state.meta = meta
                st.session_state.selected_cols = df.columns.tolist()
                st.session_state.modified_labels = meta.column_names_to_labels.copy()
                st.session_state.file_loaded = True
                
                st.success(f"✅ Archivo cargado: {len(df.columns)} columnas y {len(df)} registros.")
            else:
                # Usar datos de session_state
                df = st.session_state.df
                meta = st.session_state.meta
                st.info(f"📂 Archivo en memoria: {len(st.session_state.selected_cols)} columnas seleccionadas de {len(df.columns)} totales.")

            # Organizamos la App en Pestañas para que sea cómoda en Android
            tab_preview, tab_structure, tab_edit, tab_codebook = st.tabs([
                "📊 Ver Datos",
                "📋 Ver Estructura", 
                "✏️ Editar Variables",
                "📖 Libro de Códigos"
            ])

            # --- PESTAÑA: VISTA PREVIA ---
            with tab_preview:
                st.subheader("Vista rápida de los datos")
                st.dataframe(df.head(20), use_container_width=True)

            # --- PESTAÑA: VER ESTRUCTURA ---
            with tab_structure:
                st.subheader("📋 Estructura de Variables SPSS")
                st.markdown("Información detallada de cada variable (tipo, formato, etiquetas, valores)")
                
                # Crear tabla con metadatos de variables
                structure_data = []
                
                for col_name in df.columns:
                    # Tipo de dato
                    dtype = df[col_name].dtype
                    if dtype == 'object':
                        var_type = "Cadena (String)"
                    elif dtype in ['int64', 'int32', 'float64', 'float32']:
                        var_type = "Numérica"
                    else:
                        var_type = str(dtype)
                    
                    # Formato original de SPSS
                    original_format = meta.original_variable_types.get(col_name, "N/A") if hasattr(meta, 'original_variable_types') else "N/A"
                    
                    # Longitud (ancho de columna)
                    col_width = meta.variable_display_width.get(col_name, "N/A") if hasattr(meta, 'variable_display_width') else "N/A"
                    
                    # Decimales
                    decimals = "N/A"
                    if dtype in ['float64', 'float32']:
                        # Intentar obtener decimales del formato
                        if hasattr(meta, 'formats') and col_name in meta.formats:
                            fmt = meta.formats[col_name]
                            # Formato típico: F8.2 (8 total, 2 decimales)
                            if '.' in fmt:
                                decimals = fmt.split('.')[-1]
                    
                    # Etiqueta de variable
                    var_label = st.session_state.modified_labels.get(
                        col_name, 
                        meta.column_names_to_labels.get(col_name, "")
                    )
                    
                    # Value labels (etiquetas de valores)
                    value_labels = ""
                    if col_name in meta.variable_value_labels:
                        labels_dict = meta.variable_value_labels[col_name]
                        # Formatear como "1=Sí, 2=No, 3=No sabe"
                        value_labels = ", ".join([f"{k}={v}" for k, v in labels_dict.items()])
                        # Limitar longitud para visualización
                        if len(value_labels) > 100:
                            value_labels = value_labels[:100] + "..."
                    
                    structure_data.append({
                        "Variable": col_name,
                        "Tipo": var_type,
                        "Formato": original_format,
                        "Ancho": col_width,
                        "Decimales": decimals,
                        "Etiqueta": var_label,
                        "Valores": value_labels
                    })
                
                # Crear DataFrame de estructura
                structure_df = pd.DataFrame(structure_data)
                
                # Buscador de variables
                search_struct = st.text_input("🔍 Buscar variable en estructura:", "", key="search_structure")
                if search_struct:
                    structure_df = structure_df[structure_df['Variable'].str.contains(search_struct, case=False, na=False)]
                
                # Mostrar tabla con formato
                st.dataframe(
                    structure_df,
                    use_container_width=True,
                    height=400,
                    column_config={
                        "Variable": st.column_config.TextColumn("Variable", width="small"),
                        "Tipo": st.column_config.TextColumn("Tipo", width="small"),
                        "Formato": st.column_config.TextColumn("Formato", width="small"),
                        "Ancho": st.column_config.TextColumn("Ancho", width="small"),
                        "Decimales": st.column_config.TextColumn("Decimales", width="small"),
                        "Etiqueta": st.column_config.TextColumn("Etiqueta Variable", width="medium"),
                        "Valores": st.column_config.TextColumn("Etiquetas de Valores", width="large")
                    }
                )
                
                # Estadísticas de la estructura
                st.divider()
                col1, col2, col3 = st.columns(3)
                with col1:
                    num_vars = len(structure_df)
                    st.metric("Total Variables", num_vars)
                with col2:
                    num_numeric = len(structure_df[structure_df['Tipo'] == "Numérica"])
                    st.metric("Variables Numéricas", num_numeric)
                with col3:
                    num_string = len(structure_df[structure_df['Tipo'] == "Cadena (String)"])
                    st.metric("Variables de Texto", num_string)

            # --- PESTAÑA: EDITAR VARIABLES (COMBINA BORRAR COLUMNAS Y EDITAR SINTAXIS) ---
            with tab_edit:
                st.subheader("✏️ Gestión de Variables")
                st.markdown("Selecciona columnas y edita etiquetas en un solo lugar")
                
                # Dividir en dos columnas: izquierda para selección, derecha para edición
                col_left, col_right = st.columns([1, 1])
                
                # COLUMNA IZQUIERDA: SELECCIÓN DE COLUMNAS
                with col_left:
                    st.markdown("### 🗑️ Seleccionar Columnas")
                    
                    # Botones de selección rápida
                    btn_col1, btn_col2 = st.columns(2)
                    all_cols = df.columns.tolist()
                    
                    with btn_col1:
                        if st.button("✅ Todas", use_container_width=True, key="select_all_edit"):
                            st.session_state.selected_cols = all_cols
                            st.rerun()
                    
                    with btn_col2:
                        if st.button("❌ Ninguna", use_container_width=True, key="deselect_all_edit"):
                            st.session_state.selected_cols = []
                            st.rerun()
                    
                    # Buscador de columnas
                    search_term = st.text_input("🔍 Buscar:", "", key="search_edit")
                    filtered_options = [col for col in all_cols if search_term.lower() in col.lower()] if search_term else all_cols
                    
                    selected_cols = st.multiselect(
                        "Columnas a conservar:",
                        options=filtered_options,
                        default=[col for col in st.session_state.selected_cols if col in filtered_options],
                        key="col_selector_edit",
                        help="Solo las columnas seleccionadas se exportarán"
                    )
                    
                    # Actualizar session_state
                    if selected_cols != st.session_state.selected_cols:
                        st.session_state.selected_cols = selected_cols
                    
                    st.info(f"📊 {len(st.session_state.selected_cols)} de {len(all_cols)} columnas")
                
                # COLUMNA DERECHA: EDICIÓN DE ETIQUETAS
                with col_right:
                    st.markdown("### 📝 Editar Etiquetas")
                    
                    if not st.session_state.selected_cols:
                        st.warning("⚠️ Selecciona columnas primero")
                    else:
                        # Formulario compacto para editar etiquetas
                        with st.form("edit_labels_combined"):
                            st.markdown(f"**Editando {len(st.session_state.selected_cols)} variables**")
                            
                            temp_labels = {}
                            
                            # Mostrar solo las primeras 10 para no saturar, con scroll
                            max_display = min(10, len(st.session_state.selected_cols))
                            
                            for col_name in st.session_state.selected_cols[:max_display]:
                                current_label = st.session_state.modified_labels.get(
                                    col_name, 
                                    meta.column_names_to_labels.get(col_name, col_name)
                                )
                                
                                new_label = st.text_input(
                                    f"**{col_name}**", 
                                    value=current_label, 
                                    key=f"label_edit_{col_name}",
                                    label_visibility="visible"
                                )
                                temp_labels[col_name] = new_label
                            
                            if len(st.session_state.selected_cols) > max_display:
                                st.info(f"ℹ️ Mostrando {max_display} de {len(st.session_state.selected_cols)}. Usa el buscador para encontrar más.")
                            
                            submitted = st.form_submit_button("💾 Guardar Etiquetas", use_container_width=True)
                            if submitted:
                                st.session_state.modified_labels.update(temp_labels)
                                st.toast("✅ Etiquetas actualizadas")
                                st.success(f"Se actualizaron {len(temp_labels)} etiquetas")

            # --- PESTAÑA: LIBRO DE CÓDIGOS ---
            with tab_codebook:
                st.subheader("📖 Generador de Libro de Códigos")
                st.markdown("Exporta un libro de códigos en Excel con tipos de pregunta y etiquetas de valores")
                
                if not st.session_state.selected_cols:
                    st.warning("⚠️ Primero selecciona columnas en la pestaña 'Editar Variables'")
                else:
                    st.info(f"📊 Generando libro de códigos para {len(st.session_state.selected_cols)} variables")
                    
                    # Opciones de configuración
                    with st.expander("⚙️ Opciones del Libro de Códigos"):
                        include_stats = st.checkbox("Incluir estadísticas descriptivas", value=True)
                        include_frequencies = st.checkbox("Incluir frecuencias de valores", value=True)
                    
                    # Generar libro de códigos
                    codebook_data = []
                    
                    for col_name in st.session_state.selected_cols:
                        # Tipo de dato
                        dtype = df[col_name].dtype
                        if dtype == 'object':
                            var_type = "Cadena"
                            question_type = "Abierta"
                        elif dtype in ['int64', 'int32', 'float64', 'float32']:
                            var_type = "Numérica"
                            
                            # Determinar tipo de pregunta basado en value labels
                            if col_name in meta.variable_value_labels:
                                labels_dict = meta.variable_value_labels[col_name]
                                unique_values = df[col_name].dropna().unique()
                                
                                # Dicotómica: 2 valores (ej: Sí/No, 0/1)
                                if len(labels_dict) == 2:
                                    question_type = "Dicotómica"
                                # Simple: múltiples valores mutuamente excluyentes
                                elif len(unique_values) <= 20:
                                    question_type = "Simple"
                                else:
                                    question_type = "Múltiple/Escala"
                            else:
                                question_type = "Numérica continua"
                        else:
                            var_type = str(dtype)
                            question_type = "Otro"
                        
                        # Etiqueta de variable
                        var_label = st.session_state.modified_labels.get(
                            col_name, 
                            meta.column_names_to_labels.get(col_name, "")
                        )
                        
                        # Value labels (códigos y etiquetas)
                        value_labels_str = ""
                        if col_name in meta.variable_value_labels:
                            labels_dict = meta.variable_value_labels[col_name]
                            value_labels_str = "; ".join([f"{k}={v}" for k, v in sorted(labels_dict.items())])
                        
                        # Estadísticas básicas
                        n_valid = df[col_name].notna().sum()
                        n_missing = df[col_name].isna().sum()
                        
                        codebook_entry = {
                            "Variable": col_name,
                            "Etiqueta": var_label,
                            "Tipo": var_type,
                            "Tipo Pregunta": question_type,
                            "Códigos y Etiquetas": value_labels_str,
                            "N Válidos": n_valid if include_stats else "",
                            "N Perdidos": n_missing if include_stats else ""
                        }
                        
                        codebook_data.append(codebook_entry)
                    
                    # Crear DataFrame del libro de códigos
                    codebook_df = pd.DataFrame(codebook_data)
                    
                    # Vista previa
                    st.markdown("### Vista Previa del Libro de Códigos")
                    st.dataframe(codebook_df, use_container_width=True, height=300)
                    
                    # Estadísticas del libro de códigos
                    st.divider()
                    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                    with stat_col1:
                        st.metric("Total Variables", len(codebook_df))
                    with stat_col2:
                        n_dicotomica = len(codebook_df[codebook_df['Tipo Pregunta'] == "Dicotómica"])
                        st.metric("Dicotómicas", n_dicotomica)
                    with stat_col3:
                        n_simple = len(codebook_df[codebook_df['Tipo Pregunta'] == "Simple"])
                        st.metric("Simples", n_simple)
                    with stat_col4:
                        n_abierta = len(codebook_df[codebook_df['Tipo Pregunta'] == "Abierta"])
                        st.metric("Abiertas", n_abierta)
                    
                    # Botón de descarga
                    st.divider()
                    output_codebook = io.BytesIO()
                    with pd.ExcelWriter(output_codebook, engine='openpyxl') as writer:
                        codebook_df.to_excel(writer, index=False, sheet_name='Libro de Códigos')
                        
                        # Ajustar ancho de columnas
                        worksheet = writer.sheets['Libro de Códigos']
                        for idx, col in enumerate(codebook_df.columns):
                            max_length = max(
                                codebook_df[col].astype(str).apply(len).max(),
                                len(col)
                            )
                            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
                    
                    st.download_button(
                        label="📥 Descargar Libro de Códigos (.xlsx)",
                        data=output_codebook.getvalue(),
                        file_name="libro_codigos.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        help="Descarga el libro de códigos con tipos de pregunta y etiquetas"
                    )

            # --- SECCIÓN DE EXPORTACIÓN ---
            st.divider()
            st.subheader("💾 Exportar y Descargar")
            
            # Preparar dataframe filtrado
            df_filtered = df[st.session_state.selected_cols] if st.session_state.selected_cols else df
            
            # Campo para nombre de archivo
            st.markdown("### 📝 Nombre del Archivo")
            col_name1, col_name2 = st.columns(2)
            
            with col_name1:
                filename_base = st.text_input(
                    "Nombre base del archivo:",
                    value="encuesta_exportada",
                    help="Nombre sin extensión (se agregará .xlsx o .sav automáticamente)",
                    key="filename_input"
                )
            
            with col_name2:
                st.markdown("&nbsp;")  # Espaciador
                if st.button("🔄 Cargar Nuevo Archivo", use_container_width=True):
                    st.session_state.file_loaded = False
                    st.session_state.df = None
                    st.session_state.meta = None
                    st.session_state.selected_cols = []
                    st.session_state.modified_labels = {}
                    st.rerun()
            
            st.divider()
            exp1, exp2 = st.columns(2)

            with exp1:
                st.write("**📊 Formato Excel**")
                # Opción para simplificar el encabezado de Excel
                excel_header = st.radio(
                    "Encabezados:",
                    ["Nombres cortos", "Etiquetas largas"],
                    index=0,
                    key="excel_header_radio"
                )
                
                output_xlsx = io.BytesIO()
                df_excel = df_filtered.copy()
                
                if excel_header == "Etiquetas largas":
                    df_excel.columns = [st.session_state.modified_labels.get(c, c) for c in df_excel.columns]

                with pd.ExcelWriter(output_xlsx, engine='openpyxl') as writer:
                    df_excel.to_excel(writer, index=False)
                
                # Generar nombre de archivo con extensión
                excel_filename = f"{filename_base}.xlsx" if filename_base else "encuesta_exportada.xlsx"
                
                st.download_button(
                    label="📥 Descargar Excel",
                    data=output_xlsx.getvalue(),
                    file_name=excel_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    help=f"Descarga: {excel_filename}"
                )

            with exp2:
                st.write("**📊 Formato SPSS**")
                st.markdown("&nbsp;")  # Espaciador para alinear con el radio button
                st.markdown("&nbsp;")
                
                output_sav_path = "cleaned_data.sav"
                
                # Escribimos el nuevo SAV manteniendo etiquetas de valor y nuevas etiquetas de variable
                pyreadstat.write_sav(
                    df_filtered, 
                    output_sav_path, 
                    column_labels=st.session_state.modified_labels,
                    variable_value_labels=meta.variable_value_labels
                )
                
                # Generar nombre de archivo con extensión
                sav_filename = f"{filename_base}.sav" if filename_base else "encuesta_limpia.sav"
                
                with open(output_sav_path, "rb") as f:
                    st.download_button(
                        label="📥 Descargar SPSS",
                        data=f,
                        file_name=sav_filename,
                        mime="application/octet-stream",
                        use_container_width=True,
                        help=f"Descarga: {sav_filename}"
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
