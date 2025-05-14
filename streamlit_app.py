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
    '01': 'Enero','02': 'Febrero','03': 'Marzo',
    '04': 'Abril','05': 'Mayo','06': 'Junio',
    '07': 'Julio','08': 'Agosto','09': 'Septiembre',
    '10': 'Octubre','11': 'Noviembre','12': 'Diciembre'
}
# Meses completos para 2024 (1–12) y 2025 (1–3)
MONTHS_BY_YEAR = {
    '2024': list(NUM2MONTH.values()),
    '2025': [NUM2MONTH[m] for m in ['01','02','03']]
}

LINE_REGEX = re.compile(r"^([A-Za-zÁÉÍÓÚáéíóúÑñüÜ\s\-/\(\)]+?)\s+(-?\d+[.,]\d+)$")

@st.cache_data(ttl=3600)
def load_data():
    rows = []
    for year, page_url in YEAR_PAGES.items():
        resp = requests.get(page_url); resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        hrefs = {
            a['href'] for a in soup.select("a[href$='.pdf']")
            if 'valor_cb' in a['href'].lower() or 'valor_cba' in a['href'].lower()
        }
        for href in sorted(hrefs):
            pdf_url = urljoin(page_url, href)
            fname = pdf_url.rsplit('/',1)[-1]
            mnum = re.search(rf'{year[2:]}\.(\d{{2}})', fname)
            mes = NUM2MONTH.get(mnum.group(1)) if mnum else None
            if mes not in MONTHS_BY_YEAR[year]:
                continue

            # descarga
            try:
                r2 = requests.get(pdf_url); r2.raise_for_status()
            except:
                continue
            stream = BytesIO(r2.content)

            # parse
            with pdfplumber.open(stream) as pdf:
                for i, page in enumerate(pdf.pages):
                    if i < SKIP_PAGES: continue
                    for line in (page.extract_text() or '').split('\n'):
                        m = LINE_REGEX.match(line.strip())
                        if not m: continue
                        prod = m.group(1).strip()
                        val  = float(m.group(2).replace(',', '.'))
                        # filtrar ruidos
                        if prod.lower() in [mes.lower() for mes in MONTHS_BY_YEAR[year]]: continue
                        if abs(val) > 100: continue
                        rows.append({'year': year, 'mes': mes, 'producto': prod, 'variacion': val})

    if not rows:
        return pd.DataFrame(columns=['year','mes','producto','variacion'])
    return pd.DataFrame(rows)

# ========= STREAMLIT =========
st.set_page_config(page_title="Monitor CBA", layout="wide")
st.title("📊 Monitor Variaciones Canasta Básica")

df = load_data()
if df.empty:
    st.error("No hay datos. Verifica la conexión o la fuente.")
    st.stop()

# --- SIDEBAR FILTROS ---
st.sidebar.header("Filtros")

# Año
years = sorted(df['year'].unique())
year_sel = st.sidebar.multiselect("Año", years, default=years)

# Mes (dinámico según año seleccionado)
available_months = sorted(df[df['year'].isin(year_sel)]['mes'].unique(),
                          key=lambda m: list(NUM2MONTH.values()).index(m))
month_sel = st.sidebar.multiselect("Mes", available_months,
                                    default=available_months)

# Producto
products = sorted(df['producto'].unique())
prod_sel = st.sidebar.multiselect("Producto", products, default=products)

# --- FILTRAR DF ---
df_f = df[
    df['year'].isin(year_sel) &
    df['mes'].isin(month_sel) &
    df['producto'].isin(prod_sel)
].copy()

# Orden cronológico
df_f['mes'] = pd.Categorical(df_f['mes'], categories=MONTHS_BY_YEAR[year_sel[0]], ordered=True)

# --- GRÁFICO ---
chart = (
    df_f
    .pivot_table(index='mes', columns='producto', values='variacion', aggfunc='mean')
    .loc[month_sel]
)
st.subheader("Variación Mensual por Producto")
st.line_chart(chart)

# --- TABLA ---
st.subheader("Datos Detallados")
st.dataframe(df_f.reset_index(drop=True), use_container_width=True)
