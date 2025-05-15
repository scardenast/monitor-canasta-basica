import streamlit as st
import pandas as pd
import pdfplumber
import requests
import re
from io import BytesIO
import datetime
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional, Tuple

# ====== CONFIGURACIÓN DE DISEÑO Y ESTILO ======
# Paleta de colores (ejemplo)
COLOR_PRIMARY_TEXT = "#0A2342"  # Azul oscuro para texto principal
COLOR_SECONDARY_TEXT = "#555555" # Gris medio para texto secundario
COLOR_ACCENT = "#007BFF"         # Azul brillante para acentos y gráficos
COLOR_ACCENT_SUCCESS = "#28A745" # Verde para alzas
COLOR_ACCENT_DANGER = "#DC3545"  # Rojo para bajas
COLOR_BACKGROUND_MAIN = "#FFFFFF"
COLOR_BACKGROUND_SIDEBAR = "#F0F2F6" # Gris muy claro para la sidebar
COLOR_BORDER = "#DEE2E6"
FONT_FAMILY_SANS_SERIF = "Inter, sans-serif"

# Logo (reemplazar con la URL o ruta a tu logo)
APP_LOGO_URL = "https://www.shareicon.net/data/2015/10/02/110087_analysis_512x512.png" # Placeholder icon

# CSS Personalizado
CUSTOM_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

body {{
    font-family: {FONT_FAMILY_SANS_SERIF};
    color: {COLOR_PRIMARY_TEXT};
    background-color: {COLOR_BACKGROUND_MAIN};
}}

/* --- Encabezado --- */
.app-header {{
    display: flex;
    align-items: center;
    justify-content: center; /* Centra el título si no hay logo o el logo es pequeño */
    padding: 10px 20px;
    border-bottom: 1px solid {COLOR_BORDER};
    margin-bottom: 20px;
    background-color: {COLOR_BACKGROUND_MAIN};
}}
.app-header img.logo {{
    height: 40px;
    margin-right: 15px;
}}
.app-header .title {{
    font-size: 1.8em;
    font-weight: 600;
    color: {COLOR_PRIMARY_TEXT};
    text-align: center;
    flex-grow: 1; /* Permite que el título ocupe espacio y se centre */
}}

/* --- Barra Lateral --- */
[data-testid="stSidebar"] {{
    background-color: {COLOR_BACKGROUND_SIDEBAR};
    padding: 15px;
}}
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3,
[data-testid="stSidebar"] .stMarkdown p {{
    font-family: {FONT_FAMILY_SANS_SERIF};
    color: {COLOR_PRIMARY_TEXT};
}}
[data-testid="stSidebar"] .stMarkdown h3 {{
    font-size: 1.1em;
    font-weight: 600;
    margin-top: 20px;
    margin-bottom: 10px;
    color: {COLOR_ACCENT};
    border-bottom: 1px solid {COLOR_BORDER};
    padding-bottom: 5px;
}}

/* --- Métricas (KPIs) --- */
div[data-testid="stMetric"] {{
    background-color: #FFFFFF;
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 15px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}}
div[data-testid="stMetric"] label p {{ /* Estilo para la etiqueta del KPI */
    font-size: 0.95em !important;
    font-weight: 500 !important;
    color: {COLOR_SECONDARY_TEXT} !important;
}}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{ /* Estilo para el valor del KPI */
    font-size: 1.8em !important;
    font-weight: 700 !important;
    color: {COLOR_ACCENT} !important;
}}
/* Colores específicos para delta (si se usa) */
div[data-testid="stMetric"] div.st-emotion-cache-1g6goys {{ /* Selector para el delta positivo */
    color: {COLOR_ACCENT_SUCCESS} !important;
}}
div[data-testid="stMetric"] div.st-emotion-cache-mcjb54 {{ /* Selector para el delta negativo */
    color: {COLOR_ACCENT_DANGER} !important;
}}


/* --- Títulos y Texto General --- */
h1, h2, h3 {{
    font-family: {FONT_FAMILY_SANS_SERIF};
    color: {COLOR_PRIMARY_TEXT};
    font-weight: 600;
}}
h1 {{ font-size: 2em; margin-bottom: 0.7em; }}
h2 {{ font-size: 1.5em; margin-top: 1.5em; margin-bottom: 0.6em; color: {COLOR_PRIMARY_TEXT}; border-bottom: 2px solid {COLOR_ACCENT}; padding-bottom: 0.2em;}}
h3 {{ font-size: 1.2em; margin-top: 1.2em; margin-bottom: 0.5em; color: {COLOR_SECONDARY_TEXT};}}

.stButton>button {{
    border-radius: 6px !important;
    background-color: {COLOR_ACCENT} !important;
    color: white !important;
    border: none !important;
    padding: 8px 16px !important;
}}
.stButton>button:hover {{
    opacity: 0.85;
}}
.stSelectbox [data-baseweb="select"] > div {{
    border-radius: 6px !important;
    border-color: {COLOR_BORDER} !important;
}}
.stMultiSelect [data-baseweb="select"] > div {{
    border-radius: 6px !important;
    border-color: {COLOR_BORDER} !important;
}}

