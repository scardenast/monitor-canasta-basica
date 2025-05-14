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
    '01':'Enero','02':'Febrero','03':'Marzo',
    '04':'Abril','05':'Mayo','06':'Junio',
    '07':'Julio','08':'Agosto','09':'Septiembre',
    '10':'Octubre','11':'Noviembre','12':'Diciembre'
}
MONTHS_BY_YEAR = {
    '2024': list(NUM2MONTH.values()),
    '2025': [NUM2MONTH[m] for m in ('01','02','03')]
}

# Regex: producto – variación %
LINE_REGEX = re.compile(r"^(.+?)\s+(-?\d+[.,]\d+)$")

@st.cache_data(ttl=3600)
def load_data():
    """
    Descarga y parsea variaciones desde los PDFs de 2024 y 2025,
    devolviendo DataFrame con columnas: year, mes, producto, variacion.
    """
    registros = []
    for year, page_url in YEAR_PAGES.items():
        resp = requests.get(page_url); resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = {a['href'] for a in soup.select("a[href$='.pdf']")
                 if 'valor_cb' in a['href'].lower() or 'valor_cba' in a['href'].lower()}
        for href in sorted(links):
            pdf_url = urljoin(page_url, href)
            fname   = pdf_url.rsplit('/',1)[-1]
            mnum    = re.search(rf"{year[2:]}\.(\d{{2}})", fname)
            mes     = NUM2MONTH.get(mnum.group(1)) if mnum else None
            if mes not in MONTHS_BY_YEAR[year]:
                continue
            try:
                r2 = requests.get(pdf_url); r2.raise_for_status()
            except Exception:
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
                        # descartar totales y ruidos
                        if prod.lower() == 'cba': continue
                        if not re.search(r'[A-Za-zÁÉÍÓÚáéíóúÑñ]', prod): continue
                        if abs(val) > 100: continue
                        registros.append({'year': year, 'mes': mes, 'producto': prod, 'variacion': val})
    if not registros:
        return pd.DataFrame(columns=['year','mes','producto','variacion'])
    df = pd.DataFrame(registros)
    # eliminar duplicados exactos
    return df.drop_duplicates(subset=['year','mes','producto'])

# ========= STREAMLIT APP =========
st.set_page_config(page_title="Monitor Canasta Básica", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica")

with st.spinner("🔄 Descargando y procesando…"):
    df = load_data()

if df.empty:
    st.error("⚠️ No se encontraron datos. Verifica la conexión o la fuente.")
    st.stop()

# --- FILTRAR TOP 20 PRODUCTOS POR RELEVANCIA ---
# relevancia = variación absoluta promedio
top20 = (
    df.assign(absvar=df['variacion'].abs())
      .groupby('producto')['absvar']
      .mean()
      .nlargest(20)
      .index
)
df = df[df['producto'].isin(top20)]

st.success(f"✅ Cargados {len(df)} registros. Mostrando top 20 productos.")

# --- SIDEBAR: FILTROS ---
st.sidebar.header("Filtros")
years = sorted(df['year'].unique())
year_sel = st.sidebar.multiselect("Año", years, default=years)

months_avail = sorted(
    df[df['year'].isin(year_sel)]['mes'].unique(),
    key=lambda m: list(NUM2MONTH.values()).index(m)
)
month_sel = st.sidebar.multiselect("Mes", months_avail, default=months_avail)

products = sorted(df['producto'].unique())
prod_sel = st.sidebar.multiselect("Producto", products, default=products)

# --- APLICAR FILTROS ---
df_f = df[
    df['year'].isin(year_sel) &
    df['mes'].isin(month_sel) &
    df['producto'].isin(prod_sel)
].copy()

# construir y ordenar periodo
order_periodos = [f"{y} {m}" for y in years for m in MONTHS_BY_YEAR[y]
                  if y in year_sel and m in month_sel]
df_f['periodo'] = df_f['year'].astype(str) + ' ' + df_f['mes']
df_f['periodo'] = pd.Categorical(df_f['periodo'], categories=order_periodos, ordered=True)

# --- GRÁFICO 1: Variación Mensual (líneas) ---
st.subheader("Variación Porcentual Mensual por Producto")
monthly_pivot = (
    df_f.pivot_table(index='periodo', columns='producto', values='variacion', aggfunc='mean')
        .loc[order_periodos]
)
st.line_chart(monthly_pivot)

# --- INTERPRETACIONES ---
st.subheader("📝 Interpretaciones y Conclusiones")
avg_var = df_f['variacion'].mean()
st.markdown(f"- Variación porcentual promedio: **{avg_var:.2f}%**.")
row_max = df_f.loc[df_f['variacion'].idxmax()]
st.markdown(
    f"- **Mayor alza**: _{row_max['producto']}_ con +{row_max['variacion']:.2f}% en {row_max['periodo']}."
)
row_min = df_f.loc[df_f['variacion'].idxmin()]
st.markdown(
    f"- **Mayor baja**: _{row_min['producto']}_ con {row_min['variacion']:.2f}% en {row_min['periodo']}."
)

# --- GRÁFICO 2: Variación Anual Promedio (tabla) ---
st.subheader("Resumen Anual de Variación Porcentual")
res_anual = df_f.groupby('year')['variacion'].mean().rename('Var.% Media')
st.table(res_anual)

# --- TABLA DETALLADA ---
st.subheader("Datos Detallados")
st.dataframe(
    df_f[['year','mes','producto','variacion']]
      .sort_values(['year','mes','producto'])
      .reset_index(drop=True),
    use_container_width=True
)
