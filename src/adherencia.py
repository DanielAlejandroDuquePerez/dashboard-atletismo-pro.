import streamlit as st
import json
import os
from datetime import datetime

DATA_FILE = "adherencia_log.json"

def cargar_registros():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def guardar_registro(nuevo_registro):
    registros = cargar_registros()
    registros.insert(0, nuevo_registro) # El más reciente arriba
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(registros, f, indent=4, ensure_ascii=False)

def borrar_historial():
    """Elimina el archivo JSON de registros si existe."""
    if os.path.exists(DATA_FILE):
        try:
            os.remove(DATA_FILE)
            return True
        except Exception:
            return False
    return False

def render_adherencia_module(ai_coach_recomendacion=None):
    st.markdown("### 📊 Diario de Adherencia y Feedback Semanal")
    st.markdown("Documenta el cumplimiento real de tu plan semanal y guarda el análisis de cargas de tu AI Coach.")

    with st.form("form_adherencia"):
        col1, col2 = st.columns(2)
        
        with col1:
            semana_label = st.text_input("Identificador de Semana (Ej. Semana 3 - Bloque Base)", value=f"Semana del {datetime.now().strftime('%d/%m/%Y')}")
            cumplimiento = st.slider("Adherencia al Plan (%)", 0, 100, 80, 5)
            
        with col2:
            fatiga_percibida = st.select_slider(
                "Nivel de Fatiga General de la Semana",
                options=["Muy Fresco", "Fresco", "Normal / Controlado", "Cargado", "Muy Fatigado"]
            )
            objetivo_cumplido = st.radio(
                "¿Pudiste ejecutar los entrenamientos de calidad clave?",
                ["Sí, por completo", "Parcialmente (tuve que ajustar)", "No, prioricé descanso"]
            )

        observaciones = st.text_area(
            "Notas de campo y sensaciones (Ej. 'El umbral salió cómodo, pero el jueves sentí pesados los cuádriceps...')"
        )
        
        # Opción para guardar también el último diagnóstico del coach si está disponible
        incluir_coach = st.checkbox("Guardar también el último diagnóstico del AI Coach generado", value=True)
        
        submitted = st.form_submit_button("💾 Guardar Registro y Análisis Semanal")
        
        if submitted:
            registro = {
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "semana": semana_label,
                "adherencia": cumplimiento,
                "fatiga": fatiga_percibida,
                "cumplimiento_calidad": objetivo_cumplido,
                "notas": observaciones,
                "diagnostico_coach": ai_coach_recomendacion if incluir_coach and ai_coach_recomendacion else "No se adjuntó diagnóstico en este registro."
            }
            guardar_registro(registro)
            st.success("¡Registro y análisis del coach guardados con éxito en tu historial!")
            st.rerun()

    st.markdown("---")
    st.markdown("#### 📁 Historial de Seguimiento y Diagnósticos")
    
    registros_guardados = cargar_registros()
    if registros_guardados:
        for reg in registros_guardados[:5]: # Mostrar los últimos 5
            with st.expander(f"📌 {reg['semana']} — Adherencia: {reg['adherencia']}% ({reg['fecha']})"):
                st.markdown(f"- **Fatiga reportada:** {reg['fatiga']}")
                st.markdown(f"- **Calidad:** {reg['cumplimiento_calidad']}")
                st.markdown(f"- **Notas de campo:** {reg['notas']}")
                st.markdown("---")
                st.markdown("**🤖 Análisis y Recomendación del AI Coach de esa semana:**")
                st.markdown(reg['diagnostico_coach'])
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Botón para limpiar registros de prueba o errores
        with st.expander("⚙️ Opciones de Gestión de Datos"):
            st.warning("⚠️ Cuidado: Esta acción borrará por completo todos los registros e historiales guardados en el archivo local.")
            if st.button("🗑️ Borrar Todo el Historial de Entrenamientos"):
                if borrar_historial():
                    st.success("¡Historial borrado con éxito!")
                    st.rerun()
                else:
                    st.error("No se pudo borrar el archivo o no hay registros.")
    else:
        st.info("Aún no hay registros guardados. Completa el formulario de arriba para documentar tu primera semana.")