/* --- Contenedores y Secciones --- */
.section-container {{
    padding: 20px;
    background-color: #FFFFFF; /* Fondo blanco para secciones dentro del gris claro */
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    margin-bottom: 25px;
}}
.interpretation-text {{
    font-size: 0.95em;
    color: {COLOR_SECONDARY_TEXT};
    line-height: 1.6;
}}
.stCaption p {{
    color: {COLOR_SECONDARY_TEXT} !important;
    font-size: 0.85em !important;
}}

/* Ocultar el "Made with Streamlit" del footer */
footer {{
    visibility: hidden;
}}
/* Opcional: Añadir un footer personalizado si se desea */
.custom-footer {{
    text-align: center;
    padding: 10px;
    font-size: 0.8em;
    color: {COLOR_SECONDARY_TEXT};
    border-top: 1px solid {COLOR_BORDER};
}}

"""

# ====== CONFIGURACIÓN DE DATOS ======
START_YEAR_DATA = 2015
current_year = datetime.date.today().year
MAX_YEARS_CONFIG: Dict[str, List[str]] = {}
for year_num in range(START_YEAR_DATA, current_year + 1):
    year_str = str(year_num)
    if year_num < current_year:
        MAX_YEARS_CONFIG[year_str] = [f"{i:02d}" for i in range(1, 13)]
    else:
        current_month_for_data = datetime.date.today().month
        if datetime.date.today().day < 20: # Asumir que los datos del mes anterior están disponibles después del día 20
            current_month_for_data -= 1
        if current_month_for_data == 0:
            if str(current_year - 1) in MAX_YEARS_CONFIG:
                 MAX_YEARS_CONFIG[str(current_year - 1)] = [f"{i:02d}" for i in range(1, 13)]
            if year_str == str(current_year): # No agregar meses para el año actual si es Enero muy temprano
                 MAX_YEARS_CONFIG[year_str] = [] # Inicializar vacío
        else:
            MAX_YEARS_CONFIG[year_str] = [f"{i:02d}" for i in range(1, current_month_for_data + 1)]

SKIP_PAGES = 4
NUM2MONTH = {
    '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril', '05': 'Mayo', '06': 'Junio',
    '07': 'Julio', '08': 'Agosto', '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
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
    "Carnes Rojas y Procesados": ["Carne molida", "Chuleta de cerdo centro o vetada", "Costillar de cerdo", "Pulpa de cerdo", "Jamón de cerdo", "Longaniza", "Salchicha y vienesa tradicional", "Pate", "Aliado (jamón queso) o Barros Jarpa", "Asiento"],
    "Aves y Derivados": ["Pollo entero", "Pechuga de pollo", "Trutro de pollo", "Carne de pavo molida", "Salchicha y vienesa de ave", "Pollo asado entero"],
    "Cordero": ["Pulpa de cordero fresco o refrigerado"],
    "Pescados y Mariscos": ["Merluza fresca o refrigerada", "Choritos frescos o refrigerados en su concha", "Jurel en conserva", "Surtido en conserva"],
    "Lácteos y Huevos": ["Leche líquida entera", "Leche en polvo entera instantánea", "Yogurt", "Queso Gouda", "Quesillo y queso fresco con sal", "Queso crema", "Mantequilla con sal", "Margarina", "Huevo de gallina"],
    "Aceites y Grasas": ["Aceite vegetal combinado o puro"],
    "Frutas": ["Plátano", "Manzana", "Limón", "Palta"],
    "Legumbres y Frutos Secos": ["Poroto", "Lenteja", "Maní salado"],
    "Verduras y Tubérculos": ["Lechuga", "Zapallo", "Tomate", "Zanahoria", "Cebolla nueva", "Papa de guarda", "Choclo congelado"],
    "Azúcares y Dulces": ["Azúcar", "Chocolate", "Caramelo", "Helado familiar un sabor", "Galleta dulce"],
    "Snacks Salados": ["Galleta no dulce", "Papas fritas"],
    "Salsas y Condimentos": ["Salsa de tomate"],
    "Bebestibles (Café, Té)": ["Sucedáneo de café", "Te para preparar", "Té corriente"],
    "Bebidas Frías y Refrescos": ["Agua mineral", "Bebida gaseosa tradicional", "Bebida energizante", "Refresco isotónico", "Jugo líquido", "Néctar líquido", "Refresco en polvo"],
    "Comidas Preparadas y Rápidas": ["Completo", "Entrada (ensalada o sopa)", "Postre para almuerzo", "Promoción de comida rápida", "Empanada de horno", "Colación o menú del día o almuerzo ejecutivo", "Plato de fondo para almuerzo"],
    "Sin Categoría": [] # Se poblará automáticamente
}

PRESIDENTIAL_PERIODS = {
    "Todos los Periodos": None,
    "Gabriel Boric (Mar 2022 - Actualidad)": {"start_year": 2022, "start_month": 3, "end_year": current_year, "end_month": datetime.date.today().month},
    "Sebastián Piñera II (Mar 2018 - Mar 2022)": {"start_year": 2018, "start_month": 3, "end_year": 2022, "end_month": 3},
    "Michelle Bachelet II (Mar 2014 - Mar 2018)": {"start_year": 2014, "start_month": 3, "end_year": 2018, "end_month": 3},
    # Añadir más periodos si START_YEAR_DATA lo permite y se tienen los datos
}
# Filtrar periodos presidenciales para que solo incluyan años desde START_YEAR_DATA
VALID_PRESIDENTIAL_PERIODS = {"Todos los Periodos": None}
for name, details in PRESIDENTIAL_PERIODS.items():
    if name == "Todos los Periodos": continue
    if details and details["end_year"] >= START_YEAR_DATA:
        # Ajustar el año de inicio si es anterior a START_YEAR_DATA
        if details["start_year"] < START_YEAR_DATA:
            adjusted_details = details.copy()
            adjusted_details["start_year"] = START_YEAR_DATA
            adjusted_details["start_month"] = 1 # Empezar desde enero del START_YEAR_DATA
            VALID_PRESIDENTIAL_PERIODS[name] = adjusted_details
        else:
            VALID_PRESIDENTIAL_PERIODS[name] = details


# ====== FUNCIONES DE CARGA Y PROCESAMIENTO DE DATOS ======
@st.cache_data(ttl=3600 * 12) # Cachear PDFs por 12 horas
def fetch_pdf_content_cached(url: str) -> Optional[bytes]:
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.content
    except requests.exceptions.RequestException:
        return None

@st.cache_data(ttl=3600 * 4) # Cachear datos procesados por 4 horas
def load_data(years_to_fetch_config: Dict[str, List[str]]) -> pd.DataFrame:
    rows = []
    # st.write(f"Debug: load_data called with years_to_fetch_config: {years_to_fetch_config}") # Para depuración
    sorted_years_keys = sorted(years_to_fetch_config.keys())

    for year_str in sorted_years_keys:
        meses_str = years_to_fetch_config[year_str]
        if not meses_str: continue
        short_year = year_str[2:]
        for mm_str in meses_str:
            url = (
                f"https://observatorio.ministeriodesarrollosocial.gob.cl"
                f"/storage/docs/cba/nueva_serie/{year_str}"
                f"/Valor_CBA_y_LPs_{short_year}.{mm_str}.pdf"
            )
            pdf_bytes = fetch_pdf_content_cached(url)
            if not pdf_bytes: continue

            month_name = NUM2MONTH[mm_str]
            try:
                with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                    for i, page in enumerate(pdf.pages):
                        if i < SKIP_PAGES: continue
                        page_text = page.extract_text() or ""
                        for line in page_text.split("\n"):
                            match = LINE_REGEX.match(line.strip())
                            if not match: continue
                            product_name = match.group(1).strip()
                            try:
                                value = float(match.group(2).replace(",", "."))
                            except ValueError: continue
                            if product_name.lower() == "cba": continue
                            if product_name not in FIXED_PRODUCTS: continue
                            if abs(value) > 250: continue # Umbral amplio
                            rows.append({
                                "year": int(year_str),
                                "mes_num": int(mm_str),
                                "mes": month_name,
                                "producto": product_name,
                                "variacion": value
                            })
            except Exception: # pylint: disable=broad-except
                # Consider logging this error if running in production
                # st.warning(f"Error procesando PDF para {month_name} {year_str}. URL: {url}. Error: {e}")
                continue
    
    df = pd.DataFrame(rows)
    if df.empty: return df
    
    df['year'] = df['year'].astype(int)
    df['mes_num'] = df['mes_num'].astype(int)
    return df.drop_duplicates(subset=["year", "mes_num", "producto"], keep='first')

def calculate_period_cumulative_variation(df_period_product: pd.DataFrame) -> float:
    """Calcula la variación acumulada para un producto sobre un período de varios meses/años."""
    if df_period_product.empty: return 0.0
    
    # Asegurar orden cronológico
    df_sorted = df_period_product.sort_values(['year', 'mes_num'])
    
    cumulative_factor = 1.0
    for var_monthly in df_sorted['variacion']:
        cumulative_factor *= (1 + var_monthly / 100.0)
    return (cumulative_factor - 1) * 100.0

def get_presidential_kpis(df_presidency_scope: pd.DataFrame, all_products_in_period_scope: pd.DataFrame, selected_prods_for_avg: List[str]) -> Dict:
    kpis = {
        "avg_cumulative_variation": None,
        "max_increase_product": None, "max_increase_value": None,
        "max_decrease_product": None, "max_decrease_value": None,
    }
    if df_presidency_scope.empty: return kpis

    # 1. Variación acumulada promedio (para productos seleccionados en el filtro general)
    cumulative_variations_selected_prods = []
    if selected_prods_for_avg:
        for prod in selected_prods_for_avg:
            df_prod_period = df_presidency_scope[df_presidency_scope['producto'] == prod]
            if not df_prod_period.empty:
                cum_var = calculate_period_cumulative_variation(df_prod_period)
                cumulative_variations_selected_prods.append(cum_var)
        if cumulative_variations_selected_prods:
            kpis["avg_cumulative_variation"] = sum(cumulative_variations_selected_prods) / len(cumulative_variations_selected_prods)

    # 2. Producto con mayor alza/baja (considerando TODOS los productos en FIXED_PRODUCTS que tengan datos en el periodo)
    product_cumulative_variations = {}
    # Usar all_products_in_period_scope que ya está filtrado por el periodo presidencial
    for prod_name in all_products_in_period_scope['producto'].unique():
        df_prod_full_period = all_products_in_period_scope[all_products_in_period_scope['producto'] == prod_name]
        if not df_prod_full_period.empty:
            product_cumulative_variations[prod_name] = calculate_period_cumulative_variation(df_prod_full_period)
    
    if product_cumulative_variations:
        max_prod = max(product_cumulative_variations, key=product_cumulative_variations.get)
        min_prod = min(product_cumulative_variations, key=product_cumulative_variations.get)
        kpis["max_increase_product"] = max_prod
        kpis["max_increase_value"] = product_cumulative_variations[max_prod]
        kpis["max_decrease_product"] = min_prod
        kpis["max_decrease_value"] = product_cumulative_variations[min_prod]
        
    return kpis

def generate_years_to_load_from_filters(
    presidency_details: Optional[Dict], 
    selected_years_override: Optional[List[str]]
    ) -> Dict[str, List[str]]:
    """
    Determina qué años y meses cargar basado en el período presidencial o selección manual de años.
    """
    years_config = {}
    
    min_year_to_consider = START_YEAR_DATA
    max_year_to_consider = current_year

    target_start_year, target_start_month = min_year_to_consider, 1
    target_end_year, target_end_month = max_year_to_consider, 12

    if presidency_details: # Filtro presidencial tiene prioridad para definir el rango general
        target_start_year = max(min_year_to_consider, presidency_details["start_year"])
        target_start_month = presidency_details["start_month"] if presidency_details["start_year"] >= min_year_to_consider else 1
        target_end_year = min(max_year_to_consider, presidency_details["end_year"])
        target_end_month = presidency_details["end_month"]
    elif selected_years_override: # Si no hay periodo presidencial, usar los años del multiselect
        # En este caso, cargaremos todos los meses de los años seleccionados.
        # El filtrado por meses específicos se hará después de cargar los datos de estos años.
        for year_str_override in selected_years_override:
            year_int_override = int(year_str_override)
            if min_year_to_consider <= year_int_override <= max_year_to_consider:
                years_config[year_str_override] = MAX_YEARS_CONFIG.get(year_str_override, [f"{m:02d}" for m in range(1,13)])
        return years_config # Retornar directamente si se usan años de override
    else: # Caso por defecto (ej. "Todos los periodos" sin años seleccionados manualmente)
        # Cargar todo el rango definido en MAX_YEARS_CONFIG
         return MAX_YEARS_CONFIG.copy()


    # Construir la configuración de años y meses para el rango presidencial
    for year_num in range(target_start_year, target_end_year + 1):
        year_s = str(year_num)
        year_months = []
        
        start_m = target_start_month if year_num == target_start_year else 1
        end_m = target_end_month if year_num == target_end_year else 12
        
        # Usar los meses disponibles en MAX_YEARS_CONFIG como base para no pedir meses inexistentes
        available_months_for_year = MAX_YEARS_CONFIG.get(year_s, [])
        
        for month_num in range(start_m, end_m + 1):
            month_s = f"{month_num:02d}"
            if month_s in available_months_for_year:
                year_months.append(month_s)
        
        if year_months:
            years_config[year_s] = year_months
            
    return years_config

# ====== INICIALIZACIÓN DE LA APP ======
st.set_page_config(page_title="Monitor Canasta Básica Chile", layout="wide", initial_sidebar_state="expanded")
st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)

# --- Encabezado Fijo (Simulado) ---
header_cols = st.columns([0.1, 0.8, 0.1])
with header_cols[0]:
    st.image(APP_LOGO_URL, width=50)
with header_cols[1]:
    st.markdown(f'<div class="app-header"><h1 class="title">Monitor Inteligente de la Canasta Básica de Alimentos - Chile</h1></div>', unsafe_allow_html=True)


# --- Contenedor Principal para la Carga de Datos ---
main_placeholder = st.empty()

with main_placeholder.container():
    with st.spinner("🔄 Iniciando aplicación y preparando filtros..."):
        # ====== BARRA LATERAL DE FILTROS (Se renderiza primero) ======
        st.sidebar.markdown("<h1>Filtros</h1>", unsafe_allow_html=True)

        # --- Filtro por Período Presidencial ---
        st.sidebar.markdown("### Periodo Gubernamental", unsafe_allow_html=True)
        selected_presidential_period_name = st.sidebar.selectbox(
            "Análisis por Gobierno",
            options=list(VALID_PRESIDENTIAL_PERIODS.keys()),
            index=0, # Default a "Todos los Periodos"
            help="Selecciona un periodo presidencial para analizar tendencias y KPIs específicos de ese gobierno. Esto ajustará los años disponibles."
        )
        active_presidency_details = VALID_PRESIDENTIAL_PERIODS[selected_presidential_period_name]

        # Determinar años disponibles basados en el periodo presidencial o el rango completo
        # y configurar años por defecto para el multiselect de años.
        
        # Años disponibles para el multiselect de Años
        # Si se selecciona un periodo presidencial, los años se limitan a ese periodo.
        # Si no, se usan todos los años de MAX_YEARS_CONFIG.
        years_for_multiselect_selector = []
        default_years_for_multiselect = []

        if active_presidency_details:
            start_y = max(START_YEAR_DATA, active_presidency_details["start_year"])
            end_y = min(current_year, active_presidency_details["end_year"])
            for y in range(start_y, end_y + 1):
                if str(y) in MAX_YEARS_CONFIG and MAX_YEARS_CONFIG[str(y)]: # Solo si el año tiene meses configurados
                    years_for_multiselect_selector.append(str(y))
            default_years_for_multiselect = years_for_multiselect_selector[:] # Todos los años del periodo
        else: # "Todos los Periodos"
            years_for_multiselect_selector = [y for y in MAX_YEARS_CONFIG.keys() if MAX_YEARS_CONFIG[y]] # Solo años con meses
            if years_for_multiselect_selector:
                 default_years_for_multiselect = [max(years_for_multiselect_selector)] # Año más reciente por defecto

        years_for_multiselect_selector.sort(reverse=True)
        default_years_for_multiselect.sort(reverse=True)


        st.sidebar.markdown("### Periodo Específico", unsafe_allow_html=True)
        selected_years_str_list = st.sidebar.multiselect(
            "Año(s)",
            options=years_for_multiselect_selector,
            default=default_years_for_multiselect,
            help="Selecciona uno o más años para el análisis. Se ajusta según el periodo presidencial."
        )
        
        # Lógica para determinar qué años realmente cargar
        # Si se seleccionó un periodo presidencial, se usa ese rango.
        # Si además se seleccionaron años en el multiselect, estos actúan como un sub-filtro DENTRO del periodo presidencial.
        # Si "Todos los Periodos" está activo, se usan los años del multiselect.
        
        active_years_to_load_config = {}
        if active_presidency_details:
            # Generar config para el periodo presidencial
            temp_config_presidency = generate_years_to_load_from_filters(active_presidency_details, None)
            if selected_years_str_list: # Si hay años seleccionados, filtrar la config presidencial
                for year_k in list(temp_config_presidency.keys()): # Iterar sobre copia de llaves
                    if year_k not in selected_years_str_list:
                        del temp_config_presidency[year_k]
            active_years_to_load_config = temp_config_presidency
        elif selected_years_str_list: # "Todos los periodos" Y hay años seleccionados
            active_years_to_load_config = generate_years_to_load_from_filters(None, selected_years_str_list)
        else: # "Todos los periodos" Y NO hay años seleccionados (cargar todo lo de MAX_YEARS_CONFIG)
            active_years_to_load_config = MAX_YEARS_CONFIG.copy()


        # --- Filtro por Mes ---
        # Los meses disponibles se basan en los AÑOS EFECTIVAMENTE SELECCIONADOS para la carga
        # (ya sea por periodo presidencial o multiselect de años)
        
        # Primero, obtener todos los meses únicos de los años que se van a cargar
        all_possible_months_in_active_load_config = set()
        temp_df_for_month_extraction = load_data(active_years_to_load_config) # Carga preliminar para meses

        if not temp_df_for_month_extraction.empty:
            for year_val_str in active_years_to_load_config.keys():
                if year_val_str in selected_years_str_list: # Solo considerar meses de años realmente seleccionados
                    df_year_specific = temp_df_for_month_extraction[temp_df_for_month_extraction['year'] == int(year_val_str)]
                    all_possible_months_in_active_load_config.update(df_year_specific['mes'].unique())
        
        ordered_available_months = sorted(
            list(all_possible_months_in_active_load_config),
            key=lambda m: list(NUM2MONTH.values()).index(m) if m in NUM2MONTH.values() else -1
        )
        selected_months_names = st.sidebar.multiselect(
            "Mes(es)",
            options=ordered_available_months,
            default=ordered_available_months, # Todos los meses disponibles por defecto
            help="Selecciona uno o más meses. Se listan los meses con datos para los años seleccionados."
        )

        # --- Filtro de Productos por Categoría ---
        st.sidebar.markdown("### Productos", unsafe_allow_html=True)
        
        # Poblar "Sin Categoría"
        all_categorized_prods = {prod for cat_prods in PRODUCT_CATEGORIES.values() for prod in cat_prods}
        PRODUCT_CATEGORIES["Sin Categoría"] = sorted([
            p for p in FIXED_PRODUCTS if p not in all_categorized_prods
        ])

        # Categorías activas (con productos presentes en FIXED_PRODUCTS)
        active_product_categories = {
            cat: sorted([p for p in prods if p in FIXED_PRODUCTS])
            for cat, prods in PRODUCT_CATEGORIES.items()
        }
        active_product_categories = {cat: prods for cat, prods in active_product_categories.items() if prods}
        
        category_multiselect_options = sorted(list(active_product_categories.keys()))
        default_categories = ["Panadería y Masas", "Lácteos y Huevos"]
        # Asegurar que las categorías por defecto existan en las opciones
        valid_default_categories = [cat for cat in default_categories if cat in category_multiselect_options]


        selected_category_names = st.sidebar.multiselect(
            "Categoría(s) de Producto",
            category_multiselect_options,
            default=valid_default_categories,
            help="Selecciona una o más categorías para filtrar la lista de productos."
        )

        products_for_multiselect = []
        if not selected_category_names: # Si no se selecciona ninguna categoría, ofrecer todos los productos
            products_for_multiselect = sorted(FIXED_PRODUCTS)
        else:
            for cat_name in selected_category_names:
                if cat_name in active_product_categories:
                    products_for_multiselect.extend(active_product_categories[cat_name])
        products_for_multiselect = sorted(list(set(products_for_multiselect)))

        selected_products = st.sidebar.multiselect(
            "Producto(s) Específico(s)",
            products_for_multiselect,
            default=products_for_multiselect, # Todos los productos de las categorías seleccionadas por defecto
            help="Selecciona productos individuales. La lista se basa en las categorías elegidas."
        )

# --- Carga Principal de Datos (basada en filtros de tiempo) ---
# Este spinner se mostrará DENTRO del placeholder si la carga es larga.
with main_placeholder.container():
    spinner_message = "🔄 Cargando datos para el periodo seleccionado..."
    if not active_years_to_load_config: # Si no hay años para cargar (ej. mala config de filtros)
        st.warning("No hay un rango de años válido seleccionado para cargar datos. Por favor, ajusta los filtros de periodo o año.")
        st.stop()

    with st.spinner(spinner_message):
        df_data_loaded_scope = load_data(active_years_to_load_config)

# --- Limpiar Placeholder y Mostrar Contenido ---
main_placeholder.empty()


if df_data_loaded_scope.empty:
    st.error("⚠️ No se encontraron datos para el rango de tiempo y productos configurados. Verifica la disponibilidad de los PDFs en la fuente o ajusta los filtros.")
    st.stop()

# Aplicar filtros finales de mes y producto al DataFrame cargado para el SCOPE
df_final_filtered = df_data_loaded_scope.copy()
if selected_months_names:
    df_final_filtered = df_final_filtered[df_final_filtered["mes"].isin(selected_months_names)]
if selected_products:
    df_final_filtered = df_final_filtered[df_final_filtered["producto"].isin(selected_products)]
else: # Si no se seleccionan productos explícitamente, mostrar un mensaje en lugar de error o todo
    st.info("ℹ️ Por favor, selecciona al menos un producto en la barra lateral para visualizar los datos.")
    st.stop()


# ====== SECCIÓN DE KPIs PRESIDENCIALES ======
if active_presidency_details: # Solo mostrar si se ha seleccionado un periodo presidencial específico
    st.markdown("---")
    st.markdown(f"<h2>Análisis del Periodo Presidencial: {selected_presidential_period_name}</h2>", unsafe_allow_html=True)
    
    # Para los KPIs de min/max producto, necesitamos todos los datos del periodo presidencial, no solo los filtrados por producto en la sidebar.
    # df_data_loaded_scope ya contiene los datos del periodo presidencial.
    presidency_kpis = get_presidential_kpis(df_final_filtered, df_data_loaded_scope, selected_products)

    kpi_cols = st.columns(3)
    with kpi_cols[0]:
        if presidency_kpis["avg_cumulative_variation"] is not None:
            st.metric(
                label=f"Var. Acum. Promedio (Prod. Selec.)",
                value=f"{presidency_kpis['avg_cumulative_variation']:.2f}%",
                help="Variación de precio acumulada promedio para los productos actualmente seleccionados en la barra lateral, durante este periodo presidencial."
            )
            st.caption("Este indicador refleja cómo, en promedio, los productos que tienes seleccionados cambiaron de precio durante este gobierno.")
        else:
            st.info("No hay datos suficientes para la var. acum. promedio de productos seleccionados.")
    
    with kpi_cols[1]:
        if presidency_kpis["max_increase_product"]:
            st.metric(
                label=f"Mayor Alza Acumulada",
                value=f"{presidency_kpis['max_increase_product']}",
                delta=f"{presidency_kpis['max_increase_value']:.2f}%", delta_color="inverse",
                help=f"El producto (de toda la canasta monitoreada) que más subió de precio acumulado durante el periodo: {presidency_kpis['max_increase_product']} ({presidency_kpis['max_increase_value']:.2f}%)."
            )
            st.caption("Identifica el producto de la canasta general que experimentó el mayor encarecimiento durante este mandato.")
        else:
            st.info("No hay datos para la mayor alza.")

    with kpi_cols[2]:
        if presidency_kpis["max_decrease_product"]:
            st.metric(
                label=f"Mayor Baja Acumulada",
                value=f"{presidency_kpis['max_decrease_product']}",
                delta=f"{presidency_kpis['max_decrease_value']:.2f}%", delta_color="normal",
                help=f"El producto (de toda la canasta monitoreada) que más bajó de precio (o menos subió) acumulado durante el periodo: {presidency_kpis['max_decrease_product']} ({presidency_kpis['max_decrease_value']:.2f}%)."
            )
            st.caption("Muestra el producto de la canasta general que tuvo la mayor reducción de precio (o la menor alza) en este gobierno.")
        else:
            st.info("No hay datos para la mayor baja.")
    st.markdown("---")


# ====== VISUALIZACIONES Y DATOS (para el df_final_filtered) ======
if not df_final_filtered.empty:
    current_year_str_kpi = str(datetime.date.today().year)
    # Convertir selected_years_str_list a int para comparación
    selected_years_int_list = [int(y) for y in selected_years_str_list]

    if int(current_year_str_kpi) in selected_years_int_list:
        st.markdown(f"<h2>Resumen Año en Curso ({current_year_str_kpi})</h2>", unsafe_allow_html=True)
        df_current_year_for_kpi_source = df_data_loaded_scope[ # Usar datos del scope cargado
            (df_data_loaded_scope['year'] == int(current_year_str_kpi)) &
            (df_data_loaded_scope['producto'].isin(selected_products))
        ]
        
        cumulative_variations_calc = []
        if not df_current_year_for_kpi_source.empty:
            for prod_name_kpi in df_current_year_for_kpi_source['producto'].unique():
                df_single_prod_curr_year = df_current_year_for_kpi_source[df_current_year_for_kpi_source['producto'] == prod_name_kpi]
                if not df_single_prod_curr_year.empty:
                    # Necesitamos una función que calcule la variación acumulada para un solo año.
                    # Reutilizamos calculate_period_cumulative_variation, que funciona bien para un solo año también.
                    cum_var = calculate_period_cumulative_variation(df_single_prod_curr_year)
                    cumulative_variations_calc.append(cum_var)
            if cumulative_variations_calc:
                avg_cumulative_variation_year = sum(cumulative_variations_calc) / len(cumulative_variations_calc)
                st.metric(
                    label=f"Variación Acumulada Promedio {current_year_str_kpi} (Prod. Seleccionados)",
                    value=f"{avg_cumulative_variation_year:.2f}%",
                    help="Variación de precio acumulada promedio para los productos seleccionados, desde inicio de año hasta el último mes con datos."
                )
            else:
                st.info(f"No hay suficientes datos mensuales en {current_year_str_kpi} para los productos seleccionados para calcular la variación acumulada del año.")
        else:
            st.info(f"No hay datos para el año {current_year_str_kpi} con los productos seleccionados para calcular la variación acumulada del año.")
        st.markdown("---")

    # --- Preparación de Periodo para Gráficos ---
    df_final_filtered["periodo"] = df_final_filtered["year"].astype(str) + " " + df_final_filtered["mes"]
    
    # Ordenar periodos para el gráfico
    # Usar todos los periodos posibles del df_data_loaded_scope como base para el orden global
    df_scope_copy = df_data_loaded_scope.copy()
    df_scope_copy['periodo_temp'] = df_scope_copy['year'].astype(str) + " " + df_scope_copy['mes']
    all_periods_in_scope_ordered = sorted(
        df_scope_copy["periodo_temp"].unique(),
        key=lambda x: (int(x.split()[0]), list(NUM2MONTH.values()).index(x.split()[1]))
    )
    actual_periods_in_final_filtered = df_final_filtered["periodo"].unique()
    ordered_periods_for_chart = [p for p in all_periods_in_scope_ordered if p in actual_periods_in_final_filtered]

    if ordered_periods_for_chart:
        df_final_filtered["periodo"] = pd.Categorical(
            df_final_filtered["periodo"], categories=ordered_periods_for_chart, ordered=True
        )

        st.markdown("<h2>Análisis de Variaciones Mensuales</h2>", unsafe_allow_html=True)
        # st.subheader("Variación Porcentual Mensual por Producto")
        monthly_pivot = df_final_filtered.pivot_table(
            index="periodo", columns="producto", values="variacion", aggfunc="mean"
        )
        monthly_pivot = monthly_pivot.reindex(ordered_periods_for_chart).dropna(how='all', axis=0)

        if not monthly_pivot.empty:
            fig_line = px.line(
                monthly_pivot, x=monthly_pivot.index.astype(str), y=monthly_pivot.columns,
                labels={'value': 'Variación (%)', 'periodo': 'Período', 'producto': 'Producto'},
                color_discrete_sequence=px.colors.qualitative.Plotly # Paleta de colores
            )
            fig_line.update_layout(
                height=500, legend_title_text='Productos', xaxis_tickangle=-45, 
                hovermode="x unified", paper_bgcolor=COLOR_BACKGROUND_MAIN, plot_bgcolor=COLOR_BACKGROUND_MAIN,
                font=dict(family=FONT_FAMILY_SANS_SERIF, color=COLOR_PRIMARY_TEXT)
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No hay datos suficientes para mostrar el gráfico de líneas con los filtros actuales.")

        st.markdown("<h3>Top 5 Alzas y Bajas (Promedio en Período Seleccionado)</h3>", unsafe_allow_html=True)
        avg_variation_per_product = df_final_filtered.groupby('producto')['variacion'].mean().sort_values()
        top_increases = avg_variation_per_product[avg_variation_per_product > 0].nlargest(5).sort_values(ascending=False)
        top_decreases = avg_variation_per_product[avg_variation_per_product <= 0].nsmallest(5).sort_values(ascending=True)
        combined_tops = pd.concat([top_decreases, top_increases.iloc[::-1]] ).sort_values()

        if not combined_tops.empty:
            colors = [COLOR_ACCENT_DANGER if v < 0 else (COLOR_ACCENT_SUCCESS if v > 0 else COLOR_SECONDARY_TEXT) for v in combined_tops.values]
            fig_bar_tops = go.Figure(go.Bar(
                y=combined_tops.index, x=combined_tops.values, orientation='h',
                marker_color=colors, text=combined_tops.values, texttemplate='%{text:.2f}%', textposition='outside'
            ))
            fig_bar_tops.update_layout(
                xaxis_title="Variación Promedio Mensual (%)", yaxis_title="Producto",
                height=max(400, len(combined_tops) * 40 + 100), 
                yaxis_autorange="reversed", paper_bgcolor=COLOR_BACKGROUND_MAIN, plot_bgcolor=COLOR_BACKGROUND_MAIN,
                font=dict(family=FONT_FAMILY_SANS_SERIF, color=COLOR_PRIMARY_TEXT)
            )
            st.plotly_chart(fig_bar_tops, use_container_width=True)
        else:
            st.info("No hay suficientes datos para mostrar el top de alzas y bajas con los filtros actuales.")

        st.markdown("<h3>📝 Interpretaciones (Periodo Seleccionado en Filtros)</h3>", unsafe_allow_html=True)
        if not df_final_filtered["variacion"].empty and df_final_filtered["variacion"].notna().any():
            avg_overall_variation = df_final_filtered["variacion"].mean()
            st.markdown(f"<p class='interpretation-text'>- <b>Variación media general</b> de los productos seleccionados en el periodo filtrado: <b>{avg_overall_variation:.2f}%</b>.</p>", unsafe_allow_html=True)
            
            idx_max = df_final_filtered["variacion"].idxmax() # Mayor variación mensual puntual
            row_max_variation = df_final_filtered.loc[idx_max]
            st.markdown(f"<p class='interpretation-text'>- <b>Mayor alza mensual puntual</b> registrada: <i>{row_max_variation['producto']}</i> con <b>+{row_max_variation['variacion']:.2f}%</b> en {row_max_variation['periodo']}.</p>", unsafe_allow_html=True)
            
            idx_min = df_final_filtered["variacion"].idxmin() # Mayor baja mensual puntual
            row_min_variation = df_final_filtered.loc[idx_min]
            st.markdown(f"<p class='interpretation-text'>- <b>Mayor baja mensual puntual</b> registrada: <i>{row_min_variation['producto']}</i> con <b>{row_min_variation['variacion']:.2f}%</b> en {row_min_variation['periodo']}.</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p class='interpretation-text'>- No hay datos de variación disponibles para calcular interpretaciones con los filtros actuales.</p>", unsafe_allow_html=True)
    else:
        st.info("ℹ️ No hay datos de período para mostrar después de aplicar todos los filtros. Intenta ampliar el rango de fechas o la selección de productos.")
        
    with st.expander("📄 Ver Datos Detallados Filtrados", expanded=False):
        cols_to_show = ["year", "mes", "producto", "variacion"]
        df_display_detailed = df_final_filtered.copy()
        if "periodo" in df_display_detailed.columns:
             df_display_detailed = df_display_detailed.sort_values(["periodo", "producto"])
        else: # Ordenar por año y mes_num si 'periodo' no está (debería estar)
            df_display_detailed = df_display_detailed.sort_values(['year', 'mes_num', 'producto'])

        st.dataframe(
            df_display_detailed[cols_to_show],
            use_container_width=True,
            hide_index=True
        )

elif selected_years_str_list and selected_months_names and selected_products :
    st.info("ℹ️ No se encontraron datos que coincidan con todos los filtros seleccionados. Prueba con una selección diferente.")
else:
    st.info("✨ Por favor, ajusta los filtros en la barra lateral para comenzar el análisis.")


# --- Footer Personalizado ---
st.markdown(f"""
<div class="custom-footer">
    Aplicación para monitorear la Canasta Básica de Alimentos en Chile.<br>
    Datos obtenidos del Observatorio Social, Ministerio de Desarrollo Social y Familia.<br>
    Desarrollado con Streamlit.
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.info("Los datos se actualizan según la disponibilidad en la fuente oficial. La primera carga puede ser más lenta.")
