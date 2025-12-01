import json
import re
from pydantic import BaseModel
from pypdf import PdfReader

# Configuration
PDF_PATH = "ems-protocol-manual.pdf"
OUTPUT_FILE = "database_seed.json"

# Based on your PDF, Adult Protocols are roughly pages 10 to 68
START_PAGE = 10 
END_PAGE = 68

def clean_title(text):
    """
    Heuristic to find the protocol title from the page text.
    Usually the first or second line in uppercase.
    """
    lines = text.split('\n')
    for line in lines[:5]: # Look at first 5 lines
        clean_line = line.strip()
        # If line is mostly uppercase and long enough, it's likely a title
        if len(clean_line) > 5 and clean_line.isupper():
            return clean_line.title() # Convert "SEIZURE" to "Seizure"
    return "Unknown Protocol"

def ingest_manual():
    print(f"📚 Reading {PDF_PATH}...")
    reader = PdfReader(PDF_PATH)
    
    database = {}
    
    # Loop through the specific page range
    for i in range(START_PAGE, END_PAGE):
        page = reader.pages[i]
        text = page.extract_text()
        
        if not text:
            continue

        # Extract Title
        title = clean_title(text)
        
        # Create a unique ID (e.g., "Seizure" -> "seizure")
        protocol_id = title.lower().replace(" ", "_").replace("/", "_")
        
        # Skip generic pages if they don't look like protocols
        if "General" in title or "Table" in title:
            continue

        print(f"   Found: {title}")

        # Add to Database
        database[protocol_id] = {
            "title": title,
            "page_number": i + 1, # Humans read 1-based, Python is 0-based
            "raw_text": text[:500] + "..." # Store first 500 chars for preview
        }

    # Save to JSON
    with open(OUTPUT_FILE, "w") as f:
        json.dump(database, f, indent=4)
    
    print(f"✅ Successfully ingested {len(database)} protocols into {OUTPUT_FILE}")

if __name__ == "__main__":
    ingest_manual()