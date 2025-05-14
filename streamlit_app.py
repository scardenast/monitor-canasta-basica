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
SKIP_PAGES = 4

NUM2MONTH = {
    '01':'Enero','02':'Febrero','03':'Marzo',
    '04':'Abril','05':'Mayo','06':'Junio',
    '07':'Julio','08':'Agosto','09':'Septiembre',
    '10':'Octubre','11':'Noviembre','12':'Diciembre'
}
MONTHS_BY_YEAR = {
    '2024': list(NUM2MONTH.values()),
    '2025': [NUM2MONTH[m] for m in ('01','02','03')]
}

# Captura: producto – precio CLP – variación %
LINE_REGEX = re.compile(r"^(.+?)\s+([\d\.,]+)\s+(-?\d+[.,]\d+)$")

@st.cache_data(ttl=3600)
def load_data():
    rows = []
    for year, page_url in YEAR_PAGES.items():
        resp = requests.get(page_url); resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        pdf_links = {
            a['href'] for a in soup.select("a[href$='.pdf']")
            if 'valor_cb' in a['href'].lower() or 'valor_cba' in a['href'].lower()
        }
        for href in sorted(pdf_links):
            pdf_url = urljoin(page_url, href)
            fname = pdf_url.rsplit('/',1)[-1]
            mnum  = re.search(rf"{year[2:]}\.(\d{{2}})", fname)
            mes   = NUM2MONTH.get(mnum.group(1)) if mnum else None
            if mes not in MONTHS_BY_YEAR[year]:
                continue
            try:
                r2 = requests.get(pdf_url); r2.raise_for_status()
            except:
                continue

            with pdfplumber.open(BytesIO(r2.content)) as pdf:
                for i, page in enumerate(pdf.pages):
                    if i < SKIP_PAGES:
                        continue
                    for line in (page.extract_text() or "").split('\n'):
                        m = LINE_REGEX.match(line.strip())
                        if not m:
                            continue
                        prod      = m.group(1).strip()
                        price_str = m.group(2)
                        var_str   = m.group(3)

                        # convertir
                        price = float(price_str.replace('.', '').replace(',', '.'))
                        var   = float(var_str.replace(',', '.'))

                        # filtros:
                        # 1) quitar fila de totales
                        if prod.lower() == 'cba':
                            continue
                        # 2) descartar strings formados solo por números/puntuación
                        if re.fullmatch(r'[\d\.,\s\-/]+', prod):
                            continue
                        # 3) descartar ruido de tabla
                        if abs(var) > 100 or price > 1e6:
                            continue

                        rows.append({
                            'year':      year,
                            'mes':       mes,
                            'producto':  prod,
                            'precio':    price,
                            'variacion': var
                        })

    if not rows:
        return pd.DataFrame(columns=['year','mes','producto','precio','variacion'])
    return pd.DataFrame(rows)


