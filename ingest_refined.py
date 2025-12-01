import json
import re

TEXT_FILE = "ems-protocol-manual.txt"
OUTPUT_FILE = "database_seed.json"

def clean_text(text):
    # Remove lines that are just page numbers
    lines = [line for line in text.split('\n') if not re.match(r'^\d+$', line.strip())]
    return '\n'.join(lines).strip()

def parse_manual_strict():
    print(f"📄 Reading {TEXT_FILE}...")
    
    with open(TEXT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        full_text = f.read()

    database = {}

    # Strict Lists based on your Table of Contents
    CATEGORY_MAP = {
        "Adult": [
            "General Adult Assessment", "General Adult Trauma Assessment", "Abdominal Pain/Flank Pain, Nausea & Vomiting",
            "Allergic Reaction", "Altered Mental Status/Syncope", "Behavioral Emergencies", "Bradycardia", "Burns",
            "Cardiac Arrest (Non-Traumatic)", "Chest Pain (Non-Traumatic) and Suspected Acute Coronary Syndrome",
            "Childbirth/Labor", "Cold Related Illness", "Epistaxis", "Heat-Related Illness", "Hyperkalemia (Suspected)",
            "Obstetrical Emergency", "Overdose/Poisoning", "Pain Management", "Pulmonary Edema/CHF",
            "Respiratory Distress", "Seizure", "Sepsis", "Shock", "Smoke Inhalation", "STEMI (Suspected)",
            "Stroke (CVA)", "Tachycardia/Stable", "Tachycardia/Unstable", "Ventilation Management"
        ],
        "Pediatric": [
            "General Pediatric Assessment", "General Pediatric Trauma Assessment", "Abdominal/Flank Pain, Nausea & Vomiting",
            "Pediatric Allergic Reaction", "Pediatric Altered Mental Status", "Pediatric Behavioral Emergency", 
            "Pediatric Bradycardia", "Pediatric Burns", "Pediatric Cardiac Arrest (Non-Traumatic)", 
            "Pediatric Cold-Related Illness", "Pediatric Epistaxis", "Pediatric Heat-Related Illness", 
            "Neonatal Resuscitation", "Pediatric Overdose / Poisoning", "Pediatric Pain Management", 
            "Pediatric Respiratory Distress", "Pediatric Seizure", "Pediatric Shock", "Pediatric Smoke Inhalation",
            "Pediatric Tachycardia / Stable", "Pediatric Tachycardia / Unstable", "Pediatric Ventilation Management",
            "Pediatric Patient Destination"
        ],
        "Procedures": [
            "Cervical Stabilization", "Electrical Therapy/Defibrillation", "Electrical Therapy/Synchronized Cardioversion",
            "Electrical Therapy/Transcutaneous Pacing", "Endotracheal Intubation", "Extraglottic Device",
            "First Response Evaluate/Release", "Hemorrhage Control", "Medication Administration",
            "Needle Cricothyroidotomy", "Needle Thoracostomy", "Non-Invasive Positive Pressure Ventilation (NIPPV)",
            "Patient Restraint", "Tracheostomy Tube Replacement", "Traction Splint", "Vagal Maneuvers", "Vascular Access"
        ],
        "Operations": [
            "Communications", "Do Not Resuscitate (DNR/POLST)", "Documentation", "Hostile Mass Casualty Incident",
            "Inter-Facility Transfer of Patients by Ambulance", "Prehospital Death Determination",
            "Public Intoxication/Mental Health Crisis", "Quality Improvement Review", "Termination of Resuscitation",
            "Transport Destinations", "Trauma Field Triage Criteria", "Waiting Room Criteria"
        ]
    }

    # Build a lookup map for case-insensitive matching
    # Map "BRADYCARDIA" -> ("Bradycardia", "Adult")
    title_lookup = {}
    
    # We also create a regex pattern to find these titles in the text
    all_titles = []

    for cat, titles in CATEGORY_MAP.items():
        for t in titles:
            clean_t = t.strip()
            all_titles.append(clean_t)
            title_lookup[clean_t.upper()] = (clean_t, cat)

    # Sort titles by length (longest first) to match "General Adult Trauma Assessment" before "General Adult Assessment"
    all_titles.sort(key=len, reverse=True)
    
    # Escape for Regex
    escaped_titles = [re.escape(t) for t in all_titles]
    pattern = r'\n(' + '|'.join(escaped_titles) + r')\n'
    
    # Split the entire file using the Titles as delimiters
    splits = re.split(pattern, full_text, flags=re.IGNORECASE)
    
    print(f"   🔍 Found {len(splits)} segments")

    # Iterate through the splits. 
    # split[i] is the Content before the title
    # split[i+1] is the Title itself
    # split[i+2] is the Content of that title
    
    # We skip index 0 (preamble text)
    for i in range(1, len(splits), 2):
        raw_title = splits[i].strip()
        
        # Guard check: Ensure next index exists
        if i + 1 >= len(splits): break
        
        content = splits[i+1].strip()

        # Lookup proper casing and category
        lookup_key = raw_title.upper()
        
        # Direct lookup
        if lookup_key in title_lookup:
            proper_title, category = title_lookup[lookup_key]
        else:
            # Fallback: fuzzy match
            continue

        # Create ID
        prot_id = proper_title.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        
        # Handle Duplicates (e.g. Seizure in Adult vs Peds)
        if prot_id in database:
            # If the category is different, append category to ID
            if database[prot_id]['category'] != category:
                prot_id = f"{prot_id}_{category.lower()}"
            else:
                # Same ID, Same Category? It's likely a Table of Contents entry or duplicate.
                # If the new content is longer, overwrite. If shorter, skip.
                if len(content) > len(database[prot_id]['raw_text']):
                    pass # Proceed to overwrite
                else:
                    continue # Skip this duplicate

        # Ignore empty/short sections (likely Table of Contents matches)
        if len(content) < 100:
            continue

        database[prot_id] = {
            "title": proper_title,
            "category": category,
            "raw_text": clean_text(content)
        }
        print(f"   ✅ [{category}] {proper_title}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(database, f, indent=4)
    
    print(f"🎉 Database rebuilt. Verified {len(database)} items.")

if __name__ == "__main__":
    parse_manual_strict()