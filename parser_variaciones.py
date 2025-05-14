import pdfplumber
import os
import re
import pandas as pd

pdf_dir = 'pdf'
datos = []

for filename in sorted(os.listdir(pdf_dir)):
    if filename.endswith('.pdf'):
        ruta = os.path.join(pdf_dir, filename)
        print(f"📄 Procesando: {filename}")

        with pdfplumber.open(ruta) as pdf:
            for page in pdf.pages:
                texto = page.extract_text()

                # Buscar línea con mes y año (ej: "marzo 2025")
                for linea in texto.split('\n'):
                    if re.search(r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre) \d{4}", linea, re.IGNORECASE):
                        partes = linea.strip().lower().split()
                        mes = partes[0]
                        año = partes[1]
                        break

                # Buscar productos y valores tipo: "Pan 1,2"
                for linea in texto.split('\n'):
                    match = re.match(r"(.+?)\s+(-?\d+,\d+)", linea.strip())
                    if match:
                        producto = match.group(1).strip()
                        valor = match.group(2).replace(',', '.')
                        datos.append({
                            'producto': producto,
                            'valor': float(valor),
                            'mes': mes,
                            'año': int(año)
                        })

# Guardar como CSV
df = pd.DataFrame(datos)
df.to_csv('variaciones_canasta.csv', index=False)
print("\n✅ Archivo CSV generado: variaciones_canasta.csv")
