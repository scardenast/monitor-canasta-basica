# Monitor Inteligente de la Canasta Básica

**URL en producción:** https://monitor-canasta-basica-chile.streamlit.app/

---

## Objetivo  
Crear un dashboard interactivo que extrae y visualiza automáticamente las variaciones porcentuales de precios de productos esenciales de la canasta básica en Chile, con análisis comparativo por periodos presidenciales.

---

## Tecnologías y Arquitectura  
- **Lenguaje & Framework**: Python 3 + Streamlit  
- **Procesamiento de documentos**:  
  - `requests` para descarga de PDFs  
  - `pdfplumber` para leer texto de informes oficiales  
- **Análisis de datos**: `pandas` para ETL y series temporales  
- **Visualización**: `plotly.express` y `plotly.graph_objects`  
- **UX/UI**:  
  - Diseño minimalista con paleta neutra + acento azul  
  - Tipografía “Inter” y CSS personalizado  
  - Sidebar con filtros dinámicos (año, mes, categoría, producto, periodos presidenciales)  
- **Optimización**:  
  - `st.cache_data` para cachear PDFs (12 h) y datos procesados (4 h)  
  - Carga condicional de sólo periodos y productos seleccionados  

---

## Infraestructura AWS  
- **AWS S3**  
  - Bucket público `canasta-basica-data` para almacenar los PDFs descargados  
  - Estructura de objetos:  
    ```
    s3://canasta-basica-data/raw/{year}/{month}.pdf
    ```  
- **AWS Lambda**  
  - Función programada (cron diario 12:00 UTC) que:  
    1. Descarga los nuevos informes mensuales.  
    2. Sube los PDFs al bucket S3.  
    3. Elimina versiones con más de 90 días para controlar costos.  
- **CI/CD**  
  - GitHub Actions ejecuta linter y tests en cada push  
  - Despliegue automático en Streamlit Cloud cuando la rama `main` pasa los checks  
- **Seguridad y Secrets**  
  - Variables de entorno en GitHub/Streamlit: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_BUCKET_NAME`  

---

## Funcionalidades Clave  
1. **Pipeline ETL**  
   - Construcción automática de URLs  
   - Extracción precisa de “producto + variación %”  
2. **Filtros Inteligentes**  
   - Preselección por defecto de “Panadería y Masas” y “Lácteos y Huevos”  
   - Filtrado por “Periodo Presidencial” 
3. **Visualizaciones Interactivas**  
   - Gráfico de líneas con hover unificado  
   - Top 5 alzas y bajas (barras horizontales)  
   - KPI de variación acumulada promedio  
4. **Interpretaciones Automáticas**  
   - Texto dinámico con “variación media”, “mayor alza puntual”, “mayor baja puntual”  
   - Tooltips y captions contextualizando cada indicador  

---

## Habilidades Demostradas  
- Arquitectura ETL para datos no estructurados (PDFs)  
- Implementación de microservicios en AWS (S3 + Lambda)  
- Diseño de dashboards de alto rendimiento y UX profesional  
- Desarrollo de KPIs compuestos y análisis político-económico  
- Integración CI/CD con GitHub Actions y Streamlit Cloud  

---

