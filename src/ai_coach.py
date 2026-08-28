import os
import streamlit as st
from google import genai
from google.genai import types

def generar_recomendacion_coach(contexto):
    """
    Envía las métricas actuales del atleta a Gemini utilizando el modelo principal 
    para generar el plan semanal estructurado día por día.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "⚠️ Error: No se encontró la GEMINI_API_KEY en las variables de entorno."

    try:
        client = genai.Client(api_key=api_key)
        
        # Prompt estructurado con rol de entrenador profesional de resistencia
        prompt = f"""
        Actúa como un entrenador profesional de atletismo de fondo y medio fondo, experto en las metodologías de Jack Daniels (VDOT), 
        Pete Pfitzinger y Stephen Fitzgerald. 

        Aquí tienes las métricas actuales del atleta para esta semana:
        - VDOT Actual: {contexto.get('VDOT')}
        - Fitness (CTL - Carga Crónica): {contexto.get('CTL_Fitness')}
        - Fatiga (ATL - Carga Aguda): {contexto.get('ATL_Fatiga')}
        - Frescura (TSB - Balance de Estrés): {contexto.get('TSB_Frescura')}
        - Ratio de Lesión (ACWR): {contexto.get('ACWR')}
        - Índice de Monotonía: {contexto.get('Monotonia')}
        - Último RPE (Esfuerzo Percibido): {contexto.get('Ultimo_RPE')}
        - Estado Muscular: {contexto.get('Estado_Muscular')}

        Por favor, genera un informe de entrenamiento que contenga obligatoriamente dos partes:

        1. **DIAGNÓSTICO BREVE DE CARGAS:** Un análisis rápido de su estado actual (basado en su TSB, ACWR y fatiga) para justificar la semana.
        2. **PLAN SEMANAL ESTRUCTURADO (Lunes a Domingo):** Diseña un microciclo de entrenamiento detallado día por día. Cada día de running debe incluir:
           - **Tipo de sesión** (Ej. Regenerativo, Calidad/Intervalos, Tempo, Tirada Larga, Descanso, Fuerza).
           - **Distancia estimada** en kilómetros.
           - **Ritmos específicos o zonas** (vinculados a su VDOT actual).
           - **Estímulo fisiológico buscado** (explicando brevemente qué busca entrenar ese día el cuerpo).

        Mantén un tono directo, motivador, riguroso y estructurado con viñetas claras para que el atleta pueda consultarlo fácilmente.
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text

    except Exception as e:
        return f"⚠️ Error al conectar con el AI Coach: {str(e)}"