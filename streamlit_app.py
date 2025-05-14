import streamlit as st
import pandas as pd
import pdfplumber, requests, os, re
from bs4 import BeautifulSoup
from io import BytesIO

# --- Configuración ---
YEARS = {
    '2024': 'https://observatorio.ministeriodesarrollosocial.gob.cl/nueva-serie-cba-2024',
    '2025': 'https://observatorio.ministeriodesarrollosocial.gob.cl/nueva-serie-cba-2025',
}
SKIP_PAGES = 1
MONTHS = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']

@st.cache_data(ttl=3600)
def load_data():
    # 1) Descargar PDFs en memoria
    pdf_files = []
    for year, url in YEARS.items():
        r = requests.get(url); r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text().lower()
            if href.lower().endswith('.pdf') and year in (href+text):
                pdf_url = requests.compat.urljoin(url, href)
                resp = requests.get(pdf_url); resp.raise_for_status()
                pdf_files.append((os.path.basename(pdf_url), BytesIO(resp.content)))

    # 2) Funciones de extracción
    def extract_variations(pdf_stream):
        df = []
        pattern = re.compile(r'^(.+?)\s+(-?\d+[.,]?\d*)$')
        with pdfplumber.open(pdf_stream) as pdf:
            # detectar mes/año en nombre de archivo
            # asumimos nombre algo como VALOR_cb_<MES>_<YYYY>.pdf
            name = pdf_stream.name.lower()
            match_m = re.search(r'_(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)_', name)
            mes = match_m.group(1) if match_m else 'mes'
            for i, page in enumerate(pdf.pages):
                if i < SKIP_PAGES: continue
                for line in (page.extract_text() or '').split('\n'):
                    m = pattern.match(line.strip())
                    if m:
                        prod = m.group(1).strip()
                        val  = float(m.group(2).replace(',','.'))
                        df.append({'producto':prod,'variacion':val,'mes':mes})
        return pd.DataFrame(df)

    # 3) Parsear todos
    dfs = [extract_variations(stream) for _, stream in pdf_files]
    full = pd.concat(dfs, ignore_index=True)
    # Map mes abreviado a nombre completo
    mapa = {'ene':'Enero','feb':'Febrero','mar':'Marzo','abr':'Abril',
            'may':'Mayo','jun':'Junio','jul':'Julio','ago':'Agosto',
            'sep':'Septiembre','oct':'Octubre','nov':'Noviembre','dic':'Diciembre'}
    full['mes'] = full['mes'].map(mapa).fillna(full['mes'].str.title())
    return full

# --- App UI ---
st.title("Monitor Inteligente de la Canasta Básica (Streamlit)")
df = load_data()
st.sidebar.header("Productos")
productos = st.sidebar.multiselect("Elige productos", df['producto'].unique(), default=df['producto'].unique())
df_sel = df[df['producto'].isin(productos)]

# Gráfico
chart_data = df_sel.pivot(index='mes', columns='producto', values='variacion')
st.line_chart(chart_data)

# Tabla de datos
st.dataframe(df_sel)
