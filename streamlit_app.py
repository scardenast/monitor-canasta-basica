import streamlit as st
import pandas as pd
import pdfplumber
import requests
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from io import BytesIO

# ========= CONFIGURACIÓN =========
YEAR_PAGES = {
    '2024': 'https://observatorio.ministeriodesarrollosocial.gob.cl/nueva-serie-cba-2024',
    '2025': 'https://observatorio.ministeriodesarrollosocial.gob.cl/nueva-serie-cba-2025',
}
SKIP_PAGES = 4  # páginas introductorias a omitir

NUM2MONTH = {
    '01': 'Enero','02': 'Febrero','03': 'Marzo',
    '04': 'Abril','05': 'Mayo','06': 'Junio',
    '07': 'Julio','08': 'Agosto','09': 'Septiembre',
    '10': 'Octubre','11': 'Noviembre','12': 'Diciembre'
}
MONTHS_BY_YEAR = {
    '2024': list(NUM2MONTH.values()),
    '2025': [NUM2MONTH[m] for m in ['01','02','03']]
}

# Regex para capturar: producto, precio CLP, variación %
LINE_REGEX = re.compile(r"^([A-Za-zÁÉÍÓÚáéíóúÑñüÜ\s\-/\(\)]+?)\s+([\d\.\,]+)\s+(-?\d+[.,]\d+)$")

@st.cache_data(ttl=3600)
def load_data():
    registros = []
    for year, page_url in YEAR_PAGES.items():
        resp = requests.get(page_url); resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        hrefs = {
            a['href'] for a in soup.select("a[href$='.pdf']")
            if 'valor_cb' in a['href'].lower() or 'valor_cba' in a['href'].lower()
        }
        for href in sorted(hrefs):
            pdf_url = urljoin(page_url, href)
            fname = pdf_url.rsplit('/', 1)[-1]
            mnum = re.search(rf"{year[2:]}\.(\d{{2}})", fname)
            mes = NUM2MONTH.get(mnum.group(1)) if mnum else None
            if mes not in MONTHS_BY_YEAR[year]:
                continue
            try:
                r2 = requests.get(pdf_url); r2.raise_for_status()
            except:
                continue
            stream = BytesIO(r2.content)
            with pdfplumber.open(stream) as pdf:
                for idx, page in enumerate(pdf.pages):
                    if idx < SKIP_PAGES:
                        continue
                    text = page.extract_text() or ""
                    for line in text.split('\n'):
                        m = LINE_REGEX.match(line.strip())
                        if not m:
                            continue
                        prod      = m.group(1).strip()
                        price_str = m.group(2)
                        var_str   = m.group(3)
                        price_val = float(price_str.replace('.', '').replace(',', '.'))
                        var_val   = float(var_str.replace(',', '.'))
                        if prod.lower() == "cba" or abs(price_val) > 1e6 or abs(var_val) > 100:
                            continue
                        registros.append({
                            'year':      year,
                            'mes':       mes,
                            'producto':  prod,
                            'precio':    price_val,
                            'variacion': var_val
                        })
    if not registros:
        return pd.DataFrame(columns=['year','mes','producto','precio','variacion'])
    return pd.DataFrame(registros)

# ========= STREAMLIT APP =========
st.set_page_config(page_title="Monitor Canasta Básica", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica")

with st.spinner("🔄 Descargando y procesando datos…"):
    df = load_data()

if df.empty:
    st.error("⚠️ No se encontraron datos. Verifica la conexión o la fuente.")
    st.stop()

st.success(f"✅ Cargados {len(df)} registros.")

# --- SIDEBAR: FILTROS ---
st.sidebar.header("Filtros")

# Año
years = sorted(df['year'].unique())
year_sel = st.sidebar.multiselect("Año", years, default=years)

# Mes (dinámico)
available_months = [
    m for y in year_sel for m in MONTHS_BY_YEAR[y]
]
month_sel = st.sidebar.multiselect(
    "Mes",
    options=available_months,
    default=available_months
)

# Producto
products = sorted(df['producto'].unique())
prod_sel  = st.sidebar.multiselect("Producto", products, default=products)

# Métrica
metric = st.sidebar.radio("Métrica", ('Variación %','Precio CLP'))

# --- APLICAR FILTROS ---
df_f = df[
    df['year'].isin(year_sel) &
    df['mes'].isin(month_sel) &
    df['producto'].isin(prod_sel)
].copy()

# Construir índice year_mes ordenado
year_mes_order = [f"{y} {m}" for y in years if y in year_sel
                  for m in MONTHS_BY_YEAR[y] if m in month_sel]
df_f['year_mes'] = df_f['year'] + ' ' + df_f['mes']
df_f['year_mes'] = pd.Categorical(df_f['year_mes'],
                                  categories=year_mes_order, ordered=True)

# --- GRÁFICO ---
if metric == 'Variación %':
    pivot = df_f.pivot_table(index='year_mes',
                             columns='producto',
                             values='variacion',
                             aggfunc='mean')
    ylabel = '%'
else:
    pivot = df_f.pivot_table(index='year_mes',
                             columns='producto',
                             values='precio',
                             aggfunc='mean')
    ylabel = 'CLP'

pivot = pivot.reindex(index=year_mes_order)
st.subheader(f"{metric} Mensual por Producto")
st.line_chart(pivot)

# --- INTERPRETACIONES Y CONCLUSIONES ---
st.subheader("📝 Interpretaciones y Conclusiones")

serie = df_f['variacion'] if metric=='Variación %' else df_f['precio']
unit = '%' if metric=='Variación %' else 'CLP'

# 1) Promedio general
mean_val = serie.mean()
st.markdown(
    f"- El **valor promedio** de la métrica seleccionada "
    f"({metric.lower()}) fue de **{mean_val:.2f} {unit}** "
    f"entre {year_sel[0]}–{year_sel[-1]} y los meses seleccionados."
)

# 2) Máximo y mínimo
idx_max = serie.idxmax()
idx_min = serie.idxmin()
row_max = df_f.loc[idx_max]
row_min = df_f.loc[idx_min]

if metric == 'Variación %':
    st.markdown(
        f"- **Mayor aumento porcentual**: "
        f"{row_max['producto']} con **{row_max['variacion']:.2f}%** "
        f"en {row_max['mes']} {row_max['year']}."
    )
    st.markdown(
        f"- **Mayor descenso porcentual**: "
        f"{row_min['producto']} con **{row_min['variacion']:.2f}%** "
        f"en {row_min['mes']} {row_min['year']}."
    )
else:
    st.markdown(
        f"- **Precio máximo**: "
        f"{row_max['producto']} a **${row_max['precio']:.0f}** "
        f"en {row_max['mes']} {row_max['year']}."
    )
    st.markdown(
        f"- **Precio mínimo**: "
        f"{row_min['producto']} a **${row_min['precio']:.0f}** "
        f"en {row_min['mes']} {row_min['year']}."
    )

# 3) Promedio por año_mes
st.markdown(
    f"**Promedio por periodo (año y mes):**"
)
grouped = (df_f.groupby('year_mes')
               [ 'variacion' if metric=='Variación %' else 'precio' ]
               .mean()
               .reindex(year_mes_order))
for ym, val in grouped.items():
    sym = f"{val:.2f}%" if metric=='Variación %' else f"${val:.0f}"
    st.markdown(f"  - {ym}: {sym}")

# --- TABLA DETALLADA ---
st.subheader("Datos Detallados")
st.dataframe(df_f[['year','mes','producto','precio','variacion']]
             .reset_index(drop=True),
             use_container_width=True)
