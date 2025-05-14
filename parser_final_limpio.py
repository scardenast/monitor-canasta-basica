import pdfplumber
import os
import re
import pandas as pd
from collections import Counter

# Carpeta que contiene los archivos PDF
df_dir = 'pdf'
# Número de páginas iniciales a omitir (metadata/intros)
skip_pages = 1
# Archivo de lista blanca
ewhitelist_file = 'whitelist.txt'
# Expresión regular para líneas válidas: producto + valor\patron_valido = re.compile(r"^(.+?)\s+(-?\d{1,3}(?:[.,]\d{1,2})?)$")

# 1) Generar automáticamente la lista de productos (candidatos)
candidates = []
for filename in sorted(os.listdir(df_dir)):
    if not filename.lower().endswith('.pdf'):
        continue
    ruta = os.path.join(df_dir, filename)
    with pdfplumber.open(ruta) as pdf:
        for page in pdf.pages[skip_pages:]:
            texto = page.extract_text() or ''
            for linea in texto.splitlines():
                match = patron_valido.match(linea.strip())
                if match:
                    producto = match.group(1).strip().lower()
                    candidates.append(producto)

# 2) Contar frecuencias y seleccionar top 10 productos
contador = Counter(candidates)
top_products = [prod for prod, _ in contador.most_common(10)]
# Guardar whitelist
with open(whitelist_file, 'w', encoding='utf-8') as f:
    for prod in top_products:
        f.write(prod + '\n')
print(f"✅ Lista blanca generada automáticamente con {len(top_products)} productos: {top_products}")

# 3) Cargar lista blanca y procesar datos limpios
auth_products = set(top_products)

datos = []

for filename in sorted(os.listdir(df_dir)):
    if not filename.lower().endswith('.pdf'):
        continue
    ruta = os.path.join(df_dir, filename)
    print(f"📄 Procesando: {filename}")
    with pdfplumber.open(ruta) as pdf:
        mes, año = None, None
        for idx, page in enumerate(pdf.pages):
            if idx < skip_pages:
                continue
            texto = page.extract_text() or ''
            # Detectar mes y año
            if not mes or not año:
                for linea in texto.splitlines():
                    fecha = re.search(r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(\d{4})", linea, re.IGNORECASE)
                    if fecha:
                        mes = fecha.group(1).lower()
                        año = int(fecha.group(2))
                        break
            if not mes or not año:
                continue
            # Extraer solo productos de la lista blanca
            for linea in texto.splitlines():
                match = patron_valido.match(linea.strip())
                if not match:
                    continue
                producto = match.group(1).strip().lower()
                if producto not in auth_products:
                    continue
                valor = float(match.group(2).replace(',', '.'))
                datos.append({'producto': producto, 'valor': valor, 'mes': mes, 'año': año})

# Guardar CSV final
df = pd.DataFrame(datos)
df.to_csv('variaciones_canasta_limpio.csv', index=False)
print(f"\n✅ CSV limpio generado con {len(df)} registros.")
