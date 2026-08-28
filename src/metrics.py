import pandas as pd
import numpy as np

class MetricsEngine:
    def __init__(self, data):
        df = data.copy()
        
        # Identificar dinámicamente la columna de fecha (CSV o Supabase)
        col_fecha = next((col for col in ['Activity Date', 'fecha', 'Fecha', 'Date'] if col in df.columns), None)
        
        if col_fecha:
            df[col_fecha] = pd.to_datetime(df[col_fecha])
            self.data = df.sort_values(col_fecha).reset_index(drop=True)
        else:
            self.data = df
            
        self.df = self.data  # Alias para mantener compatibilidad interna

        self.data = self._clasificar_por_titulo(self.data)

    def _clasificar_por_titulo(self, df):
        """Etiqueta el tipo de entrenamiento basándose en palabras clave en el nombre o tipo"""
        def etiquetar(nombre):
            if not isinstance(nombre, str):
                return "Desconocido"
            n = nombre.lower()
            if any(k in n for k in ["z2", "zona 2", "suave", "regenerativo", "trote", "largo"]):
                return "Suave / Volumen"
            elif any(k in n for k in ["intervalos", "series", "fartlek", "umbral", "repeticiones", "vo2"]):
                return "Calidad / Alta Intensidad"
            elif any(k in n for k in ["competencia", "carrera", "10k", "15k", "retos", "test"]):
                return "Competencia / Test"
            else:
                return "Moderado / General"

        col_nombre = next((col for col in ['Nombre de la actividad', 'Activity Name', 'Name', 'tipo_actividad'] if col in df.columns), None)
        df['Tipo_Entrenamiento'] = df[col_nombre].apply(etiquetar) if col_nombre else "General"
        return df

    def calculate_pmc(self):
        """Calcula PMC (CTL, ATL, TSB) y ACWR con fallback de carga estandarizado para CSV y Supabase."""
        col_fecha = next((c for c in ['Activity Date', 'fecha', 'Fecha', 'date'] if c in self.data.columns), None)
        
        if not col_fecha:
            return pd.DataFrame(columns=["Fecha", "Carga", "CTL", "ATL", "TSB", "ACWR"])

        df_temp = self.data.copy()
        df_temp[col_fecha] = pd.to_datetime(df_temp[col_fecha])

        # 1. Identificar dinámicamente la columna de distancia (CSV o Supabase)
        col_dist = next((c for c in ['Distance_km', 'distancia_km', 'Distance', 'distancia'] if c in df_temp.columns), None)
        
        if col_dist:
            dist_series = pd.to_numeric(df_temp[col_dist], errors='coerce').fillna(0)
            # Si los valores vienen en metros (ej. 5000 m en lugar de 5 km), normalizar a km
            if dist_series.mean() > 100:
                dist_series = dist_series / 1000.0
        else:
            dist_series = pd.Series(0.0, index=df_temp.index)

        # 2. Identificar dinámicamente la columna de esfuerzo
        col_esfuerzo = next((c for c in ['Relative Effort', 'relative_effort', 'esfuerzo_relativo'] if c in df_temp.columns), None)

        # 3. Calcular la Carga de Entrenamiento de forma resiliente
        if col_esfuerzo and pd.to_numeric(df_temp[col_esfuerzo], errors='coerce').dropna().sum() > 0:
            df_temp['Carga_Calculada'] = pd.to_numeric(df_temp[col_esfuerzo], errors='coerce').fillna(dist_series * 7.5)
        else:
            df_temp['Carga_Calculada'] = dist_series * 7.5

        # 4. Agrupar por fecha y construir el PMC diario
        df_diario = df_temp.groupby(df_temp[col_fecha].dt.date)['Carga_Calculada'].sum().reset_index()
        df_diario.columns = ["Fecha", "Carga"]
        df_diario["Fecha"] = pd.to_datetime(df_diario["Fecha"])
        df_diario = df_diario.set_index("Fecha").resample("D").asfreq().fillna(0).reset_index()

        carga = df_diario["Carga"]
        ctl = [0.0]
        atl = [0.0]
        
        for i in range(len(df_diario)):
            ctl_hoy = ctl[-1] + (carga.iloc[i] - ctl[-1]) / 42
            atl_hoy = atl[-1] + (carga.iloc[i] - atl[-1]) / 7
            ctl.append(ctl_hoy)
            atl.append(atl_hoy)
        
        df_diario["CTL"] = ctl[1:]
        df_diario["ATL"] = atl[1:]
        df_diario["TSB"] = df_diario["CTL"].shift(1) - df_diario["ATL"].shift(1)
        df_diario["ACWR"] = np.where(df_diario["CTL"] > 0, df_diario["ATL"] / df_diario["CTL"], 0.0)
        
        return df_diario.fillna(0)
    
    def calculate_training_strain(self, df_diario):
        """Calcula la Monotonía y la Tensión de Entrenamiento a 7 días (Pfitzinger)"""
        if df_diario.empty or len(df_diario) < 7:
            return 0.0, 0.0, "Estable"
        
        ultimos_7 = df_diario["Carga"].tail(7)
        promedio_7 = ultimos_7.mean()
        std_7 = ultimos_7.std()
        
        monotonía = (promedio_7 / std_7) if std_7 > 0 else 1.0
        strain = promedio_7 * monotonía
        
        estado_monotonia = "Normal"
        if monotonía > 2.0:
            estado_monotonia = "Monótono (Alto Riesgo)"
        elif monotonía < 1.5:
            estado_monotonia = "Variado y Óptimo"
            
        return round(monotonía, 2), round(strain, 2), estado_monotonia

    def evaluate_mental_battery(self, historial_disfrute, acwr_actual):
        """Evalúa la Batería Mental de Disfrute (Fitzgerald)"""
        if not historial_disfrute or len(historial_disfrute) < 7:
            return "Estable", "Sin datos suficientes"
        
        prom_7 = sum(historial_disfrute[-7:]) / 7
        if prom_7 < 1.8 and acwr_actual > 1.3:
            return "Agotada", "⚠️ Batería Mental Agotada: Riesgo de burnout mental."
        return "Óptima", "✅ Batería Mental Saludable."

    def get_vdot_level(self):
        """
        Calcula el VDOT evaluando ÚNICAMENTE los mejores esfuerzos de calidad 
        o carreras/tests de las últimas semanas (Metodología Jack Daniels).
        """
        try:
            df_run = self.data.copy()
            
            # 1. Identificar columnas de distancia y tiempo
            col_dist = next((c for c in ['Distance_km', 'distancia_km', 'distance', 'Distance'] if c in df_run.columns), None)
            col_time = next((c for c in ['Moving_Time_min', 'tiempo_movimiento_min', 'moving_time', 'Moving Time'] if c in df_run.columns), None)
            
            if not col_dist or not col_time:
                return 44

            dist_km = df_run[col_dist] / 1000.0 if df_run[col_dist].mean() > 100 else df_run[col_dist]
            time_h = df_run[col_time] / 3600.0 if df_run[col_time].mean() > 500 else df_run[col_time] / 60.0

            df_run['speed_kmh'] = dist_km / time_h

            # 2. FILTRO METODOLÓGICO: Solo considerar actividades de calidad o velocidad alta
            # Se descartan trotes por debajo de velocidad de umbral para no contaminar la métrica
            df_calidad = df_run[
                (dist_km >= 3.0) & 
                (df_run['Tipo_Entrenamiento'].isin(["Calidad / Alta Intensidad", "Competencia / Test", "Moderado / General"])) &
                (df_run['speed_kmh'] > 10.5)  # Ritmos más vivos que el trote suave
            ]

            # Si no hay suficientes registros de calidad guardados, toma el top 5% general
            if df_calidad.empty:
                df_calidad = df_run[(dist_km >= 2.0) & (df_run['speed_kmh'] > 8.0)]
                top_speed = df_calidad['speed_kmh'].max() if not df_calidad.empty else 12.0
            else:
                top_speed = np.percentile(df_calidad['speed_kmh'].dropna(), 90)

            # 3. Conversión de velocidad pico estimada a VDOT equivalente
            vdot_estimado = round(top_speed * 3.3)
            
            return max(38, min(vdot_estimado, 65))
            
        except Exception as e:
            print(f"Error calculando VDOT: {e}")
            return 44

    def get_pace_zones(self, vdot):
        """Calcula las zonas de ritmo calibradas."""
        def sec_to_min_sec(sec_per_km):
            m = int(sec_per_km // 60)
            s = int(round(sec_per_km % 60))
            if s == 60:
                m += 1
                s = 0
            return f"{m}:{s:02d}"

        return {
            "Zona E (Fácil / Suave)": f"{sec_to_min_sec(315)} - {sec_to_min_sec(350)} min/km",
            "Zona M (Maratón)": f"{sec_to_min_sec(270)} - {sec_to_min_sec(295)} min/km",
            "Zona T (Umbral / Tempo)": f"{sec_to_min_sec(240)} - {sec_to_min_sec(255)} min/km",
            "Zona I (Intervalos / VO2max)": f"{sec_to_min_sec(210)} - {sec_to_min_sec(225)} min/km",
            "Zona R (Repeticiones / Velocidad)": f"{sec_to_min_sec(195)} - {sec_to_min_sec(210)} min/km"
        }

    def get_polarization_ratio(self):
        if 'Tipo_Entrenamiento' not in self.data.columns:
            return 0.0, 0.0
        conteo = self.data['Tipo_Entrenamiento'].value_counts(normalize=True) * 100
        volumen_pct = conteo.get("Suave / Volumen", 0.0)
        calidad_pct = conteo.get("Calidad / Alta Intensidad", 0.0) + conteo.get("Competencia / Test", 0.0)
        return volumen_pct, calidad_pct