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
def load_variaciones():
    # 1) Descarga en memoria los PDFs
    pdf_list = []
    for year, url in YEARS.items():
        r = requests.get(url); r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            txt  = a.get_text().lower()
            if href.lower().endswith('.pdf') and year in (href + txt):
                full_url = requests.compat.urljoin(url, href)
                r2 = requests.get(full_url); r2.raise_for_status()
                fname = full_url.split('/')[-1]
                pdf_list.append((fname, BytesIO(r2.content)))

    # 2) Parser sin gating por «Anexo»
    def parse_variaciones(fname, stream):
        rows = []
        regex = re.compile(r"^(.+?)\s+(-?\d+[.,]?\d*)$")
        # extraer abreviatura de mes
        m = re.search(r'_(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)_', fname.lower())
        mes_full = MES_MAP.get(m.group(1), None) if m else None
        if not mes_full:
            return pd.DataFrame()

        with pdfplumber.open(stream) as pdf:
            for i, page in enumerate(pdf.pages):
                if i < SKIP_PAGES:
                    continue
                texto = page.extract_text() or ''
                for line in texto.split('\n'):
                    match = regex.match(line.strip())
                    if match:
                        prod = match.group(1).strip()
                        val  = float(match.group(2).replace(',', '.'))
                        rows.append({
                            'producto':  prod,
                            'variacion': val,
                            'mes':       mes_full
                        })
        return pd.DataFrame(rows)

    # 3) Aplicar a todos los PDFs
    dfs = [parse_variaciones(fn, st) for fn, st in pdf_list]
    valid = [df for df in dfs if not df.empty]
    if not valid:
        return pd.DataFrame(columns=['producto','variacion','mes'])
    return pd.concat(valid, ignore_index=True)

# ========= STREAMLIT APP =========
st.set_page_config(page_title="Monitor Canasta Básica", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica de Alimentos")

df = load_variaciones()
if df.empty:
    st.error("No se pudieron cargar datos. Verifica la conexión o la fuente.")
    st.stop()

# Sidebar
st.sidebar.header("Filtros")
productos = sorted(df['producto'].unique())
sel = st.sidebar.multiselect("Selecciona productos", productos, default=productos)
df_sel = df[df['producto'].isin(sel)].copy()

# Orden cronológico de meses
df_sel['mes'] = pd.Categorical(df_sel['mes'], categories=MESES_ORDEN, ordered=True)

# Pivot con agregación
chart_data = (
    df_sel
    .pivot_table(index='mes', columns='producto', values='variacion', aggfunc='mean')
    .reindex(index=MESES_ORDEN)
)

st.subheader("Variación Mensual por Producto")
st.line_chart(chart_data)

st.subheader("Datos Detallados")
st.dataframe(df_sel.reset_index(drop=True), use_container_width=True)
