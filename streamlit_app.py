import streamlit as st
import pandas as pd
import pdfplumber
import requests
import re
from io import BytesIO
import datetime
import plotly.express as px
import plotly.graph_objects as go

# ====== CONFIGURACIÓN ======
YEARS = {
    # Año actual y dos anteriores para tener un rango por defecto
    str(datetime.date.today().year - 2): [f"{i:02d}" for i in range(1, 13)],
    str(datetime.date.today().year - 1): [f"{i:02d}" for i in range(1, 13)],
    str(datetime.date.today().year): [f"{i:02d}" for i in range(1, datetime.date.today().month + 1)], # Hasta el mes actual
    # '2024': [f"{i:02d}" for i in range(1, 13)],
    # '2025': [f"{i:02d}" for i in range(1, 4)], # Ejemplo para meses futuros
}
SKIP_PAGES = 4
NUM2MONTH = {
    '01': 'Enero', '02': 'Febrero', '03': 'Marzo',
    '04': 'Abril', '05': 'Mayo', '06': 'Junio',
    '07': 'Julio', '08': 'Agosto', '09': 'Septiembre',
    '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
}
LINE_REGEX = re.compile(r"^(.+?)\s+(-?\d+[.,]\d+)$")

# !!! IMPORTANTE: DEFINE AQUÍ TODOS LOS PRODUCTOS QUE QUIERES MONITOREAR !!!
# Esta lista es la fuente maestra de productos.
FIXED_PRODUCTS = [
"Arroz","Pan corriente sin envasar","Espiral","Galleta dulce","Galleta no dulce",
    "Torta 15 o 20 personas","Prepizza familiar","Harina de trigo","Avena","Asiento",
    "Carne molida","Chuleta de cerdo centro o vetada","Costillar de cerdo","Pulpa de cerdo",
    "Carne de pavo molida","Pechuga de pollo","Pollo entero","Trutro de pollo",
    "Pulpa de cordero fresco o refrigerado","Salchicha y vienesa de ave",
    "Salchicha y vienesa tradicional","Longaniza","Jamón de cerdo","Pate",
    "Merluza fresca o refrigerada","Choritos frescos o refrigerados en su concha",
    "Jurel en conserva","Surtido en conserva","Leche líquida entera",
    "Leche en polvo entera instantánea","Yogurt","Queso Gouda",
    "Quesillo y queso fresco con sal","Queso crema","Huevo de gallina",
    "Mantequilla con sal","Margarina","Aceite vegetal combinado o puro",
    "Plátano","Manzana","Maní salado","Poroto","Lenteja","Lechuga","Zapallo",
    "Limón","Palta","Tomate","Zanahoria","Cebolla nueva","Choclo congelado",
    "Papa de guarda","Azúcar","Chocolate","Caramelo","Helado familiar un sabor",
    "Salsa de tomate","Sucedáneo de café","Te para preparar","Agua mineral",
    "Bebida gaseosa tradicional","Bebida energizante","Refresco isotónico",
    "Jugo líquido","Néctar líquido","Refresco en polvo","Completo","Papas fritas",
    "Té corriente","Biscochos dulces y medialunas","Entrada (ensalada o sopa)",
    "Postre para almuerzo","Promoción de comida rápida",
    "Tostadas (palta o mantequilla o mermelada o mezcla de estas)",
    "Aliado (jamón queso) o Barros Jarpa","Pollo asado entero","Empanada de horno",
    "Colación o menú del día o almuerzo ejecutivo","Plato de fondo para almuerzo"
]

