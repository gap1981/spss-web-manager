import streamlit as st
import pandas as pd
import pyreadstat
import io
import os
import plotly.express as px
import plotly.graph_objects as go

import json

# Configuración de la página para dispositivos móviles y escritorio
st.set_page_config(
    page_title="SPSS Web Tool Manager",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def tool_manager_exporter():
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
                st.dataframe(df.head(20), width="stretch")

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
                    width="stretch",
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
                        if st.button("✅ Todas", width="stretch", key="select_all_edit"):
                            st.session_state.selected_cols = all_cols
                            st.rerun()
                    
                    with btn_col2:
                        if st.button("❌ Ninguna", width="stretch", key="deselect_all_edit"):
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
                            
                            submitted = st.form_submit_button("💾 Guardar Etiquetas", width="stretch")
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
                    st.dataframe(codebook_df, width="stretch", height=300)
                    
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
                        width="stretch",
                        help="Descarga el libro de códigos con tipos de pregunta y etiquetas"
                    )

            # --- SECCIÓN DE EXPORTACIÓN (AHORA EN SIDEBAR) ---
            with st.sidebar:
                st.divider()
                st.header("💾 Exportar Datos")
                
                # Preparar dataframe filtrado
                df_filtered = df[st.session_state.selected_cols] if st.session_state.selected_cols else df
                
                # Campo para nombre de archivo
                filename_base = st.text_input(
                    "Nombre del archivo (sin extensión):",
                    value="encuesta_exportada",
                    key="filename_input"
                )

                st.subheader("Excel")
                # Opción para simplificar el encabezado de Excel
                excel_header = st.radio(
                    "Encabezados Excel:",
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
                    width="stretch"
                )

                st.subheader("SPSS (.sav)")
                output_sav_path = "cleaned_data.sav"
                
                # Escribimos el nuevo SAV manteniendo etiquetas de valor y nuevas etiquetas de variable
                try:
                    pyreadstat.write_sav(
                        df_filtered, 
                        output_sav_path, 
                        column_labels=st.session_state.modified_labels,
                        variable_value_labels=meta.variable_value_labels
                    )
                    
                    sav_filename = f"{filename_base}.sav" if filename_base else "encuesta_limpia.sav"
                    
                    with open(output_sav_path, "rb") as f:
                        st.download_button(
                            label="📥 Descargar SPSS",
                            data=f,
                            file_name=sav_filename,
                            mime="application/octet-stream",
                            width="stretch"
                        )
                except Exception as e:
                    st.error(f"Error al generar SPSS: {e}")

                st.divider()
                if st.button("🔄 Cargar Nuevo Archivo", width="stretch"):
                    st.session_state.file_loaded = False
                    st.session_state.df = None
                    st.session_state.meta = None
                    st.session_state.selected_cols = []
                    st.session_state.modified_labels = {}
                    st.rerun()

        except Exception as e:
            st.error(f"Hubo un problema al procesar el archivo: {str(e)}")
        
        finally:
            # Limpieza de archivos temporales
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists("cleaned_data.sav"):
                os.remove("cleaned_data.sav")

# --- TOOL ADVANCED EDITOR ---

