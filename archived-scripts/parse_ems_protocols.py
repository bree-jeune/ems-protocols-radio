import json
import re
from pathlib import Path

# Configuration
TEXT_FILE = "ems-protocol-manual.txt"
OUTPUT_FILE = "ems_protocols.json"

def clean_text(text):
    """Clean up text by removing page numbers and extra whitespace."""
    lines = text.split('\n')
    cleaned = []
    
    for line in lines:
        line = line.strip()
        # Skip page numbers (lines that are just digits)
        if re.match(r'^\d+$', line):
            continue
        # Skip very short lines (likely artifacts)
        if len(line) < 2:
            continue
        cleaned.append(line)
    
    return '\n'.join(cleaned)

def extract_medications(text):
    """Extract medication names and dosages from text."""
    medications = []
    
    # Common EMS medications
    med_patterns = [
        r'EPINEPHRINE',
        r'ATROPINE',
        r'NALOXONE',
        r'ALBUTEROL',
        r'LEVALBUTEROL',
        r'NITROGLYCERIN',
        r'ASPIRIN',
        r'ACETYLSALICYLIC ACID',
        r'MORPHINE',
        r'FENTANYL',
        r'MIDAZOLAM',
        r'DIAZEPAM',
        r'DIPHENHYDRAMINE',
        r'ONDANSETRON',
        r'ADENOSINE',
        r'AMIODARONE',
        r'LIDOCAINE',
        r'MAGNESIUM SULFATE',
        r'CALCIUM CHLORIDE',
        r'SODIUM BICARBONATE',
        r'GLUCOSE',
        r'D10',
        r'DEXTROSE',
        r'GLUCAGON',
        r'KETAMINE',
        r'ETOMIDATE',
        r'ACETAMINOPHEN',
        r'HYDROMORPHONE',
        r'METOCLOPRAMIDE',
        r'DROPERIDOL',
        r'PROCHLORPERAZINE',
        r'HYDROXOCOBALAMIN',
        r'IPRATROPIUM',
        r'PHENYLEPHRINE',
        r'OXYMETAZOLINE'
    ]
    
    for med in med_patterns:
        # Look for medication with dosage
        pattern = rf'{med}\s*\n?\s*(\d+\.?\d*\s*(?:mg|mcg|g|ml|L|%)[^\n]*)'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            medications.append({
                'name': med.title().replace('_', ' '),
                'dosage_text': match.group(1).strip()
            })
    
    return medications

def extract_contraindications(text):
    """Extract contraindications from text."""
    contraindications = []
    
    # Look for contraindications section
    contra_pattern = r'CONTRAINDICATION[S]?:?\s*([^\n]+(?:\n(?![A-Z\s]+:)[^\n]+)*)'
    matches = re.finditer(contra_pattern, text, re.IGNORECASE)
    
    for match in matches:
        contra_text = match.group(1).strip()
        # Split by common delimiters
        items = re.split(r'[;•\n]', contra_text)
        for item in items:
            item = item.strip()
            if item and len(item) > 5:
                contraindications.append(item)
    
    return contraindications

def extract_pearls(text):
    """Extract clinical pearls from text."""
    pearls = []
    
    # Look for Pearls section
    pearls_pattern = r'Pearls?\s*\n((?:^\s*\*[^\n]+\n?)+)'
    matches = re.finditer(pearls_pattern, text, re.IGNORECASE | re.MULTILINE)
    
    for match in matches:
        pearl_text = match.group(1)
        # Extract individual pearls (usually bullet points)
        individual_pearls = re.findall(r'\*\s*([^\n]+)', pearl_text)
        pearls.extend([p.strip() for p in individual_pearls if len(p.strip()) > 10])
    
    # Also look for standalone pearls
    standalone_pattern = r'(?:^|\n)\s*\*\s*([A-Z][^\n]{20,})'
    standalone_matches = re.finditer(standalone_pattern, text, re.MULTILINE)
    for match in standalone_matches:
        pearl = match.group(1).strip()
        if pearl not in pearls and len(pearl) > 20:
            pearls.append(pearl)
    
    return pearls[:15]  # Limit to top 15 pearls

