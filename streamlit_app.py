import streamlit as st
import pandas as pd
import pdfplumber
import requests
import re
from bs4 import BeautifulSoup
from io import BytesIO

# ========= CONFIGURACIÓN =========
YEARS = {
    '2024': 'https://observatorio.ministeriodesarrollosocial.gob.cl/nueva-serie-cba-2024',
    '2025': 'https://observatorio.ministeriodesarrollosocial.gob.cl/nueva-serie-cba-2025',
}
SKIP_PAGES = 1

MES_MAP = {
    'ene':'Enero','feb':'Febrero','mar':'Marzo','abr':'Abril',
    'may':'Mayo','jun':'Junio','jul':'Julio','ago':'Agosto',
    'sep':'Septiembre','oct':'Octubre','nov':'Noviembre','dic':'Diciembre'
}
MESES_ORDEN = list(MES_MAP.values())

@st.cache_data(ttl=3600)
def load_data():
    pdf_files = []
    # Descargar todos los PDFs de los dos años
    for year, url in YEARS.items():
        r = requests.get(url); r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            href, txt = a['href'], a.get_text().lower()
            if href.lower().endswith('.pdf') and year in (href + txt):
                pdf_url = requests.compat.urljoin(url, href)
                resp = requests.get(pdf_url); resp.raise_for_status()
                fname = pdf_url.split('/')[-1]
                pdf_files.append((fname, BytesIO(resp.content)))

    def extract_variations(filename, stream):
        recs, in_table = [], False
        pat = re.compile(r"^(.+?)\s+(-?\d+[.,]?\d*)$")
        abbr = re.search(r'_(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)_', filename.lower())
        mes_full = MES_MAP.get(abbr.group(1), '') if abbr else ''
        with pdfplumber.open(stream) as pdf:
            for i, page in enumerate(pdf.pages):
                if i < SKIP_PAGES: continue
                for line in (page.extract_text() or '').split('\n'):
                    if 'anexo 2' in line.lower():
                        in_table = True
                        continue
                    if not in_table:
                        continue
                    m2 = pat.match(line.strip())
                    if m2:
                        recs.append({
                            'producto':  m2.group(1).strip(),
                            'variacion': float(m2.group(2).replace(',', '.')),
                            'mes':       mes_full
                        })
        return pd.DataFrame(recs)

    dfs = [extract_variations(n, s) for n,s in pdf_files]
    if not dfs:
        return pd.DataFrame(columns=['producto','variacion','mes'])
    df = pd.concat(dfs, ignore_index=True)
    return df

# ========== UI ==========

st.set_page_config(page_title="Monitor Canasta Básica", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica de Alimentos")

df = load_data()
if df.empty:
    st.error("No se cargaron datos. Revisa la fuente.")
    st.stop()

# Filtros
st.sidebar.header("Filtros")
productos = st.sidebar.multiselect(
    "Productos",
    options=sorted(df['producto'].unique()),
    default=sorted(df['producto'].unique())
)
df_sel = df[df['producto'].isin(productos)].copy()
df_sel['mes'] = pd.Categorical(df_sel['mes'], categories=MESES_ORDEN, ordered=True)

# Gráfico
chart_data = df_sel.pivot_table(
    index='mes', columns='producto', values='variacion', aggfunc='mean'
).reindex(index=MESES_ORDEN)
st.subheader("Variación Mensual por Producto")
st.line_chart(chart_data)

# Tabla
st.subheader("Datos Detallados")
st.dataframe(df_sel.reset_index(drop=True), use_container_width=True)
