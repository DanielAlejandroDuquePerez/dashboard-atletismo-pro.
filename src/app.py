import os
import sys
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Registrar la ruta absoluta de la carpeta src en el path de Python
DIR_ACTUAL = os.path.dirname(os.path.abspath(__file__))
if DIR_ACTUAL not in sys.path:
    sys.path.append(DIR_ACTUAL)

# Importaciones de tus módulos locales
from parser import load_and_clean_data
from metrics import MetricsEngine
from ai_coach import generar_recomendacion_coach
from adherencia import render_adherencia_module
from database import sincronizar_csv_a_supabase, cargar_actividades_desde_supabase

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Pro-Athlete Running Dashboard", 
    page_icon="⏱️", 
    layout="wide"
)

# --- ESTÉTICA HIGH-END SPORT-TECH ---
st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif; }
    h1, h2, h3 { color: #f8fafc !important; font-weight: 700; letter-spacing: -0.5px; }
    div[data-testid="stMetric"] {
        background-color: #111827;
        border: 1px solid #1f2937;
        padding: 1.2rem;
        border-radius: 16px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
        transition: transform 0.2s ease;
    }
    div[data-testid="stMetric"]:hover { transform: translateY(-2px); border-color: #3b82f6; }
    [data-testid="stMetricValue"] { color: #10b981 !important; font-weight: 800; font-size: 2.2rem !important; letter-spacing: -1px; }
    [data-testid="stMetricLabel"] { color: #9ca3af !important; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 1px; }
    .stAlert { background-color: #111827; border: 1px solid #374151; border-radius: 12px; color: #e2e8f0; }
    .stButton button {
        background-color: #2563eb;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        letter-spacing: 0.5px;
        border: 1px solid #1d4ed8;
        padding: 0.6rem 1.2rem;
        transition: all 0.2s ease;
    }
    .stButton button:hover { background-color: #1d4ed8; box-shadow: 0 0 15px rgba(37, 99, 235, 0.4); border-color: #60a5fa; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; border-bottom: 1px solid #1f2937; padding-bottom: 5px; }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #6b7280;
        font-weight: 600;
        padding: 10px 15px;
        border: none;
        text-transform: uppercase;
        font-size: 0.85rem;
        letter-spacing: 0.5px;
    }
    .stTabs [aria-selected="true"] {
        color: #3b82f6 !important;
        background-color: rgba(59, 130, 246, 0.1);
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("⏱️ COMMAND CENTER | Pro-Athlete")
st.markdown("<p style='color:#9ca3af; font-size:1.1rem; margin-top:-15px; margin-bottom:30px;'>Análisis Biomecánico y Carga de Entrenamiento</p>", unsafe_allow_html=True)

# --- SIDEBAR: GESTIÓN DE DATOS ---
st.sidebar.markdown("### 📡 Conexión de Dispositivo")
uploaded_file = st.sidebar.file_uploader("Cargar activities.csv (Strava)", type=["csv"])

raw_data = None

# Opción A: Cargar por CSV
if uploaded_file is not None:
    raw_data = load_and_clean_data(uploaded_file)
    st.sidebar.success("✅ CSV Cargado Localmente")
    
    if st.sidebar.button("☁️ Sincronizar con Supabase", type="primary"):
        with st.sidebar.spinner("Enviando datos a Supabase..."):
            filas_guardadas = sincronizar_csv_a_supabase(raw_data)
            if filas_guardadas > 0:
                st.sidebar.success(f"🚀 ¡{filas_guardadas} actividades guardadas!")
            else:
                st.sidebar.warning("No se guardaron filas nuevas.")
# Opción B: Cargar desde Supabase de forma automática si no hay archivo subido
else:
    with st.spinner("Conectando con Supabase..."):
        raw_data = cargar_actividades_desde_supabase()
        if raw_data is not None and not raw_data.empty:
            st.sidebar.info("☁️ Datos leídos desde Supabase")

# --- RENDERIZADO DEL DASHBOARD ---
if raw_data is not None and not raw_data.empty:
    engine = MetricsEngine(raw_data)
    pmc_df = engine.calculate_pmc()
    vdot_actual = engine.get_vdot_level()
    vol_suave, vol_calidad = engine.get_polarization_ratio()
    
    ctl_actual = pmc_df["CTL"].iloc[-1]
    atl_actual = pmc_df["ATL"].iloc[-1]
    tsb_actual = pmc_df["TSB"].iloc[-1]
    acwr_actual = pmc_df["ACWR"].iloc[-1]
    
    # VDOT Destacado en Sidebar
    st.sidebar.markdown(f"""
        <div style="background-color:#111827; padding:15px; border-radius:12px; border:1px solid #3b82f6; text-align:center;">
            <p style="color:#9ca3af; margin:0; font-size:0.8rem; text-transform:uppercase; letter-spacing:1px;">Nivel VDOT Estimado</p>
            <h1 style="color:#3b82f6; margin:0; font-size:3rem;">{vdot_actual}</h1>
        </div>
    """, unsafe_allow_html=True)
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    
    with st.sidebar.expander("🎯 Zonas de Ritmo (Pace)"):
        zonas = engine.get_pace_zones(vdot_actual)
        for k, v in zonas.items():
            st.markdown(f"- **{k}:** `{v}`")

    # --- ARQUITECTURA DE PESTAÑAS ---
    tab_dashboard, tab_coach, tab_bitacora, tab_fatiga = st.tabs([
        "📊 OVERVIEW & PMC", 
        "🤖 AI COACH", 
        "📝 BITÁCORA", 
        "🩺 ESTADO NEUROMUSCULAR"
    ])

    # ================= TAB 1: DASHBOARD & PMC =================
    with tab_dashboard:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Carga Crónica (CTL)", value=round(ctl_actual, 1), help="Fitness aeróbico construido a 42 días.")
        with col2:
            st.metric("Carga Aguda (ATL)", value=round(atl_actual, 1), help="Fatiga generada en los últimos 7 días.")
        with col3:
            tsb_color = "normal" if tsb_actual > -15 else "inverse"
            st.metric("Frescura (TSB)", value=round(tsb_actual, 1), delta="Recuperado" if tsb_actual > -10 else "Fatigado", delta_color=tsb_color)

        st.markdown("<br>", unsafe_allow_html=True)

        g_col1, g_col2 = st.columns([1, 2])
        
        with g_col1:
            st.markdown("### 🚨 Ratio de Lesión (ACWR)")
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = acwr_actual,
                domain = {'x': [0, 1], 'y': [0, 1]},
                gauge = {
                    'axis': {'range': [0, 2], 'tickwidth': 1, 'tickcolor': "white"},
                    'bar': {'color': "#3b82f6"},
                    'bgcolor': "#111827",
                    'borderwidth': 2,
                    'bordercolor': "#1f2937",
                    'steps': [
                        {'range': [0, 0.8], 'color': "#4b5563"},
                        {'range': [0.8, 1.3], 'color': "#10b981"},
                        {'range': [1.3, 1.5], 'color': "#f59e0b"},
                        {'range': [1.5, 2], 'color': "#ef4444"}
                    ],
                    'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': acwr_actual}
                }
            ))
            fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor="#0b0f19", font={'color': "#f8fafc"})
            st.plotly_chart(fig_gauge, use_container_width=True)

            if acwr_actual > 1.5:
                st.error("🔴 ZONA ROJA: Reduce volumen inmediatamente.")
            elif 0.8 <= acwr_actual <= 1.3:
                st.success("🟢 ZONA ÓPTIMA: Carga asimilada correctamente.")

        with g_col2:
            st.markdown("### 📈 Curva de Rendimiento (PMC)")
            fig = px.line(
                pmc_df, x="Fecha", y=["CTL", "ATL", "TSB"],
                color_discrete_map={"CTL": "#3b82f6", "ATL": "#ef4444", "TSB": "#10b981"},
                template="plotly_dark"
            )
            fig.update_layout(
                legend_title_text="", hovermode="x unified", 
                plot_bgcolor="#111827", paper_bgcolor="#0b0f19",
                height=280, margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#1f2937")
            )
            st.plotly_chart(fig, use_container_width=True)

    # ================= TAB 2: AI COACH & PLAN =================
    with tab_coach:
        st.markdown("### 🧠 Procesamiento Táctico")
        st.markdown("Generación del microciclo basado en algoritmos de Daniels y Pfitzinger.")

        if "ultima_recomendacion" not in st.session_state:
            st.session_state.ultima_recomendacion = None

        if st.button("⚡ Generar Microciclo de Entrenamiento"):
            with st.spinner("Analizando carga crónica y proyectando adaptaciones..."):
                contexto_actual = {
                    "VDOT": vdot_actual,
                    "CTL_Fitness": round(ctl_actual, 1),
                    "ATL_Fatiga": round(atl_actual, 1),
                    "TSB_Frescura": round(tsb_actual, 1),
                    "ACWR": round(acwr_actual, 2),
                    "Monotonia": 1.2,
                    "Ultimo_RPE": 5,
                    "Estado_Muscular": "Evaluando"
                }
                st.session_state.ultima_recomendacion = generar_recomendacion_coach(contexto_actual)

        if st.session_state.ultima_recomendacion:
            st.markdown("<div style='background-color:#111827; padding:20px; border-radius:12px; border-left:4px solid #3b82f6;'>", unsafe_allow_html=True)
            st.markdown(st.session_state.ultima_recomendacion)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("💡 Panel en espera. Inicia la generación del plan táctico.")

    # ================= TAB 3: BITÁCORA & ADHERENCIA =================
    with tab_bitacora:
        render_adherencia_module(ai_coach_recomendacion=st.session_state.get("ultima_recomendacion"))

    # ================= TAB 4: FATIGA & HPA =================
    with tab_fatiga:
        st.markdown("### 🔬 Telemetría del Sistema HPA")
        
        monotonia, strain, estado_monot = engine.calculate_training_strain(pmc_df)
        
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            st.metric("Índice de Monotonía", value=monotonia, delta=estado_monot)
            if monotonia > 2.0:
                st.warning("⚠️ Patrón de entrenamiento repetitivo detectado.")
            else:
                st.success("✅ Variabilidad de cargas óptima.")
        
        with f_col2:
            calidad_sueno = st.selectbox("Métrica de Sueño (Manual)", ["Óptima", "Regular", "Deficiente"])
            hr_matutina = st.checkbox("¿Frecuencia Cardíaca en reposo alterada (>5 ppm)?")
            
            if calidad_sueno == "Deficiente" and hr_matutina:
                st.error("🚨 Posible fatiga del sistema nervioso central.")
            else:
                st.info("🟢 Parámetros de recuperación sistémica normales.")

else:
    st.info("📡 **Esperando conexión de datos.** Carga tu archivo CSV en la barra lateral o guarda datos en Supabase.")