def extract_vital_signs_criteria(text):
    """Extract vital signs criteria and thresholds."""
    criteria = []
    
    # Pattern for vital signs with values
    patterns = [
        r'(HR|Heart Rate)\s*[<>]=?\s*(\d+)',
        r'(BP|Blood Pressure|SBP|DBP)\s*[<>]=?\s*(\d+)',
        r'(RR|Respiratory Rate)\s*[<>]=?\s*(\d+)',
        r'(SpO2|Oxygen Saturation)\s*[<>]=?\s*(\d+)',
        r'(ETCO2)\s*[<>]=?\s*(\d+)',
        r'(Temperature|Temp)\s*[<>]=?\s*(\d+\.?\d*)',
        r'(GCS|Glasgow Coma Score)\s*[<>]=?\s*(\d+)',
        r'(BG|Blood Glucose)\s*[<>]=?\s*(\d+)'
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            criteria.append({
                'parameter': match.group(1),
                'threshold': match.group(2),
                'context': match.group(0)
            })
    
    return criteria

def extract_warnings(text):
    """Extract warnings and cautions."""
    warnings = []
    
    # Look for warning indicators
    warning_patterns = [
        r'⚠[^\n]+',
        r'WARNING:?\s*([^\n]+)',
        r'CAUTION:?\s*([^\n]+)',
        r'CRITICAL:?\s*([^\n]+)',
        r'NEVER\s+([^\n]{10,})',
        r'DO NOT\s+([^\n]{10,})',
        r'ALWAYS\s+([^\n]{10,})'
    ]
    
    for pattern in warning_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            warning_text = match.group(1) if match.lastindex else match.group(0)
            warning_text = warning_text.strip()
            if len(warning_text) > 10 and warning_text not in warnings:
                warnings.append(warning_text)
    
    return warnings[:10]  # Limit to top 10 warnings

def extract_age_specific_info(text):
    """Extract age-specific information."""
    age_info = {
        'pediatric_specific': bool(re.search(r'pediatric|child|infant|neonate', text, re.IGNORECASE)),
        'adult_specific': bool(re.search(r'adult|>=?\s*18', text, re.IGNORECASE)),
        'geriatric_mentioned': bool(re.search(r'geriatric|elderly|age\s*>\s*65', text, re.IGNORECASE)),
        'age_based_dosing': bool(re.search(r'mg/kg|ml/kg|years of age|age-appropriate', text, re.IGNORECASE))
    }
    return age_info

def extract_required_equipment(text):
    """Extract required equipment and procedures."""
    equipment = []
    
    equipment_patterns = [
        r'AED', r'BVM', r'ECG', r'Cardiac [Mm]onitor',
        r'IV|IO|IM|IN', r'ETT', r'Extraglottic',
        r'Defibrillator', r'Pulse Oximetry', r'Capnography',
        r'12-Lead', r'Tourniquet', r'Splint'
    ]
    
    for pattern in equipment_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            # Clean up the pattern for display
            eq = pattern.replace(r'\s*', ' ').replace('[Mm]', 'M')
            equipment.append(eq)
    
    return list(set(equipment))

def extract_differential_diagnosis(text):
    """Extract differential diagnosis items."""
    differentials = []
    
    # Look for Differential section
    diff_pattern = r'Differential\s*\n((?:^\s*\*[^\n]+\n?)+)'
    matches = re.finditer(diff_pattern, text, re.IGNORECASE | re.MULTILINE)
    
    for match in matches:
        diff_text = match.group(1)
        items = re.findall(r'\*\s*([^\n]+)', diff_text)
        differentials.extend([d.strip() for d in items if len(d.strip()) > 3])
    
    return differentials

def extract_metadata(text):
    """Extract comprehensive metadata from protocol text."""
    
    medications = extract_medications(text)
    contraindications = extract_contraindications(text)
    pearls = extract_pearls(text)
    vital_criteria = extract_vital_signs_criteria(text)
    warnings = extract_warnings(text)
    age_info = extract_age_specific_info(text)
    equipment = extract_required_equipment(text)
    differentials = extract_differential_diagnosis(text)
    
    metadata = {
        # Basic indicators
        'has_dosages': bool(re.search(r'\d+\s*(mg|mcg|g|ml|L)', text, re.IGNORECASE)),
        'has_vitals': bool(re.search(r'(BP|HR|RR|SpO2|ETCO2)', text)),
        'requires_telemetry': bool(re.search(r'telemetry|contact.*physician|physician order', text, re.IGNORECASE)),
        'mentions_vascular_access': bool(re.search(r'(IV|IO|IM|IN)', text)),
        'requires_cardiac_monitor': bool(re.search(r'cardiac monitor', text, re.IGNORECASE)),
        
        # Complexity indicators
        'is_life_threatening': bool(re.search(r'cardiac arrest|respiratory arrest|shock|sepsis|STEMI|stroke', text, re.IGNORECASE)),
        'requires_advanced_airway': bool(re.search(r'intubat|ETT|extraglottic', text, re.IGNORECASE)),
        'mentions_CPR': bool(re.search(r'\bCPR\b', text)),
        
        # Provider level
        'emt_level': bool(re.search(r'\bE\b.*EMT', text)),
        'aemt_level': bool(re.search(r'\bA\b.*AEMT', text)),
        'paramedic_level': bool(re.search(r'\bP\b.*Paramedic', text)),
        
        # Extracted structured data
        'medications': medications,
        'contraindications': contraindications,
        'clinical_pearls': pearls,
        'vital_signs_criteria': vital_criteria,
        'warnings': warnings,
        'age_specific': age_info,
        'required_equipment': equipment,
        'differential_diagnosis': differentials,
        
        # Counts
        'medication_count': len(medications),
        'pearl_count': len(pearls),
        'warning_count': len(warnings),
        'contraindication_count': len(contraindications)
    }
    
    return metadata

def parse_protocols():
    """Parse the EMS protocol manual into structured JSON."""
    
    print(f"📄 Reading {TEXT_FILE}...")
    with open(TEXT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        full_text = f.read()
    
    # Define protocol categories and their protocols
    categories = {
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
    
    # Build mapping of title to category
    title_to_category = {}
    all_titles = []
    
    for category, titles in categories.items():
        for title in titles:
            title_to_category[title.upper()] = category
            all_titles.append(title)
    
    # Sort titles by length (longest first) for better matching
    all_titles.sort(key=len, reverse=True)
    
    # Create regex pattern
    escaped_titles = [re.escape(t) for t in all_titles]
    pattern = r'(' + '|'.join(escaped_titles) + r')'
    
    # Split text by protocol titles
    segments = re.split(pattern, full_text, flags=re.IGNORECASE)
    
    print(f"   🔍 Found {len(segments) // 2} potential protocols")
    
    # Parse protocols
    protocols = {}
    
    for i in range(1, len(segments), 2):
        if i + 1 >= len(segments):
            break
            
        raw_title = segments[i].strip()
        content = segments[i + 1]
        
        # Skip if content is too short
        if len(content) < 100:
            continue
        
        # Determine category
        category = title_to_category.get(raw_title.upper(), "Uncategorized")
        
        # Special handling for pediatric protocols that might not have "Pediatric" prefix in text
        if category == "Uncategorized" and any(ped in raw_title.upper() for ped in ["PEDIATRIC", "NEONATAL"]):
            category = "Pediatric"
        
        # Clean title
        clean_title = raw_title.title()
        
        # Generate ID
        protocol_id = clean_title.lower()
        protocol_id = re.sub(r'[^\w\s-]', '', protocol_id)
        protocol_id = re.sub(r'[-\s]+', '_', protocol_id)
        
        # Clean content
        cleaned_content = clean_text(content)
        
        # Extract metadata
        metadata = extract_metadata(cleaned_content)
        
        # Create protocol entry
        protocol_entry = {
            "id": protocol_id,
            "title": clean_title,
            "category": category,
            "content": cleaned_content,
            "metadata": metadata,
            "word_count": len(cleaned_content.split()),
            "source": "Clark County EMS System Emergency Medical Care Protocols"
        }
        
        # Merge if protocol already exists (continuation on next page)
        if protocol_id in protocols:
            if protocols[protocol_id]['category'] == category:
                print(f"   🔗 Merging continuation: {clean_title}")
                protocols[protocol_id]['content'] += "\n\n" + cleaned_content
                protocols[protocol_id]['word_count'] = len(protocols[protocol_id]['content'].split())
            else:
                # Different category - make unique ID
                new_id = f"{protocol_id}_{category.lower()}"
                protocols[new_id] = protocol_entry
                print(f"   ✅ [{category}] {clean_title}")
        else:
            protocols[protocol_id] = protocol_entry
            print(f"   ✅ [{category}] {clean_title}")
    
    # Create output structure
    output = {
        "metadata": {
            "source": "Clark County EMS System",
            "version": "Effective October 15, 2025",
            "total_protocols": len(protocols),
            "categories": {cat: len([p for p in protocols.values() if p['category'] == cat]) 
                          for cat in categories.keys()}
        },
        "protocols": protocols
    }
    
    # Write to file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Success! Created {OUTPUT_FILE}")
    print(f"   📊 Total protocols: {len(protocols)}")
    print(f"   📁 Categories: {', '.join(categories.keys())}")
    
    return output

if __name__ == "__main__":
    result = parse_protocols()
    
    # Print summary
    print("\n📈 Protocol Summary by Category:")
    for category, count in result['metadata']['categories'].items():
        print(f"   {category}: {count} protocols")