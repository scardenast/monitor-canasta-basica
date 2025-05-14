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
SKIP_PAGES = 4  # Ahora omitimos las 4 primeras páginas introductorias

# Mapeo de mes numérico (sufijo 25.MM) → nombre completo
NUM2MONTH = {
    '01': 'Enero','02': 'Febrero','03': 'Marzo',
    '04': 'Abril','05': 'Mayo','06': 'Junio',
    '07': 'Julio','08': 'Agosto','09': 'Septiembre',
    '10': 'Octubre','11': 'Noviembre','12': 'Diciembre'
}
MESES_ORDEN = ['Enero','Febrero','Marzo']  # solo estos meses

# Regex para líneas "Producto   -1,2"
LINE_REGEX = re.compile(r"^([A-Za-zÁÉÍÓÚáéíóúÑñüÜ\s\-/\(\)]+?)\s+(-?\d+[.,]\d+)$")

# ========= PARSER EN MEMORIA =========
@st.cache_data(ttl=3600)
def load_variaciones():
    registros = []

    for year, page_url in YEARS.items():
        resp = requests.get(page_url); resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Coleccionar enlaces a PDFs de CBA
        hrefs = {
            a['href'] for a in soup.select("a[href$='.pdf']")
            if 'valor_cb' in a['href'].lower() or 'valor_cba' in a['href'].lower()
        }

        for href in sorted(hrefs):
            pdf_url = urljoin(page_url, href)
            filename = pdf_url.rsplit('/', 1)[-1]

            # Extraer mes del sufijo "25.MM"
            mnum = re.search(r'25\.(\d{2})', filename)
            mes = NUM2MONTH.get(mnum.group(1)) if mnum else None
            if mes not in MESES_ORDEN:
                continue

            # Descargar PDF en memoria
            try:
                r2 = requests.get(pdf_url); r2.raise_for_status()
            except Exception as e:
                # Si falla, lo notificamos y seguimos
                st.warning(f"No se pudo descargar {filename}: {e}")
                continue

            stream = BytesIO(r2.content)

            # Abrir PDF y extraer líneas válidas
            with pdfplumber.open(stream) as pdf:
                for i, page in enumerate(pdf.pages):
                    if i < SKIP_PAGES:
                        continue
                    text = page.extract_text() or ''
                    for line in text.split('\n'):
                        m = LINE_REGEX.match(line.strip())
                        if not m:
                            continue
                        producto = m.group(1).strip()
                        valor    = float(m.group(2).replace(',', '.'))
                        # Filtrar encabezados o valores absurdos
                        if producto.lower() in [x.lower() for x in MESES_ORDEN]:
                            continue
                        if abs(valor) > 100:  # descartar ruidos
                            continue
                        registros.append({
                            'producto':  producto,
                            'variacion': valor,
                            'mes':       mes
                        })

    if not registros:
        return pd.DataFrame(columns=['producto','variacion','mes'])

    df = pd.DataFrame(registros)
    return df

# ========= STREAMLIT APP =========
st.set_page_config(page_title="Monitor CBA Ene–Mar 2025", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica (Ene–Mar 2025)")

with st.spinner("Descargando y parseando datos…"):
    df = load_variaciones()

if df.empty:
    st.error("⚠️ No se encontraron variaciones. Verifica la conexión o las URLs.")
    st.stop()

st.success(f"✅ Cargados {len(df)} registros de variaciones.")

# Sidebar: selección de productos
st.sidebar.header("Filtros")
todos = sorted(df['producto'].unique())
seleccion = st.sidebar.multiselect("Selecciona productos", todos, default=todos)
df_sel = df[df['producto'].isin(seleccion)].copy()

# Orden cronológico de meses
df_sel['mes'] = pd.Categorical(df_sel['mes'], categories=MESES_ORDEN, ordered=True)

# Pivot table con agregación para manejarlos duplicados
chart_data = (
    df_sel
      .pivot_table(index='mes', columns='producto', values='variacion', aggfunc='mean')
      .reindex(index=MESES_ORDEN)
)

# Mostrar gráfico
st.subheader("Variación Mensual por Producto")
st.line_chart(chart_data)

# Mostrar tabla de datos
st.subheader("Datos Detallados")
st.dataframe(df_sel.reset_index(drop=True), use_container_width=True)
