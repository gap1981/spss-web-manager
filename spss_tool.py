import streamlit as st
import pandas as pd
import pyreadstat
import io
import os

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="SPSS Ultimate Web Manager", layout="wide", page_icon="⚙️")

def main():
    st.title("📊 SPSS Ultimate Web Manager")
    st.markdown("Gestión integral: Exportación, Limpieza, Planchado y Sintaxis.")

    # 1. CARGA INICIAL (SAV DE LIMESURVEY)
    uploaded_sav = st.sidebar.file_uploader("1. Subir SAV (Metadatos Base)", type=["sav"])

    if uploaded_sav:
        # Guardar y leer metadatos
        with open("base.sav", "wb") as f:
            f.write(uploaded_sav.getbuffer())
        df_orig, meta = pyreadstat.read_sav("base.sav")
        
        # Guardar metadatos en session_state para persistencia
        if 'meta' not in st.session_state:
            st.session_state.meta = meta

        # --- PESTAÑAS DEL FLUJO DE TRABAJO ---
        t1, t2, t3, t4 = st.tabs([
            "📥 1. Exportar para Cliente", 
            "✂️ 2. Borrar Columnas", 
            "🔥 3. Planchar y Editar", 
            "📜 4. Sintaxis y Finalizar"
        ])

        # TAB 1: EXPORTAR EXCEL CRUDO
        with t1:
            st.subheader("Generar Excel para revisión")
            st.write("Este archivo contiene los datos originales y el diccionario de códigos.")
            
            output_rev = io.BytesIO()
            with pd.ExcelWriter(output_rev, engine='openpyxl') as writer:
                df_orig.to_excel(writer, sheet_name='Datos_Crudos', index=False)
                # Hoja de códigos
                dicc = []
                for var, labels in meta.variable_value_labels.items():
                    for val, lab in labels.items():
                        dicc.append({"Variable": var, "Código": val, "Etiqueta": lab})
                pd.DataFrame(dicc).to_excel(writer, sheet_name='Diccionario', index=False)
            
            st.download_button("📥 Descargar Excel Crudo", output_rev.getvalue(), 
                               file_name="Revision_Cliente.xlsx", mime="application/vnd.ms-excel")

        # TAB 2: BORRAR COLUMNAS
        with t2:
            st.subheader("Limpieza de Variables")
            cols_to_keep = st.multiselect("Selecciona las columnas que deseas MANTENER:", 
                                         options=df_orig.columns, default=list(df_orig.columns))
            df_cleaned = df_orig[cols_to_keep]
            st.warning(f"Columnas eliminadas: {len(df_orig.columns) - len(cols_to_keep)}")

        # TAB 3: PLANCHAR Y EDITAR DATOS
        with t3:
            st.subheader("Planchado de datos revisados")
            file_revisado = st.file_uploader("Subir Excel con cambios del cliente", type=["xlsx"])
            
            if file_revisado:
                df_planchado = pd.read_excel(file_revisado)
                # Sincronizar con las columnas elegidas en el paso anterior
                df_final_edit = df_planchado[[c for c in cols_to_keep if c in df_planchado.columns]]
                st.success("✅ Datos del cliente cargados sobre la estructura seleccionada.")
            else:
                df_final_edit = df_cleaned
                st.info("Editando datos actuales (o sube un Excel arriba para planchar).")

            # Editor interactivo (Permite modificar datos puntuales)
            df_final_edit = st.data_editor(df_final_edit, use_container_width=True, height=400)

        # TAB 4: SINTAXIS Y EXPORTACIÓN FINAL
        with t4:
            st.subheader("Generación de Sintaxis y SAV")
            
            # Generar sintaxis base
            syntax_text = "* Sintaxis generada por Web Manager.\n"
            syntax_text += "VARIABLE LABELS\n"
            for var in df_final_edit.columns:
                label = meta.column_names_to_labels.get(var, var)
                syntax_text += f"  {var} '{label}'\n"
            syntax_text += ".\nEXECUTE."

            # Area de edición de sintaxis (puedes modificarla manualmente aquí)
            custom_syntax = st.text_area("Puedes modificar la sintaxis aquí:", value=syntax_text, height=200)

            col_a, col_b = st.columns(2)
            with col_a:
                # Botón Exportar SAV
                if st.button("💾 Generar .SAV Final"):
                    pyreadstat.write_sav(
                        df_final_edit, "final.sav",
                        column_labels={k: v for k, v in meta.column_names_to_labels.items() if k in df_final_edit.columns},
                        variable_value_labels={k: v for k, v in meta.variable_value_labels.items() if k in df_final_edit.columns}
                    )
                    with open("final.sav", "rb") as f:
                        st.download_button("📥 Descargar SAV", f, file_name="Estudio_Final.sav")
            
            with col_b:
                # Botón Descargar Sintaxis Editada
                st.download_button("📥 Descargar Sintaxis (.sps)", custom_syntax, file_name="Sintaxis_Final.sps")

    else:
        st.info("👈 Sube un archivo .sav en el panel lateral para comenzar el flujo.")

if __name__ == "__main__":
    main()
    
