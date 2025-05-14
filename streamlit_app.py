import streamlit as st
import pandas as pd
import pdfplumber
import requests
import re
from io import BytesIO

# ====== CONFIGURACIÓN ======
YEARS = {
    '2024': [f"{i:02d}" for i in range(1, 13)],  # Meses de Enero a Diciembre
    '2025': [f"{i:02d}" for i in range(1, 4)],   # Meses de Enero a Marzo (ejemplo)
}
SKIP_PAGES = 4  # Número de páginas iniciales a omitir en cada PDF
NUM2MONTH = {
    '01': 'Enero', '02': 'Febrero', '03': 'Marzo',
    '04': 'Abril', '05': 'Mayo', '06': 'Junio',
    '07': 'Julio', '08': 'Agosto', '09': 'Septiembre',
    '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
}
# Expresión regular para extraer el nombre del producto y su variación
# Captura: (nombre del producto) (espacio) (valor numérico con . o , como decimal)
LINE_REGEX = re.compile(r"^(.+?)\s+(-?\d+[.,]\d+)$")

# Lista fija de productos que se buscarán en los PDFs.
# !!! IMPORTANTE: !!!
# 1. Debes reemplazar esta lista con los nombres EXACTOS de los productos que te interesan.
# 2. Todos los elementos DEBEN SER CADENAS DE TEXTO (strings).
# 3. El nombre debe coincidir con el texto extraído del PDF después de aplicar .strip().
#    La comparación es sensible a mayúsculas/minúsculas.
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

@st.cache_data(ttl=3600)  # Cachear los datos por 1 hora
def load_data():
    """
    Carga los datos de variación de precios de productos desde PDFs online.
    Extrae información de PDFs del Observatorio Social del Ministerio de Desarrollo Social.
    """
    rows = []
    for year, meses in YEARS.items():
        short_year = year[2:]  # Formato de año 'yy' para la URL
        for mm in meses:
            # Construcción de la URL del PDF
            url = (
                f"https://observatorio.ministeriodesarrollosocial.gob.cl"
                f"/storage/docs/cba/nueva_serie/{year}"
                f"/Valor_CBA_y_LPs_{short_year}.{mm}.pdf"
            )
            try:
                # Petición para obtener el PDF
                r = requests.get(url, timeout=10) # Timeout para evitar esperas indefinidas
                r.raise_for_status()  # Lanza un error si la petición falla (e.g., 404)
            except requests.exceptions.RequestException as e:
                # st.warning(f"No se pudo descargar el PDF para {NUM2MONTH[mm]} {year}: {url} (Error: {e})")
                continue  # Continuar con el siguiente mes/año si hay un error

            month_name = NUM2MONTH[mm]
            try:
                # Abrir el PDF desde el contenido binario en memoria
                with pdfplumber.open(BytesIO(r.content)) as pdf:
                    for i, page in enumerate(pdf.pages):
                        if i < SKIP_PAGES:
                            continue  # Omitir las primeras páginas según SKIP_PAGES

                        # Extraer texto de la página; usar "" si la extracción falla
                        page_text = page.extract_text() or ""
                        for line in page_text.split("\n"):
                            match = LINE_REGEX.match(line.strip())
                            if not match:
                                continue  # Si la línea no coincide con el formato esperado

                            product_name = match.group(1).strip()
                            try:
                                # Convertir valor a float, reemplazando coma por punto para el decimal
                                value = float(match.group(2).replace(",", "."))
                            except ValueError:
                                # st.warning(f"Error al convertir valor para '{product_name}' en {month_name} {year}: '{match.group(2)}'")
                                continue


                            # Filtrar productos no deseados o valores anómalos
                            if product_name.lower() == "cba": # Ignorar la línea "CBA"
                                continue
                            if product_name not in FIXED_PRODUCTS: # Solo incluir productos de nuestra lista
                                continue
                            if abs(value) > 100:  # Ignorar variaciones porcentuales extremas (ej. > 100%)
                                continue

                            rows.append({
                                "year": year,
                                "mes": month_name,
                                "producto": product_name,
                                "variacion": value
                            })
            except Exception as e:
                # Captura errores durante el procesamiento del PDF
                # st.warning(f"Error procesando PDF para {month_name} {year} desde {url}: {e}")
                continue


    df = pd.DataFrame(rows)
    # Eliminar duplicados si existen, manteniendo la primera ocurrencia
    return df.drop_duplicates(subset=["year", "mes", "producto"], keep='first') if not df.empty else df

# ====== CONFIGURACIÓN DE LA PÁGINA DE STREAMLIT ======
st.set_page_config(page_title="Monitor Canasta Básica", layout="wide")
st.title("📊 Monitor Inteligente de la Canasta Básica")

# Cargar datos con un spinner
with st.spinner("🔄 Cargando datos de los PDFs… Por favor, espere."):
    df_data = load_data()

if df_data.empty:
    st.error("⚠️ No se encontraron datos para los productos y periodos especificados. Verifica la lista `FIXED_PRODUCTS` y la disponibilidad de los PDFs.")
    st.stop() # Detener la ejecución si no hay datos

# ====== BARRA LATERAL DE FILTROS ======
st.sidebar.header("Filtros")

# Filtro por Año
available_years = sorted(df_data["year"].unique())
selected_years = st.sidebar.multiselect("Año(s)", available_years, default=available_years)

# Filtro por Mes (dependiente de los años seleccionados)
if selected_years:
    available_months = sorted(
        df_data[df_data["year"].isin(selected_years)]["mes"].unique(),
        key=lambda m: list(NUM2MONTH.values()).index(m) # Ordenar meses cronológicamente
    )
    selected_months = st.sidebar.multiselect("Mes(es)", available_months, default=available_months)
