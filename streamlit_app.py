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
SKIP_PAGES = 1  # páginas introductorias a omitir

# Map abreviatura → nombre completo
MES_MAP = {
    'ene': 'Enero', 'feb': 'Febrero', 'mar': 'Marzo',
    'abr': 'Abril','may': 'Mayo',    'jun': 'Junio',
    'jul': 'Julio','ago': 'Agosto',  'sep': 'Septiembre',
    'oct': 'Octubre','nov': 'Noviembre','dic': 'Diciembre'
}
# Mapa numérico de mes (del sufijo 25.MM) → abreviatura
NUM2ABBR = {
    '01':'ene','02':'feb','03':'mar','04':'abr',
    '05':'may','06':'jun','07':'jul','08':'ago',
    '09':'sep','10':'oct','11':'nov','12':'dic'
}
MESES_ORDEN = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
               'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

# ========= PARSER EN MEMORIA =========
@st.cache_data(ttl=3600)
def load_variaciones():
    # regex para líneas tipo "Producto   1,23"
    line_pat = re.compile(r"^(.+?)\s+(-?\d+[.,]?\d*)$")
    rows = []

    for year, url in YEARS.items():
        resp = requests.get(url); resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        # extraer todos los PDFs de 'valor_cb' o 'Valor_CBA'
        links = [
            a['href'] for a in soup.select("a[href$='.pdf']")
            if 'valor_cb' in a['href'].lower() or 'valor_cba' in a['href'].lower()
        ]
        for href in sorted(set(links)):
            full_url = requests.compat.urljoin(url, href)
            fname = full_url.rsplit('/',1)[-1]

            # detectar mes numérico del patrón "...25.MM.pdf"
            mnum = re.search(r'25\.(\d{2})', fname)
            mes_abbr = NUM2ABBR.get(mnum.group(1)) if mnum else None
            mes_full = MES_MAP.get(mes_abbr)
            if not mes_full:
                continue

            # descargar en memoria
            r2 = requests.get(full_url); r2.raise_for_status()
            stream = BytesIO(r2.content)

            # parsear
            with pdfplumber.open(stream) as pdf:
                for i, page in enumerate(pdf.pages):
                    if i < SKIP_PAGES:
                        continue
                    text = page.extract_text() or ''
                    for line in text.split('\n'):
                        m = line_pat.match(line.strip())
                        if m:
                            prod = m.group(1).strip()
                            val  = float(m.group(2).replace(',', '.'))
                            rows.append({
                                'producto':  prod,
                                'variacion': val,
                                'mes':       mes_full
                            })

    if not rows:
        return pd.DataFrame(columns=['producto','variacion','mes'])
    return pd.DataFrame(rows)

# ========= STREAMLIT APP =========
st.set_page_config(page_title="Monitor Canasta Básica", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica de Alimentos")

df = load_variaciones()
if df.empty:
    st.error("⚠️ No se encontraron variaciones. Revisa la conexión o las URLs.")
    st.stop()

# Sidebar: filtros
st.sidebar.header("Filtros")
todos = sorted(df['producto'].unique())
sel = st.sidebar.multiselect("Selecciona productos", todos, default=todos)
df_sel = df[df['producto'].isin(sel)].copy()

# Orden cronológico de meses
df_sel['mes'] = pd.Categorical(df_sel['mes'], categories=MESES_ORDEN, ordered=True)

# Pivot para gráfico
chart_data = (
    df_sel
      .pivot_table(index='mes', columns='producto', values='variacion', aggfunc='mean')
      .reindex(index=MESES_ORDEN)
)

st.subheader("Variación Mensual por Producto")
st.line_chart(chart_data)

st.subheader("Datos Detallados")
st.dataframe(df_sel.reset_index(drop=True), use_container_width=True)
