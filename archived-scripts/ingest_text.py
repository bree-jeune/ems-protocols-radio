import json
import re

TEXT_FILE = "ems-protocol-manual.txt"
OUTPUT_FILE = "database_seed.json"

def parse_text_manual():
    print(f"📄 Reading {TEXT_FILE}...")
    
    with open(TEXT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        full_text = f.read()

    # Split by "PAGE" markers or capitalized headers
    # This regex looks for lines that are ALL CAPS and at least 5 chars long
    # It's a heuristic, but works well for manuals
    sections = re.split(r'\n([A-Z\s\/\-&]{5,})\n', full_text)
    
    database = {}
    
    # Iterate through chunks
    # re.split returns [preamble, title1, content1, title2, content2...]
    for i in range(1, len(sections), 2):
        title = sections[i].strip()
        content = sections[i+1].strip()
        
        # Filter out junk titles
        if "PAGE" in title or "TABLE OF CONTENTS" in title or len(content) < 50:
            continue
            
        protocol_id = title.lower().replace(" ", "_").replace("/", "_")
        
        print(f"   Found Protocol: {title}")
        
        database[protocol_id] = {
            "title": title.title(), # Convert "SEIZURE" to "Seizure"
            "raw_text": content
        }

    # Save to JSON
    with open(OUTPUT_FILE, "w") as f:
        json.dump(database, f, indent=4)
        
    print(f"✅ Successfully ingested {len(database)} protocols from text file!")

if __name__ == "__main__":
    parse_text_manual()