# !!! IMPORTANTE: ORGANIZA TUS PRODUCTOS DE FIXED_PRODUCTS EN CATEGORÍAS !!!
PRODUCT_CATEGORIES = {
    "Cereales y Harinas": [
        "Arroz",
        "Harina de trigo",
        "Avena",
        "Espiral"
    ],
    "Panadería y Masas": [
        "Pan corriente sin envasar",
        "Torta 15 o 20 personas",
        "Prepizza familiar",
        "Biscochos dulces y medialunas",
        "Tostadas (palta o mantequilla o mermelada o mezcla de estas)"
    ],
    "Carnes Rojas y Procesados": [
        "Carne molida",
        "Chuleta de cerdo centro o vetada",
        "Costillar de cerdo",
        "Pulpa de cerdo",
        "Jamón de cerdo",
        "Longaniza",
        "Salchicha y vienesa tradicional",
        "Pate",
        "Aliado (jamón queso) o Barros Jarpa"
    ],
    "Aves y Derivados": [
        "Pollo entero",
        "Pechuga de pollo",
        "Trutro de pollo",
        "Carne de pavo molida",
        "Salchicha y vienesa de ave",
        "Pollo asado entero"
    ],
    "Cordero": [
        "Pulpa de cordero fresco o refrigerado"
    ],
    "Pescados y Mariscos": [
        "Merluza fresca o refrigerada",
        "Choritos frescos o refrigerados en su concha",
        "Jurel en conserva",
        "Surtido en conserva"
    ],
    "Lácteos y Huevos": [
        "Leche líquida entera",
        "Leche en polvo entera instantánea",
        "Yogurt",
        "Queso Gouda",
        "Quesillo y queso fresco con sal",
        "Queso crema",
        "Mantequilla con sal",
        "Margarina",
        "Huevo de gallina"
    ],
    "Aceites y Grasas": [
        "Aceite vegetal combinado o puro"
    ],
    "Frutas": [
        "Plátano",
        "Manzana",
        "Limón",
        "Palta"
    ],
    "Legumbres y Frutos Secos": [
        "Poroto",
        "Lenteja",
        "Maní salado"
    ],
    "Verduras y Tubérculos": [
        "Lechuga",
        "Zapallo",
        "Tomate",
        "Zanahoria",
        "Cebolla nueva",
        "Papa de guarda",
        "Choclo congelado"
    ],
    "Azúcares y Dulces": [
        "Azúcar",
        "Chocolate",
        "Caramelo",
        "Helado familiar un sabor"
    ],
    "Salsas y Condimentos": [
        "Salsa de tomate",
        "Sucedáneo de café",
        "Te para preparar"
    ],
    "Bebidas Frías y Refrescos": [
        "Agua mineral",
        "Bebida gaseosa tradicional",
        "Bebida energizante",
        "Refresco isotónico",
        "Jugo líquido",
        "Néctar líquido",
        "Refresco en polvo",
        "Té corriente"
    ],
    "Snacks y Platos Preparados": [
        "Completo",
        "Papas fritas",
        "Entrada (ensalada o sopa)",
        "Postre para almuerzo",
        "Promoción de comida rápida",
        "Empanada de horno",
        "Colación o menú del día o almuerzo ejecutivo",
        "Plato de fondo para almuerzo"
    ],
    "Sin Categoría": []
}
 # Se poblará automáticamente con productos de FIXED_PRODUCTS no listados arriba


@st.cache_data(ttl=3600 * 6) # Cachear por 6 horas
def fetch_pdf_content_cached(url):
    """
    Descarga el contenido de un PDF desde una URL y lo cachea.
    Retorna los bytes del contenido o None si falla.
    """
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.content
    except requests.exceptions.RequestException as e:
        # st.warning(f"No se pudo descargar el PDF: {url}. Error: {e}") # Descomentar para depuración
        return None

@st.cache_data(ttl=3600) # Cachear los datos procesados por 1 hora
def load_data():
    """
    Carga los datos de variación de precios de productos desde PDFs online.
    """
    rows = []
    # Ordenar YEARS para procesar en orden cronológico (útil si se quisiera lógica dependiente del orden)
    sorted_years = sorted(YEARS.keys())

    for year in sorted_years:
        meses = YEARS[year]
        short_year = year[2:]
        for mm in meses:
            url = (
                f"https://observatorio.ministeriodesarrollosocial.gob.cl"
                f"/storage/docs/cba/nueva_serie/{year}"
                f"/Valor_CBA_y_LPs_{short_year}.{mm}.pdf"
            )
            
            pdf_bytes = fetch_pdf_content_cached(url)
            if not pdf_bytes:
                # st.warning(f"Omitiendo {NUM2MONTH[mm]} {year} debido a error de descarga.")
                continue

            month_name = NUM2MONTH[mm]
            try:
                with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                    for i, page in enumerate(pdf.pages):
                        if i < SKIP_PAGES:
                            continue
                        
                        page_text = page.extract_text() or ""
                        for line in page_text.split("\n"):
                            match = LINE_REGEX.match(line.strip())
                            if not match:
                                continue

                            product_name = match.group(1).strip()
                            try:
                                value = float(match.group(2).replace(",", "."))
                            except ValueError:
                                continue
                            
                            if product_name.lower() == "cba":
                                continue
                            if product_name not in FIXED_PRODUCTS: # Solo incluir productos de nuestra lista maestra
                                continue
                            if abs(value) > 200: # Umbral más amplio por si hay variaciones grandes legítimas
                                continue

                            rows.append({
                                "year": year,
                                "mes": month_name,
                                "producto": product_name,
                                "variacion": value
                            })
            except Exception as e:
                # st.warning(f"Error procesando PDF para {month_name} {year} desde {url}: {e}") # Descomentar para depuración
                continue
    
    df = pd.DataFrame(rows)
    return df.drop_duplicates(subset=["year", "mes", "producto"], keep='first') if not df.empty else df

