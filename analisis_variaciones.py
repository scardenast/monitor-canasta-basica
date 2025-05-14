import pandas as pd
import matplotlib.pyplot as plt
import os

# --- Configuración ---
CSV_PATH    = 'output/variaciones_productos.csv'
OUTPUT_DIR  = 'output/graficas'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Carga y pre-procesamiento ---
df = pd.read_csv(CSV_PATH)
# Extraer mes de la columna file
df['mes'] = (
    df['file']
      .str.extract(r'_(ENE|FEB|MAR)_')[0]
      .map({'ENE':'Enero','FEB':'Febrero','MAR':'Marzo'})
)

# --- Graficar por producto ---
for producto, grupo in df.groupby('producto'):
    plt.figure()
    plt.plot(grupo['mes'], grupo['variacion'], marker='o')
    plt.title(f'Variación mensual: {producto}')
    plt.xlabel('Mes')
    plt.ylabel('% Variación')
    plt.grid(True)
    # Guardar cada gráfico en output/graficas
    safe_name = producto.replace(' ', '_').replace('/', '_')
    plt.savefig(f'{OUTPUT_DIR}/{safe_name}_variacion.png')
    plt.close()
