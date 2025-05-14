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
SKIP_PAGES = 4  # omitimos las 4 páginas introductorias

# Mapeo de mes numérico (sufijo 25.MM) → nombre completo
NUM2MONTH = {
    '01': 'Enero', '02': 'Febrero', '03': 'Marzo',
    '04': 'Abril', '05': 'Mayo',    '06': 'Junio',
    '07': 'Julio', '08': 'Agosto',  '09': 'Septiembre',
    '10': 'Octubre','11': 'Noviembre','12': 'Diciembre'
}
# Los únicos meses disponibles para comparar
MESES_DISPONIBLES = ['Enero','Febrero','Marzo']

# Regex para capturar líneas válidas
LINE_REGEX = re.compile(r"^([A-Za-zÁÉÍÓÚáéíóúÑñüÜ\s\-/\(\)]+?)\s+(-?\d+[.,]?\d+)$")

# ========= PARSER EN MEMORIA =========
@st.cache_data(ttl=3600)
def load_variaciones():
    registros = []

    for year, page_url in YEARS.items():
        resp = requests.get(page_url); resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        hrefs = {
            a['href'] for a in soup.select("a[href$='.pdf']")
            if 'valor_cb' in a['href'].lower() or 'valor_cba' in a['href'].lower()
        }

        for href in sorted(hrefs):
            pdf_url = urljoin(page_url, href)
            filename = pdf_url.rsplit('/', 1)[-1]

            # Extraer mes del filename con patrón 25.MM
            mnum = re.search(r'25\.(\d{2})', filename)
            mes = NUM2MONTH.get(mnum.group(1)) if mnum else None
            if mes not in MESES_DISPONIBLES:
                continue

            try:
                r2 = requests.get(pdf_url); r2.raise_for_status()
            except Exception:
                continue

            stream = BytesIO(r2.content)
            with pdfplumber.open(stream) as pdf:
                for idx, page in enumerate(pdf.pages):
                    if idx < SKIP_PAGES:
                        continue
                    text = page.extract_text() or ''
                    for line in text.split('\n'):
                        m = LINE_REGEX.match(line.strip())
                        if not m:
                            continue
                        producto = m.group(1).strip()
                        valor    = float(m.group(2).replace(',', '.'))
                        # filtrar encabezados y ruidos
                        if producto.lower() in [x.lower() for x in MESES_DISPONIBLES]:
                            continue
                        if abs(valor) > 100:
                            continue
                        registros.append({
                            'producto':  producto,
                            'variacion': valor,
                            'mes':       mes
                        })

    if not registros:
        return pd.DataFrame(columns=['producto','variacion','mes'])
    return pd.DataFrame(registros)

# ========= STREAMLIT APP =========
st.set_page_config(page_title="Monitor CBA Ene–Mar 2025", layout="wide")
st.title("📊 Monitor Variaciones Canasta Básica (Ene–Mar 2025)")

with st.spinner("🔄 Descargando y procesando datos…"):
    df = load_variaciones()

if df.empty:
    st.error("⚠️ No se encontraron variaciones. Verifica la conexión o las URLs.")
    st.stop()

st.success(f"✅ {len(df)} registros cargados.")

# ---- Sidebar: filtros dinámicos ----
st.sidebar.header("Filtros")

# 1) Filtro de meses
meses_sel = st.sidebar.multiselect(
    "Selecciona meses",
    options=MESES_DISPONIBLES,
    default=MESES_DISPONIBLES
)

# 2) Filtro de productos
prod_list = sorted(df['producto'].unique())
prod_sel  = st.sidebar.multiselect(
    "Selecciona productos",
    options=prod_list,
    default=prod_list
)

# Aplicar filtros
df_filtrado = df[
    df['mes'].isin(meses_sel) &
    df['producto'].isin(prod_sel)
].copy()

# Asegurar orden cronológico seleccionado
df_filtrado['mes'] = pd.Categorical(
    df_filtrado['mes'],
    categories=[m for m in MESES_DISPONIBLES if m in meses_sel],
    ordered=True
)

# ---- Generar gráfico ----
chart_data = (
    df_filtrado
      .pivot_table(index='mes', columns='producto', values='variacion', aggfunc='mean')
      .reindex(index=[m for m in MESES_DISPONIBLES if m in meses_sel])
)

st.subheader("Variación Mensual por Producto")
st.line_chart(chart_data)

# ---- Mostrar tabla ----
st.subheader("Datos Detallados")
st.dataframe(df_filtrado.reset_index(drop=True), use_container_width=True)
