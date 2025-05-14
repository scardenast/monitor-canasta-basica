import pdfplumber
import os
import re
import pandas as pd
from collections import Counter

# Carpeta que contiene los archivos PDF
pdf_dir = 'pdf'
# Número de páginas iniciales a omitir (metadata/intros)
skip_pages = 1
# Nombre del archivo para lista blanca
iwhitelist_file = 'whitelist.txt'

# Expresión regular para líneas válidas: "Producto" seguido de espacio y valor decimal
patron_valido = re.compile(r"^(.+?)\s+(-?\d{1,3}(?:[.,]\d{1,2})?)$")

# Función para filtrar nombres válidos de producto

def es_nombre_valido(prod):
    # debe contener al menos una letra y no comenzar con dígito
    return bool(re.search(r"[A-Za-z]", prod)) and not prod[0].isdigit()

# 1) Generar automáticamente lista de candidatos de productos
candidates = []
for filename in sorted(os.listdir(pdf_dir)):
    if not filename.lower().endswith('.pdf'):
        continue
    ruta = os.path.join(pdf_dir, filename)
    with pdfplumber.open(ruta) as pdf:
        for page in pdf.pages[skip_pages:]:
            texto = page.extract_text() or ''
            for linea in texto.splitlines():
                match = patron_valido.match(linea.strip())
                if match:
                    prod = match.group(1).strip().lower()
                    if es_nombre_valido(prod):
                        candidates.append(prod)

# 2) Seleccionar los más frecuentes (top 10)
contador = Counter(candidates)
top_products = [prod for prod, _ in contador.most_common(10)]
# Guardar whitelist
with open(whitelist_file, 'w', encoding='utf-8') as f:
    for prod in top_products:
        f.write(prod + '\n')
print(f"✅ Lista blanca generada ({len(top_products)} productos): {top_products}")

auth_products = set(top_products)

datos = []

# 3) Extraer datos usando lista blanca
for filename in sorted(os.listdir(pdf_dir)):
    if not filename.lower().endswith('.pdf'):
        continue
    ruta = os.path.join(pdf_dir, filename)
    print(f"📄 Procesando archivo: {filename}")
    with pdfplumber.open(ruta) as pdf:
        mes, año = None, None
        for idx, page in enumerate(pdf.pages):
            if idx < skip_pages:
                continue
            texto = page.extract_text() or ''
            # Detectar mes y año (una sola vez)
            if mes is None or año is None:
                for linea in texto.splitlines():
                    fecha = re.search(
                        r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(\d{4})",
                        linea, re.IGNORECASE
                    )
                    if fecha:
                        mes = fecha.group(1).lower()
                        año = int(fecha.group(2))
                        print(f"   Fecha detectada: {mes.title()} {año}")
                        break
            if mes is None or año is None:
                continue

            # Extraer líneas válidas y filtradas
            for linea in texto.splitlines():
                match = patron_valido.match(linea.strip())
                if not match:
                    continue
                producto = match.group(1).strip().lower()
                if producto not in auth_products:
                    continue
                valor = float(match.group(2).replace(',', '.'))
                datos.append({
                    'producto': producto,
                    'valor': valor,
                    'mes': mes,
                    'año': año
                })

# 4) Guardar CSV final
if datos:
    df = pd.DataFrame(datos)
    df.to_csv('variaciones_canasta_limpio.csv', index=False)
    print(f"\n✅ CSV limpio guardado: variaciones_canasta_limpio.csv ({len(df)} registros)")
else:
    print("🚫 No se extrajeron datos válidos. Revisa tu whitelist o PDF.")
