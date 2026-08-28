import pandas as pd

def load_and_clean_data(file_path):
    try:
        # 1. Leer datos crudos del CSV
        df = pd.read_csv(file_path)
        
        # 2. Mapeo inteligente (Soporte dual: Español e Inglés)
        column_mappings = {
            # Fechas
            'Fecha': 'Activity Date',
            'Fecha de la actividad': 'Activity Date',
            'Date': 'Activity Date',
            
            # Distancia
            'Distancia': 'Distance',
            'Distance': 'Distance',
            
            # Tiempos
            'Tiempo en movimiento': 'Moving Time',
            'Moving Time': 'Moving Time',
            
            # Tipos de actividad
            'Tipo de actividad': 'Activity Type',
            'Activity Type': 'Activity Type',
            
            # Esfuerzo (Relativo / TSS proxy)
            'Esfuerzo relativo': 'Relative Effort',
            'Relative Effort': 'Relative Effort'
        }
        
        # Renombrar columnas existentes de forma segura
        df = df.rename(columns={col: column_mappings[col] for col in df.columns if col in column_mappings})
        
        # Verificar que existan las columnas críticas mínimas
        required_cols = ['Activity Date', 'Distance', 'Moving Time', 'Activity Type']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Falta la columna crítica '{col}' en el CSV. Verifica el formato de exportación.")

        # 3. Traducción y Normalización de Fechas (Español/Inglés)
        meses_es_en = {
            'ene': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'abr': 'Apr', 'may': 'May', 'jun': 'Jun',
            'jul': 'Jul', 'ago': 'Aug', 'sep': 'Sep', 'oct': 'Oct', 'nov': 'Nov', 'dic': 'Dec'
        }
        
        def normalizar_fecha(fecha_str):
            if not isinstance(fecha_str, str): 
                return fecha_str
            # Limpiar caracteres especiales de espacios o puntos (ej. p.m. / a.m.)
            f = fecha_str.replace('.', '').replace('\u202f', ' ').strip()
            for es, en in meses_es_en.items():
                if es in f.lower():
                    f = f.lower().replace(es, en)
                    break
            return f

        df['Activity Date'] = df['Activity Date'].apply(normalizar_fecha)
        df['Activity Date'] = pd.to_datetime(df['Activity Date'], errors="coerce")
        df = df.dropna(subset=['Activity Date'])
        
        # 4. Conversiones Numéricas y Estandarización de Unidades
        df['Distance'] = pd.to_numeric(df['Distance'], errors="coerce").fillna(0)
        df['Moving Time'] = pd.to_numeric(df['Moving Time'], errors="coerce").fillna(0)
        
        # Si la distancia viene en metros (como en algunos CSV de Strava), convertir a kilómetros
        # Verificamos si el promedio de distancia es muy alto para asumir metros, o normalizamos si supera un umbral lógico.
        # En tu CSV vimos que 'Distance' venía en metros puros (ej: 9749.0 para 9.75km). Vamos a normalizarlo dinámicamente:
        if df['Distance'].max() > 100:  
            df['Distance'] = df['Distance'] / 1000.0

        # Minutos en movimiento para fórmulas posteriores (Daniels / Puntos de Estrés)
        df['duration_minutes'] = df['Moving Time'] / 60
        
        # Si 'Relative Effort' (Esfuerzo relativo) viene vacío, creamos un proxy básico basado en tiempo y tipo
        if 'Relative Effort' not in df.columns or df['Relative Effort'].isna().all():
            df['Relative Effort'] = df['duration_minutes'] * 0.5 # Estimador de respaldo seguro
        else:
            df['Relative Effort'] = pd.to_numeric(df['Relative Effort'], errors="coerce").fillna(df['duration_minutes'] * 0.5)

        # 5. Filtrado Estricto: Solo actividades de tipo Carrera (Soporte multuidioma: 'Carrera' o 'Run')
        df['Activity Type'] = df['Activity Type'].astype(str).str.strip().str.capitalize()
        df_carreras = df[df['Activity Type'].isin(['Carrera', 'Run'])].copy()
        
        return df_carreras

    except Exception as e:
        print(f"Error crítico en Ingesta de Datos (`parser.py`): {e}")
        return None