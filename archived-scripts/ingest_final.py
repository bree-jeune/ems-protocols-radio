import json
import re

TEXT_FILE = "ems-protocol-manual.txt"
OUTPUT_FILE = "database_seed.json"

def clean_block(text):
    """Cleans up the text block: removes page nums, joins broken lines."""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        l = line.strip()
        # Remove page numbers (lines that are just digits) and tiny artifacts
        if re.match(r'^\d+$', l) or len(l) < 3:
            continue
        cleaned.append(l)
    return '\n'.join(cleaned)

def parse_manual_blocks():
    print(f"📄 Reading {TEXT_FILE}...")
    with open(TEXT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        full_text = f.read()

    database = {}

    # 1. Define Categories and their Protocols explicitly
    SECTIONS = [
        ("Adult", [
            "General Adult Assessment", "General Adult Trauma Assessment", "Abdominal Pain/Flank Pain, Nausea & Vomiting",
            "Allergic Reaction", "Altered Mental Status/Syncope", "Behavioral Emergencies", "Bradycardia", "Burns",
            "Cardiac Arrest (Non-Traumatic)", "Chest Pain (Non-Traumatic) and Suspected Acute Coronary Syndrome",
            "Childbirth/Labor", "Cold Related Illness", "Epistaxis", "Heat-Related Illness", "Hyperkalemia (Suspected)",
            "Obstetrical Emergency", "Overdose/Poisoning", "Pain Management", "Pulmonary Edema/CHF",
            "Respiratory Distress", "Seizure", "Sepsis", "Shock", "Smoke Inhalation", "STEMI (Suspected)",
            "Stroke (CVA)", "Tachycardia/Stable", "Tachycardia/Unstable", "Ventilation Management"
        ]),
        ("Pediatric", [
            "General Pediatric Assessment", "General Pediatric Trauma Assessment", "Abdominal/Flank Pain, Nausea & Vomiting",
            "Pediatric Allergic Reaction", "Pediatric Altered Mental Status", "Pediatric Behavioral Emergency", 
            "Pediatric Bradycardia", "Pediatric Burns", "Pediatric Cardiac Arrest (Non-Traumatic)", 
            "Pediatric Cold-Related Illness", "Pediatric Epistaxis", "Pediatric Heat-Related Illness", 
            "Neonatal Resuscitation", "Pediatric Overdose / Poisoning", "Pediatric Pain Management", 
            "Pediatric Respiratory Distress", "Pediatric Seizure", "Pediatric Shock", "Pediatric Smoke Inhalation",
            "Pediatric Tachycardia / Stable", "Pediatric Tachycardia / Unstable", "Pediatric Ventilation Management",
            "Pediatric Patient Destination"
        ]),
        ("Procedures", [
            "Cervical Stabilization", "Electrical Therapy/Defibrillation", "Electrical Therapy/Synchronized Cardioversion",
            "Electrical Therapy/Transcutaneous Pacing", "Endotracheal Intubation", "Extraglottic Device",
            "First Response Evaluate/Release", "Hemorrhage Control", "Medication Administration",
            "Needle Cricothyroidotomy", "Needle Thoracostomy", "Non-Invasive Positive Pressure Ventilation (NIPPV)",
            "Patient Restraint", "Tracheostomy Tube Replacement", "Traction Splint", "Vagal Maneuvers", "Vascular Access"
        ]),
        ("Operations", [
            "Communications", "Do Not Resuscitate (DNR/POLST)", "Documentation", "Hostile Mass Casualty Incident",
            "Inter-Facility Transfer of Patients by Ambulance", "Prehospital Death Determination",
            "Public Intoxication/Mental Health Crisis", "Quality Improvement Review", "Termination of Resuscitation",
            "Transport Destinations", "Trauma Field Triage Criteria", "Waiting Room Criteria"
        ])
    ]

    # 2. Build the Giant Regex Pattern
    all_titles_flat = []
    title_to_cat = {}
    
    for cat, titles in SECTIONS:
        for t in titles:
            all_titles_flat.append(t)
            title_to_cat[t.upper()] = cat

    # Sort by length (longest first)
    all_titles_flat.sort(key=len, reverse=True)
    
    escaped = [re.escape(t) for t in all_titles_flat]
    pattern = r'(' + '|'.join(escaped) + r')'

    # 3. SPLIT THE FILE
    segments = re.split(pattern, full_text, flags=re.IGNORECASE)

    print(f"   🔍 Found {len(segments)} blocks.")

    # 4. Process Blocks
    for i in range(1, len(segments), 2):
        raw_title = segments[i].strip()
        content = segments[i+1]
        
        # Determine Category & Clean Title
        clean_title = raw_title.title()\
            .replace("Cva", "CVA").replace("Chf", "CHF")\
            .replace("Stemi", "STEMI").replace("Dnr", "DNR")\
            .replace("Polst", "POLST").replace("Nippv", "NIPPV")\
            .replace("Ecmo", "ECMO")
            
        category = title_to_cat.get(raw_title.upper(), "Uncategorized")
        
        # Generate ID
        prot_id = clean_title.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        
        # SKIP if content is basically empty (just a header found in TOC)
        if len(content) < 50: 
            continue 

        cleaned_text = clean_block(content)

        # --- MERGE LOGIC ---
        if prot_id in database:
            # If the category matches, it's the same protocol on the next page. MERGE IT.
            if database[prot_id]['category'] == category:
                print(f"   🔗 Merging Page 2 for: {clean_title}")
                database[prot_id]['raw_text'] += "\n\n" + cleaned_text
            else:
                # Same name, different category (e.g. Seizure Adult vs Seizure Pediatric)
                new_id = f"{prot_id}_{category.lower()}"
                database[new_id] = {
                    "title": clean_title,
                    "category": category,
                    "raw_text": cleaned_text
                }
                print(f"   ✅ [{category}] New Entry: {clean_title} ({new_id})")
        else:
            # New Entry
            database[prot_id] = {
                "title": clean_title,
                "category": category,
                "raw_text": cleaned_text
            }
            print(f"   ✅ [{category}] {clean_title}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(database, f, indent=4)
    
    print(f"🎉 Database rebuilt. Verified {len(database)} unique items.")

if __name__ == "__main__":
    parse_manual_blocks()