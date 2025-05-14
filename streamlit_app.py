import streamlit as st
import pandas as pd
import pdfplumber
import requests
from bs4 import BeautifulSoup
import re
from io import BytesIO

# ========= CONFIGURACIÓN =========
YEARS = {
    '2024': 'https://observatorio.ministeriodesarrollosocial.gob.cl/nueva-serie-cba-2024',
    '2025': 'https://observatorio.ministeriodesarrollosocial.gob.cl/nueva-serie-cba-2025',
}
SKIP_PAGES = 1  # páginas introductorias a omitir

# Mapa abreviatura → nombre completo de mes
MES_MAP = {
    'ene': 'Enero', 'feb': 'Febrero', 'mar': 'Marzo', 'abr': 'Abril',
    'may': 'Mayo', 'jun': 'Junio', 'jul': 'Julio', 'ago': 'Agosto',
    'sep': 'Septiembre', 'oct': 'Octubre', 'nov': 'Noviembre', 'dic': 'Diciembre'
}

# Orden cronológico de los meses
MESES_ORDEN = list(MES_MAP.values())


@st.cache_data(ttl=3600)
def load_data():
    """Descarga y parsea los PDFs de 2024 y 2025 en memoria."""
    pdf_files = []
    for year, url in YEARS.items():
        resp = requests.get(url); resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text().lower()
            if href.lower().endswith('.pdf') and year in (href + text):
                full_url = requests.compat.urljoin(url, href)
                r2 = requests.get(full_url); r2.raise_for_status()
                fname = full_url.split('/')[-1]
                pdf_files.append((fname, BytesIO(r2.content)))

    def extract_variations(filename, pdf_stream):
        """Extrae variaciones de Anexo 2 de un PDF dado."""
        records = []
        in_table = False
        pat = re.compile(r"^(.+?)\s+(-?\d+[.,]?\d*)$")
        m = re.search(r'_(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)_', filename.lower())
        mes_abbr = m.group(1) if m else ''
        with pdfplumber.open(pdf_stream) as pdf:
            for i, page in enumerate(pdf.pages):
                if i < SKIP_PAGES:
                    continue
                text = page.extract_text() or ''
                for line in text.split('\n'):
                    if 'Anexo 2' in line:
                        in_table = True
                        continue
                    if not in_table:
                        continue
                    m2 = pat.match(line.strip())
                    if m2:
                        prod = m2.group(1).strip()
                        val  = float(m2.group(2).replace(',', '.'))
                        records.append({
                            'producto':  prod,
                            'variacion': val,
                            'mes':       mes_abbr
                        })
        return pd.DataFrame(records)

    # Parsear todos los PDFs
    dfs = [extract_variations(fname, stream) for fname, stream in pdf_files]
    if not dfs:
        return pd.DataFrame(columns=['producto','variacion','mes'])
    df = pd.concat(dfs, ignore_index=True)
    # Mapear abreviaturas a nombres completos
    df['mes'] = df['mes'].map(MES_MAP).fillna(df['mes'].str.title())
    return df


# ========= STREAMLIT UI =========
st.set_page_config(page_title="Monitor Canasta Básica", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica de Alimentos")

df = load_data()
if df.empty:
    st.error("No se pudieron cargar datos. Revisa tu conexión o la fuente.")
    st.stop()

# Filtros de producto
st.sidebar.header("Filtros")
productos = st.sidebar.multiselect(
    "Selecciona productos",
    options=sorted(df['producto'].unique()),
    default=sorted(df['producto'].unique())
)
df_sel = df[df['producto'].isin(productos)].copy()

# Asegurar orden cronológico de meses
df_sel['mes'] = pd.Categorical(df_sel['mes'], categories=MESES_ORDEN, ordered=True)

# Pivot con agregación para evitar duplicados
chart_data = df_sel.pivot_table(
    index='mes',
    columns='producto',
    values='variacion',
    aggfunc='mean'
).reindex(index=MESES_ORDEN)

# Mostrar gráfico
st.subheader("Variación Mensual por Producto")
st.line_chart(chart_data)

# Mostrar tabla de datos
st.subheader("Datos Detallados")
st.dataframe(df_sel.reset_index(drop=True), use_container_width=True)
