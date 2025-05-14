import streamlit as st
import pandas as pd
import pdfplumber
import requests
import re
from io import BytesIO

# ====== CONFIG ======
YEARS = {
    '2024': [f"{i:02d}" for i in range(1,13)],
    '2025': [f"{i:02d}" for i in range(1,4)],
}
SKIP_PAGES = 4
NUM2MONTH = {
    '01':'Enero','02':'Febrero','03':'Marzo',
    '04':'Abril','05':'Mayo','06':'Junio',
    '07':'Julio','08':'Agosto','09':'Septiembre',
    '10':'Octubre','11':'Noviembre','12':'Diciembre'
}

LINE_REGEX = re.compile(r"^(.+?)\s+(-?\d+[.,]\d+)$")

@st.cache_data(ttl=3600)
def load_data():
    rows = []
    for year, meses in YEARS.items():
        short = year[2:]
        for mm in meses:
            url = (
                "https://observatorio.ministeriodesarrollosocial.gob.cl"
                f"/storage/docs/cba/nueva_serie/{year}"
                f"/Valor_CBA_y_LPs_{short}.{mm}.pdf"
            )
            try:
                r = requests.get(url)
                r.raise_for_status()
            except:
                continue

            mes_nombre = NUM2MONTH[mm]
            with pdfplumber.open(BytesIO(r.content)) as pdf:
                for i, page in enumerate(pdf.pages):
                    if i < SKIP_PAGES: 
                        continue
                    for line in (page.extract_text() or "").split("\n"):
                        m = LINE_REGEX.match(line.strip())
                        if not m:
                            continue
                        prod = m.group(1).strip()
                        val  = float(m.group(2).replace(",","."))
                        # filtros básicos
                        if prod.lower()=="cba": 
                            continue
                        if not re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]", prod):
                            continue
                        if abs(val)>100:
                            continue
                        rows.append({
                            "year":      year,
                            "mes":       mes_nombre,
                            "producto":  prod,
                            "variacion": val
                        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.drop_duplicates(["year","mes","producto"])

# ====== APP ======
st.set_page_config(page_title="Monitor Canasta Básica", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica")

with st.spinner("🔄 Descargando y procesando…"):
    df = load_data()
if df.empty:
    st.error("⚠️ No se encontraron datos.")
    st.stop()

# Top‐20 productos por variación absoluta media
df["absvar"] = df["variacion"].abs()
top20 = df.groupby("producto")["absvar"].mean().nlargest(20).index
df = df[df["producto"].isin(top20)].drop(columns="absvar")

# Sidebar
st.sidebar.header("Filtros")
years_all = sorted(df["year"].unique())
year_sel  = st.sidebar.multiselect("Año", years_all, default=years_all)
months_all = sorted(
    df[df["year"].isin(year_sel)]["mes"].unique(),
    key=lambda m: list(NUM2MONTH.values()).index(m)
)
month_sel = st.sidebar.multiselect("Mes", months_all, default=months_all)
prod_all  = sorted(df["producto"].unique())
prod_sel  = st.sidebar.multiselect("Producto", prod_all, default=prod_all)

# Filtrado final
df_f = df[
    df["year"].isin(year_sel) &
    df["mes"].isin(month_sel) &
    df["producto"].isin(prod_sel)
].copy()

# Construir columna periodo y categorizar
periodos = []
for y in sorted(year_sel):
    for mm in YEARS[y]:
        mesn = NUM2MONTH[mm]
        if mesn in month_sel:
            periodos.append(f"{y} {mesn}")

df_f["periodo"] = df_f["year"] + " " + df_f["mes"]
df_f["periodo"] = pd.Categorical(df_f["periodo"], categories=periodos, ordered=True)

# GRÁFICO MENSUAL
st.subheader("🔄 Variación Porcentual Mensual por Producto")
monthly = df_f.pivot_table(
    index="periodo", columns="producto", values="variacion", aggfunc="mean"
)
# reindex solo con los periodos realmente existentes
monthly = monthly.reindex(periodos).dropna(how="all")
st.line_chart(monthly)

# RESUMEN ANUAL
st.subheader("📋 Resumen Anual de Variación Porcentual")
res_anual = df_f.groupby("year")["variacion"].mean().rename("Var.% Media")
st.table(res_anual)

# INTERPRETACIONES
st.subheader("📝 Interpretaciones y Conclusiones")
avg_var = df_f["variacion"].mean()
st.markdown(f"- Variación porcentual promedio: **{avg_var:.2f}%**.")

row_max = df_f.loc[df_f["variacion"].idxmax()]
st.markdown(f"- **Mayor alza**: _{row_max['producto']}_ con **+{row_max['variacion']:.2f}%** en **{row_max['periodo']}**.")
row_min = df_f.loc[df_f["variacion"].idxmin()]
st.markdown(f"- **Mayor baja**: _{row_min['producto']}_ con **{row_min['variacion']:.2f}%** en **{row_min['periodo']}**.")

# DATOS DETALLADOS
st.subheader("📊 Datos Detallados")
st.dataframe(
    df_f[["year","mes","producto","variacion"]]
      .sort_values(["periodo","producto"])
      .reset_index(drop=True),
    use_container_width=True
)
