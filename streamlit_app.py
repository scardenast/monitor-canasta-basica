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
SKIP_PAGES = 1  # Cuántas páginas introductorias omitir

# Mapeo de mes numérico a nombre completo
NUM2MONTH = {
    '01': 'Enero',
    '02': 'Febrero',
    '03': 'Marzo',
    '04': 'Abril',
    '05': 'Mayo',
    '06': 'Junio',
    '07': 'Julio',
    '08': 'Agosto',
    '09': 'Septiembre',
    '10': 'Octubre',
    '11': 'Noviembre',
    '12': 'Diciembre'
}
MESES_ORDEN = ['Enero', 'Febrero', 'Marzo']  # sólo los tres meses

# ========= PARSER EN MEMORIA =========
@st.cache_data(ttl=3600)
def load_variaciones():
    """
    Descarga los PDFs de DIRECT_PDF_URLS, extrae todas las líneas
    que encajen con "Producto   valor" y devuelve un DataFrame.
    """
    regex_line = re.compile(r"^(.+?)\s+(-?\d+[.,]?\d*)$")
    registros = []

    for url in DIRECT_PDF_URLS:
        # Descargar PDF
        try:
            resp = requests.get(url)
            resp.raise_for_status()
        except Exception as e:
            print(f"⚠️ No se pudo descargar {url}: {e}")
            continue

        # Determinar mes a partir del nombre de archivo (25.MM.pdf)
        filename = url.rsplit('/', 1)[-1]
        mnum = re.search(r'25\.(\d{2})', filename)
        month = NUM2MONTH.get(mnum.group(1)) if mnum else None
        if not month:
            print(f"⚠️ Mes no reconocido en {filename}")
            continue

        # Abrir PDF en memoria y extraer líneas válidas
        stream = BytesIO(resp.content)
        with pdfplumber.open(stream) as pdf:
            for i, page in enumerate(pdf.pages):
                if i < SKIP_PAGES:
                    continue
                text = page.extract_text() or ''
                for line in text.split('\n'):
                    match = regex_line.match(line.strip())
                    if not match:
                        continue
                    producto = match.group(1).strip()
                    # Ignorar líneas que no sean productos
                    if re.search(r'\d', producto):
                        continue
                    valor = float(match.group(2).replace(',', '.'))
                    registros.append({
                        'producto': producto,
                        'variacion': valor,
                        'mes': month
                    })

    if not registros:
        return pd.DataFrame(columns=['producto','variacion','mes'])
    return pd.DataFrame(registros)

# ========= STREAMLIT APP =========
st.set_page_config(page_title="Canasta Básica 2025", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica (Ene–Mar 2025)")

df = load_variaciones()
if df.empty:
    st.error("⚠️ No se encontraron variaciones. Verifica las URLs o tu conexión.")
    st.stop()

# Sidebar: filtros
st.sidebar.header("Filtros")
productos = sorted(df['producto'].unique())
seleccion = st.sidebar.multiselect("Selecciona productos", productos, default=productos)
df_sel = df[df['producto'].isin(seleccion)].copy()

# Ordenar meses
df_sel['mes'] = pd.Categorical(df_sel['mes'], categories=MESES_ORDEN, ordered=True)

# Pivot table con media para duplicados
chart_data = (
    df_sel
    .pivot_table(index='mes', columns='producto', values='variacion', aggfunc='mean')
    .reindex(index=MESES_ORDEN)
)

# Gráfico
st.subheader("Variación Mensual por Producto")
st.line_chart(chart_data)

# Tabla detallada
st.subheader("Datos Detallados")
st.dataframe(df_sel.reset_index(drop=True), use_container_width=True)
