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

# Mapeo de mes numérico (sufijo 25.MM) → nombre completo
NUM2MONTH = {
    '01': 'Enero', '02': 'Febrero', '03': 'Marzo',
    '04': 'Abril', '05': 'Mayo',    '06': 'Junio',
    '07': 'Julio', '08': 'Agosto',  '09': 'Septiembre',
    '10': 'Octubre','11': 'Noviembre','12': 'Diciembre'
}
MESES_ORDEN = ['Enero','Febrero','Marzo']  # solo los tres meses que queremos

# ========= PARSER EN MEMORIA =========
@st.cache_data(ttl=3600)
def load_variaciones():
    """
    Descarga todos los PDFs de YEARS, extrae líneas "Producto  valor"
    y devuelve DataFrame con columnas: producto, variacion, mes.
    """
    line_regex = re.compile(r"^([A-Za-zÁÉÍÓÚáéíóúÑñüÜ\s\-/\(\)]+?)\s+(-?\d+[.,]?\d+)$")
    registros = []

    for year, page_url in YEARS.items():
        resp = requests.get(page_url); resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Tomar enlaces que contengan 'valor_cb' o 'Valor_CBA'
        hrefs = {
            a['href'] for a in soup.select("a[href$='.pdf']")
            if 'valor_cb' in a['href'].lower() or 'valor_cba' in a['href'].lower()
        }

        for href in sorted(hrefs):
            pdf_url = urljoin(page_url, href)
            filename = pdf_url.rsplit('/',1)[-1]

            # Extraer mes numérico de '25.MM'
            mnum = re.search(r'25\.(\d{2})', filename)
            mes_full = NUM2MONTH.get(mnum.group(1)) if mnum else None
            if mes_full not in MESES_ORDEN:
                continue

            # Descargar PDF en memoria
            r2 = requests.get(pdf_url)
            try:
                r2.raise_for_status()
            except:
                st.warning(f"No se pudo bajar {filename}")
                continue
            stream = BytesIO(r2.content)

            # Parsear cada página útil
            with pdfplumber.open(stream) as pdf:
                for i, page in enumerate(pdf.pages):
                    if i < SKIP_PAGES:
                        continue
                    text = page.extract_text() or ''
                    for line in text.split('\n'):
                        m = line_regex.match(line.strip())
                        if not m:
                            continue

                        producto = m.group(1).strip()
                        valor    = float(m.group(2).replace(',', '.'))

                        # Filtrar encabezados y valores absurdos
                        if producto.lower() in [mes.lower() for mes in MESES_ORDEN]:
                            continue
                        if abs(valor) > 100:  # descarta números inverosímiles (p.ej. '2025')
                            continue

                        registros.append({
                            'producto':  producto,
                            'variacion': valor,
                            'mes':       mes_full
                        })

    if not registros:
        return pd.DataFrame(columns=['producto','variacion','mes'])
    return pd.DataFrame(registros)

# ========= STREAMLIT APP =========
st.set_page_config(page_title="Canasta Básica 2025", layout="wide")
st.title("📊 Monitor Variaciones Canasta Básica Ene–Mar 2025")

df = load_variaciones()
if df.empty:
    st.error("⚠️ No se encontraron variaciones. Revisa enlace o conexión.")
    st.stop()

# Sidebar: filtro de productos
st.sidebar.header("Filtros")
todos = sorted(df['producto'].unique())
sel = st.sidebar.multiselect("Selecciona productos", todos, default=todos)
df_sel = df[df['producto'].isin(sel)].copy()

# Ordenar cronológicamente
df_sel['mes'] = pd.Categorical(df_sel['mes'], categories=MESES_ORDEN, ordered=True)

# Pivot con media para duplicados
chart_data = (
    df_sel
      .pivot_table(index='mes', columns='producto', values='variacion', aggfunc='mean')
      .reindex(index=MESES_ORDEN)
)

# Gráfico
st.subheader("Variación Mensual por Producto")
st.line_chart(chart_data)

# Tabla
st.subheader("Datos Detallados")
st.dataframe(df_sel.reset_index(drop=True), use_container_width=True)
