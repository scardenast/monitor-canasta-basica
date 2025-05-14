import pdfplumber
import os
import re
import pandas as pd

pdf_dir = 'pdf'
datos = []

# Regex que detecta una línea tipo: Producto + espacio + número decimal positivo o negativo
patron_linea_valida = re.compile(r"^(.+?)\s+(-?\d{1,4}(?:[.,]\d{1,2})?)$")

for filename in sorted(os.listdir(pdf_dir)):
    if filename.endswith('.pdf'):
        ruta = os.path.join(pdf_dir, filename)
        print(f"📄 Procesando: {filename}")

        with pdfplumber.open(ruta) as pdf:
            for page in pdf.pages:
                texto = page.extract_text()

                # Buscar mes y año (ej: "diciembre 2015")
                mes, año = None, None
                for linea in texto.split('\n'):
                    fecha = re.search(r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(\d{4})", linea, re.IGNORECASE)
                    if fecha:
                        mes = fecha.group(1).lower()
                        año = fecha.group(2)
                        break

                # Procesar solo si se encontró mes y año
                if not mes or not año:
                    continue

                for linea in texto.split('\n'):
                    match = patron_linea_valida.match(linea.strip())
                    if match:
                        producto = match.group(1).strip()
                        valor_raw = match.group(2).replace(",", ".")
                        try:
                            valor = float(valor_raw)
                            datos.append({
                                "producto": producto,
                                "valor": valor,
                                "mes": mes,
                                "año": int(año)
                            })
                        except ValueError:
                            continue

# Guardar CSV limpio
df = pd.DataFrame(datos)
df.to_csv("variaciones_canasta_limpio.csv", index=False)
print("\n✅ Archivo limpio generado: variaciones_canasta_limpio.csv")