def calculate_yearly_cumulative_variation(df_product_year):
    """
    Calcula la variación acumulada para un producto en un año específico.
    df_product_year: DataFrame filtrado para un solo producto y un solo año.
    """
    if df_product_year.empty:
        return 0.0

    # Crear un mapeo de nombre de mes a número de mes para ordenar
    month_to_num_map = {name: int(num_str) for num_str, name in NUM2MONTH.items()}
    
    # Copiar para evitar SettingWithCopyWarning y añadir columna de número de mes
    df_sorted = df_product_year.copy()
    df_sorted['month_num'] = df_sorted['mes'].map(month_to_num_map)
    df_sorted = df_sorted.sort_values('month_num')

    cumulative_factor = 1.0
    for var in df_sorted['variacion']:
        cumulative_factor *= (1 + var / 100.0)
    return (cumulative_factor - 1) * 100.0

# ====== CONFIGURACIÓN DE LA PÁGINA ======
st.set_page_config(page_title="Monitor Canasta Básica", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica")

with st.spinner("🔄 Cargando datos de los PDFs… Por favor, espere."):
    df_data = load_data()

if df_data.empty:
    st.error("⚠️ No se encontraron datos para los productos y periodos configurados. Verifica `FIXED_PRODUCTS`, `YEARS` y la disponibilidad de los PDFs.")
    st.stop()

# ====== BARRA LATERAL DE FILTROS ======
st.sidebar.header("Filtros")

# Filtro por Año
available_years = sorted(df_data["year"].unique(), reverse=True) # Años más recientes primero
default_years = [available_years[0]] if available_years else []
selected_years = st.sidebar.multiselect("Año(s)", available_years, default=default_years)

# Filtro por Mes
if selected_years:
    # Meses disponibles en los años seleccionados
    months_in_selected_years = df_data[df_data["year"].isin(selected_years)]["mes"].unique()
    # Ordenar meses cronológicamente
    ordered_available_months = sorted(
        months_in_selected_years,
        key=lambda m: list(NUM2MONTH.values()).index(m)
    )
    # Por defecto, seleccionar todos los meses disponibles para los años seleccionados
    selected_months = st.sidebar.multiselect("Mes(es)", ordered_available_months, default=ordered_available_months)
else:
    selected_months = []
    ordered_available_months = []


# --- Filtro de Productos por Categoría ---
st.sidebar.subheader("Filtro de Productos")

products_found_in_data = sorted(df_data["producto"].unique())
master_list_of_selectable_products = [p for p in FIXED_PRODUCTS if p in products_found_in_data]

if not master_list_of_selectable_products:
    st.sidebar.warning("No se encontraron datos para los productos definidos en `FIXED_PRODUCTS` en los PDFs cargados.")
    selected_products = []
else:
    # Poblar "Sin Categoría"
    categorized_prods_flat = {prod for cat_name, cat_prods in PRODUCT_CATEGORIES.items() if cat_name != "Sin Categoría" for prod in cat_prods}
    PRODUCT_CATEGORIES["Sin Categoría"] = sorted([
        p for p in master_list_of_selectable_products if p not in categorized_prods_flat
    ])

    active_categories = {
        cat: sorted([p for p in prods if p in master_list_of_selectable_products])
        for cat, prods in PRODUCT_CATEGORIES.items()
    }
    active_categories = {cat: prods for cat, prods in active_categories.items() if prods} # Quitar categorías vacías

    category_options = ["Todas"] + list(active_categories.keys())
    selected_category_option = st.sidebar.selectbox(
        "Categoría de Producto",
        category_options,
        index=0 # Default a "Todas"
    )

    products_for_multiselect = []
    if selected_category_option == "Todas":
        products_for_multiselect = master_list_of_selectable_products
    elif selected_category_option in active_categories:
        products_for_multiselect = active_categories[selected_category_option]
    
    products_for_multiselect = sorted(list(set(products_for_multiselect)))

    if not products_for_multiselect:
        st.sidebar.info("No hay productos disponibles para la categoría seleccionada.")
        selected_products = []
    else:
        selected_products = st.sidebar.multiselect(
            f"Producto(s) en '{selected_category_option}'",
            products_for_multiselect,
            default=products_for_multiselect 
        )

# ====== FILTRAR DATOS ======
if not selected_years or not selected_months or not selected_products:
    st.warning("Por favor, selecciona al menos un año, un mes y un producto para ver los resultados.")
    df_filtered = pd.DataFrame()
else:
    df_filtered = df_data[
        df_data["year"].isin(selected_years) &
        df_data["mes"].isin(selected_months) &
        df_data["producto"].isin(selected_products)
    ].copy()

# ====== VISUALIZACIONES Y DATOS ======
if not df_filtered.empty:
    # --- KPI: Variación Acumulada Año en Curso ---
    current_year_str = str(datetime.date.today().year)
    if current_year_str in selected_years: # Solo calcular si el año actual está entre los seleccionados
        st.header(f"Resumen Año {current_year_str}")
        df_current_year_for_kpi = df_data[
            (df_data['year'] == current_year_str) &
            (df_data['producto'].isin(selected_products)) & # Solo productos seleccionados globalmente
            (df_data['mes'].isin(ordered_available_months)) # Solo meses disponibles y seleccionados
        ]

        cumulative_variations_calc = []
        if not df_current_year_for_kpi.empty:
            for prod_name in df_current_year_for_kpi['producto'].unique():
                df_single_prod_curr_year = df_current_year_for_kpi[df_current_year_for_kpi['producto'] == prod_name]
                if not df_single_prod_curr_year.empty:
                    cum_var = calculate_yearly_cumulative_variation(df_single_prod_curr_year)
                    cumulative_variations_calc.append(cum_var)
            
            if cumulative_variations_calc:
                avg_cumulative_variation = sum(cumulative_variations_calc) / len(cumulative_variations_calc)
                st.metric(
                    label=f"Variación Acumulada Promedio {current_year_str} (Prod. Seleccionados)",
                    value=f"{avg_cumulative_variation:.2f}%"
                )
            else:
                st.info(f"No hay suficientes datos mensuales en {current_year_str} para los productos seleccionados para calcular la variación acumulada.")
        else:
            st.info(f"No hay datos para el año {current_year_str} con los filtros actuales para calcular la variación acumulada.")
        st.divider()


    # --- Preparación de Periodo para Gráficos ---
    df_filtered["periodo"] = df_filtered["year"] + " " + df_filtered["mes"]
    
    # Orden cronológico global de todos los periodos posibles en los datos originales
    all_periods_ordered_globally = sorted(
        (df_data["year"] + " " + df_data["mes"]).unique(),
        key=lambda x: (
            int(x.split()[0]), 
            list(NUM2MONTH.values()).index(x.split()[1])
        )
    )
    actual_periods_in_filtered_data = df_filtered["periodo"].unique()
    ordered_periods_for_chart = [p for p in all_periods_ordered_globally if p in actual_periods_in_filtered_data]

    if ordered_periods_for_chart:
        df_filtered["periodo"] = pd.Categorical(
            df_filtered["periodo"],
            categories=ordered_periods_for_chart,
            ordered=True
        )

        # --- Gráfico de Líneas: Variación Mensual ---
        st.header("Análisis de Variaciones")
        st.subheader("Variación Porcentual Mensual por Producto")
        monthly_pivot = df_filtered.pivot_table(
            index="periodo", columns="producto", values="variacion", aggfunc="mean"
        )
        monthly_pivot = monthly_pivot.reindex(ordered_periods_for_chart).dropna(how='all', axis=0)

        if not monthly_pivot.empty:
            fig_line = px.line(
                monthly_pivot,
                x=monthly_pivot.index.astype(str),
                y=monthly_pivot.columns,
                labels={'value': 'Variación (%)', 'periodo': 'Período', 'producto': 'Producto'},
                title="" # Título ya está en subheader
            )
            fig_line.update_layout(
                height=500,
                legend_title_text='Productos',
                xaxis_tickangle=-30,
                hovermode="x unified"
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No hay datos suficientes para mostrar el gráfico de líneas con los filtros actuales.")

        # --- Gráfico de Barras: Top 5 Alzas y Bajas ---
        st.subheader("Top 5 Alzas y Bajas (Promedio en Período Seleccionado)")
        avg_variation_per_product = df_filtered.groupby('producto')['variacion'].mean().sort_values()
        
        top_increases = avg_variation_per_product[avg_variation_per_product > 0].nlargest(5).sort_values(ascending=False)
        top_decreases = avg_variation_per_product[avg_variation_per_product <= 0].nsmallest(5).sort_values(ascending=True)
        
        # Concatenar para un solo gráfico, manteniendo el orden deseado para visualización
        # Queremos las bajas más bajas primero, luego las alzas más altas
        combined_tops = pd.concat([top_decreases, top_increases.iloc[::-1]] ).sort_values()


        if not combined_tops.empty:
            colors = ['#d62728' if v < 0 else ('#2ca02c' if v > 0 else '#7f7f7f') for v in combined_tops.values] # Rojo, Verde, Gris
            fig_bar_tops = go.Figure(go.Bar(
                y=combined_tops.index,
                x=combined_tops.values,
                orientation='h',
                marker_color=colors,
                text=combined_tops.values,
                texttemplate='%{text:.2f}%',
                textposition='outside'
            ))
            fig_bar_tops.update_layout(
                # title_text="Top Alzas (Verde) y Bajas (Rojo) Promedio", # Título ya en subheader
                xaxis_title="Variación Promedio (%)",
                yaxis_title="Producto",
                height=max(400, len(combined_tops) * 35 + 100), # Altura dinámica
                yaxis_autorange="reversed" # Para mostrar las mayores alzas arriba si se ordenan así
            )
            st.plotly_chart(fig_bar_tops, use_container_width=True)
        else:
            st.info("No hay suficientes datos para mostrar el top de alzas y bajas con los filtros actuales.")


        # --- Interpretaciones y Conclusiones ---
        st.subheader("📝 Interpretaciones (Periodo Seleccionado)")
        if not df_filtered["variacion"].empty and df_filtered["variacion"].notna().any():
            avg_overall_variation = df_filtered["variacion"].mean()
            st.markdown(f"- **Variación media general** de los productos seleccionados: **{avg_overall_variation:.2f}%**.")

            idx_max = df_filtered["variacion"].idxmax()
            row_max_variation = df_filtered.loc[idx_max]
            st.markdown(
                f"- **Mayor alza puntual registrada**: _{row_max_variation['producto']}_ con **+{row_max_variation['variacion']:.2f}%** en {row_max_variation['periodo']}."
            )

            idx_min = df_filtered["variacion"].idxmin()
            row_min_variation = df_filtered.loc[idx_min]
            st.markdown(
                f"- **Mayor baja puntual registrada**: _{row_min_variation['producto']}_ con **{row_min_variation['variacion']:.2f}%** en {row_min_variation['periodo']}."
            )
        else:
            st.markdown("- No hay datos de variación disponibles para calcular interpretaciones con los filtros actuales.")
    else:
        st.info("No hay datos de período para mostrar después de aplicar los filtros.")
        
    # --- Datos Detallados ---
    st.header("📄 Datos Detallados")
    st.dataframe(
        df_filtered[["year", "mes", "producto", "variacion", "periodo"]]
        .sort_values(["periodo", "producto"])
        .drop(columns=["periodo"] if "periodo" in df_filtered.columns else []),
        use_container_width=True,
        hide_index=True
    )

elif selected_years and selected_months and selected_products:
    st.info("No se encontraron datos que coincidan con todos los filtros seleccionados.")

st.sidebar.markdown("---")
st.sidebar.info("Aplicación desarrollada para monitorear la Canasta Básica de Alimentos en Chile.")