else:
    selected_months = [] # Si no hay años seleccionados, no hay meses para seleccionar

# Filtro por Producto
# Asegurarse de que FIXED_PRODUCTS solo contenga strings válidos que estén en los datos cargados
# para evitar errores en multiselect y ofrecer solo opciones relevantes.
products_in_data = sorted(df_data["producto"].unique())
relevant_fixed_products = [p for p in FIXED_PRODUCTS if p in products_in_data]

if not relevant_fixed_products:
    st.sidebar.warning("Ninguno de los productos en `FIXED_PRODUCTS` fue encontrado en los datos cargados.")
    selected_products = []
else:
    selected_products = st.sidebar.multiselect("Producto(s)", relevant_fixed_products, default=relevant_fixed_products)


# ====== FILTRAR DATOS SEGÚN SELECCIÓN ======
if not selected_years or not selected_months or not selected_products:
    st.warning("Por favor, selecciona al menos un año, un mes y un producto para ver los resultados.")
    df_filtered = pd.DataFrame() # DataFrame vacío si no hay selección completa
else:
    df_filtered = df_data[
        df_data["year"].isin(selected_years) &
        df_data["mes"].isin(selected_months) &
        df_data["producto"].isin(selected_products)
    ].copy() # Usar .copy() para evitar SettingWithCopyWarning

# ====== PREPARACIÓN DE PERIODOS CRONOLÓGICOS PARA GRÁFICOS ======
if not df_filtered.empty:
    # 1) Crear columna combinada "periodo" (Año Mes)
    df_filtered["periodo"] = df_filtered["year"] + " " + df_filtered["mes"]

    # 2) Extraer periodos únicos de los datos filtrados
    # Usamos df_data para obtener el orden global de periodos, luego filtramos los que están en df_filtered
    
    # Orden cronológico global de todos los periodos posibles en los datos originales
    all_periods_ordered = sorted(
        (df_data["year"] + " " + df_data["mes"]).unique(),
        key=lambda x: (
            int(x.split()[0]), # Año como entero
            list(NUM2MONTH.values()).index(x.split()[1]) # Índice del mes
        )
    )
    
    # Periodos que realmente existen en los datos filtrados
    actual_periods_in_filtered_data = df_filtered["periodo"].unique()
    
    # Mantener el orden cronológico global pero solo para los periodos presentes en df_filtered
    ordered_periods_for_chart = [p for p in all_periods_ordered if p in actual_periods_in_filtered_data]


    if ordered_periods_for_chart:
        # 4) Aplicar como categoría ordenada para el gráfico
        df_filtered["periodo"] = pd.Categorical(
            df_filtered["periodo"],
            categories=ordered_periods_for_chart,
            ordered=True
        )

        # ====== GRÁFICO DE VARIACIÓN MENSUAL ======
        st.subheader("📈 Variación Porcentual Mensual por Producto")
        # Pivotear la tabla para el gráfico: periodo como índice, producto como columnas
        monthly_pivot = df_filtered.pivot_table(
            index="periodo",
            columns="producto",
            values="variacion",
            aggfunc="mean" # Usar la media si hay múltiples entradas (no debería si drop_duplicates funcionó)
        )
        # Reindexar para asegurar el orden cronológico y solo periodos con datos
        monthly_pivot = monthly_pivot.reindex(ordered_periods_for_chart).dropna(how='all', axis=0)

        if not monthly_pivot.empty:
            st.line_chart(monthly_pivot)
        else:
            st.info("No hay datos suficientes para mostrar el gráfico con los filtros actuales.")

        # ====== INTERPRETACIONES Y CONCLUSIONES ======
        st.subheader("📝 Interpretaciones y Conclusiones")
        if not df_filtered["variacion"].empty and df_filtered["variacion"].notna().any():
            avg_variation = df_filtered["variacion"].mean()
            st.markdown(f"- **Variación media** de los productos seleccionados en el período: **{avg_variation:.2f}%**.")

            # Asegurar que haya datos para idxmax/idxmin
            row_max_variation = df_filtered.loc[df_filtered["variacion"].idxmax()]
            st.markdown(
                f"- **Mayor alza registrada**: _{row_max_variation['producto']}_ con **+{row_max_variation['variacion']:.2f}%** "
                f"en {row_max_variation['periodo']}."
            )

            row_min_variation = df_filtered.loc[df_filtered["variacion"].idxmin()]
            st.markdown(
                f"- **Mayor baja registrada**: _{row_min_variation['producto']}_ con **{row_min_variation['variacion']:.2f}%** "
                f"en {row_min_variation['periodo']}."
            )
        else:
            st.markdown("- No hay datos de variación disponibles para calcular interpretaciones con los filtros actuales.")

    else: # Si ordered_periods_for_chart está vacío
        st.info("No hay datos de período para mostrar después de aplicar los filtros.")
        
    # ====== DATOS DETALLADOS ======
    st.subheader("📄 Datos Detallados Filtrados")
    st.dataframe(
        df_filtered[["year", "mes", "producto", "variacion", "periodo"]]
        .sort_values(["periodo", "producto"]) # Ordenar por el periodo categórico y luego producto
        .reset_index(drop=True)
        .drop(columns=["periodo"] if "periodo" in df_filtered.columns else []), # Opcional: quitar periodo si no se quiere mostrar
        use_container_width=True
    )

else: # Si df_filtered está vacío inicialmente
    if selected_years and selected_months and selected_products: # Solo si se hizo una selección pero no arrojó datos
        st.info("No se encontraron datos que coincidan con todos los filtros seleccionados.")

