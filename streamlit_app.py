import streamlit as st
import pandas as pd
import pdfplumber
import requests
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from io import BytesIO

# ========= CONFIGURACIÓN =========
YEAR_PAGES = {
    '2024': 'https://observatorio.ministeriodesarrollosocial.gob.cl/nueva-serie-cba-2024',
    '2025': 'https://observatorio.ministeriodesarrollosocial.gob.cl/nueva-serie-cba-2025',
}
SKIP_PAGES = 4  # páginas introductorias a omitir

NUM2MONTH = {
    '01': 'Enero','02': 'Febrero','03': 'Marzo',
    '04': 'Abril','05': 'Mayo','06': 'Junio',
    '07': 'Julio','08': 'Agosto','09': 'Septiembre',
    '10': 'Octubre','11': 'Noviembre','12': 'Diciembre'
}
MONTHS_BY_YEAR = {
    '2024': list(NUM2MONTH.values()),
    '2025': [NUM2MONTH[m] for m in ['01','02','03']]
}

# Regex que captura: producto, precio (CLP), variación (%)
LINE_REGEX = re.compile(
    r"^([A-Za-zÁÉÍÓÚáéíóúÑñüÜ\s\-/\(\)]+?)\s+([\d\.\,]+)\s+(-?\d+[.,]\d+)$"
)

@st.cache_data(ttl=3600)
def load_data():
    registros = []
    for year, page_url in YEAR_PAGES.items():
        resp = requests.get(page_url); resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        hrefs = {
            a['href'] for a in soup.select("a[href$='.pdf']")
            if 'valor_cb' in a['href'].lower() or 'valor_cba' in a['href'].lower()
        }

        for href in sorted(hrefs):
            pdf_url = urljoin(page_url, href)
            filename = pdf_url.rsplit('/', 1)[-1]

            # extraer mes de '25.MM'
            mnum = re.search(rf"{year[2:]}\.(\d{{2}})", filename)
            mes = NUM2MONTH.get(mnum.group(1)) if mnum else None
            if mes not in MONTHS_BY_YEAR[year]:
                continue

            try:
                r2 = requests.get(pdf_url); r2.raise_for_status()
            except:
                continue

            stream = BytesIO(r2.content)
            with pdfplumber.open(stream) as pdf:
                for idx, page in enumerate(pdf.pages):
                    if idx < SKIP_PAGES:
                        continue
                    text = page.extract_text() or ""
                    for line in text.split('\n'):
                        m = LINE_REGEX.match(line.strip())
                        if not m:
                            continue
                        prod      = m.group(1).strip()
                        price_str = m.group(2)
                        var_str   = m.group(3)

                        # convertir CLP: eliminar miles y poner punto decimal
                        price_val = float(price_str.replace('.', '').replace(',', '.'))
                        # convertir % variación
                        var_val   = float(var_str.replace(',', '.'))

                        # filtrar ruidos
                        if prod.lower() == "cba" or abs(price_val) > 1e6 or abs(var_val) > 100:
                            continue

                        registros.append({
                            'year':      year,
                            'mes':       mes,
                            'producto':  prod,
                            'precio':    price_val,
                            'variacion': var_val
                        })

    if not registros:
        return pd.DataFrame(columns=['year','mes','producto','precio','variacion'])
    return pd.DataFrame(registros)

# ========= STREAMLIT =========
st.set_page_config(page_title="Canasta Básica Monitor", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica")

# cargar datos
with st.spinner("🔄 Descargando y procesando..."):
    df = load_data()

if df.empty:
    st.error("No hay datos. Verifica la conexión o la fuente.")
    st.stop()

st.success(f"✅ Cargados {len(df)} registros.")

# ---- SIDEBAR: FILTROS ----
st.sidebar.header("Filtros")

# 1) Año
years = sorted(df['year'].unique())
year_sel = st.sidebar.multiselect("Año", years, default=years)

# 2) Mes (dinámico)
available_months = sorted(
    df[df['year'].isin(year_sel)]['mes'].unique(),
    key=lambda m: list(NUM2MONTH.values()).index(m)
)
month_sel = st.sidebar.multiselect("Mes", available_months, default=available_months)

# 3) Producto
products = sorted(df['producto'].unique())
prod_sel = st.sidebar.multiselect("Producto", products, default=products)

# 4) Métrica: Precio o Variación
metric = st.sidebar.radio("Métrica", ('Variación %','Precio CLP'))

# ---- APLICAR FILTROS ----
df_f = df[
    df['year'].isin(year_sel) &
    df['mes'].isin(month_sel) &
    df['producto'].isin(prod_sel)
].copy()

df_f['mes'] = pd.Categorical(
    df_f['mes'],
    categories=[m for m in MONTHS_BY_YEAR[year_sel[0]] if m in month_sel],
    ordered=True
)

# ---- GRÁFICO ----
if metric == 'Variación %':
    pivot = df_f.pivot_table(
        index='mes', columns='producto', values='variacion', aggfunc='mean'
    )
else:
    pivot = df_f.pivot_table(
        index='mes', columns='producto', values='precio', aggfunc='mean'
    )

pivot = pivot.reindex(index=[m for m in MONTHS_BY_YEAR[year_sel[0]] if m in month_sel])

st.subheader(f"{metric} Mensual por Producto")
st.line_chart(pivot)

# ---- INTERPRETACIONES ----
st.subheader("📝 Interpretaciones")
avg = df_f['variacion'].mean() if metric=='Variación %' else df_f['precio'].mean()
unit = '%' if metric=='Variación %' else 'CLP'
st.markdown(f"- Valor promedio ({metric.lower()}): **{avg:.2f} {unit}** sobre el rango seleccionado.")

# ---- TABLA ----
st.subheader("Datos Detallados")
st.dataframe(df_f.reset_index(drop=True), use_container_width=True)
