import streamlit as st
import pandas as pd
import pdfplumber
import requests
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from io import BytesIO

# ========= CONFIGURACIÓN =========
YEARS = {
    '2024': 'https://observatorio.ministeriodesarrollosocial.gob.cl/nueva-serie-cba-2024',
    '2025': 'https://observatorio.ministeriodesarrollosocial.gob.cl/nueva-serie-cba-2025',
}
SKIP_PAGES = 1  # páginas introductorias a omitir

MES_MAP = {
    'ene': 'Enero', 'feb': 'Febrero', 'mar': 'Marzo', 'abr': 'Abril',
    'may': 'Mayo', 'jun': 'Junio', 'jul': 'Julio', 'ago': 'Agosto',
    'sep': 'Septiembre', 'oct': 'Octubre', 'nov': 'Noviembre', 'dic': 'Diciembre'
}
MESES_ORDEN = list(MES_MAP.values())

# ========= PARSER EN MEMORIA =========
@st.cache_data(ttl=3600)
def load_variaciones():
    """Descarga y parsea los PDFs de la canasta básica."""
    regex_line = re.compile(r"^(.+?)\s+(-?\d+[.,]?\d*)$")
    dfs = []

    for year, base_url in YEARS.items():
        resp = requests.get(base_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Busca todos los enlaces que tengan 'valor_cb_' y terminen en .pdf
        links = [
            a['href'] for a in soup.find_all('a', href=True)
            if a['href'].lower().endswith('.pdf') and 'valor_cb_' in a['href'].lower()
        ]

        for href in set(links):
            pdf_url = urljoin(base_url, href)
            filename = pdf_url.rsplit('/', 1)[-1]
            m = re.search(r'_(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)_', filename.lower())
            mes_full = MES_MAP.get(m.group(1), None) if m else None
            if not mes_full:
                continue

            # Descargar PDF en memoria
            r2 = requests.get(pdf_url)
            r2.raise_for_status()
            stream = BytesIO(r2.content)

            # Abrir con pdfplumber y extraer líneas válidas
            with pdfplumber.open(stream) as pdf:
                for i, page in enumerate(pdf.pages):
                    if i < SKIP_PAGES:
                        continue
                    text = page.extract_text() or ''
                    for line in text.split('\n'):
                        match = regex_line.match(line.strip())
                        if match:
                            prod = match.group(1).strip()
                            val  = float(match.group(2).replace(',', '.'))
                            dfs.append({
                                'producto':  prod,
                                'variacion': val,
                                'mes':       mes_full
                            })

    if not dfs:
        return pd.DataFrame(columns=['producto','variacion','mes'])
    return pd.DataFrame(dfs)

# ========= STREAMLIT APP =========
st.set_page_config(page_title="Canasta Básica Monitor", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica de Alimentos")

df = load_variaciones()
if df.empty:
    st.error("⚠️ No se encontraron datos. Verifica la conexión o los PDFs en la web.")
    st.stop()

# Sidebar: filtro de productos
st.sidebar.header("Filtros")
todos = sorted(df['producto'].unique())
seleccion = st.sidebar.multiselect("Selecciona productos", todos, default=todos)
df_sel = df[df['producto'].isin(seleccion)].copy()

# Asegurar orden cronológico de meses
df_sel['mes'] = pd.Categorical(df_sel['mes'], categories=MESES_ORDEN, ordered=True)

# Pivot con media para manejar duplicados
chart_data = (
    df_sel
    .pivot_table(index='mes', columns='producto', values='variacion', aggfunc='mean')
    .reindex(index=MESES_ORDEN)
)

# Gráfico de líneas
st.subheader("Variación Mensual por Producto")
st.line_chart(chart_data)

# Tabla de datos
st.subheader("Datos Detallados")
st.dataframe(df_sel.reset_index(drop=True), use_container_width=True)
