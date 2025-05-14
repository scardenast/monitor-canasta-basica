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
SKIP_PAGES = 1  # Cuántas páginas intro omitir
# Mapa abreviatura → mes completo
MES_MAP = {
    'ene': 'Enero', 'feb': 'Febrero', 'mar': 'Marzo', 'abr': 'Abril',
    'may': 'Mayo', 'jun': 'Junio', 'jul': 'Julio', 'ago': 'Agosto',
    'sep': 'Septiembre', 'oct': 'Octubre', 'nov': 'Noviembre', 'dic': 'Diciembre'
}
MESES_ORDEN = list(MES_MAP.values())

# ========= FUNCIÓN DE CARGA Y PARSEO =========
@st.cache_data(ttl=3600)
def load_variaciones():
    """Descarga los PDFs de 2024 y 2025, extrae Anexo 2 y devuelve un DataFrame."""
    # 1) Encontrar y descargar PDFs en memoria
    pdf_list = []
    for year, url in YEARS.items():
        resp = requests.get(url); resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text().lower()
            if href.lower().endswith('.pdf') and year in (href.lower() + text):
                pdf_url = requests.compat.urljoin(url, href)
                r2 = requests.get(pdf_url); r2.raise_for_status()
                filename = pdf_url.split('/')[-1]
                pdf_list.append((filename, BytesIO(r2.content)))

    # 2) Parser de variaciones de "Anexo 2"
    def parse_anexo2(filename, pdf_stream):
        rows = []
        regex = re.compile(r"^(.+?)\s+(-?\d+[.,]?\d*)$")
        # Extraer abreviatura de mes del nombre de archivo
        m = re.search(r'_(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)_', filename.lower())
        mes_full = MES_MAP.get(m.group(1), None) if m else None

        with pdfplumber.open(pdf_stream) as pdf:
            in_table = False
            for i, page in enumerate(pdf.pages):
                if i < SKIP_PAGES:
                    continue
                text = page.extract_text() or ''
                for line in text.split('\n'):
                    if 'anexo 2' in line.lower():
                        in_table = True
                        continue
                    if not in_table:
                        continue
                    match = regex.match(line.strip())
                    if match and mes_full:
                        producto = match.group(1).strip()
                        valor    = float(match.group(2).replace(',', '.'))
                        rows.append({'producto': producto, 'variacion': valor, 'mes': mes_full})

        return pd.DataFrame(rows)

    # 3) Aplicar parser a cada PDF
    dfs = [parse_anexo2(fn, stream) for fn, stream in pdf_list]
    valid = [df for df in dfs if not df.empty]
    if not valid:
        return pd.DataFrame(columns=['producto', 'variacion', 'mes'])
    return pd.concat(valid, ignore_index=True)

# ========= STREAMLIT APP =========
st.set_page_config(page_title="Monitor Canasta Básica", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica de Alimentos")

df = load_variaciones()
if df.empty:
    st.error("No se pudieron cargar datos. Verifica la conexión o la fuente.")
    st.stop()

# Sidebar: filtro de productos
st.sidebar.header("Filtros")
productos = sorted(df['producto'].unique())
seleccion = st.sidebar.multiselect("Selecciona productos", productos, default=productos)
df_sel = df[df['producto'].isin(seleccion)].copy()

# Ordenar meses cronológicamente
df_sel['mes'] = pd.Categorical(df_sel['mes'], categories=MESES_ORDEN, ordered=True)

# Pivot con agregación para manejar duplicados
chart_data = (
    df_sel
    .pivot_table(index='mes', columns='producto', values='variacion', aggfunc='mean')
    .reindex(index=MESES_ORDEN)
)

# Gráfico
st.subheader("Variación Mensual por Producto")
st.line_chart(chart_data)

# Tabla de datos
st.subheader("Datos Detallados")
st.dataframe(df_sel.reset_index(drop=True), use_container_width=True)
