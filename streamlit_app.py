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
    '01':'Enero','02':'Febrero','03':'Marzo',
    '04':'Abril','05':'Mayo','06':'Junio',
    '07':'Julio','08':'Agosto','09':'Septiembre',
    '10':'Octubre','11':'Noviembre','12':'Diciembre'
}
MONTHS_BY_YEAR = {
    '2024': list(NUM2MONTH.values()),
    '2025': [NUM2MONTH[m] for m in ('01','02','03')]
}

# Regex para capturar: PRODUCTO   -1,23
LINE_REGEX = re.compile(r"^(.+?)\s+(-?\d+[.,]\d+)$")

@st.cache_data(ttl=3600)
def load_data():
    registros = []
    for year, page_url in YEAR_PAGES.items():
        resp = requests.get(page_url); resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        pdf_links = {
            a['href'] for a in soup.select("a[href$='.pdf']")
            if 'valor_cb' in a['href'].lower() or 'valor_cba' in a['href'].lower()
        }
        for href in sorted(pdf_links):
            pdf_url = urljoin(page_url, href)
            fname   = pdf_url.rsplit('/',1)[-1]
            m = re.search(rf"{year[2:]}\\.(\\d{{2}})", fname)
            mes = NUM2MONTH.get(m.group(1)) if m else None
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
                    for line in (page.extract_text() or "").split("\n"):
                        m2 = LINE_REGEX.match(line.strip())
                        if not m2:
                            continue
                        prod = m2.group(1).strip()
                        val  = float(m2.group(2).replace(",", "."))
                        # descartar totales y ruido
                        if prod.lower() == "cba":
                            continue
                        if not re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]", prod):
                            continue
                        if abs(val) > 100:
                            continue
                        registros.append({
                            "year":      year,
                            "mes":       mes,
                            "producto":  prod,
                            "variacion": val
                        })

    if not registros:
        return pd.DataFrame(columns=["year","mes","producto","variacion"])

    df = pd.DataFrame(registros)
    # eliminar duplicados exactos
    df = df.drop_duplicates(subset=["year","mes","producto"])
    return df

# ========= UI =========
st.set_page_config(page_title="Monitor Canasta Básica", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica")

with st.spinner("🔄 Descargando y procesando datos…"):
    df = load_data()

if df.empty:
    st.error("⚠️ No se encontraron datos. Verifica la conexión o la fuente.")
    st.stop()

# ===== TOP 20 PRODUCTOS =====
df["absvar"] = df["variacion"].abs()
top20 = df.groupby("producto")["absvar"].mean().nlargest(20).index
df = df[df["producto"].isin(top20)].drop(columns="absvar")
st.success(f"✅ Cargados {len(df)} registros. Mostrando top 20 productos.")

# ===== SIDEBAR: FILTROS =====
st.sidebar.header("Filtros")
years       = sorted(df["year"].unique())
year_sel    = st.sidebar.multiselect("Año",   years, default=years)
months_avail= sorted(
    df[df["year"].isin(year_sel)]["mes"].unique(),
    key=lambda m: list(NUM2MONTH.values()).index(m)
)
month_sel   = st.sidebar.multiselect("Mes",   months_avail, default=months_avail)
products    = sorted(df["producto"].unique())
prod_sel    = st.sidebar.multiselect("Producto", products, default=products)

# ===== APLICAR FILTROS =====
df_f = df[
    df["year"].isin(year_sel) &
    df["mes"].isin(month_sel) &
    df["producto"].isin(prod_sel)
].copy()

# ===== PERIODO CRONOLÓGICO =====
# construye lista ["2024 Enero", ...]
periodos = [
    f"{y} {m}"
    for y in years
    for m in MONTHS_BY_YEAR[y]
    if y in year_sel and m in month_sel
]
df_f["periodo"] = df_f["year"].astype(str) + " " + df_f["mes"]
df_f["periodo"] = pd.Categorical(df_f["periodo"], categories=periodos, ordered=True)

# ===== GRÁFICO 1: VARIACIÓN MENSUAL =====
st.subheader("Variación Porcentual Mensual por Producto")
monthly_pivot = (
    df_f
      .pivot_table(index="periodo", columns="producto", values="variacion", aggfunc="mean")
      .loc[periodos]
)
st.line_chart(monthly_pivot)

# ===== RESUMEN ANUAL (TABLA) =====
st.subheader("Resumen Anual de Variación Porcentual")
res_anual = df_f.groupby("year")["variacion"].mean().rename("Variación % Media")
st.table(res_anual)

# ===== INTERPRETACIONES =====
st.subheader("📝 Interpretaciones y Conclusiones")

avg_var = df_f["variacion"].mean()
st.markdown(f"- La variación porcentual promedio fue **{avg_var:.2f}%**.")

# Mayor alza
row_max = df_f.loc[df_f["variacion"].idxmax()]
st.markdown(
    f"- **Mayor alza**: _{row_max['producto']}_ con **+{row_max['variacion']:.2f}%** "
    f"en **{row_max['periodo']}**."
)

# Mayor baja
row_min = df_f.loc[df_f["variacion"].idxmin()]
st.markdown(
    f"- **Mayor baja**: _{row_min['producto']}_ con **{row_min['variacion']:.2f}%** "
    f"en **{row_min['periodo']}**."
)

# Variación media por mes
st.markdown("**Variación porcentual media por mes:**")
for p in periodos:
    mes = p.split(" ",1)[1]
    v = df_f[df_f["periodo"]==p]["variacion"].mean()
    st.markdown(f"  - {p}: {v:.2f}%")

# ===== DATOS DETALLADOS =====
st.subheader("Datos Detallados")
st.dataframe(
    df_f[["year","mes","producto","variacion"]]
      .sort_values(["year","mes","producto"])
      .reset_index(drop=True),
    use_container_width=True
)
