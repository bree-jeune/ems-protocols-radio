import json
import re

TEXT_FILE = "ems-protocol-manual.txt"
OUTPUT_FILE = "medication_formulary.json"

class FormularyParser:
    """Parse EMS medication formulary with detailed drug information"""
    
    def __init__(self):
        self.medications = {}
    
    def extract_medication_blocks(self, text: str) -> dict:
        """Split formulary into individual medication entries"""
        
        # Find FORMULARY section
        formulary_match = re.search(r'FORMULARY\s*\n(.*?)(?=APPENDICES|Southern Nevada Health District)', 
                                    text, re.DOTALL | re.IGNORECASE)
        
        if not formulary_match:
            print("⚠️  Could not find FORMULARY section")
            return {}
        
        formulary_text = formulary_match.group(1)
        
        # Known medications in the formulary
        medication_names = [
            "ACETAMINOPHEN",
            "ACETYLSALICYLIC ACID",
            "ADENOSINE",
            "ALBUTEROL",
            "AMIODARONE",
            "ATROPINE SULFATE",
            "BRONCHODILATOR METERED DOSE INHALER",
            "CALCIUM CHLORIDE",
            "DIAZEPAM",
            "DIPHENHYDRAMINE HYDROCHLORIDE",
            "DROPERIDOL",
            "EPINEPHRINE 1:1000",
            "EPINEHPRHINE 1:10,000",
            "EPINEHPRINE 1:100,000",
            "EPINEPHRINE AUTO-INJECTOR",
            "ETOMIDATE",
            "FENTANYL CITRATE",
            "GLUCAGON",
            "GLUCOSE - ORAL GLUCOSE",
            "GLUCOSE - D10",
            "HYDROMORPHONE",
            "HYDROXOCOBALAMIN",
            "IPRATROPIUM BROMIDE",
            "IPRATROPIUM BROMIDE and ALBUTEROL SULFATE",
            "KETAMINE",
            "LEVALBUTEROL",
            "LIDOCAINE",
            "MAGNESIUM SULFATE",
            "METOCLOPRAMIDE",
            "MIDAZOLAM",
            "MORPHINE SULFATE",
            "NALOXONE HYDROCHLORIDE",
            "NITROGLYCERIN",
            "ONDANSETRON HYDROCHLORIDE",
            "OXYMETAZOLINE",
            "PHENYLEPHRINE",
            "PHENYLEPHRINE PUSH DOSE",
            "PROCHLORPERAZINE",
            "SODIUM BICARBONATE"
        ]
        
        # Sort by length to match longest names first
        medication_names.sort(key=len, reverse=True)
        
        # Create pattern to split
        pattern = r'(' + '|'.join(re.escape(name) for name in medication_names) + r')'
        segments = re.split(pattern, formulary_text, flags=re.IGNORECASE)
        
        medications = {}
        
        # Process segments
        for i in range(1, len(segments), 2):
            if i + 1 >= len(segments):
                break
            
            med_name = segments[i].strip()
            med_content = segments[i + 1]
            
            # Skip if too short
            if len(med_content) < 50:
                continue
            
            medications[med_name] = self.parse_medication(med_name, med_content)
        
        return medications
    
    def parse_medication(self, name: str, text: str) -> dict:
        """Parse individual medication entry"""
        
        med_data = {
            "trade_name": self.extract_trade_name(name),
            "generic_name": self.extract_generic_name(name),
            "class": self.extract_field(text, "CLASS"),
            "action": self.extract_field(text, "ACTION"),
            "dose": self.extract_dose(text),
            "routes": self.extract_routes(text),
            "indications": self.extract_indications(text, name),
            "contraindications": self.extract_contraindications(text),
            "adverse_reactions": self.extract_adverse_reactions(text),
            "onset": self.extract_onset(text),
            "repeat_dose_allowed": self.check_repeat_dose(text),
            "protocols": self.find_related_protocols(name)
        }
        
        return med_data
    
    def extract_trade_name(self, name: str) -> str:
        """Extract trade name from medication header"""
        # Pattern: NAME (Trade Name)
        match = re.search(r'\(([^)]+)\)', name)
        return match.group(1) if match else name.split()[0]
    
    def extract_generic_name(self, name: str) -> str:
        """Extract generic name"""
        # Remove trade name in parentheses
        generic = re.sub(r'\([^)]+\)', '', name).strip()
        return generic
    
    def extract_field(self, text: str, field_name: str) -> str:
        """Extract a labeled field from text"""
        pattern = rf'{field_name}:\s*([^\n]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else ""
    
    def extract_dose(self, text: str) -> dict:
        """Extract dosing information"""
        dose_text = self.extract_field(text, "DOSE")
        
        # Parse adult vs pediatric dosing
        adult_dose = ""
        pediatric_dose = ""
        
        if "Adult:" in dose_text or "Pediatric:" in dose_text:
            adult_match = re.search(r'Adult:\s*([^;]+)', dose_text, re.IGNORECASE)
            peds_match = re.search(r'Pediatric:\s*([^;]+)', dose_text, re.IGNORECASE)
            
            adult_dose = adult_match.group(1).strip() if adult_match else ""
            pediatric_dose = peds_match.group(1).strip() if peds_match else ""
        else:
            adult_dose = dose_text
        
        return {
            "adult": adult_dose,
            "pediatric": pediatric_dose,
            "raw": dose_text
        }
    
    def extract_routes(self, text: str) -> list:
        """Extract administration routes"""
        routes = []
        
        route_patterns = [
            (r'\bIV\b', 'IV'),
            (r'\bIM\b', 'IM'),
            (r'\bIO\b', 'IO'),
            (r'\bIN\b', 'IN'),
            (r'\bPO\b', 'PO'),
            (r'\bSL\b', 'SL'),
            (r'\bPR\b', 'PR'),
            (r'\bSQ\b|\bSC\b', 'Subcutaneous'),
            (r'Inhalation|Nebulizer|SVN|MDI', 'Inhalation')
        ]
        
        for pattern, route in route_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                if route not in routes:
                    routes.append(route)
        
        return routes
    
    def extract_indications(self, text: str, med_name: str) -> list:
        """Infer indications from action and context"""
        indications = []
        
        # Map common medication classes to indications
        indication_map = {
            'EPINEPHRINE': ['Anaphylaxis', 'Cardiac Arrest', 'Severe Asthma'],
            'NALOXONE': ['Opioid Overdose'],
            'ALBUTEROL': ['Bronchospasm', 'Asthma', 'COPD'],
            'NITROGLYCERIN': ['Chest Pain', 'Acute Coronary Syndrome'],
            'ATROPINE': ['Bradycardia', 'Organophosphate Poisoning'],
            'ADENOSINE': ['SVT'],
            'AMIODARONE': ['Ventricular Fibrillation', 'Ventricular Tachycardia'],
            'MORPHINE': ['Severe Pain'],
            'FENTANYL': ['Severe Pain'],
            'MIDAZOLAM': ['Seizures', 'Sedation'],
            'ONDANSETRON': ['Nausea', 'Vomiting']
        }
        
        for key, values in indication_map.items():
            if key in med_name.upper():
                indications = values
                break
        
        return indications
    
    def extract_contraindications(self, text: str) -> list:
        """Extract contraindications"""
        contra_text = self.extract_field(text, "CONTRAINDICATIONS")
        
        if not contra_text or contra_text.lower() == "none":
            return []
        
        # Split by semicolons or common delimiters
        items = re.split(r'[;•]', contra_text)
        return [item.strip() for item in items if item.strip() and len(item.strip()) > 3]
    
    def extract_adverse_reactions(self, text: str) -> list:
        """Extract adverse reactions"""
        adverse_text = self.extract_field(text, "ADVERSE REACTIONS")
        
        if not adverse_text or adverse_text.lower() == "none":
            return []
        
        items = re.split(r'[;•]', adverse_text)
        return [item.strip() for item in items if item.strip() and len(item.strip()) > 3]
    
    def extract_onset(self, text: str) -> str:
        """Extract onset of action if mentioned"""
        onset_pattern = r'onset[:\s]+([^\n.;]+)'
        match = re.search(onset_pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else "Not specified"
    
    def check_repeat_dose(self, text: str) -> bool:
        """Check if repeat dosing is allowed"""
        repeat_keywords = [
            r'may repeat',
            r'repeat dose',
            r'repeat.*min',
            r'repeat.*needed',
            r'q\s+\d+.*min'
        ]
        
        for keyword in repeat_keywords:
            if re.search(keyword, text, re.IGNORECASE):
                return True
        return False
    
    def find_related_protocols(self, med_name: str) -> list:
        """Find protocols that commonly use this medication"""
        protocol_map = {
            'EPINEPHRINE': ['Cardiac Arrest', 'Anaphylaxis', 'Respiratory Distress'],
            'NALOXONE': ['Overdose/Poisoning', 'Altered Mental Status'],
            'ALBUTEROL': ['Respiratory Distress'],
            'NITROGLYCERIN': ['Chest Pain', 'STEMI'],
            'ATROPINE': ['Bradycardia'],
            'ADENOSINE': ['Tachycardia/Stable'],
            'AMIODARONE': ['Cardiac Arrest', 'Tachycardia/Unstable'],
            'MORPHINE': ['Pain Management'],
            'FENTANYL': ['Pain Management'],
            'MIDAZOLAM': ['Seizure', 'Behavioral Emergencies'],
            'ONDANSETRON': ['Nausea/Vomiting']
        }
        
        for key, protocols in protocol_map.items():
            if key in med_name.upper():
                return protocols
        
        return []
    
    def parse_formulary(self):
        """Main parsing function"""
        print("📄 Reading formulary from EMS protocol manual...")
        
        with open(TEXT_FILE, "r", encoding="utf-8", errors="ignore") as f:
            full_text = f.read()
        
        self.medications = self.extract_medication_blocks(full_text)
        
        print(f"   ✅ Parsed {len(self.medications)} medications")
        
        return self.medications
    
    def save_to_file(self):
        """Save to JSON"""
        output = {
            "metadata": {
                "source": "Clark County EMS System Formulary",
                "version": "Effective October 15, 2025",
                "total_medications": len(self.medications)
            },
            "medications": self.medications
        }
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    parser = FormularyParser()
    parser.parse_formulary()
    parser.save_to_file()