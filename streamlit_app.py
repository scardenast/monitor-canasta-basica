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
    "Arroz","Pan corriente sin envasar","Espiral","Galleta dulce","Galleta no dulce",
    "Torta 15 o 20 personas","Prepizza familiar","Harina de trigo","Avena","Asiento",
    "Carne molida","Chuleta de cerdo centro o vetada","Costillar de cerdo","Pulpa de cerdo",
    "Carne de pavo molida","Pechuga de pollo","Pollo entero","Trutro de pollo",
    "Pulpa de cordero fresco o refrigerado","Salchicha y vienesa de ave",
    "Salchicha y vienesa tradicional","Longaniza","Jamón de cerdo","Pate",
    "Merluza fresca o refrigerada","Choritos frescos o refrigerados en su concha",
    "Jurel en conserva","Surtido en conserva","Leche líquida entera",
    "Leche en polvo entera instantánea","Yogurt","Queso Gouda","Quesillo y queso fresco con sal",
    "Queso crema","Huevo de gallina","Mantequilla con sal","Margarina",
    "Aceite vegetal combinado o puro","Plátano","Manzana","Maní salado","Poroto",
    "Lenteja","Lechuga","Zapallo","Limón","Palta","Tomate","Zanahoria",
    "Cebolla nueva","Choclo congelado","Papa de guarda","Azúcar","Chocolate",
    "Caramelo","Helado familiar un sabor","Salsa de tomate","Sucedáneo de café",
    "Te para preparar","Agua mineral","Bebida gaseosa tradicional","Bebida energizante",
    "Refresco isotónico","Jugo líquido","Néctar líquido","Refresco en polvo","Completo",
    "Papas fritas","Té corriente","Biscochos dulces y medialunas","Entrada (ensalada o sopa)",
    "Postre para almuerzo","Promoción de comida rápida",
    "Tostadas (palta o mantequilla o mermelada o mezcla de estas)",
    "Aliado (jamón queso) o Barros Jarpa","Pollo asado entero","Empanada de horno",
    "Colación o menú del día o almuerzo ejecutivo","Plato de fondo para almuerzo"
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
                r = requests.get(url); r.raise_for_status()
            except:
                continue
            mes_nombre = NUM2MONTH[mm]
            with pdfplumber.open(BytesIO(r.content)) as pdf:
                for i,page in enumerate(pdf.pages):
                    if i < SKIP_PAGES: continue
                    for line in (page.extract_text() or "").split("\n"):
                        m = LINE_REGEX.match(line.strip())
                        if not m: continue
                        prod = m.group(1).strip()
                        val  = float(m.group(2).replace(",","."))
                        if prod.lower()=="cba": continue
                        if prod not in FIXED_PRODUCTS: continue
                        if abs(val)>100: continue
                        rows.append({"year":year,"mes":mes_nombre,
                                     "producto":prod,"variacion":val})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.drop_duplicates(["year","mes","producto"] )

# APP
st.set_page_config(page_title="Monitor Canasta Básica", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica")
with st.spinner("🔄 Cargando…"):
    df = load_data()
if df.empty:
    st.error("⚠️ No se encontraron datos.")
    st.stop()

# Sidebar
st.sidebar.header("Filtros")

years = sorted(df["year"].unique())
year_sel = st.sidebar.multiselect("Año", years, default=years)
months = sorted(df[df["year"].isin(year_sel)]["mes"].unique(),
                key=lambda m: list(NUM2MONTH.values()).index(m))
month_sel = st.sidebar.multiselect("Mes", months, default=months)
prod_sel = st.sidebar.multiselect("Producto", FIXED_PRODUCTS, default=FIXED_PRODUCTS)

# Filtrar
df_f = df[df["year"].isin(year_sel) & df["mes"].isin(month_sel) & df["producto"].isin(prod_sel)]

# Periodo
periodos = [f"{y} {m}" for y in years for m in MONTHS_BY_YEAR[y] if y in year_sel and m in month_sel]
df_f["periodo"] = df_f["year"] + " " + df_f["mes"]
df_f["periodo"] = pd.Categorical(df_f["periodo"], categories=periodos, ordered=True)

# Gráfico mensual
st.subheader("Variación Porcentual Mensual por Producto")
monthly = df_f.pivot_table(index="periodo", columns="producto", values="variacion", aggfunc="mean")
monthly = monthly.reindex(periodos).dropna(how="all")
st.line_chart(monthly)

# Interpretaciones
st.subheader("📝 Interpretaciones y Conclusiones")
avg = df_f["variacion"].mean()
st.markdown(f"- Variación media: **{avg:.2f}%**.")
row_max = df_f.loc[df_f["variacion"].idxmax()]
st.markdown(f"- Mayor alza: _{row_max['producto']}_ +{row_max['variacion']:.2f}% en {row_max['periodo']}.")
row_min = df_f.loc[df_f["variacion"].idxmin()]
st.markdown(f"- Mayor baja: _{row_min['producto']}_ {row_min['variacion']:.2f}% en {row_min['periodo']}.")

# Datos detallados
st.subheader("Datos Detallados")
st.dataframe(df_f[["year","mes","producto","variacion"]]
              .sort_values(["periodo","producto"]).reset_index(drop=True),
              use_container_width=True)
