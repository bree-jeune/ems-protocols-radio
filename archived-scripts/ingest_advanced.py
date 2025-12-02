import json
import re
from pathlib import Path
from typing import Dict, List, Optional

TEXT_FILE = "ems-protocol-manual.txt"
OUTPUT_FILE = "ems_protocols_structured.json"

class ProtocolParser:
    """Advanced parser for EMS protocols with structured field extraction"""
    
    def __init__(self):
        self.protocols = {}
        
    def extract_section(self, text: str, section_name: str) -> Optional[str]:
        """Extract a specific section from protocol text"""
        # Try various section header formats
        patterns = [
            rf'{section_name}\s*\n(.*?)(?=\n[A-Z][a-z]+:|$)',
            rf'{section_name}\s*\n(.*?)(?=\n\n[A-Z]|$)',
            rf'\*\s*{section_name}[:\s]*(.*?)(?=\n\*|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        return None
    
    def extract_bulleted_list(self, text: str) -> List[str]:
        """Extract bullet point items"""
        if not text:
            return []
        
        items = []
        # Match various bullet formats
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if re.match(r'^[\*\-•]\s+', line):
                items.append(re.sub(r'^[\*\-•]\s+', '', line))
            elif line and len(items) > 0:
                # Continuation of previous item
                items[-1] += " " + line
        
        return [item.strip() for item in items if item.strip()]
    
    def extract_history_section(self, text: str) -> List[str]:
        """Extract history items"""
        history_text = self.extract_section(text, "History")
        return self.extract_bulleted_list(history_text) if history_text else []
    
    def extract_signs_symptoms(self, text: str) -> List[str]:
        """Extract signs and symptoms"""
        ss_text = self.extract_section(text, "Signs and Symptoms")
        return self.extract_bulleted_list(ss_text) if ss_text else []
    
    def extract_differential(self, text: str) -> List[str]:
        """Extract differential diagnosis"""
        diff_text = self.extract_section(text, "Differential")
        return self.extract_bulleted_list(diff_text) if diff_text else []
    
    def extract_pearls(self, text: str) -> List[str]:
        """Extract clinical pearls"""
        pearls = []
        
        # Look for Pearls section
        pearls_pattern = r'Pearls?\s*\n((?:^\s*\*[^\n]+\n?)+)'
        matches = re.finditer(pearls_pattern, text, re.IGNORECASE | re.MULTILINE)
        
        for match in matches:
            pearl_text = match.group(1)
            items = re.findall(r'\*\s*([^\n]+)', pearl_text)
            pearls.extend([p.strip() for p in items if len(p.strip()) > 10])
        
        return pearls[:20]  # Limit to top 20
    
    def extract_qi_metrics(self, text: str) -> List[str]:
        """Extract QI Metrics"""
        qi_text = self.extract_section(text, "QI Metrics")
        return self.extract_bulleted_list(qi_text) if qi_text else []
    
    def extract_disposition(self, text: str) -> Dict[str, any]:
        """Extract disposition/transport criteria"""
        disp_text = self.extract_section(text, "Disposition")
        
        if not disp_text:
            return {}
        
        return {
            "text": disp_text,
            "transport_criteria": self.extract_bulleted_list(disp_text)
        }
    
    def extract_medications(self, text: str) -> List[Dict]:
        """Extract medication administrations with dosages"""
        meds = []
        
        # Comprehensive medication patterns
        med_patterns = {
            'EPINEPHRINE': r'EPINEPHRINE\s+(?:1:1000|1:10,000|1:100,000)?\s*,?\s*([^\n]+)',
            'ATROPINE': r'ATROPINE\s+([^\n]+)',
            'NALOXONE': r'NALOXONE\s+([^\n]+)',
            'ALBUTEROL': r'ALBUTEROL\s+([^\n]+)',
            'MIDAZOLAM': r'MIDAZOLAM\s+([^\n]+)',
            'FENTANYL': r'FENTANYL\s+([^\n]+)',
            'MORPHINE': r'MORPHINE\s+([^\n]+)',
            'NITROGLYCERIN': r'NITROGLYCERIN\s+([^\n]+)',
            'ADENOSINE': r'ADENOSINE\s+([^\n]+)',
            'AMIODARONE': r'AMIODARONE\s+([^\n]+)',
            'CALCIUM CHLORIDE': r'CALCIUM CHLORIDE\s+([^\n]+)',
            'SODIUM BICARBONATE': r'SODIUM BICARBONATE\s+([^\n]+)',
            'GLUCOSE': r'(?:GLUCOSE|D10)\s+([^\n]+)',
            'DIPHENHYDRAMINE': r'DIPHENHYDRAMINE\s+([^\n]+)',
            'ONDANSETRON': r'ONDANSETRON\s+([^\n]+)',
        }
        
        for med_name, pattern in med_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                dosage_info = match.group(1).strip()
                
                # Extract route
                route = None
                if re.search(r'\bIV\b', dosage_info, re.IGNORECASE):
                    route = "IV"
                elif re.search(r'\bIM\b', dosage_info, re.IGNORECASE):
                    route = "IM"
                elif re.search(r'\bIO\b', dosage_info, re.IGNORECASE):
                    route = "IO"
                elif re.search(r'\bIN\b', dosage_info, re.IGNORECASE):
                    route = "IN"
                
                meds.append({
                    'name': med_name.title(),
                    'dosage': dosage_info,
                    'route': route
                })
        
        return meds
    
    def extract_decision_tree(self, text: str) -> List[Dict]:
        """Extract if/then decision logic"""
        decisions = []
        
        # Pattern for Yes/No decision points
        yes_no_pattern = r'(Yes|No)\s+([^\n]{20,100})'
        matches = re.finditer(yes_no_pattern, text, re.IGNORECASE)
        
        for match in matches:
            decision = match.group(1)
            action = match.group(2).strip()
            if action:
                decisions.append({
                    'decision': decision,
                    'action': action
                })
        
        return decisions[:10]  # Limit to prevent noise
    
    def requires_telemetry(self, text: str) -> bool:
        """Check if protocol requires telemetry"""
        telemetry_keywords = [
            r'telemetry.*required',
            r'contact.*physician',
            r'physician order',
            r'medical control',
            r'telemetry contact shall be established'
        ]
        
        for keyword in telemetry_keywords:
            if re.search(keyword, text, re.IGNORECASE):
                return True
        return False
    
    def extract_contraindications(self, text: str) -> List[str]:
        """Extract contraindications"""
        contra_text = self.extract_section(text, "CONTRAINDICATIONS")
        if not contra_text:
            return []
        
        # Split by semicolons or bullet points
        items = re.split(r'[;•\n]', contra_text)
        return [item.strip() for item in items if item.strip() and len(item.strip()) > 5]
    
    def extract_adverse_reactions(self, text: str) -> List[str]:
        """Extract adverse reactions"""
        adverse_text = self.extract_section(text, "ADVERSE REACTIONS")
        if not adverse_text or adverse_text.lower() == "none":
            return []
        
        items = re.split(r'[;•\n]', adverse_text)
        return [item.strip() for item in items if item.strip() and len(item.strip()) > 5]
    
    def parse_medication_formulary(self, text: str) -> Dict:
        """Parse medication from formulary section"""
        med_data = {
            'trade_name': None,
            'generic_name': None,
            'class': None,
            'action': None,
            'dose': None,
            'route': [],
            'contraindications': [],
            'adverse_reactions': [],
            'repeat_dose_allowed': False
        }
        
        # Extract class
        class_match = re.search(r'CLASS:\s*([^\n]+)', text, re.IGNORECASE)
        if class_match:
            med_data['class'] = class_match.group(1).strip()
        
        # Extract action
        action_match = re.search(r'ACTION:\s*([^\n]+)', text, re.IGNORECASE)
        if action_match:
            med_data['action'] = action_match.group(1).strip()
        
        # Extract dose
        dose_match = re.search(r'DOSE:\s*([^\n]+)', text, re.IGNORECASE)
        if dose_match:
            med_data['dose'] = dose_match.group(1).strip()
        
        # Extract routes from text
        routes = []
        if re.search(r'\bIV\b', text):
            routes.append('IV')
        if re.search(r'\bIM\b', text):
            routes.append('IM')
        if re.search(r'\bIO\b', text):
            routes.append('IO')
        if re.search(r'\bIN\b', text):
            routes.append('IN')
        if re.search(r'\bPO\b', text):
            routes.append('PO')
        med_data['route'] = routes
        
        # Contraindications
        med_data['contraindications'] = self.extract_contraindications(text)
        
        # Adverse reactions
        med_data['adverse_reactions'] = self.extract_adverse_reactions(text)
        
        # Check for repeat dosing
        if re.search(r'may repeat|repeat dose', text, re.IGNORECASE):
            med_data['repeat_dose_allowed'] = True
        
        return med_data

    def parse_protocol(self, title: str, text: str, category: str) -> Dict:
        """Parse a complete protocol with all structured fields"""
        
        protocol = {
            "id": self.generate_id(title),
            "title": title,
            "category": category,
            "raw_text": text,
            
            # Clinical Information
            "history": self.extract_history_section(text),
            "signs_symptoms": self.extract_signs_symptoms(text),
            "differential": self.extract_differential(text),
            "pearls": self.extract_pearls(text),
            
            # Treatment Information
            "medications": self.extract_medications(text),
            "decision_tree": self.extract_decision_tree(text),
            
            # Operational Information
            "requires_telemetry": self.requires_telemetry(text),
            "disposition": self.extract_disposition(text),
            "qi_metrics": self.extract_qi_metrics(text),
            
            # Metadata
            "word_count": len(text.split()),
            "has_flowchart": bool(re.search(r'Yes\s+No', text)),
            "provider_level": self.determine_provider_level(text)
        }
        
        return protocol
    
    def determine_provider_level(self, text: str) -> List[str]:
        """Determine which provider levels can use this protocol"""
        levels = []
        if re.search(r'\bE\b.*EMT', text):
            levels.append('EMT')
        if re.search(r'\bA\b.*AEMT', text):
            levels.append('AEMT')
        if re.search(r'\bP\b.*Paramedic', text):
            levels.append('Paramedic')
        return levels or ['All']
    
    def generate_id(self, title: str) -> str:
        """Generate clean protocol ID"""
        clean = title.lower()
        clean = re.sub(r'[^\w\s-]', '', clean)
        clean = re.sub(r'[-\s]+', '_', clean)
        return clean
    
    def parse_all_protocols(self):
        """Main parsing function"""
        print(f"📄 Reading {TEXT_FILE}...")
        with open(TEXT_FILE, "r", encoding="utf-8", errors="ignore") as f:
            full_text = f.read()
        
        # Define all protocol titles and categories
        categories = self.get_protocol_categories()
        
        # Build title mapping
        title_to_category = {}
        all_titles = []
        
        for category, titles in categories.items():
            for title in titles:
                title_to_category[title.upper()] = category
                all_titles.append(title)
        
        # Sort by length for better matching
        all_titles.sort(key=len, reverse=True)
        
        # Create regex pattern
        escaped_titles = [re.escape(t) for t in all_titles]
        pattern = r'(' + '|'.join(escaped_titles) + r')'
        
        # Split text
        segments = re.split(pattern, full_text, flags=re.IGNORECASE)
        
        print(f"   🔍 Found {len(segments) // 2} protocol segments")
        
        # Process each protocol
        for i in range(1, len(segments), 2):
            if i + 1 >= len(segments):
                break
            
            raw_title = segments[i].strip()
            content = segments[i + 1]
            
            # Skip if too short
            if len(content) < 100:
                continue
            
            # Get category
            category = title_to_category.get(raw_title.upper(), "Uncategorized")
            
            # Parse protocol
            protocol = self.parse_protocol(raw_title, content, category)
            
            # Handle duplicates (merge or create variant)
            protocol_id = protocol['id']
            if protocol_id in self.protocols:
                if self.protocols[protocol_id]['category'] == category:
                    # Merge continuation
                    print(f"   🔗 Merging: {raw_title}")
                    self.protocols[protocol_id]['raw_text'] += "\n\n" + content
                else:
                    # Different category variant
                    new_id = f"{protocol_id}_{category.lower()}"
                    self.protocols[new_id] = protocol
                    print(f"   ✅ [{category}] {raw_title}")
            else:
                self.protocols[protocol_id] = protocol
                print(f"   ✅ [{category}] {raw_title}")
        
        return self.protocols
    
    def get_protocol_categories(self) -> Dict[str, List[str]]:
        """Return comprehensive protocol categories"""
        return {
            "Adult": [
                "General Adult Assessment",
                "General Adult Trauma Assessment",
                "Abdominal Pain/Flank Pain, Nausea & Vomiting",
                "Allergic Reaction",
                "Altered Mental Status/Syncope",
                "Behavioral Emergencies",
                "Bradycardia",
                "Burns",
                "Cardiac Arrest (Non-Traumatic)",
                "Chest Pain (Non-Traumatic) and Suspected Acute Coronary Syndrome",
                "Cold Related Illness",
                "Epistaxis",
                "Heat-Related Illness",
                "Hyperkalemia (Suspected)",
                "OB-Obstetric Emergency",
                "OB-Preeclampsia/Eclampsia",
                "OB-Uncomplicated Childbirth/Labor",
                "Overdose/Poisoning",
                "Pain Management",
                "Pulmonary Edema/CHF",
                "Respiratory Distress",
                "Seizure",
                "Sepsis",
                "Shock",
                "Smoke Inhalation",
                "STEMI (Suspected)",
                "Stroke (CVA)",
                "Tachycardia/Stable",
                "Tachycardia/Unstable",
                "Ventilation Management"
            ],
            "Pediatric": [
                "General Pediatric Assessment",
                "General Pediatric Trauma Assessment",
                "Abdominal/Flank Pain, Nausea & Vomiting",
                "Allergic Reaction",
                "Altered Mental Status",
                "Behavioral Emergencies",
                "Bradycardia",
                "Burns",
                "Cardiac Arrest (Non-Traumatic)",
                "Cold Related Illness",
                "Epistaxis",
                "Heat Related Illness",
                "Neonatal Resuscitation",
                "Overdose/Poisoning",
                "Pain Management",
                "Respiratory Distress",
                "Seizure",
                "Shock",
                "Smoke Inhalation",
                "Tachycardia/Stable",
                "Tachycardia/Unstable",
                "Ventilation Management"
            ],
            "Procedures": [
                "Cervical Stabilization",
                "Electrical Therapy/Defibrillation",
                "Electrical Therapy/Synchronized Cardioversion",
                "Electrical Therapy/Transcutaneous Pacing",
                "Endotracheal Intubation",
                "Extraglottic Device",
                "First Response Evaluate/Release",
                "Hemorrhage Control",
                "Medication Administration",
                "Needle Cricothyroidotomy",
                "Needle Thoracostomy",
                "Non-Invasive Positive Pressure Ventilation (NIPPV)",
                "Patient Restraint",
                "Tracheostomy Tube Replacement",
                "Traction Splint",
                "Vagal Maneuvers",
                "Vascular Access"
            ],
            "Operations": [
                "Communications",
                "Do Not Resuscitate (DNR/POLST)",
                "Documentation",
                "Hostile Mass Casualty Incident",
                "Inter-Facility Transfer of Patients by Ambulance",
                "Pediatric Patient Destination",
                "Prehospital Death Determination",
                "Public Intoxication/Mental Health Crisis",
                "Quality Improvement Review",
                "Termination of Resuscitation",
                "Transport Destinations",
                "Trauma Field Triage Criteria",
                "Waiting Room Criteria"
            ]
        }
    
    def save_to_file(self):
        """Save parsed protocols to JSON"""
        output = {
            "metadata": {
                "source": "Clark County EMS System",
                "version": "Effective October 15, 2025",
                "total_protocols": len(self.protocols),
                "parse_date": "2025-11-30"
            },
            "protocols": self.protocols
        }
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 Success! Created {OUTPUT_FILE}")
        print(f"   📊 Total protocols parsed: {len(self.protocols)}")
        
        # Print summary by category
        category_counts = {}
        for protocol in self.protocols.values():
            cat = protocol['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        print("\n📈 Protocols by Category:")
        for cat, count in sorted(category_counts.items()):
            print(f"   {cat}: {count}")

if __name__ == "__main__":
    parser = ProtocolParser()
    parser.parse_all_protocols()
    parser.save_to_file()