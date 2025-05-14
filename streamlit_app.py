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
SKIP_PAGES = 4

NUM2MONTH = {
    '01': 'Enero', '02': 'Febrero', '03': 'Marzo',
    '04': 'Abril','05': 'Mayo','06': 'Junio',
    '07': 'Julio','08': 'Agosto','09': 'Septiembre',
    '10': 'Octubre','11': 'Noviembre','12': 'Diciembre'
}
MONTHS_BY_YEAR = {
    '2024': list(NUM2MONTH.values()),
    '2025': [NUM2MONTH[m] for m in ['01','02','03']]
}

LINE_REGEX = re.compile(r"^([A-Za-zÁÉÍÓÚáéíóúÑñüÜ\s\-/\(\)]+?)\s+(-?\d+[.,]\d+)$")

@st.cache_data(ttl=3600)
def load_data():
    registros = []
    for year, page_url in YEAR_PAGES.items():
        r = requests.get(page_url); r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        hrefs = {
            a['href'] for a in soup.select("a[href$='.pdf']")
            if 'valor_cb' in a['href'].lower() or 'valor_cba' in a['href'].lower()
        }
        for href in sorted(hrefs):
            pdf_url = urljoin(page_url, href)
            fname   = pdf_url.rsplit('/',1)[-1]
            mnum    = re.search(rf"{year[2:]}\.(\d{{2}})", fname)
            mes     = NUM2MONTH.get(mnum.group(1)) if mnum else None
            if mes not in MONTHS_BY_YEAR[year]:
                continue
            try:
                r2 = requests.get(pdf_url); r2.raise_for_status()
            except:
                continue
            with pdfplumber.open(BytesIO(r2.content)) as pdf:
                for i, page in enumerate(pdf.pages):
                    if i < SKIP_PAGES: continue
                    text = page.extract_text() or ''
                    for line in text.split('\n'):
                        m = LINE_REGEX.match(line.strip())
                        if not m: continue
                        prod = m.group(1).strip()
                        val  = float(m.group(2).replace(',', '.'))
                        if prod.lower() == 'cba' or abs(val) > 100: continue
                        registros.append({
                            'year':      year,
                            'mes':       mes,
                            'producto':  prod,
                            'variacion': val
                        })
    if not registros:
        return pd.DataFrame(columns=['year','mes','producto','variacion'])
    return pd.DataFrame(registros)

# ========= APP =========
st.set_page_config(page_title="Monitor Canasta Básica", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica")

with st.spinner("🔄 Descargando y procesando…"):
    df = load_data()

if df.empty:
    st.error("⚠️ No se encontraron datos. Verifica la conexión o la fuente.")
    st.stop()

st.success(f"✅ Cargados {len(df)} registros.")

# --- SIDEBAR: FILTROS ---
st.sidebar.header("Filtros")
years       = sorted(df['year'].unique())
year_sel    = st.sidebar.multiselect("Año", years, default=years)
months_avail= sorted(
    df[df['year'].isin(year_sel)]['mes'].unique(),
    key=lambda m: list(NUM2MONTH.values()).index(m)
)
month_sel   = st.sidebar.multiselect("Mes", months_avail, default=months_avail)
products    = sorted(df['producto'].unique())
prod_sel    = st.sidebar.multiselect("Producto", products, default=products)

# --- FILTRADO ---
df_f = df[
    df['year'].isin(year_sel) &
    df['mes'].isin(month_sel) &
    df['producto'].isin(prod_sel)
].copy()

# Orden cronológico de meses según primer año
order_meses = MONTHS_BY_YEAR[year_sel[0]]
df_f['mes'] = pd.Categorical(df_f['mes'], categories=order_meses, ordered=True)

# --- GRÁFICO 1: VARIACIÓN MENSUAL (líneas) ---
st.subheader("Variación Porcentual Mensual por Producto")
monthly_pivot = (
    df_f
      .pivot_table(index='mes', columns='producto', values='variacion', aggfunc='mean')
      .reindex(order_meses)
)
st.line_chart(monthly_pivot)

# --- GRÁFICO 2: VARIACIÓN ANUAL PROMEDIO (barras) ---
st.subheader("Variación Porcentual Anual Promedio por Producto")
annual_pivot = (
    df_f
      .groupby(['year','producto'])['variacion']
      .mean()
      .unstack(fill_value=0)
)
st.bar_chart(annual_pivot)

# --- INTERPRETACIONES Y CONCLUSIONES ---
st.subheader("📝 Interpretaciones y Conclusiones")

# Promedio general
avg_var = df_f['variacion'].mean()
st.markdown(f"- La variación porcentual promedio de los productos seleccionados fue **{avg_var:.2f}%**.")

# Producto con mayor alza y mayor baja
row_max = df_f.loc[df_f['variacion'].idxmax()]
row_min = df_f.loc[df_f['variacion'].idxmin()]
st.markdown(
    f"- **Mayor alza**: _{row_max['producto']}_ con **+{row_max['variacion']:.2f}%** "
    f"en {row_max['mes']} {row_max['year']}."
)
st.markdown(
    f"- **Mayor baja**: _{row_min['producto']}_ con **{row_min['variacion']:.2f}%** "
    f"en {row_min['mes']} {row_min['year']}."
)

# Variación media por mes
st.markdown("**Variación porcentual media por mes (promedio de todos los productos):**")
for mes in order_meses:
    if mes in month_sel:
        vm = df_f[df_f['mes']==mes]['variacion'].mean()
        st.markdown(f"  - {mes}: {vm:.2f}%")

# --- DATOS DETALLADOS ---
st.subheader("Datos Detallados")
st.dataframe(
    df_f[['year','mes','producto','variacion']]
      .sort_values(['year','mes','producto'])
      .reset_index(drop=True),
    use_container_width=True
)
