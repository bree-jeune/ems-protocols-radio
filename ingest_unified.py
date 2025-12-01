import json
import re
import os

TEXT_FILE = "ems-protocol-manual.txt"
OUTPUT_FILE = "ems_protocols.json"

class UnifiedIngestor:
    def __init__(self):
        self.database = {}
        
        # Define specific titles for each section
        self.CATEGORIES = {
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

    def clean_text(self, text):
        """Removes page numbers and stitches broken lines."""
        lines = text.split('\n')
        cleaned = []
        for line in lines:
            l = line.strip()
            # Skip Page numbers (digits only)
            if re.match(r'^\d+$', l): continue
            # Skip Footer text
            if "Clark County EMS" in l: continue
            cleaned.append(l)
        return '\n'.join(cleaned)

    def find_real_index(self, text, substring, start_search=0):
        """Finds the index of a substring, ensuring it's NOT in the Table of Contents."""
        idx = text.find(substring, start_search)
        
        # If found in the first 5000 characters, it's likely the TOC. Look again!
        if idx != -1 and idx < 5000:
            # Recursive call to find the NEXT occurrence
            return self.find_real_index(text, substring, idx + 1)
            
        return idx

    def parse_file(self):
        print(f"📄 Reading {TEXT_FILE}...")
        with open(TEXT_FILE, "r", encoding="utf-8", errors="ignore") as f:
            raw_content = f.read()
            
        # 1. Global Cleanup: Remove source tags using Regex
        # This removes patterns like 
        full_text = re.sub(r'\', '', raw_content)

        # --- ROBUST ZONE SPLITTING ---
        # We use the FIRST PROTOCOL of each section as the Anchor.
        
        idx_terms = full_text.find("TERMS AND CONVENTIONS")
        
        # Use recursive finder to skip TOC
        idx_adult = self.find_real_index(full_text, "General Adult Assessment")
        idx_peds = self.find_real_index(full_text, "General Pediatric Assessment")
        
        # Operations Headers
        idx_ops = self.find_real_index(full_text, "OPERATIONS PROTOCOLS")
        if idx_ops == -1: 
             idx_ops = self.find_real_index(full_text, "Communications")

        idx_proc = self.find_real_index(full_text, "PROCEDURES PROTOCOLS")
        if idx_proc == -1: 
             idx_proc = self.find_real_index(full_text, "Cervical Stabilization")

        idx_form = self.find_real_index(full_text, "FORMULARY")
        idx_end = self.find_real_index(full_text, "APPENDICES")
        
        if idx_end == -1: idx_end = len(full_text)

        # Guard against failure
        if idx_adult == -1: 
            print("❌ Critical Error: Could not find Adult Section. Check text file contents.")
            return

        # Define the Zones based on indices
        zones = {
            "Definitions": full_text[idx_terms:idx_adult],
            "Adult": full_text[idx_adult:idx_peds],
            "Pediatric": full_text[idx_peds:idx_ops],
            "Operations": full_text[idx_ops:idx_proc], 
            "Procedures": full_text[idx_proc:idx_form],
            "Formulary": full_text[idx_form:idx_end]
        }

        for category, zone_text in zones.items():
            print(f"   Processing Zone: {category} (Size: {len(zone_text)} chars)...")
            
            if len(zone_text) < 1000:
                print(f"   ⚠️  WARNING: Zone {category} seems too small. Check indices.")
                continue
            
            if category == "Formulary":
                self.process_formulary(zone_text)
            elif category == "Definitions":
                self.process_definitions(zone_text)
            else:
                self.process_protocol_zone(category, zone_text)

        self.save()

    def process_definitions(self, text):
        lines = self.clean_text(text).split('\n')
        for i in range(len(lines) - 1):
            line = lines[i].strip()
            next_line = lines[i+1].strip()
            # Look for: "AED" then "means..."
            if len(line) < 15 and line.isupper() and next_line.lower().startswith("means"):
                definition = next_line.replace("means", "").strip()
                term_id = line.lower().replace(" ", "_")
                self.database[term_id] = {
                    "title": line,
                    "category": "Definitions",
                    "raw_text": definition,
                    "metadata": {}
                }

    def process_protocol_zone(self, category, text):
        allowed_titles = self.CATEGORIES.get(category, [])
        allowed_titles.sort(key=len, reverse=True)
        
        # Create Regex for titles in this zone
        escaped = [re.escape(t) for t in allowed_titles]
        pattern = r'(' + '|'.join(escaped) + r')'
        segments = re.split(pattern, text, flags=re.IGNORECASE)
        
        for i in range(1, len(segments), 2):
            raw_title = segments[i].strip()
            content = segments[i+1]
            
            clean_title = raw_title.title().replace("Cva", "CVA").replace("Chf", "CHF").replace("Stemi", "STEMI")
            
            if category == "Pediatric" and "Pediatric" not in clean_title and "Neonatal" not in clean_title:
                clean_title = f"Pediatric {clean_title}"

            prot_id = clean_title.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
            cleaned_content = self.clean_text(content)
            
            if len(cleaned_content) < 50: continue

            # Basic metadata extraction
            metadata = {
                "medications": list(set(re.findall(r'([A-Z]{4,})', cleaned_content)))
            }

            # Merge logic
            if prot_id in self.database:
                # If it's the same category, append text (Page 2 of protocol)
                if self.database[prot_id]['category'] == category:
                    self.database[prot_id]['raw_text'] += "\n\n" + cleaned_content
            else:
                self.database[prot_id] = {
                    "title": clean_title,
                    "category": category,
                    "raw_text": cleaned_content,
                    "metadata": metadata
                }

    def process_formulary(self, text):
        # Splits by Drug Name (All Caps) followed by CLASS:
        drug_pattern = r'([A-Z][A-Z0-9 \-\/\(\)]+)\s*\n+CLASS:'
        segments = re.split(drug_pattern, text)
        
        for i in range(1, len(segments), 2):
            name = segments[i].strip()
            content = "CLASS:" + segments[i+1]
            
            drug_id = name.lower().replace(" ", "_").replace("(", "").replace(")", "")
            
            class_match = re.search(r'CLASS:\s*(.+)', content)
            action_match = re.search(r'ACTION:\s*(.+)', content)
            dose_match = re.search(r'DOSE:\s*(.+)', content)

            self.database[drug_id] = {
                "title": name.title(),
                "category": "Formulary",
                "raw_text": content,
                "metadata": {
                    "class": class_match.group(1).strip() if class_match else "",
                    "action": action_match.group(1).strip() if action_match else "",
                    "dose": dose_match.group(1).strip() if dose_match else ""
                }
            }

    def save(self):
        # Save in the structure main.py expects
        output = {"metadata": {"version": "3.0"}, "protocols": self.database}
        with open(OUTPUT_FILE, "w") as f:
            json.dump(output, f, indent=4)
        print(f"🎉 Success! Saved {len(self.database)} items to {OUTPUT_FILE}")

if __name__ == "__main__":
    ingestor = UnifiedIngestor()
    ingestor.parse_file()