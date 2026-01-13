import streamlit as st
import pandas as pd
import pyreadstat
import io
import os

st.set_page_config(page_title="SPSS Ultimate Manager", layout="wide", page_icon="🌳")

def main():
    st.title("📊 SPSS Manager: Flujo de Datos y Árbol de Códigos")
    
    # 1. CARGA DEL SAV ORIGINAL (BASE DE METADATOS)
    with st.sidebar:
        st.header("Configuración")
        uploaded_sav = st.file_uploader("Subir SAV de LimeSurvey", type=["sav"])
        if st.button("🔄 Reiniciar Aplicación"):
            st.rerun()

    if not uploaded_sav:
        st.info("👈 Sube el archivo .sav original para extraer el árbol de códigos y la estructura.")
        return

    # Leer archivo base
    with open("base_meta.sav", "wb") as f:
        f.write(uploaded_sav.getbuffer())
    df_orig, meta = pyreadstat.read_sav("base_meta.sav")

    # PESTAÑAS DEL FLUJO
    t1, t2, t3, t4 = st.tabs([
        "🌳 Árbol de Códigos & Exportación", 
        "✂️ Limpieza (Borrar)", 
        "🔥 Planchar & Editar", 
        "📜 Sintaxis Final"
    ])

    # --- TAB 1: ÁRBOL DE CÓDIGOS Y EXCEL CRUDO ---
    with t1:
        st.subheader("Generación de Diccionario y Datos Crudos")
        
        # Crear el Árbol de Códigos
        arbol_data = []
        for var, labels in meta.variable_value_labels.items():
            for val, lab in labels.items():
                arbol_data.append({
                    "Código Variable": var,
                    "Pregunta/Etiqueta": meta.column_names_to_labels.get(var, ""),
                    "Valor (Código)": val,
                    "Etiqueta de Respuesta": lab
                })
        df_arbol = pd.DataFrame(arbol_data)

        col1, col2 = st.columns(2)
        with col1:
            st.write("📖 **Árbol de Códigos detectado:**")
            st.dataframe(df_arbol, use_container_width=True, height=300)
        
        with col2:
            st.write("📥 **Descargas para el cliente:**")
            # Generar Excel con dos hojas
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_orig.to_excel(writer, sheet_name='DATOS_CRUDOS', index=False)
                df_arbol.to_excel(writer, sheet_name='ARBOL_DE_CODIGOS', index=False)
            
            st.download_button(
                "📥 Descargar Pack: Datos + Árbol de Códigos",
                output.getvalue(),
                file_name="Para_Revision_Cliente.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # --- TAB 2: BORRAR COLUMNAS ---
    with t2:
        st.subheader("Seleccionar Variables a Mantener")
        st.write("Marca las columnas que quieres que sobrevivan al planchado final.")
        
        # Checkbox para seleccionar todo/nada
        all_cols = list(df_orig.columns)
        cols_to_keep = st.multiselect("Columnas activas:", options=all_cols, default=all_cols)
        
        df_cleaned = df_orig[cols_to_keep]
        st.warning(f"Se eliminarán {len(all_cols) - len(cols_to_keep)} columnas.")

    # --- TAB 3: PLANCHAR EXCEL Y EDITAR ---
    with t3:
        st.subheader("Planchado de Excel Revisado")
        excel_revisado = st.file_uploader("Subir el Excel corregido por el cliente", type=["xlsx"])
        
        if excel_revisado:
            # Planchar datos (leemos la primera hoja)
            df_revisado = pd.read_excel(excel_revisado, sheet_name=0)
            # Asegurar que solo queden las columnas que elegimos en el paso 2
            df_final = df_revisado[[c for c in cols_to_keep if c in df_revisado.columns]]
            st.success("✅ Datos planchados sobre la estructura de metadatos.")
        else:
            df_final = df_cleaned
            st.info("Editando datos actuales. Sube el Excel para sustituirlos masivamente.")

        # Editor interactivo (Estilo SPSS Data View)
        df_final = st.data_editor(df_final, use_container_width=True, height=400)

    # --- TAB 4: SINTAXIS Y SAV FINAL ---
    with t4:
        st.subheader("Editor de Sintaxis y Exportación Final")
        
        # Generar sintaxis dinámica
        stx = ["* --- SINTAXIS GENERADA POR SPSS MANAGER ---\n"]
        stx.append("VARIABLE LABELS")
        for col in df_final.columns:
            label = meta.column_names_to_labels.get(col, col)
            stx.append(f"  {col} '{label}'")
        stx.append(".\n")
        
        if meta.variable_value_labels:
            stx.append("VALUE LABELS")
            for var, labels in meta.variable_value_labels.items():
                if var in df_final.columns:
                    stx.append(f"  / {var}")
                    for val, lab in labels.items():
                        v_str = f"'{val}'" if isinstance(val, str) else str(val)
                        stx.append(f"    {v_str} '{lab}'")
            stx.append(".\n")
        stx.append("EXECUTE.")
        
        # Area de texto para modificar la sintaxis manualmente
        final_syntax = st.text_area("Puedes modificar o añadir comandos aquí:", "\n".join(stx), height=250)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 Generar .SAV Planchado"):
                pyreadstat.write_sav(
                    df_final, "final_planchado.sav",
                    column_labels={k: v for k, v in meta.column_names_to_labels.items() if k in df_final.columns},
                    variable_value_labels={k: v for k, v in meta.variable_value_labels.items() if k in df_final.columns}
                )
                with open("final_planchado.sav", "rb") as f:
                    st.download_button("📥 Descargar SAV Final", f, file_name="Estudio_Final.sav")
        
        with c2:
            st.download_button("📥 Descargar Sintaxis (.sps)", final_syntax, file_name="Sintaxis.sps")

    # Limpieza de archivos temporales
    if os.path.exists("base_meta.sav"): os.remove("base_meta.sav")
    if os.path.exists("final_planchado.sav"): os.remove("final_planchado.sav")

if __name__ == "__main__":
    main()
