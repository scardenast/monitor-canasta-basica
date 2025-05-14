import pdfplumber
import os

# Carpeta de PDFs
pdf_dir = 'pdf'

# Recorre los archivos PDF
for filename in sorted(os.listdir(pdf_dir)):
    if filename.endswith('.pdf'):
        ruta = os.path.join(pdf_dir, filename)
        print(f"\n📄 Procesando archivo: {filename}")

        with pdfplumber.open(ruta) as pdf:
            for i, page in enumerate(pdf.pages):
                print(f"\n--- Página {i+1} ---")
                texto = page.extract_text()
                print(texto[:1000])  # Mostrar los primeros 1000 caracteres
