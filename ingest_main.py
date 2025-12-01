import json
import re
import os

TEXT_FILE = "ems-protocol-manual.txt"
OUTPUT_FILE = "ems_protocols.json"

class EMSIngestor:
    def __init__(self, filepath):
        self.filepath = filepath
        self.raw_text = ""
        self.database = {}
        
        # Define the exact titles we look for in the manual
        self.PROTOCOL_MAP = {
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

    def load_and_clean(self):
        print(f"📄 Reading {self.filepath}...")
        with open(self.filepath, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        
        # 1. Remove Page Numbers (digits on a line by themselves)
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        
        # 2. Remove Headers that repeat on every page (Modify "CLARK COUNTY" to match your header)
        text = re.sub(r'CLARK COUNTY EMS SYSTEM.*?\n', '', text, flags=re.IGNORECASE)
        
        self.raw_text = text
        print("   ✅ Text cleaned (Removed page numbers and artifacts)")

    def parse_formulary(self):
        """Extracts the Drug List specifically."""
        print("   💊 Parsing Formulary...")
        
        # Find the section between "FORMULARY" and "APPENDICES"
        match = re.search(r'FORMULARY(.*?)(APPENDICES|Scope of Practice)', self.raw_text, re.DOTALL)
        if not match:
            print("   ⚠️  Formulary section not found.")
            return

        formulary_text = match.group(1)
        
        # Simple Regex to find drug blocks: Look for all caps lines followed by "CLASS:"
        # This regex looks for a WORD in caps, newline, then "CLASS:"
        drug_pattern = r'([A-Z][A-Z0-9 \-\/\(\)]+)\n+CLASS:'
        
        splits = re.split(drug_pattern, formulary_text)
        
        # split[0] is garbage, then it alternates: Title, Content, Title, Content
        for i in range(1, len(splits), 2):
            name = splits[i].strip()
            content = "CLASS:" + splits[i+1] # Add CLASS back in
            
            # Create a clean ID
            drug_id = name.lower().replace(" ", "_").replace("(", "").replace(")", "").replace(":", "")
            
            # Extract basic metadata
            class_match = re.search(r'CLASS:\s*(.+)', content)
            action_match = re.search(r'ACTION:\s*(.+)', content)
            dose_match = re.search(r'DOSE:\s*(.+)', content)
            
            self.database[drug_id] = {
                "title": name.title(),
                "category": "Formulary",
                "raw_text": content.strip(),
                "metadata": {
                    "class": class_match.group(1).strip() if class_match else "Unknown",
                    "action": action_match.group(1).strip() if action_match else "Unknown",
                    "dose_snippet": dose_match.group(1).strip() if dose_match else "See text"
                }
            }

    def parse_protocols(self):
        """Parses the main protocols using strict Zone logic."""
        
        # Create a giant map of Title -> Category
        title_map = {}
        all_titles = []
        for cat, titles in self.PROTOCOL_MAP.items():
            for t in titles:
                title_map[t.upper()] = cat
                all_titles.append(t)
        
        # Sort titles by length (longest first) to match specific titles before generic ones
        all_titles.sort(key=len, reverse=True)
        
        # Create regex to split the file by these titles
        escaped_titles = [re.escape(t) for t in all_titles]
        pattern = r'(' + '|'.join(escaped_titles) + r')'
        
        segments = re.split(pattern, self.raw_text, flags=re.IGNORECASE)
        
        print(f"   🔍 Found {len(segments)//2} protocol blocks.")

        for i in range(1, len(segments), 2):
            raw_title = segments[i].strip()
            content = segments[i+1].strip()
            
            if len(content) < 50: continue # Skip TOC entries
            
            # Determine Category
            category = title_map.get(raw_title.upper(), "Uncategorized")
            
            # Clean Title
            clean_title = raw_title.title()\
                .replace("Cva", "CVA").replace("Chf", "CHF")\
                .replace("Stemi", "STEMI").replace("Dnr", "DNR")\
                .replace("Polst", "POLST").replace("Nippv", "NIPPV")
            
            # Handle Pediatric names that don't have "Pediatric" in the title text
            if category == "Pediatric" and "Pediatric" not in clean_title and "Neonatal" not in clean_title:
                clean_title = f"Pediatric {clean_title}"

            # Generate ID
            prot_id = clean_title.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
            
            # Merge Logic (If ID exists, append text)
            if prot_id in self.database:
                self.database[prot_id]["raw_text"] += "\n\n" + content
            else:
                self.database[prot_id] = {
                    "title": clean_title,
                    "category": category,
                    "raw_text": content,
                    "metadata": {} # Placeholder for future extraction
                }

    def save(self):
        # Wrap it in the structure your API expects
        output = {
            "metadata": {"version": "1.0", "source": "IngestMaster"},
            "protocols": self.database
        }
        
        with open(OUTPUT_FILE, "w") as f:
            json.dump(output, f, indent=4)
        print(f"🎉 Success! Database built with {len(self.database)} items.")

if __name__ == "__main__":
    ingestor = EMSIngestor(TEXT_FILE)
    ingestor.load_and_clean()
    ingestor.parse_protocols()
    ingestor.parse_formulary()
    ingestor.save()