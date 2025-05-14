import pandas as pd
from sklearn.ensemble import IsolationForest

# --- Configuración ---
CSV_PATH   = 'output/variaciones_productos.csv'
ABS_THRESH = 5.0   # umbral absoluto en % (|variación| > 5)
CONTAM     = 0.1   # porcentaje estimado de outliers para IsolationForest

# --- Carga de datos ---
df = pd.read_csv(CSV_PATH)
# Extraer mes de la columna file
df['mes'] = (
    df['file']
      .str.extract(r'_(ENE|FEB|MAR)_')[0]
      .map({'ENE':'Enero','FEB':'Febrero','MAR':'Marzo'})
)

# --- Detección 1: Z-score suave (|z| > 1) ---
df['z_score'] = df.groupby('producto')['variacion']\
                  .transform(lambda x: (x - x.mean()) / x.std(ddof=1))
df['anomaly_z1'] = df['z_score'].abs() > 1

# --- Detección 2: Umbral absoluto (|variación| > ABS_THRESH) ---
df['anomaly_abs'] = df['variacion'].abs() > ABS_THRESH

# --- Detección 3: Isolation Forest ---
model = IsolationForest(contamination=CONTAM, random_state=42)
df['anomaly_if'] = model.fit_predict(df[['variacion']])
# IsolationForest da -1 para outliers, +1 para normales
df['anomaly_if'] = df['anomaly_if'] == -1

# --- Resultados ---
# Filtrar filas donde cualquier método marque anomalía
anomalies = df[df[['anomaly_z1','anomaly_abs','anomaly_if']].any(axis=1)]

print("Productos/Meses marcados como anomalía:")
print(anomalies[['producto','mes','variacion','z_score','anomaly_abs','anomaly_if']])

# Opcional: guardar en CSV
anomalies.to_csv('output/anomalias_detectadas.csv', index=False)
print("\n✅ Anomalías guardadas en: output/anomalias_detectadas.csv")