def load_sav_file(uploaded_file):
    """Carga el archivo .sav y extrae datos y metadatos."""
    try:
        with open("temp_upload.sav", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        df, meta = pyreadstat.read_sav("temp_upload.sav")
        
        if os.path.exists("temp_upload.sav"):
            os.remove("temp_upload.sav")
            
        return df, meta
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None, None

def save_to_sav(df, col_labels, val_labels):
    """Guarda el dataframe editado de nuevo a formato .sav usando los diccionarios de etiquetas."""
    buffer = io.BytesIO()
    temp_filename = "temp_export.sav"
    
    try:
        # pyreadstat necesita que los keys de val_labels sean los nombres de las columnas
        pyreadstat.write_sav(
            df, 
            temp_filename, 
            column_labels=col_labels,
            variable_value_labels=val_labels
        )
        
        with open(temp_filename, "rb") as f:
            buffer.write(f.read())
            
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            
        return buffer.getvalue()
    except Exception as e:
        st.error(f"Error al generar el .sav: {e}")
        return None

def tool_advanced_editor():
    # --- GESTIÓN DEL ESTADO ---

    if 'data_df' not in st.session_state:
        st.session_state['data_df'] = pd.DataFrame()
    if 'column_labels' not in st.session_state:
        st.session_state['column_labels'] = {}
    if 'value_labels' not in st.session_state:
        st.session_state['value_labels'] = {}
    if 'editor_file_name' not in st.session_state:
        st.session_state['editor_file_name'] = ""

    st.title("📊 Editor de Archivos IBM SPSS (.sav)")

    # --- CARGA INICIAL (BARRA LATERAL O CENTRAL SI ESTÁ VACÍO) ---
    if st.session_state['data_df'].empty:
        uploaded_file = st.file_uploader("Cargar archivo .sav para editar", type=["sav"], key="editor_uploader_main")
        if uploaded_file is not None:
             df, meta = load_sav_file(uploaded_file)
             if df is not None:
                st.session_state['data_df'] = df
                st.session_state['column_labels'] = meta.column_names_to_labels if meta else {}
                st.session_state['value_labels'] = meta.variable_value_labels if meta else {}
                st.session_state['editor_file_name'] = uploaded_file.name
                st.rerun()
        
        st.divider()
        if st.button("Generar Prueba (Demo)"):
            # Generar datos dummy para probar sin archivo
            dummy = pd.DataFrame({'Q1': [1,2,1], 'Q2': [5,4,3]})
            st.session_state['data_df'] = dummy
            st.session_state['column_labels'] = {'Q1': 'Pregunta Género', 'Q2': 'Satisfacción'}
            st.session_state['value_labels'] = {'Q1': {1:'M', 2:'F'}}
            st.session_state['editor_file_name'] = "prueba.sav"
            st.rerun()

    else:
        # --- BARRA DE HERRAMIENTAS (TOOLBAR) ---
        # Contenedor superior para acciones comunes
        
        col_info, col_actions = st.columns([2, 3])
        
        with col_info:
            st.info(f"📂 Archivo: **{st.session_state['editor_file_name']}** | Filas: {len(st.session_state['data_df'])} | Cols: {len(st.session_state['data_df'].columns)}")

        with col_actions:
            # Usamos columnas dentro de la columna de acciones para los botones
            b1, b2, b3, b4 = st.columns([1, 1, 1, 1])
            
            with b1:
                # Popover para agregar variable
                with st.popover("➕ Nueva", width="stretch"):
                    new_var_name = st.text_input("Nombre Variable", value="NUEVA_VAR")
                    if st.button("Crear", width="stretch"):
                        if new_var_name not in st.session_state['data_df'].columns:
                            st.session_state['data_df'][new_var_name] = 0 # Valor por defecto
                            st.toast(f"Variable {new_var_name} creada!")
                            st.rerun()
                        else:
                            st.error("Ya existe.")

            with b2:
                # Popover para borrar variables
                with st.popover("🗑️ Borrar", width="stretch"):
                    st.markdown("### Eliminar Columnas")
                    vars_to_delete = st.multiselect(
                        "Selecciona variables a borrar:",
                        options=st.session_state['data_df'].columns.tolist(),
                        key="delete_multiselect"
                    )
                    
                    if st.button("🚨 Eliminar Seleccionadas", type="primary", width="stretch"):
                        if vars_to_delete:
                            # 1. Eliminar del DataFrame
                            st.session_state['data_df'].drop(columns=vars_to_delete, inplace=True)
                            
                            # 2. Eliminar de metadatos
                            for v in vars_to_delete:
                                st.session_state['column_labels'].pop(v, None)
                                st.session_state['value_labels'].pop(v, None)
                            
                            st.toast(f"Se eliminaron {len(vars_to_delete)} variables.")
                            st.rerun()
                        else:
                            st.warning("Selecciona al menos una variable.")

            with b3:
                # Lógica de descarga directa en el botón
                sav_data = save_to_sav(
                    st.session_state['data_df'],
                    st.session_state['column_labels'],
                    st.session_state['value_labels']
                )
                if sav_data:
                    st.download_button(
                        label="💾 Guardar",
                        data=sav_data,
                        file_name=f"modificado_{st.session_state.get('editor_file_name', 'data.sav')}",
                        mime="application/x-spss-sav",
                        width="stretch"
                    )
            
            with b4:
                 if st.button("🔄 Reiniciar", width="stretch"):
                    st.session_state['data_df'] = pd.DataFrame()
                    st.session_state['column_labels'] = {}
                    st.session_state['value_labels'] = {}
                    st.session_state['editor_file_name'] = ""
                    st.rerun()

        st.divider()

        # --- PESTAÑAS PRINCIPALES ---
        tab_data, tab_vars = st.tabs(["📝 Vista de Datos", "🏷️ Vista de Variables"])

        # --- 1. VISTA DE DATOS ---
        with tab_data:
            # Editor de datos principal
            edited_df = st.data_editor(
                st.session_state['data_df'],
                num_rows="dynamic",
                key="data_editor",
                width="stretch",
                height=500
            )
            
            # Sincronizar cambios en datos
            if not st.session_state['data_df'].equals(edited_df):
                st.session_state['data_df'] = edited_df

        # --- 2. VISTA DE VARIABLES ---
        with tab_vars:
            st.markdown("##### Metadatos de Variables")
            
            # Preparar DataFrame de Metadatos para el editor
            current_columns = st.session_state['data_df'].columns.tolist()
            meta_rows = []
            
            for col in current_columns:
                # Obtener etiqueta actual
                lbl = st.session_state['column_labels'].get(col, "")
                # Obtener value labels actuales y convertir a string JSON para editar
                val_lbls_dict = st.session_state['value_labels'].get(col, {})
                val_lbls_str = json.dumps(val_lbls_dict) if val_lbls_dict else ""
                
                meta_rows.append({
                    "Nombre Variable": col,
                    "Etiqueta (Label)": lbl,
                    "Etiquetas de Valor (JSON)": val_lbls_str
                })
            
            meta_df = pd.DataFrame(meta_rows)

            # Editor de Variables
            edited_meta_df = st.data_editor(
                meta_df,
                key="meta_editor",
                width="stretch",
                height=500,
                column_config={
                    "Nombre Variable": st.column_config.TextColumn(disabled=True), # Renombrar es complejo, mejor bloquear
                    "Etiquetas de Valor (JSON)": st.column_config.TextColumn(help="Formato: {\"1\": \"Texto\", \"2\": \"Otro\"}")
                }
            )

            # Lógica para guardar cambios de metadatos al Estado
            # Comparamos si hubo cambios en la tabla de metadatos
            if not meta_df.equals(edited_meta_df):
                new_col_labels = {}
                new_val_labels = {}
                
                for index, row in edited_meta_df.iterrows():
                    var_name = row["Nombre Variable"]
                    # Actualizar Variable Label
                    if row["Etiqueta (Label)"]:
                        new_col_labels[var_name] = row["Etiqueta (Label)"]
                    
                    # Actualizar Value Labels (Parsear JSON)
                    json_str = row["Etiquetas de Valor (JSON)"]
                    if json_str and json_str.strip() != "":
                        try:
                            # Intentar limpiar comillas inteligentes si el usuario copió/pegó
                            json_clean = json_str.replace("'", '"')
                            parsed_dict = json.loads(json_clean)
                            new_val_labels[var_name] = parsed_dict
                        except json.JSONDecodeError:
                            st.warning(f"Error en JSON para variable {var_name}. Se ignoraron los cambios.")
                
                st.session_state['column_labels'] = new_col_labels
                st.session_state['value_labels'] = new_val_labels
                # No hacemos rerun forzado para no molestar, se actualizará en la próxima acción

# --- TOOL AUDIT VALIDATOR ---

def tool_audit_validator():
    st.title("🛡️ Auditoría y Validación de Datos")
    st.markdown("""
    **Módulo de Calidad de Datos**: Valida archivos de campo (Excel/CSV) contra un diccionario de datos (SPSS .SAV).
    """)

    # --- SETUP LAYOUT ---
    col_upload_ref, col_upload_target = st.columns(2)
    
    with col_upload_ref:
        st.subheader("1. Patrón (SPSS .sav)")
        ref_file = st.file_uploader("Cargar archivo maestro", type=["sav"], key="audit_ref")
    
    with col_upload_target:
        st.subheader("2. Datos (Excel/CSV)")
        target_file = st.file_uploader("Cargar datos a validar", type=["xlsx", "csv"], key="audit_target")

    # --- LOGIC ---
    if ref_file and target_file:
        st.divider()
        
        # 1. LOAD REFERENCE
        try:
            with open("temp_ref.sav", "wb") as f:
                f.write(ref_file.getbuffer())
            df_ref, meta_ref = pyreadstat.read_sav("temp_ref.sav")
            
            # Clean up temp file immediately
            if os.path.exists("temp_ref.sav"):
                os.remove("temp_ref.sav")
                
            st.success(f"✅ Patrón cargado: **{len(df_ref.columns)}** variables definidos.")
            
        except Exception as e:
            st.error(f"Error crítico al leer el patrón SAV: {e}")
            return

        # 2. LOAD TARGET
        try:
            if target_file.name.endswith('.xlsx'):
                df_target = pd.read_excel(target_file)
            else:
                df_target = pd.read_csv(target_file)
            
            st.info(f"📂 Datos cargados: **{len(df_target)}** registros y **{len(df_target.columns)}** columnas.")
            
        except Exception as e:
            st.error(f"Error crítico al leer el archivo de datos: {e}")
            return

        # 3. EXECUTE AUDIT
        if st.button("🚀 Ejecutar Validación Completa", type="primary", width="stretch"):
            
            with st.status("Ejecutando auditoría...", expanded=True) as status:
                st.write("🔍 Iniciando validación estructural...")
                audit_logs = []
                
                # --- A. STRUCTURE VALIDATION ---
                ref_cols = set(df_ref.columns)
                target_cols = set(df_target.columns)
                
                # Check 1: Missing Mandatory Columns
                missing_cols = list(ref_cols - target_cols)
                if missing_cols:
                    for col in missing_cols:
                        audit_logs.append({
                            "Fila": "N/A",
                            "Variable": col,
                            "Valor Encontrado": "N/A",
                            "Tipo de Error": "Estructura Missing",
                            "Mensaje": "La variable es obligatoria según el patrón pero no existe en los datos.",
                            "Criticidad": "ALTA"
                        })
                
                # Check 2: Extra Columns (Warning)
                extra_cols = list(target_cols - ref_cols)
                if extra_cols:
                    for col in extra_cols:
                        audit_logs.append({
                            "Fila": "N/A",
                            "Variable": col,
                            "Valor Encontrado": "N/A",
                            "Tipo de Error": "Estructura Extra",
                            "Mensaje": "Variable encontrada en datos pero no en el patrón.",
                            "Criticidad": "BAJA"
                        })

                st.write("🧠 Analizando consistencia de datos y valores...")
                
                # --- B. DATA & VALUE VALIDATION ---
                common_cols = list(ref_cols.intersection(target_cols))
                progress_bar = st.progress(0)
                
                for idx, col in enumerate(common_cols):
                    progress_bar.progress((idx + 1) / len(common_cols))
                    
                    # Get Ref Metadata
                    is_numeric_ref = pd.api.types.is_numeric_dtype(df_ref[col])
                    valid_range = meta_ref.variable_value_labels.get(col, {})
                    
                    # Analyze Target Column
                    # We iterate unique values for performance, assuming categorical data usually has limited cardinality
                    # For continuous data, simple type check is used
                    
                    # 1. Type Mismatch Check
                    if is_numeric_ref:
                        # Check if target has non-numeric values
                        non_numeric = pd.to_numeric(df_target[col], errors='coerce').isna() & df_target[col].notna()
                        if non_numeric.any():
                            # Log first few examples
                            bad_indices = df_target[non_numeric].index[:5]
                            for bad_idx in bad_indices:
                                val = df_target.at[bad_idx, col]
                                audit_logs.append({
                                    "Fila": bad_idx + 2, # Excel row index hint (1-based + header)
                                    "Variable": col,
                                    "Valor Encontrado": str(val),
                                    "Tipo de Error": "Tipo de Dato",
                                    "Mensaje": "Se esperaba numérico, se encontró texto/inválido.",
                                    "Criticidad": "ALTA"
                                })

                    # 2. Value Label / Range Check
                    if valid_range:
                        valid_codes = set(valid_range.keys())
                        valid_labels = set(valid_range.values())
                        
                        unique_vals = df_target[col].dropna().unique()
                        
                        for val in unique_vals:
                            # Check if value matches a code (e.g. 1) or a label (e.g. "Male")
                            match_code = val in valid_codes
                            match_label = val in valid_labels
                            
                            # Float adjustment: 1.0 == 1
                            if not match_code and isinstance(val, float) and val.is_integer():
                                match_code = int(val) in valid_codes

                            if not (match_code or match_label):
                                # Find all rows with this invalid value
                                mask = df_target[col] == val
                                affected_rows = df_target[mask].index.tolist()
                                
                                # Limit logging to avoid explosion
                                for r_idx in affected_rows[:5]: 
                                    audit_logs.append({
                                        "Fila": r_idx + 2,
                                        "Variable": col,
                                        "Valor Encontrado": str(val),
                                        "Tipo de Error": "Valor Fuera de Rango",
                                        "Mensaje": f"Valor no permitido. Opciones válidas: {list(valid_codes)[:10]}...",
                                        "Criticidad": "MEDIA"
                                    })
                                if len(affected_rows) > 5:
                                     audit_logs.append({
                                        "Fila": "...",
                                        "Variable": col,
                                        "Valor Encontrado": str(val),
                                        "Tipo de Error": "Valor Fuera de Rango",
                                        "Mensaje": f"Total {len(affected_rows)} casos con este valor.",
                                        "Criticidad": "MEDIA"
                                     })

                status.update(label="¡Auditoría Completada!", state="complete", expanded=False)
            
            # --- RESULTS VISUALIZATION ---
            if not audit_logs:
                st.balloons()
                st.success("✨ **¡Perfecto!** No se encontraron discrepancias entre los datos y el patrón.")
            else:
                logs_df = pd.DataFrame(audit_logs)
                
                # Metrics
                st.subheader("📊 Resultados")
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Hallazgos", len(logs_df), delta_color="inverse")
                m2.metric("Errores Críticos", len(logs_df[logs_df['Criticidad']=="ALTA"]), delta=None, delta_color="inverse")
                m3.metric("Advertencias", len(logs_df[logs_df['Criticidad']=="BAJA"]) + len(logs_df[logs_df['Criticidad']=="MEDIA"]))

                # Interactive Table
                st.markdown("### 📝 Detalle de Discrepancias")
                
                # Filter by criticality
                filter_crit = st.multiselect("Filtrar por Severidad:", ["ALTA", "MEDIA", "BAJA"], default=["ALTA", "MEDIA"])
                if filter_crit:
                    show_df = logs_df[logs_df['Criticidad'].isin(filter_crit)]
                else:
                    show_df = logs_df
                
                st.dataframe(
                    show_df, 
                    width="stretch", 
                    column_config={
                        "Criticidad": st.column_config.TextColumn(
                            "Severidad",
                            help="ALTA: Error estructural o de tipo. MEDIA: Valor fuera de rango.",
                        ),
                    }
                )

                # --- EXPORT REPORT ---
                st.divider()
                st.subheader("📥 Descargar Reporte")
                
                report_buffer = io.BytesIO()
                with pd.ExcelWriter(report_buffer, engine='openpyxl') as writer:
                    # 1. AUDIT LOG
                    logs_df.to_excel(writer, sheet_name='AUDIT_LOG', index=False)
                    
                    # 2. DATA (Original)
                    # We can highlight or add comments later, for now raw data
                    df_target.to_excel(writer, sheet_name='DATA', index=False)
                    
                    # 3. METADATA (Pattern info)
                    meta_info = []
                    for c in df_ref.columns:
                        meta_info.append({
                            "Variable": c,
                            "Etiqueta": meta_ref.column_names_to_labels.get(c, ""),
                            "Valores Válidos": str(meta_ref.variable_value_labels.get(c, ""))
                        })
                    pd.DataFrame(meta_info).to_excel(writer, sheet_name='METADATA_REF', index=False)

                st.download_button(
                    label="📄 Descargar Excel de Auditoría (.xlsx)",
                    data=report_buffer.getvalue(),
                    file_name="Reporte_Auditoria_Calidad.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch"
                )

                # --- EXPORT TO NEW SAV ---
                st.divider()
                st.subheader("💾 Exportar Datos + Estructura (.sav)")
                st.markdown("Genera un nuevo archivo SPSS combinando los datos validados con la estructura original del patrón (etiquetas de variables y valores).")

                try:
                    df_export = pd.DataFrame(columns=df_ref.columns)
                    
                    for col in df_ref.columns:
                        if col in df_target.columns:
                            # Alinear tipos de datos asegurando que respeten el df original para evitar errores en pyreadstat
                            if pd.api.types.is_numeric_dtype(df_ref[col]):
                                df_export[col] = pd.to_numeric(df_target[col], errors='coerce')
                            else:
                                # Convertir a string, limpiando posibles "nan" que vengan de datos nulos
                                df_export[col] = df_target[col].copy()
                                # Rellenar nulos con string vacío antes de convertir a string
                                df_export[col] = df_export[col].fillna("")
                                df_export[col] = df_export[col].astype(str)
                        else:
                            # La columna no existe en los datos target, la llenamos de nulos según el tipo original
                            if pd.api.types.is_numeric_dtype(df_ref[col]):
                                df_export[col] = pd.Series([float('nan')] * len(df_target), dtype="float64")
                            else:
                                df_export[col] = pd.Series([""] * len(df_target), dtype="object")
                                
                    export_sav_path = "temp_planchado.sav"
                    pyreadstat.write_sav(
                        df_export, 
                        export_sav_path, 
                        column_labels=meta_ref.column_names_to_labels,
                        variable_value_labels=meta_ref.variable_value_labels
                    )
                    
                    with open(export_sav_path, "rb") as f:
                        sav_bytes = f.read()
                        
                    st.download_button(
                        label="📥 Descargar SAV (Datos + Estructura)",
                        data=sav_bytes,
                        file_name="datos_planchados.sav",
                        mime="application/x-spss-sav",
                        width="stretch"
                    )
                except Exception as e:
                    st.error(f"No se pudo generar el archivo SAV para descarga: {e}")


# --- TOOL DATA STORYTELLING ---

def tool_visualizer():
    st.title("📊 Data Storytelling (Beta)")
    st.markdown("""
    **Narrativa de Datos Automatizada**: Asigna roles a tus variables y obtén un dashboard profesional al instante.
    """)

    # 1. DATA CHECK
    if st.session_state.df is None:
        st.warning("⚠️ Primero carga un archivo en el 'Gestor y Exportador' o 'Editor Avanzado'.")
        return

    df = st.session_state.df.copy()
    
    # 2. ROLE MAPPING (SIDEBAR)
    with st.sidebar:
        st.header("🎯 Mapeo de Variables")
        st.info("Define qué representa cada columna:")
        
        cols = df.columns.tolist()
        
        var_genero = st.selectbox("Género (Sex)", ["-- Seleccionar --"] + cols, index=0)
        var_edad = st.selectbox("Edad (Numérica)", ["-- Seleccionar --"] + cols, index=0)
        var_zona = st.selectbox("Zona / Localidad", ["-- Seleccionar --"] + cols, index=0)
        
        st.divider()
        st.write("Variables de Interés")
        vars_voto = st.multiselect("Intención de Voto / Imagen", cols)
        
        run_viz = st.button("✨ Generar Historia", type="primary")

    # 3. DASHBOARD GENERATION
    if run_viz:
        
        # PRE-PROCESSING: AGE RANGES
        if var_edad != "-- Seleccionar --" and pd.api.types.is_numeric_dtype(df[var_edad]):
            # Create Age Bins: 16-29, 30-49, 50+
            bins = [0, 29, 49, 150]
            labels = ['16-29 Joven', '30-49 Adulto', '50+ Senior']
            df['Rango_Edad_Gen'] = pd.cut(df[var_edad], bins=bins, labels=labels)
        else:
            df['Rango_Edad_Gen'] = "No Definido"

        # TABS
        tab_quota, tab_demo, tab_vote, tab_cross = st.tabs([
            "📋 Control de Muestra", 
            "👥 Demográficos", 
            "🗳️ Escenarios", 
            "🔄 Cruces"
        ])

        # A. CONTROL DE MUESTRA (QUOTA)
        with tab_quota:
            st.subheader("Tabla de Control de Cuotas")
            st.markdown("Frecuencias cruzadas para verificar el cumplimiento del diseño muestral.")
            
            if var_zona != "-- Seleccionar --" and var_edad != "-- Seleccionar --":
                try:
                    # Cross tabulation: Zone + Sex vs Age Range
                    quota_table = pd.crosstab(
                        index=[df[var_zona], df[var_genero]], 
                        columns=df['Rango_Edad_Gen'],
                        margins=True,
                        margins_name="Total"
                    )
                    
                    # Fix for Streamlit/Arrow serialization error with mixed types in index/columns due to "Total"
                    # We reset index to make it a standard dataframe and ensure all column names are strings
                    quota_display = quota_table.reset_index()
                    quota_display.columns = [str(c) for c in quota_display.columns]
                    
                    st.dataframe(quota_display, width="stretch")
                    
                    # Download
                    csv_quota = quota_table.to_csv().encode('utf-8')
                    st.download_button("📥 Descargar Tabla Cuotas", csv_quota, "cuotas_control.csv", "text/csv")
                except Exception as e:
                    st.error(f"No se pudo generar la tabla de cuotas: {e}")
            else:
                st.info("Selecciona 'Zona' y 'Edad' para ver la tabla de control.")

        # B. DEMOGRAPHICS
        with tab_demo:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Género")
                if var_genero != "-- Seleccionar --":
                    fig_gen = px.pie(df, names=var_genero, title="Distribución por Género", hole=0.4)
                    st.plotly_chart(fig_gen, use_container_width=True)
                else:
                    st.warning("Selecciona variable de Género.")
            
            with col2:
                st.markdown("### Edad")
                if var_edad != "-- Seleccionar --" and 'Rango_Edad_Gen' in df:
                     fig_age = px.histogram(df, x='Rango_Edad_Gen', title="Distribución por Rango Etario", color='Rango_Edad_Gen')
                     st.plotly_chart(fig_age, use_container_width=True)
                else:
                    st.warning("Selecciona variable de Edad.")

        # C. ELECTORAL SCENARIOS
        with tab_vote:
            if vars_voto:
                for v in vars_voto:
                    st.divider()
                    st.markdown(f"### {v}")
                    
                    try:
                        # Frequency with percentages
                        val_counts = df[v].value_counts(normalize=True).reset_index()
                        val_counts.columns = ['Opción', 'Porcentaje']
                        val_counts['Porcentaje'] = val_counts['Porcentaje'] * 100
                        
                        fig_vote = px.bar(
                            val_counts, 
                            x='Opción', 
                            y='Porcentaje', 
                            text_auto='.1f',
                            title=f"Resultados: {v}",
                            color='Opción'
                        )
                        st.plotly_chart(fig_vote, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error al graficar {v}: {e}")
            else:
                st.info("Selecciona variables de 'Intención de Voto' en el menú lateral.")

        # D. CROSSINGS (BIVARIATE)
        with tab_cross:
            if vars_voto and var_genero != "-- Seleccionar --":
                st.subheader("Intención de Voto por Segmentos")
                
                options = [var_genero]
                if var_zona != "-- Seleccionar --": options.append(var_zona)
                if 'Rango_Edad_Gen' in df: options.append("Rango_Edad_Gen")

                cross_var = st.selectbox("Cruzar por:", options)
                
                for v in vars_voto:
                    st.markdown(f"#### {v} según {cross_var}")
                    
                    try:
                        # Crosstab for plotting
                        cross_data = pd.crosstab(df[cross_var], df[v], normalize='index') * 100
                        cross_data = cross_data.reset_index().melt(id_vars=cross_var, var_name="Candidato", value_name="Porcentaje")
                        
                        fig_cross = px.bar(
                            cross_data,
                            x=cross_var,
                            y="Porcentaje",
                            color="Candidato",
                            title=f"{v} por {cross_var}",
                            barmode="group",
                            text_auto='.1f'
                        )
                        st.plotly_chart(fig_cross, use_container_width=True)
                    except Exception as e:
                        st.warning(f"No se pudo cruzar {v}: {e}")
            else:
                 st.info("Requiere variables de Voto y Género definidos.")

    elif not run_viz:
        st.info("👈 Configura las variables en el menú lateral y presiona 'Generar Historia'.")


def main():
    st.sidebar.title("Navegación")
    tool_select = st.sidebar.radio(
        "Selecciona la Herramienta:",
        ["Gestor y Exportador (Clásico)", "Editor Avanzado (Nuevo)", "Auditoría de Calidad (Beta)", "Data Storytelling (Beta)"]
    )
    
    if tool_select == "Gestor y Exportador (Clásico)":
        tool_manager_exporter()
    elif tool_select == "Editor Avanzado (Nuevo)":
        tool_advanced_editor()
    elif tool_select == "Auditoría de Calidad (Beta)":
        tool_audit_validator()
    elif tool_select == "Data Storytelling (Beta)":
        tool_visualizer()

if __name__ == "__main__":
    main()
