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
# Intentar cargar datos desde este año.
START_YEAR_DATA = 2015
current_year = datetime.date.today().year
YEARS = {}
for year_num in range(START_YEAR_DATA, current_year + 1):
    year_str = str(year_num)
    if year_num < current_year:
        # Todos los meses para años pasados completos
        YEARS[year_str] = [f"{i:02d}" for i in range(1, 13)]
    else:
        # Hasta el mes actual (o el anterior si el actual no está disponible) para el año en curso
        # Consideramos que el informe del mes M se publica en M+1, así que tomamos el mes anterior como referencia segura.
        # Si estamos en Enero, tomamos Diciembre del año anterior.
        current_month_for_data = datetime.date.today().month
        if datetime.date.today().day < 15: # Si es antes de mediados de mes, es menos probable que esté el informe del mes anterior
             current_month_for_data -=1
        if current_month_for_data == 0: # Si era Enero y restamos 1, vamos a Diciembre del año pasado (ya cubierto por el loop)
            if str(current_year -1) in YEARS: # Asegurar que el año anterior esté en YEARS
                 YEARS[str(current_year -1)] = [f"{i:02d}" for i in range(1, 13)]
            # Para el año actual, si es Enero y no hay datos, no agregar meses.
            if year_str == str(current_year) and current_month_for_data == 0 :
                pass # No agregar meses para el año actual si es Enero muy temprano
            else:
                 YEARS[year_str] = [f"{i:02d}" for i in range(1, current_month_for_data + 1 if current_month_for_data > 0 else 0)]
        else:
            YEARS[year_str] = [f"{i:02d}" for i in range(1, current_month_for_data + 1)]


SKIP_PAGES = 4
NUM2MONTH = {
    '01': 'Enero', '02': 'Febrero', '03': 'Marzo',
    '04': 'Abril', '05': 'Mayo', '06': 'Junio',
    '07': 'Julio', '08': 'Agosto', '09': 'Septiembre',
    '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
}
LINE_REGEX = re.compile(r"^(.+?)\s+(-?\d+[.,]\d+)$")

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

PRODUCT_CATEGORIES = {
    "Cereales y Harinas": ["Arroz", "Harina de trigo", "Avena", "Espiral"],
    "Panadería y Masas": ["Pan corriente sin envasar", "Torta 15 o 20 personas", "Prepizza familiar", "Biscochos dulces y medialunas", "Tostadas (palta o mantequilla o mermelada o mezcla de estas)"],
    "Carnes Rojas y Procesados": ["Carne molida", "Chuleta de cerdo centro o vetada", "Costillar de cerdo", "Pulpa de cerdo", "Jamón de cerdo", "Longaniza", "Salchicha y vienesa tradicional", "Pate", "Aliado (jamón queso) o Barros Jarpa", "Asiento"], # Asiento agregado
    "Aves y Derivados": ["Pollo entero", "Pechuga de pollo", "Trutro de pollo", "Carne de pavo molida", "Salchicha y vienesa de ave", "Pollo asado entero"],
    "Cordero": ["Pulpa de cordero fresco o refrigerado"],
    "Pescados y Mariscos": ["Merluza fresca o refrigerada", "Choritos frescos o refrigerados en su concha", "Jurel en conserva", "Surtido en conserva"],
    "Lácteos y Huevos": ["Leche líquida entera", "Leche en polvo entera instantánea", "Yogurt", "Queso Gouda", "Quesillo y queso fresco con sal", "Queso crema", "Mantequilla con sal", "Margarina", "Huevo de gallina"],
    "Aceites y Grasas": ["Aceite vegetal combinado o puro"],
    "Frutas": ["Plátano", "Manzana", "Limón", "Palta"],
    "Legumbres y Frutos Secos": ["Poroto", "Lenteja", "Maní salado"],
    "Verduras y Tubérculos": ["Lechuga", "Zapallo", "Tomate", "Zanahoria", "Cebolla nueva", "Papa de guarda", "Choclo congelado"],
    "Azúcares y Dulces": ["Azúcar", "Chocolate", "Caramelo", "Helado familiar un sabor", "Galleta dulce"], # Galleta dulce agregada
    "Snacks Salados": ["Galleta no dulce", "Papas fritas"], # Nueva categoría para Galleta no dulce
    "Salsas y Condimentos": ["Salsa de tomate"],
    "Bebestibles (Café, Té)": ["Sucedáneo de café", "Te para preparar", "Té corriente"], # Categoría renombrada y Té corriente agregado
    "Bebidas Frías y Refrescos": ["Agua mineral", "Bebida gaseosa tradicional", "Bebida energizante", "Refresco isotónico", "Jugo líquido", "Néctar líquido", "Refresco en polvo"],
    "Comidas Preparadas y Rápidas": ["Completo", "Entrada (ensalada o sopa)", "Postre para almuerzo", "Promoción de comida rápida", "Empanada de horno", "Colación o menú del día o almuerzo ejecutivo", "Plato de fondo para almuerzo"], # Categoría renombrada
    "Sin Categoría": []
}

