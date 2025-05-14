import pdfplumber
import os
import re
import pandas as pd

pdf_dir = 'pdf'
datos = []

# Expresión regular que identifica: "Producto" + número válido al final
patron_valido = re.compile(r"^(.+?)\s+(-?\d{1,3}(?:[.,]\d{1,2})?)$")

for filename in sorted(os.listdir(pdf_dir)):
    if filename.endswith('.pdf'):
        ruta = os.path.join(pdf_dir, filename)
        print(f"📄 Procesando: {filename}")

        with pdfplumber.open(ruta) as pdf:
            for page in pdf.pages:
                texto = page.extract_text()
                if not texto:
                    continue

                # Detectar mes y año solo si no han sido definidos
                mes, año = None, None
                for linea in texto.split('\n'):
                    fecha = re.search(r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(\d{4})", linea, re.IGNORECASE)
                    if fecha:
                        mes = fecha.group(1).lower()
                        año = int(fecha.group(2))
                        break

                if not mes or not año:
                    continue

                # Extraer líneas tipo: Producto [espacios] número final
                for linea in texto.split('\n'):
                    # Descarta líneas con más de una coma (texto complejo)
                    if linea.count(',') > 1 or not any(char.isdigit() for char in linea):
                        continue

                    match = patron_valido.match(linea.strip())
                    if match:
                        producto = match.group(1).strip()
                        valor_raw = match.group(2).replace(",", ".")
                        try:
                            valor = float(valor_raw)
                            datos.append({
                                "producto": producto,
                                "valor": valor,
                                "mes": mes,
                                "año": año
                            })
                        except ValueError:
                            continue

# Guardar el archivo limpio
df = pd.DataFrame(datos)
df.to_csv("variaciones_canasta_limpio.csv", index=False)
print("\n✅ Archivo limpio generado con éxito.")
