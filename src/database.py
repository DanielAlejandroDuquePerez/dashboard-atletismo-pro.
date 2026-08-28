import streamlit as st
import pandas as pd
from supabase import create_client, Client

def init_supabase() -> Client:
    """Inicializa la conexión con Supabase usando credenciales seguras."""
    url = st.secrets["SUPABASE_URL"].strip().rstrip('/')
    key = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)

def sincronizar_csv_a_supabase(df_limpio):
    """Inserta nuevos entrenamientos e ignora los duplicados por activity_id."""
    if df_limpio is None or df_limpio.empty:
        st.sidebar.warning("⚠️ El archivo CSV no contiene datos válidos.")
        return 0

    supabase = init_supabase()
    registros = []

    for idx, row in df_limpio.iterrows():
        # Extraer ID de la actividad
        act_id = row.get("Activity ID", row.get("activity_id", idx + 1))
        
        # Formatear la fecha a ISO8601 exigida por PostgreSQL
        fecha_raw = row.get("Fecha", row.get("fecha", row.get("Activity Date")))
        try:
            fecha_iso = pd.to_datetime(fecha_raw).strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            fecha_iso = pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M:%S")

        distancia = row.get("Distance_km", row.get("distancia_km", row.get("Distance", 0)))
        tiempo = row.get("Moving_Time_min", row.get("tiempo_movimiento_min", row.get("Moving Time", 0)))
        tipo = row.get("Activity Type", row.get("tipo_actividad", "Run"))
        ritmo = row.get("Pace", row.get("ritmo_medio", ""))
        hr = row.get("Average HR", row.get("fc_media", row.get("Average Heart Rate", None)))
        elev = row.get("Elevation Gain", row.get("elevacion_m", 0))
        
        # Extraer Esfuerzo Relativo (Clave para CTL/ATL/TSB)
        esfuerzo = row.get("Relative Effort", row.get("relative_effort", row.get("esfuerzo_relativo", None)))

        registros.append({
            "activity_id": int(act_id) if pd.notna(act_id) else (idx + 1),
            "fecha": fecha_iso,
            "tipo_actividad": str(tipo),
            "distancia_km": float(distancia) if pd.notna(distancia) else 0.0,
            "tiempo_movimiento_min": float(tiempo) if pd.notna(tiempo) else 0.0,
            "ritmo_medio": str(ritmo) if pd.notna(ritmo) else "",
            "fc_media": float(hr) if pd.notna(hr) and float(hr) > 0 else None,
            "elevacion_m": float(elev) if pd.notna(elev) else 0.0,
            "esfuerzo_relativo": float(esfuerzo) if pd.notna(esfuerzo) and float(esfuerzo) > 0 else None
        })

    if not registros:
        st.sidebar.error("⚠️ No se encontraron filas para subir.")
        return 0

    try:
        res = supabase.table("actividades").upsert(registros, on_conflict="activity_id").execute()
        count = len(res.data) if res.data else 0
        return count
    except Exception as e:
        st.sidebar.error(f"⚠️ Error al conectar con Supabase: {e}")
        return 0

def cargar_actividades_desde_supabase():
    """Consulta todas las actividades desde Supabase y devuelve un DataFrame."""
    try:
        supabase = init_supabase()
        res = supabase.table("actividades").select("*").order("fecha", desc=False).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df['fecha'] = pd.to_datetime(df['fecha'])
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"⚠️ Error al leer de Supabase: {e}")
        return pd.DataFrame()