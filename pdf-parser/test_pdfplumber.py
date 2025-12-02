import pdfplumber #Python library for reading and extracting text from pdfs
import re #Python’s regular expression library,  search and modify text patterns (used for cleaning double letters)

#Tells Python which PDF to open
pdf_path = "ems-protocol-manual-OCT25.pdf"

# Initial parsing returned double letters
# This function "cleans the text" to fix the double letter problem
# Step-by-step:
#   Checks if text is empty, returns an empty string if so.
#   re.sub(r'(.)\1', r'\1', text): Looks for any two identical characters (e.g., “SS”, “ee”, etc.) and replaces them with just one.
#   re.sub(r'\s+', ' ', cleaned): Collapses multiple spaces/tabs/newlines into a single space for easier reading.
#   Returns the cleaned text


def clean_duplicated_text(text: str) -> str:
    if not text:
        return ""

    # Collapses double letters: "CCaarrddiiaacc" -> "Cardiac"
    # Strategy: replace any pair of identical letters with a single one.
    cleaned = re.sub(r'(.)\1', r'\1', text)

    # Also collapse multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)

    return cleaned

    #  Safely opens PDF file as pdf
    # The with ... as ...: syntax auto‑closes the file when done.

with pdfplumber.open(pdf_path) as pdf:
    # Counts how many pages are in the document, so we know the loop bounds
    print(f"Total pages: {len(pdf.pages)}") 

    # Loop Over First Pages
    # For the first 3 pages (range(3)):
        # page = pdf.pages[page_num] grabs the current page.

        # raw = page.extract_text() pulls out all the text from the page in raw, so you can see what it’s like before cleaning.

        # cleaned = clean_duplicated_text(raw) runs your cleaner on that text.

        # The print statements show you the cleaned output, page by page.

    for page_num in range(3):
        page = pdf.pages[page_num]
        raw = page.extract_text()
        cleaned = clean_duplicated_text(raw)

        print(f"\n--- PAGE {page_num + 1} (CLEANED) ---\n")
        print(cleaned)
