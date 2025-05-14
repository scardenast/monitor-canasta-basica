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

# Lista fija de productos
FIXED_PRODUCTS = [
    # ... tu lista de productos aquí ...
]

@st.cache_data(ttl=3600)
def load_data():
    rows = []
    for year, meses in YEARS.items():
        short = year[2:]
        for mm in meses:
            url = (
                f"https://observatorio.ministeriodesarrollosocial.gob.cl"
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
                        val = float(m.group(2).replace(",", "."))
                        if prod.lower() == "cba":
                            continue
                        if prod not in FIXED_PRODUCTS:
                            continue
                        if abs(val) > 100:
                            continue
                        rows.append({
                            "year": year,
                            "mes": mes_nombre,
                            "producto": prod,
                            "variacion": val
                        })

    df = pd.DataFrame(rows)
    return df.drop_duplicates(["year","mes","producto"]) if not df.empty else df

# ====== APP ======
st.set_page_config(page_title="Monitor Canasta Básica", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica")

with st.spinner("🔄 Cargando datos…"):
    df = load_data()
if df.empty:
    st.error("⚠️ No se encontraron datos.")
    st.stop()

# ====== SIDEBAR ======
st.sidebar.header("Filtros")
years = sorted(df["year"].unique())
year_sel = st.sidebar.multiselect("Año", years, default=years)

months = sorted(
    df[df["year"].isin(year_sel)]["mes"].unique(),
    key=lambda m: list(NUM2MONTH.values()).index(m)
)
month_sel = st.sidebar.multiselect("Mes", months, default=months)

prod_sel = st.sidebar.multiselect("Producto", FIXED_PRODUCTS, default=FIXED_PRODUCTS)

# ====== FILTRAR ======
df_f = df[
    df["year"].isin(year_sel) &
    df["mes"].isin(month_sel) &
    df["producto"].isin(prod_sel)
].copy()

# ====== PERIODOS CRONOLÓGICOS ======
# 1) crear columna combinada
df_f["periodo"] = df_f["year"] + " " + df_f["mes"]

# 2) extraer orden único de periodos desde los datos filtrados
der_periodos = df_f["periodo"].drop_duplicates().reset_index(drop=True)

# 3) orden cronológico personalizado
periodos_orden = sorted(
    der_periodos,
    key=lambda x: (
        int(x.split()[0]),
        list(NUM2MONTH.values()).index(x.split()[1])
    )
)

# 4) aplicar como categoría ordenada
df_f["periodo"] = pd.Categorical(
    df_f["periodo"],
    categories=periodos_orden,
    ordered=True
)

# ====== GRÁFICO MENSUAL ======
st.subheader("Variación Porcentual Mensual por Producto")
monthly = df_f.pivot_table(
    index="periodo",
    columns="producto",
    values="variacion",
    aggfunc="mean"
)
# reindex solo con los periodos reales
disponibles = [p for p in periodos_orden if p in monthly.index]
monthly = monthly.reindex(disponibles)
st.line_chart(monthly)

# ====== INTERPRETACIONES ======
st.subheader("📝 Interpretaciones y Conclusiones")
avg = df_f["variacion"].mean()
st.markdown(f"- Variación media: **{avg:.2f}%**.")

row_max = df_f.loc[df_f["variacion"].idxmax()]
st.markdown(
    f"- Mayor alza: _{row_max['producto']}_ +{row_max['variacion']:.2f}% "
    f"en {row_max['periodo']}."
)

row_min = df_f.loc[df_f["variacion"].idxmin()]
st.markdown(
    f"- Mayor baja: _{row_min['producto']}_ {row_min['variacion']:.2f}% "
    f"en {row_min['periodo']}."
)

# ====== DATOS DETALLADOS ======
st.subheader("Datos Detallados")
st.dataframe(
    df_f[["year","mes","producto","variacion"]]
      .sort_values(["periodo","producto"])
      .reset_index(drop=True),
    use_container_width=True
)
