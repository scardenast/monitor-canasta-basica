import streamlit as st
import pandas as pd
import pdfplumber
import requests
import re
from io import BytesIO

# ========= CONFIG =========
DIRECT_PDF_URLS = [
    'https://observatorio.ministeriodesarrollosocial.gob.cl/storage/docs/cba/nueva_ser%C3%ADe/2025/Valor_CBA_y_LPs_25.01.pdf',
    'https://observatorio.ministeriodesarrollosocial.gob.cl/storage/docs/cba/nueva_ser%C3%ADe/2025/Valor_CBA_y_LPs_25.02.pdf',
    'https://observatorio.ministeriodesarrollosocial.gob.cl/storage/docs/cba/nueva_ser%C3%ADe/2025/Valor_CBA_y_LPs_25.03.pdf',
]
SKIP_PAGES = 1

# Mapa numérico → mes
NUM2ABBR = {'01':'ene','02':'feb','03':'mar'}
MES_MAP    = {'ene':'Enero','feb':'Febrero','mar':'Marzo'}
MESES_ORDEN= ['Enero','Febrero','Marzo']

# ========= PARSER =========
@st.cache_data(ttl=3600)
def load_variaciones():
    # Regex: sólo letras y espacios en producto, luego número con decimal
    line_pat = re.compile(r"^([A-Za-zÁÉÍÓÚáéíóúÑñüÜ\s\-/\(\)]+?)\s+(-?\d+[.,]\d+)$")
    rows = []

    for pdf_url in DIRECT_PDF_URLS:
        # extraer mes de la URL
        mnum = re.search(r'25\.(\d{2})', pdf_url)
        mes_abbr = NUM2ABBR.get(mnum.group(1)) if mnum else None
        mes_full = MES_MAP.get(mes_abbr)
        if not mes_full:
            continue

        # descargar
        r = requests.get(pdf_url); r.raise_for_status()
        stream = BytesIO(r.content)

        # parsear
        with pdfplumber.open(stream) as pdf:
            for idx, page in enumerate(pdf.pages):
                if idx < SKIP_PAGES:
                    continue
                text = page.extract_text() or ''
                for line in text.split('\n'):
                    m = line_pat.match(line.strip())
                    if not m:
                        continue
                    producto = m.group(1).strip()
                    # descartar líneas que sean simplemente nombres de meses
                    if producto.lower() in MES_MAP.values():
                        continue
                    # descartar si contiene dígitos
                    if re.search(r'\d', producto):
                        continue
                    valor = float(m.group(2).replace(',', '.'))
                    rows.append({
                        'producto':  producto,
                        'variacion': valor,
                        'mes':       mes_full
                    })

    if not rows:
        return pd.DataFrame(columns=['producto','variacion','mes'])
    return pd.DataFrame(rows)

# ========= STREAMLIT =========
st.set_page_config(page_title="Canasta Básica 2025", layout="wide")
st.title("📊 Monitor Variaciones CBA Ene–Mar 2025")

df = load_variaciones()
if df.empty:
    st.error("⚠️ No se encontraron variaciones. Verifica URLs o conexión.")
    st.stop()

# filtros
st.sidebar.header("Selecciona productos")
prod_list = sorted(df['producto'].unique())
seleccion = st.sidebar.multiselect("Productos", prod_list, default=prod_list)
df_sel = df[df['producto'].isin(seleccion)].copy()

# ordenar meses
df_sel['mes'] = pd.Categorical(df_sel['mes'], categories=MESES_ORDEN, ordered=True)

# pivot + mean para duplicados
chart_data = df_sel.pivot_table(
    index='mes', columns='producto', values='variacion', aggfunc='mean'
).reindex(index=MESES_ORDEN)

# gráfico
st.subheader("Variación Mensual por Producto")
st.line_chart(chart_data)

# tabla
st.subheader("Datos Detallados")
st.dataframe(df_sel.reset_index(drop=True), use_container_width=True)