# ========= STREAMLIT APP =========
st.set_page_config(page_title="Monitor Canasta Básica", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica")

with st.spinner("🔄 Descargando y parseando datos…"):
    df = load_data()

if df.empty:
    st.error("⚠️ No se encontraron datos. Verifica la conexión o la fuente.")
    st.stop()

st.success(f"✅ Cargados {len(df)} registros.")

# --- SIDEBAR: FILTROS ---
st.sidebar.header("Filtros")
years      = sorted(df['year'].unique())
year_sel   = st.sidebar.multiselect("Año",   years, default=years)

months_avail = sorted(
    df[df['year'].isin(year_sel)]['mes'].unique(),
    key=lambda m: list(NUM2MONTH.values()).index(m)
)
month_sel  = st.sidebar.multiselect("Mes",   months_avail, default=months_avail)

products   = sorted(df['producto'].unique())
prod_sel   = st.sidebar.multiselect("Producto", products, default=products)

# --- APLICAR FILTROS ---
df_f = df[
    df['year'].isin(year_sel) &
    df['mes'].isin(month_sel) &
    df['producto'].isin(prod_sel)
].copy()

# ordenar cronológico
order_meses = MONTHS_BY_YEAR[year_sel[0]]
df_f['mes'] = pd.Categorical(df_f['mes'], categories=order_meses, ordered=True)

# --- GRÁFICO 1: Mensual (líneas) ---
st.subheader("Variación Porcentual Mensual por Producto")
monthly = (
    df_f
      .pivot_table(index='mes', columns='producto', values='variacion', aggfunc='mean')
      .reindex(order_meses)
)
st.line_chart(monthly)

# --- GRÁFICO 2: Anual (barras) ---
st.subheader("Variación Porcentual Anual Promedio por Producto")
annual = df_f.groupby(['year','producto'])['variacion'].mean().unstack(fill_value=0)
st.bar_chart(annual)

# --- INTERPRETACIONES Y CONCLUSIONES ---
st.subheader("📝 Interpretaciones y Conclusiones")

# 1) promedio general
avg_var = df_f['variacion'].mean()
st.markdown(f"- La variación porcentual promedio fue **{avg_var:.2f}%**.")

# 2) mayor alza y caída incluyendo CLP
df_f['periodo'] = df_f['year'].astype(str) + ' ' + df_f['mes'].astype(str)
periodos = [f"{y} {m}" for y in years for m in MONTHS_BY_YEAR[y]
            if y in year_sel and m in month_sel]

imax = df_f['variacion'].idxmax(); row_max = df_f.loc[imax]
pidx = periodos.index(row_max['periodo'])
if pidx>0:
    prev = periodos[pidx-1]
    prev_price = df_f.loc[
        (df_f['periodo']==prev)&(df_f['producto']==row_max['producto']),
        'precio'
    ]
    if not prev_price.empty:
        diff = row_max['precio'] - prev_price.iloc[0]
        st.markdown(
            f"- **Mayor alza**: _{row_max['producto']}_ con **+{row_max['variacion']:.2f}%** "
            f"en {row_max['periodo']}, equivalente a **+${diff:,.0f} CLP**."
        )
    else:
        st.markdown(
            f"- **Mayor alza**: _{row_max['producto']}_ con **+{row_max['variacion']:.2f}%** "
            f"en {row_max['periodo']}."
        )
else:
    st.markdown(
        f"- **Mayor alza**: _{row_max['producto']}_ con **+{row_max['variacion']:.2f}%** "
        f"en {row_max['periodo']}."
    )

imin = df_f['variacion'].idxmin(); row_min = df_f.loc[imin]
pidx2 = periodos.index(row_min['periodo'])
if pidx2>0:
    prev2 = periodos[pidx2-1]
    prev_price2 = df_f.loc[
        (df_f['periodo']==prev2)&(df_f['producto']==row_min['producto']),
        'precio'
    ]
    if not prev_price2.empty:
        diff2 = row_min['precio'] - prev_price2.iloc[0]
        st.markdown(
            f"- **Mayor caída**: _{row_min['producto']}_ con **{row_min['variacion']:.2f}%** "
            f"en {row_min['periodo']}, equivalente a **-${abs(diff2):,.0f} CLP**."
        )
    else:
        st.markdown(
            f"- **Mayor caída**: _{row_min['producto']}_ con **{row_min['variacion']:.2f}%** "
            f"en {row_min['periodo']}."
        )
else:
    st.markdown(
        f"- **Mayor caída**: _{row_min['producto']}_ con **{row_min['variacion']:.2f}%** "
        f"en {row_min['periodo']}."
    )

# 3) media por mes
st.markdown("**Variación porcentual media por mes:**")
for m in order_meses:
    if m in month_sel:
        vm = df_f[df_f['mes']==m]['variacion'].mean()
        st.markdown(f"  - {m}: {vm:.2f}%")

# --- TABLA DETALLADA ---
st.subheader("Datos Detallados")
st.dataframe(
    df_f[['year','mes','producto','precio','variacion']]
      .sort_values(['year','mes','producto'])
      .reset_index(drop=True),
    use_container_width=True
)