# Definición de Periodos Presidenciales (Chile)
# Considerar que los datos de la fuente pueden empezar en START_YEAR_DATA
PRESIDENTIAL_PERIODS = {
    "Todos los Periodos": None,
    "Gabriel Boric (Mar 2022 - Actualidad)": {"start_year": 2022, "start_month": 3, "end_year": current_year, "end_month": datetime.date.today().month},
    "Sebastián Piñera (Mar 2018 - Mar 2022)": {"start_year": 2018, "start_month": 3, "end_year": 2022, "end_month": 3},
    "Michelle Bachelet (Mar 2014 - Mar 2018)": {"start_year": 2014, "start_month": 3, "end_year": 2018, "end_month": 3},
}


@st.cache_data(ttl=3600 * 6)
def fetch_pdf_content_cached(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.content
    except requests.exceptions.RequestException:
        return None

@st.cache_data(ttl=3600 * 2) # Cachear datos procesados por 2 horas
def load_data(years_config):
    rows = []
    sorted_years_keys = sorted(years_config.keys())

    for year in sorted_years_keys:
        meses = years_config[year]
        if not meses: # Si no hay meses para este año (ej. año actual muy temprano)
            continue
        short_year = year[2:]
        for mm in meses:
            url = (
                f"https://observatorio.ministeriodesarrollosocial.gob.cl"
                f"/storage/docs/cba/nueva_serie/{year}"
                f"/Valor_CBA_y_LPs_{short_year}.{mm}.pdf"
            )
            pdf_bytes = fetch_pdf_content_cached(url)
            if not pdf_bytes:
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
                            if product_name not in FIXED_PRODUCTS:
                                continue
                            if abs(value) > 200:
                                continue
                            rows.append({
                                "year": int(year), # Convertir a int para facilitar comparaciones
                                "mes_num": int(mm), # Guardar número de mes para orden y filtros
                                "mes": month_name,
                                "producto": product_name,
                                "variacion": value
                            })
            except Exception:
                continue
    
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    
    # Asegurar tipos correctos para columnas clave
    df['year'] = df['year'].astype(int)
    df['mes_num'] = df['mes_num'].astype(int)

    return df.drop_duplicates(subset=["year", "mes", "producto"], keep='first')


def calculate_yearly_cumulative_variation(df_product_year):
    if df_product_year.empty:
        return 0.0
    df_sorted = df_product_year.copy().sort_values('mes_num')
    cumulative_factor = 1.0
    for var in df_sorted['variacion']:
        cumulative_factor *= (1 + var / 100.0)
    return (cumulative_factor - 1) * 100.0

# ====== CONFIGURACIÓN DE LA PÁGINA ======
st.set_page_config(page_title="Monitor Canasta Básica Chile", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica de Alimentos - Chile")

with st.spinner("🔄 Cargando y procesando datos de los PDFs… Esto puede tardar unos momentos, especialmente la primera vez o con rangos amplios de años."):
    df_data_full = load_data(YEARS) # Cargar todos los datos según YEARS

if df_data_full.empty:
    st.error("⚠️ No se encontraron datos para los productos y periodos configurados. Verifica `FIXED_PRODUCTS`, la configuración de `YEARS` y la disponibilidad de los PDFs en la fuente.")
    st.stop()

# Convertir 'year' a string para consistencia con filtros que esperan strings, pero mantener datos numéricos para lógica
df_display_data = df_data_full.copy()
df_display_data['year'] = df_display_data['year'].astype(str)


# ====== BARRA LATERAL DE FILTROS ======
st.sidebar.header("Filtros de Visualización")

# --- Filtro por Período Presidencial ---
selected_presidential_period_name = st.sidebar.selectbox(
    "Periodo Presidencial",
    options=list(PRESIDENTIAL_PERIODS.keys()),
    index=0 # Default a "Todos los Periodos"
)
selected_period_details = PRESIDENTIAL_PERIODS[selected_presidential_period_name]

# Filtrar df_display_data si se selecciona un período presidencial específico
df_filtered_by_presidency = df_display_data.copy()
if selected_period_details:
    start_year = selected_period_details["start_year"]
    start_month = selected_period_details["start_month"]
    end_year = selected_period_details["end_year"]
    end_month = selected_period_details["end_month"]

    # Crear una columna de fecha para facilitar el filtrado por rango presidencial
    # Usamos el día 1 como referencia, ya que solo necesitamos mes y año.
    # Convertir 'year' y 'mes_num' de df_data_full (que son int) para esta comparación
    
    df_temp_for_presidency_filter = df_data_full.copy()
    # Asegurar que no haya errores si mes_num es 0 o inválido (aunque no debería pasar con la carga actual)
    df_temp_for_presidency_filter = df_temp_for_presidency_filter[df_temp_for_presidency_filter['mes_num'].between(1,12)]

    df_temp_for_presidency_filter["fecha_periodo"] = pd.to_datetime(
        df_temp_for_presidency_filter['year'].astype(str) + '-' + 
        df_temp_for_presidency_filter['mes_num'].astype(str) + '-01',
        format='%Y-%m-%d'
    )
    
    start_date = pd.to_datetime(f"{start_year}-{start_month:02d}-01")
    # Para el mes final, queremos incluir todo el mes, así que vamos al primer día del siguiente mes.
    if end_month == 12:
        end_date_limit = pd.to_datetime(f"{end_year + 1}-01-01")
    else:
        end_date_limit = pd.to_datetime(f"{end_year}-{end_month + 1:02d}-01")

    df_temp_for_presidency_filter = df_temp_for_presidency_filter[
        (df_temp_for_presidency_filter["fecha_periodo"] >= start_date) &
        (df_temp_for_presidency_filter["fecha_periodo"] < end_date_limit)
    ]
    
    # Recrear df_filtered_by_presidency a partir de los datos filtrados por presidencia
    # y convertir 'year' de nuevo a string para los selectores de multiselect.
    df_filtered_by_presidency = df_temp_for_presidency_filter.copy()
    df_filtered_by_presidency['year'] = df_filtered_by_presidency['year'].astype(str)
    # Quitar la columna temporal
    if 'fecha_periodo' in df_filtered_by_presidency.columns:
       df_filtered_by_presidency = df_filtered_by_presidency.drop(columns=['fecha_periodo'])


# --- Filtro por Año ---
# Usar los años disponibles DESPUÉS de filtrar por presidencia
available_years_in_filtered_df = sorted(df_filtered_by_presidency["year"].unique(), reverse=True)
if not available_years_in_filtered_df and selected_period_details:
    st.sidebar.warning(f"No hay datos disponibles para el periodo presidencial '{selected_presidential_period_name}' con los años cargados ({START_YEAR_DATA}-{current_year}).")
    selected_years = []
elif not available_years_in_filtered_df:
    st.sidebar.warning("No hay años con datos disponibles.")
    selected_years = []
else:
    # Si se seleccionó un periodo presidencial, los años por defecto son todos los de ese periodo.
    # Sino, el año más reciente.
    default_years_selection = available_years_in_filtered_df if selected_period_details else [available_years_in_filtered_df[0]]
    selected_years = st.sidebar.multiselect("Año(s)", available_years_in_filtered_df, default=default_years_selection)


# --- Filtro por Mes ---
if selected_years:
    months_in_selected_years = df_filtered_by_presidency[df_filtered_by_presidency["year"].isin(selected_years)]["mes"].unique()
    ordered_available_months = sorted(months_in_selected_years, key=lambda m: list(NUM2MONTH.values()).index(m))
    selected_months = st.sidebar.multiselect("Mes(es)", ordered_available_months, default=ordered_available_months)
else:
    selected_months = []
    ordered_available_months = []


# --- Filtro de Productos por Categoría ---
st.sidebar.subheader("Filtro de Productos")
products_found_in_data = sorted(df_filtered_by_presidency["producto"].unique()) # Usar productos del DF ya filtrado por presidencia/años
master_list_of_selectable_products = [p for p in FIXED_PRODUCTS if p in products_found_in_data]

if not master_list_of_selectable_products:
    st.sidebar.warning("No se encontraron datos para los productos definidos en `FIXED_PRODUCTS` con los filtros actuales.")
    selected_products = []
else:
    categorized_prods_flat = {prod for cat_name, cat_prods in PRODUCT_CATEGORIES.items() if cat_name != "Sin Categoría" for prod in cat_prods}
    PRODUCT_CATEGORIES["Sin Categoría"] = sorted([
        p for p in master_list_of_selectable_products if p not in categorized_prods_flat
    ])
    active_categories = {
        cat: sorted([p for p in prods if p in master_list_of_selectable_products])
        for cat, prods in PRODUCT_CATEGORIES.items()
    }
    active_categories = {cat: prods for cat, prods in active_categories.items() if prods}
    category_options = ["Todas"] + sorted(list(active_categories.keys()))
    selected_category_option = st.sidebar.selectbox("Categoría de Producto", category_options, index=0)

    products_for_multiselect = []
    if selected_category_option == "Todas":
        products_for_multiselect = master_list_of_selectable_products
    elif selected_category_option in active_categories:
        products_for_multiselect = active_categories[selected_category_option]
    products_for_multiselect = sorted(list(set(products_for_multiselect)))

    if not products_for_multiselect:
        st.sidebar.info("No hay productos disponibles para la categoría seleccionada con los filtros actuales.")
        selected_products = []
    else:
        selected_products = st.sidebar.multiselect(
            f"Producto(s) en '{selected_category_option}'",
            products_for_multiselect,
            default=products_for_multiselect
        )

# ====== FILTRAR DATOS PARA VISUALIZACIÓN FINAL ======
if not selected_years or not selected_months or not selected_products:
    st.warning("Por favor, selecciona al menos un año, un mes y un producto para ver los resultados.")
    df_final_filtered = pd.DataFrame()
else:
    # Aplicar filtros de año, mes y producto al df_filtered_by_presidency
    df_final_filtered = df_filtered_by_presidency[
        df_filtered_by_presidency["year"].isin(selected_years) &
        df_filtered_by_presidency["mes"].isin(selected_months) &
        df_filtered_by_presidency["producto"].isin(selected_products)
    ].copy()


# ====== VISUALIZACIONES Y DATOS ======
if not df_final_filtered.empty:
    # --- KPI: Variación Acumulada Año en Curso (si está seleccionado) ---
    current_year_str_kpi = str(datetime.date.today().year)
    if current_year_str_kpi in selected_years:
        st.header(f"Resumen Año {current_year_str_kpi}")
        # Usar df_data_full para el KPI para tener todos los meses del año actual, luego filtrar por productos seleccionados
        df_current_year_for_kpi_source = df_data_full[
            (df_data_full['year'] == int(current_year_str_kpi)) & # Comparar con int year
            (df_data_full['producto'].isin(selected_products))
        ]
        
        cumulative_variations_calc = []
        if not df_current_year_for_kpi_source.empty:
            for prod_name in df_current_year_for_kpi_source['producto'].unique():
                df_single_prod_curr_year = df_current_year_for_kpi_source[df_current_year_for_kpi_source['producto'] == prod_name]
                if not df_single_prod_curr_year.empty:
                    cum_var = calculate_yearly_cumulative_variation(df_single_prod_curr_year)
                    cumulative_variations_calc.append(cum_var)
            if cumulative_variations_calc:
                avg_cumulative_variation = sum(cumulative_variations_calc) / len(cumulative_variations_calc)
                st.metric(
                    label=f"Variación Acumulada Promedio {current_year_str_kpi} (Prod. Seleccionados)",
                    value=f"{avg_cumulative_variation:.2f}%"
                )
            else:
                st.info(f"No hay suficientes datos mensuales en {current_year_str_kpi} para los productos seleccionados para calcular la variación acumulada.")
        else:
            st.info(f"No hay datos para el año {current_year_str_kpi} con los productos seleccionados para calcular la variación acumulada.")
        st.divider()

    # --- Preparación de Periodo para Gráficos ---
    df_final_filtered["periodo"] = df_final_filtered["year"].astype(str) + " " + df_final_filtered["mes"]
    
    # Orden cronológico global de todos los periodos posibles en los datos originales (df_data_full)
    # Convertir year y mes_num a string para crear el periodo
    df_data_full_copy = df_data_full.copy()
    df_data_full_copy['periodo_temp'] = df_data_full_copy['year'].astype(str) + " " + df_data_full_copy['mes']
    
    all_periods_ordered_globally = sorted(
        df_data_full_copy["periodo_temp"].unique(),
        key=lambda x: (
            int(x.split()[0]), 
            list(NUM2MONTH.values()).index(x.split()[1])
        )
    )
    actual_periods_in_filtered_data = df_final_filtered["periodo"].unique()
    ordered_periods_for_chart = [p for p in all_periods_ordered_globally if p in actual_periods_in_filtered_data]

    if ordered_periods_for_chart:
        df_final_filtered["periodo"] = pd.Categorical(
            df_final_filtered["periodo"],
            categories=ordered_periods_for_chart,
            ordered=True
        )

        st.header("Análisis de Variaciones")
        st.subheader("Variación Porcentual Mensual por Producto")
        monthly_pivot = df_final_filtered.pivot_table(
            index="periodo", columns="producto", values="variacion", aggfunc="mean"
        )
        # Reindexar para asegurar el orden cronológico y solo periodos con datos
        # Usar ordered_periods_for_chart que ya está filtrado y ordenado
        monthly_pivot = monthly_pivot.reindex(ordered_periods_for_chart).dropna(how='all', axis=0)


        if not monthly_pivot.empty:
            fig_line = px.line(
                monthly_pivot,
                x=monthly_pivot.index.astype(str), # Asegurar que el índice sea string para el eje x
                y=monthly_pivot.columns,
                labels={'value': 'Variación (%)', 'periodo': 'Período', 'producto': 'Producto'},
            )
            fig_line.update_layout(height=500, legend_title_text='Productos', xaxis_tickangle=-45, hovermode="x unified")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No hay datos suficientes para mostrar el gráfico de líneas con los filtros actuales.")

        st.subheader("Top 5 Alzas y Bajas (Promedio en Período Seleccionado)")
        avg_variation_per_product = df_final_filtered.groupby('producto')['variacion'].mean().sort_values()
        top_increases = avg_variation_per_product[avg_variation_per_product > 0].nlargest(5).sort_values(ascending=False)
        top_decreases = avg_variation_per_product[avg_variation_per_product <= 0].nsmallest(5).sort_values(ascending=True)
        combined_tops = pd.concat([top_decreases, top_increases.iloc[::-1]] ).sort_values()

        if not combined_tops.empty:
            colors = ['#d62728' if v < 0 else ('#2ca02c' if v > 0 else '#7f7f7f') for v in combined_tops.values]
            fig_bar_tops = go.Figure(go.Bar(
                y=combined_tops.index, x=combined_tops.values, orientation='h',
                marker_color=colors, text=combined_tops.values, texttemplate='%{text:.2f}%', textposition='outside'
            ))
            fig_bar_tops.update_layout(
                xaxis_title="Variación Promedio (%)", yaxis_title="Producto",
                height=max(400, len(combined_tops) * 35 + 100), 
                yaxis_autorange="reversed" # Muestra las mayores alzas (positivas) arriba
            )
            st.plotly_chart(fig_bar_tops, use_container_width=True)
        else:
            st.info("No hay suficientes datos para mostrar el top de alzas y bajas con los filtros actuales.")

        st.subheader("📝 Interpretaciones (Periodo Seleccionado)")
        if not df_final_filtered["variacion"].empty and df_final_filtered["variacion"].notna().any():
            avg_overall_variation = df_final_filtered["variacion"].mean()
            st.markdown(f"- **Variación media general** de los productos seleccionados: **{avg_overall_variation:.2f}%**.")
            idx_max = df_final_filtered["variacion"].idxmax()
            row_max_variation = df_final_filtered.loc[idx_max]
            st.markdown(f"- **Mayor alza puntual registrada**: _{row_max_variation['producto']}_ con **+{row_max_variation['variacion']:.2f}%** en {row_max_variation['periodo']}.")
            idx_min = df_final_filtered["variacion"].idxmin()
            row_min_variation = df_final_filtered.loc[idx_min]
            st.markdown(f"- **Mayor baja puntual registrada**: _{row_min_variation['producto']}_ con **{row_min_variation['variacion']:.2f}%** en {row_min_variation['periodo']}.")
        else:
            st.markdown("- No hay datos de variación disponibles para calcular interpretaciones con los filtros actuales.")
    else:
        st.info("No hay datos de período para mostrar después de aplicar los filtros.")
        
    st.header("📄 Datos Detallados")
    # Columnas a mostrar en la tabla de datos detallados
    cols_to_show = ["year", "mes", "producto", "variacion"]
    # Asegurar que 'periodo' exista antes de intentar ordenarlo o quitarlo
    if "periodo" in df_final_filtered.columns:
        df_display_detailed = df_final_filtered.sort_values(["periodo", "producto"])
        # cols_to_show.append("periodo") # Descomentar si se quiere mostrar la columna periodo
    else:
        # Si no hay 'periodo', ordenar por año y mes_num (del df_data_full subyacente)
        # Necesitamos traer mes_num a df_final_filtered si no está.
        if 'mes_num' not in df_final_filtered.columns and 'year' in df_final_filtered.columns and 'mes' in df_final_filtered.columns:
             # Crear mes_num_map_inv para mapear nombre de mes a número
             mes_num_map_inv = {v: k for k, v in NUM2MONTH.items()}
             df_final_filtered['mes_num_temp'] = df_final_filtered['mes'].map(lambda m: int(mes_num_map_inv.get(m, 0)))
             df_display_detailed = df_final_filtered.sort_values([("year", "astype", "int"), "mes_num_temp", "producto"])
             df_display_detailed = df_display_detailed.drop(columns=['mes_num_temp'])
        else:
             df_display_detailed = df_final_filtered.sort_values([("year", "astype", "int"), ("mes_num", "astype", "int"), "producto"])


    st.dataframe(
        df_display_detailed[cols_to_show],
        use_container_width=True,
        hide_index=True
    )

elif selected_years and selected_months and selected_products: # Si hubo selección pero no resultaron datos
    st.info("No se encontraron datos que coincidan con todos los filtros seleccionados.")

st.sidebar.markdown("---")
st.sidebar.info("Aplicación para monitorear la Canasta Básica de Alimentos en Chile. Los datos se obtienen del Observatorio Social, Ministerio de Desarrollo Social y Familia.")
