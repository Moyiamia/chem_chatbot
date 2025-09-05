import pytesseract
from pdf2image import convert_from_path
import json
import os
import re
from module_links import MODULE_LINKS

pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

PDF_FOLDER = "pdfs"
OUTPUT_FOLDER = "modules_ocr"  

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.endswith(".pdf")]

for filename in pdf_files:
    PDF_FILENAME = os.path.join(PDF_FOLDER, filename)
    MODULE_NAME = os.path.splitext(filename)[0]
    MODULE_LINK = MODULE_LINKS.get(MODULE_NAME, "N/A")

    images = convert_from_path(PDF_FILENAME, dpi=300)
    structured_data = []

    for i, image in enumerate(images):
        text = pytesseract.image_to_string(image)

        
        paragraphs = [p.strip() for p in re.split(r"\n{2,}|\n\s*\n", text) if len(p.strip()) > 50]

        for para in paragraphs:
            structured_data.append({
                "text": para,
                "module": MODULE_NAME,
                "source": MODULE_LINK,
                "page": i + 1
            })

    output_path = os.path.join(OUTPUT_FOLDER, f"{MODULE_NAME}.jsonl")
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in structured_data:
            json.dump(entry, f, ensure_ascii=False)
            f.write("\n")

    print(f"{MODULE_NAME} done. {len(structured_data)} chunks saved to {output_path}")
