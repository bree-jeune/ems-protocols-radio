import pdfplumber
import re
from pathlib import Path

pdf_path = "ems-protocol-manual-OCT25.pdf"
output_dir = Path("output_pages")
output_dir.mkdir(exist_ok=True)

def clean_duplicated_text(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r'(.)\1', r'\1', text)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")

    for page_num, page in enumerate(pdf.pages, start=1):
        raw = page.extract_text()
        cleaned = clean_duplicated_text(raw)

        out_path = output_dir / f"page_{page_num:03}.txt"
        with out_path.open("w", encoding="utf-8") as f:
            f.write(cleaned)

        print(f"Saved {out_path}")
