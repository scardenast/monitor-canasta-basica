import streamlit as st
import pandas as pd
import pdfplumber
import requests
import re
from io import BytesIO

# ========= CONFIGURACIÓN =========
DIRECT_PDF_URLS = [
    'https://observatorio.ministeriodesarrollosocial.gob.cl/storage/docs/cba/nueva_serie/2025/Valor_CBA_y_LPs_25.01.pdf',
    'https://observatorio.ministeriodesarrollosocial.gob.cl/storage/docs/cba/nueva_serie/2025/Valor_CBA_y_LPs_25.02.pdf',
    'https://observatorio.ministeriodesarrollosocial.gob.cl/storage/docs/cba/nueva_serie/2025/Valor_CBA_y_LPs_25.03.pdf',
]

SKIP_PAGES = 1  # cuántas páginas iniciales omitir

# Mapeo abreviatura → mes completo
MES_MAP = {
    'ene': 'Enero', 'feb': 'Febrero', 'mar': 'Marzo',
    'abr': 'Abril','may': 'Mayo','jun': 'Junio',
    'jul': 'Julio','ago': 'Agosto','sep': 'Septiembre',
    'oct': 'Octubre','nov': 'Noviembre','dic': 'Diciembre'
}
MESES_ORDEN = ['Enero','Febrero','Marzo']

# ========= PARSING EN MEMORIA =========
@st.cache_data(ttl=3600)
def load_variaciones():
    pattern = re.compile(r"^(.+?)\s+(-?\d+[.,]?\d*)$")
    records = []

    for pdf_url in DIRECT_PDF_URLS:
        # Determinar mes a partir del filename
        filename = pdf_url.rsplit('/', 1)[-1]
        m = re.search(r'_(\d{2})\.', filename)  # extrae .01., .02., .03.
        mes_abbr = None
        if m:
            num = m.group(1)
            mes_abbr = {'01':'ene','02':'feb','03':'mar'}.get(num)
        mes_full = MES_MAP.get(mes_abbr)
        if not mes_full:
            continue

        # Descargar PDF en memoria
        r = requests.get(pdf_url)
        r.raise_for_status()
        stream = BytesIO(r.content)

        # Parsear páginas
        with pdfplumber.open(stream) as pdf:
            for i, page in enumerate(pdf.pages):
                if i < SKIP_PAGES:
                    continue
                text = page.extract_text() or ''
                for line in text.split('\n'):
                    m2 = pattern.match(line.strip())
                    if m2:
                        prod = m2.group(1).strip()
                        val  = float(m2.group(2).replace(',', '.'))
                        records.append({
                            'producto':  prod,
                            'variacion': val,
                            'mes':       mes_full
                        })

    if not records:
        return pd.DataFrame(columns=['producto','variacion','mes'])
    return pd.DataFrame(records)


# ========= STREAMLIT UI =========
st.set_page_config(page_title="Monitor Canasta Básica 2025", layout="wide")
st.title("📊 Variaciones Canasta Básica Ene–Mar 2025")

df = load_variaciones()
if df.empty:
    st.error("⚠️ No se encontraron variaciones. Revisa las URLs o la conexión.")
    st.stop()

# Sidebar: filtro de productos
st.sidebar.header("Filtros")
productos = sorted(df['producto'].unique())
seleccion = st.sidebar.multiselect("Selecciona productos", productos, default=productos)
df_sel = df[df['producto'].isin(seleccion)].copy()

# Asegurar orden cronológico de los tres meses
df_sel['mes'] = pd.Categorical(df_sel['mes'], categories=MESES_ORDEN, ordered=True)

# Pivot para gráfico
chart_data = (
    df_sel
    .pivot_table(index='mes', columns='producto', values='variacion', aggfunc='mean')
    .reindex(index=MESES_ORDEN)
)

# Mostrar gráfico
st.subheader("Variación Mensual por Producto")
st.line_chart(chart_data)

# Mostrar tabla
st.subheader("Datos Detallados")
st.dataframe(df_sel.reset_index(drop=True), use_container_width=True)
