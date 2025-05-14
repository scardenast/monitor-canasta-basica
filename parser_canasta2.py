import pdfplumber
import re
import os
import pandas as pd

# Carpeta que contiene los archivos PDF
pdf_dir = 'pdf'
# Páginas a omitir al inicio de cada PDF (metadatos/intros)
skip_pages = 1

# Construir lista dinámica de archivos PDF en la carpeta
def list_pdf_files(directory):
    return [f for f in sorted(os.listdir(directory)) if f.lower().endswith('.pdf')]

# Función para extraer métricas generales (CBA, LP, LPE) de 'Cuadro 1'
def extract_summary(pdf_path):
    summary = {}
    pattern = re.compile(
        r"CBA\s+(\d+[.,]?\d*)|LP por persona equivalente\s+(\d+[.,]?\d*)|LPE por persona equivalente\s+(\d+[.,]?\d*)",
        re.IGNORECASE
    )
    with pdfplumber.open(pdf_path) as pdf:
        # Leer primeras páginas donde suele estar Cuadro 1
        text = "".join(page.extract_text() or '' for page in pdf.pages[:skip_pages + 2])
        for match in pattern.finditer(text):
            if match.group(1): summary['CBA'] = float(match.group(1).replace('.', '').replace(',', '.'))
            if match.group(2): summary['LP']  = float(match.group(2).replace('.', '').replace(',', '.'))
            if match.group(3): summary['LPE'] = float(match.group(3).replace('.', '').replace(',', '.'))
    return summary

# Función para extraer variaciones de productos de 'Anexo 2'
def extract_variations(pdf_path):
    records = []
    table_start = False
    pattern = re.compile(r"^(.+?)\s+(-?\d+[.,]?\d*)$")
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ''
            for line in text.split('\n'):
                # Marcar inicio de la sección Anexo 2
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
    return pd.DataFrame(records)

# Script principal
def main():
    pdf_files = list_pdf_files(pdf_dir)
    if not pdf_files:
        print(f"🚫 No se encontraron archivos PDF en la carpeta '{pdf_dir}'")
        return

    summaries = []
    variations = []

    for pdf_name in pdf_files:
        path = os.path.join(pdf_dir, pdf_name)
        print(f"Procesando {pdf_name}...")

        # Extraer resumen
        summary = extract_summary(path)
        summary['file'] = pdf_name
        summaries.append(summary)

        # Extraer variaciones
        df_var = extract_variations(path)
        if not df_var.empty:
            df_var['file'] = pdf_name
            variations.append(df_var)

    # Consolidar resultados
    df_summary    = pd.DataFrame(summaries)
    df_variations = pd.concat(variations, ignore_index=True) if variations else pd.DataFrame()

    # Guardar outputs
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    df_summary.to_csv(os.path.join(output_dir, 'resumen_canasta.csv'), index=False)
    df_variations.to_csv(os.path.join(output_dir, 'variaciones_productos.csv'), index=False)

    print("\n✅ Extracción completa")
    print(f"- Resumen guardado en: {output_dir}/resumen_canasta.csv")
    print(f"- Variaciones guardado en: {output_dir}/variaciones_productos.csv")

if __name__ == '__main__':
    main()
