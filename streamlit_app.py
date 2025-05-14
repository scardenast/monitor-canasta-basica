import streamlit as st
import pandas as pd
import pdfplumber
import requests
import re
from io import BytesIO
from bs4 import BeautifulSoup

# ========= CONFIGURACIÓN =========
YEARS = {
    '2024': 'https://observatorio.ministeriodesarrollosocial.gob.cl/nueva-serie-cba-2024',
    '2025': 'https://observatorio.ministeriodesarrollosocial.gob.cl/nueva-serie-cba-2025',
}
SKIP_PAGES = 1  # páginas introductorias a omitir

MES_MAP = {
    'ene': 'Enero','feb': 'Febrero','mar': 'Marzo','abr': 'Abril',
    'may': 'Mayo','jun': 'Junio','jul': 'Julio','ago': 'Agosto',
    'sep': 'Septiembre','oct': 'Octubre','nov': 'Noviembre','dic': 'Diciembre'
}
MESES_ORDEN = list(MES_MAP.values())

# ========= PARSER EN MEMORIA =========
@st.cache_data(ttl=3600)
def load_variaciones():
    """Descarga los PDFs de los años configurados y extrae todas las variaciones."""
    pdf_list = []
    # 1) Recopilar todos los PDFs en memoria
    for year, url in YEARS.items():
        resp = requests.get(url); resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text().lower()
            if href.lower().endswith('.pdf') and year in (href.lower() + text):
                pdf_url = requests.compat.urljoin(url, href)
                r2 = requests.get(pdf_url); r2.raise_for_status()
                filename = pdf_url.rsplit('/', 1)[-1]
                pdf_list.append((filename, r2.content))

    # 2) Extraer variaciones con regex
    pattern = re.compile(r"^(.+?)\s+(-?\d+[.,]?\d*)$")
    dfs = []
    for filename, raw_bytes in pdf_list:
        # Determinar mes a partir del nombre de archivo
        m = re.search(r'_(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)_', filename.lower())
        mes_full = MES_MAP.get(m.group(1), None) if m else None
        if not mes_full:
            continue

        stream = BytesIO(raw_bytes)
        records = []
        with pdfplumber.open(stream) as pdf:
            for i, page in enumerate(pdf.pages):
                if i < SKIP_PAGES:
                    continue
                text = page.extract_text() or ''
                for line in text.split('\n'):
                    match = pattern.match(line.strip())
                    if match:
                        prod = match.group(1).strip()
                        val  = float(match.group(2).replace(',', '.'))
                        records.append({
                            'producto':  prod,
                            'variacion': val,
                            'mes':       mes_full
                        })
        if records:
            dfs.append(pd.DataFrame(records))

    # 3) Concatenar todos los DataFrames
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        # Si quedó vacío, devolvemos columnas para evitar errores de lectura
        return pd.DataFrame(columns=['producto','variacion','mes'])


# ========= STREAMLIT APP =========
st.set_page_config(page_title="Monitor Canasta Básica", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica de Alimentos")

df = load_variaciones()
if df.empty:
    st.error("⚠️ No se encontraron variaciones. Revisa la conexión o los PDFs.")
    st.stop()

# Sidebar: filtro de productos
st.sidebar.header("Filtros")
todos = sorted(df['producto'].unique())
seleccion = st.sidebar.multiselect("Selecciona productos", todos, default=todos)
df_sel = df[df['producto'].isin(seleccion)].copy()

# Asegurar orden cronológico de meses
df_sel['mes'] = pd.Categorical(df_sel['mes'], categories=MESES_ORDEN, ordered=True)

# Construir tabla pivot con media para manejar duplicados
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
