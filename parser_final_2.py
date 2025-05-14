import pdfplumber
import os
import re
import pandas as pd

# Carpeta que contiene los archivos PDF
pdf_dir = 'pdf'

# Archivo opcional con lista blanca de productos (uno por línea, en minúsculas)
whitelist_file = 'whitelist.txt'
if os.path.exists(whitelist_file):
    with open(whitelist_file, 'r', encoding='utf-8') as f:
        valid_products = set(line.strip().lower() for line in f if line.strip())
    print(f"📋 Lista blanca cargada con {len(valid_products)} productos.")
else:
    valid_products = None
    print("⚠️ No se encontró 'whitelist.txt'. Se incluirán todos los productos.")

# Número de páginas iniciales a omitir (metadata/intros)
skip_pages = 1

datos = []

# Regex para línea válida: texto + número decimal al final
patron_valido = re.compile(r"^(.+?)\s+(-?\d{1,3}(?:[.,]\d{1,2})?)$")

for filename in sorted(os.listdir(pdf_dir)):
    if not filename.lower().endswith('.pdf'):
        continue
    ruta = os.path.join(pdf_dir, filename)
    print(f"📄 Procesando: {filename}")

    with pdfplumber.open(ruta) as pdf:
        mes, año = None, None
        # Iterar páginas con índice para omitir las iniciales
        for idx, page in enumerate(pdf.pages):
            if idx < skip_pages:
                # Omitir primeras páginas de introducción
                continue
            texto = page.extract_text() or ''

            # Detectar mes y año (solo una vez)
            if mes is None or año is None:
                for linea in texto.splitlines():
                    fecha = re.search(r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(\d{4})", linea, re.IGNORECASE)
                    if fecha:
                        mes = fecha.group(1).lower()
                        año = int(fecha.group(2))
                        print(f"   Fecha detectada: {mes.title()} {año}")
                        break
            if not mes or not año:
                # Si no encontramos fecha aún, seguir buscando
                continue

            # Extraer líneas de producto y valor
            for linea in texto.splitlines():
                # Filtrar líneas con múltiples comas o sin dígitos
                if linea.count(',') > 1 or not any(char.isdigit() for char in linea):
                    continue
                match = patron_valido.match(linea.strip())
                if not match:
                    continue

                producto = match.group(1).strip()
                valor_raw = match.group(2).replace(',', '.')
                try:
                    valor = float(valor_raw)
                except ValueError:
                    continue

                # Aplicar lista blanca si existe
                if valid_products is not None and producto.lower() not in valid_products:
                    continue

                datos.append({
                    'producto': producto,
                    'valor': valor,
                    'mes': mes,
                    'año': año
                })

# Guardar el archivo limpio
if datos:
    df = pd.DataFrame(datos)
    df.to_csv('variaciones_canasta_limpio.csv', index=False)
    print(f"\n✅ Archivo limpio generado: 'variaciones_canasta_limpio.csv' con {len(df)} registros.")
else:
    print("🚫 No se encontraron datos válidos. Revisa la lista blanca o la estructura de los PDFs.")
