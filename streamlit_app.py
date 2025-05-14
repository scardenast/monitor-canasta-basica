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

# Mapa abreviatura → nombre completo de mes
MES_MAP = {
    'ene': 'Enero', 'feb': 'Febrero', 'mar': 'Marzo', 'abr': 'Abril',
    'may': 'Mayo', 'jun': 'Junio', 'jul': 'Julio', 'ago': 'Agosto',
    'sep': 'Septiembre', 'oct': 'Octubre', 'nov': 'Noviembre', 'dic': 'Diciembre'
}
MESES_ORDEN = list(MES_MAP.values())

# ========= FUNCIONES DE PARSEO =========
@st.cache_data(ttl=3600)
def load_variaciones():
    """
    Descarga en memoria todos los PDFs de 2024 y 2025,
    extrae las variaciones de productos de 'Anexo 2' y
    devuelve un DataFrame con columnas: producto, variacion, mes.
    """
    pdf_files = []
    for year, url in YEARS.items():
        resp = requests.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text().lower()
            if href.lower().endswith('.pdf') and year in (href + text):
                pdf_url = requests.compat.urljoin(url, href)
                r2 = requests.get(pdf_url); r2.raise_for_status()
                fname = pdf_url.rsplit('/', 1)[-1]
                pdf_files.append((fname, BytesIO(r2.content)))

    def extract_variations(filename, stream):
        """
        Lee el PDF en stream, omite SKIP_PAGES páginas introductorias,
        busca la sección 'Anexo 2' y extrae líneas de 'Producto <variación>'.
        """
        rows = []
        pat = re.compile(r"^(.+?)\s+(-?\d+[.,]?\d*)$")
        mes_abbr = ''
        m = re.search(r'_(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)_', filename.lower())
        if m:
            mes_abbr = m.group(1)
        mes_full = MES_MAP.get(mes_abbr, mes_abbr.title())

        with pdfplumber.open(stream) as pdf:
            in_table = False
            for idx, page in enumerate(pdf.pages):
                if idx < SKIP_PAGES:
                    continue
                text = page.extract_text() or ''
                for line in text.split('\n'):
                    if 'anexo 2' in line.lower():
                        in_table = True
                        continue
                    if not in_table:
                        continue
                    m2 = pat.match(line.strip())
                    if m2:
                        prod = m2.group(1).strip()
                        val  = float(m2.group(2).replace(',', '.'))
                        rows.append({'producto': prod, 'variacion': val, 'mes': mes_full})
        return pd.DataFrame(rows)

    # Parsear todos los PDFs en memoria
    dfs = [extract_variations(fn, st) for fn, st in pdf_files]
    if not dfs:
        return pd.DataFrame(columns=['producto','variacion','mes'])
    df = pd.concat(dfs, ignore_index=True)
    return df

# ========= STREAMLIT APP =========
st.set_page_config(page_title="Monitor Canasta Básica", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica de Alimentos")

# Carga datos
df = load_variaciones()
if df.empty:
    st.error("⚠️ No se pudo cargar ninguna variación. Verifica la conexión o la fuente.")
    st.stop()

# Sidebar: selección de productos
st.sidebar.header("Filtros")
productos_todos = sorted(df['producto'].unique())
selected = st.sidebar.multiselect("Selecciona productos", productos_todos, default=productos_todos)
df_sel = df[df['producto'].isin(selected)].copy()

# Asegurar orden cronológico de meses
df_sel['mes'] = pd.Categorical(df_sel['mes'], categories=MESES_ORDEN, ordered=True)

# Construir tabla pivot con agregación para duplicados
chart_data = (
    df_sel
    .pivot_table(index='mes', columns='producto', values='variacion', aggfunc='mean')
    .reindex(index=MESES_ORDEN)
)

# Mostrar gráfico interactivo
st.subheader("Variación Mensual por Producto")
st.line_chart(chart_data)

# Mostrar datos detallados
st.subheader("Datos Detallados")
st.dataframe(df_sel.reset_index(drop=True), use_container_width=True)
