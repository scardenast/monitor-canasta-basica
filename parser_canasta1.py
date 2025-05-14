import pdfplumber
import re
import os
import pandas as pd

# Lista de PDFs a procesar (solo últimos 3: enero, marzo, abril 2025)
pdf_files = [
    'Valor_cb_ENE_2025.pdf',
    'Valor_cb_FEB_2025.pdf',
    'Valor_cb_MAR_2025.pdf'
]

# Páginas a omitir al inicio de cada PDF (metadatos/intros)
skip_pages = 1

# Función para extraer métricas generales (CBA, LP, LPE) de 'Cuadro 1'
def extract_summary(pdf_path):
    summary = {}
    pattern = re.compile(r"CBA\s+(\d+[.,]?\d*)|LP por persona equivalente\s+(\d+[.,]?\d*)|LPE por persona equivalente\s+(\d+[.,]?\d*)")
    with pdfplumber.open(pdf_path) as pdf:
        text = "".join(page.extract_text() or '' for page in pdf.pages[:skip_pages+2])
        for match in pattern.finditer(text):
            if match.group(1): summary['CBA'] = float(match.group(1).replace('.', '').replace(',', '.'))
            if match.group(2): summary['LP'] = float(match.group(2).replace('.', '').replace(',', '.'))
            if match.group(3): summary['LPE'] = float(match.group(3).replace('.', '').replace(',', '.'))
    return summary

# Función para extraer variaciones de productos de 'Anexo 2'
def extract_variations(pdf_path):
    records = []
    table_start = False
    # regex para líneas de variación: "Producto <valor>"
    pattern = re.compile(r"^(.+?)\s+(-?\d+[.,]?\d*)$")
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ''
            for line in text.split('\n'):
                # Indicar inicio cuando aparece 'Anexo 2'
                if 'Anexo 2' in line:
                    table_start = True
                    continue
                if not table_start:
                    continue
                match = pattern.match(line.strip())
                if match:
                    producto = match.group(1).strip()
                    valor = float(match.group(2).replace(',', '.'))
                    records.append({'producto': producto, 'variacion': valor})
    # Convertir a DataFrame
    return pd.DataFrame(records)

# Función principal
if __name__ == '__main__':
    all_summaries = []
    all_variations = []
    for pdf_name in pdf_files:
        path = os.path.join('pdf', pdf_name)
        if not os.path.isfile(path):
            print(f"⚠️ Archivo no encontrado: {pdf_name}")
            continue
        print(f"Procesando {pdf_name}...")
        summary = extract_summary(path)
        summary['file'] = pdf_name
        all_summaries.append(summary)

        df_var = extract_variations(path)
        df_var['file'] = pdf_name
        all_variations.append(df_var)

    # Consolidar resultados
df_summary = pd.DataFrame(all_summaries)
df_variations = pd.concat(all_variations, ignore_index=True)

# Guardar outputs
output_dir = 'output'
os.makedirs(output_dir, exist_ok=True)
df_summary.to_csv(os.path.join(output_dir, 'resumen_canasta.csv'), index=False)
df_variations.to_csv(os.path.join(output_dir, 'variaciones_productos.csv'), index=False)

print("\n✅ Extracción completa:")
print(f"- Resumen guardado en: {output_dir}/resumen_canasta.csv")
print(f"- Variaciones guardado en: {output_dir}/variaciones_productos.csv")
