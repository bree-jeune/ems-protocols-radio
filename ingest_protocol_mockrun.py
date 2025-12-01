import base64
import json
import os
# We don't need OpenAI for the mock version
# from openai import OpenAI 
from pdf2image import convert_from_path

# client = OpenAI(api_key="YOUR_OPENAI_API_KEY") 

def parse_protocol_flowchart_MOCK(pdf_path, page_number):
    print(f"📄 Processing Page {page_number} of {pdf_path}...")
    
    # 1. Test the PDF conversion (This is usually where code breaks, so good to test!)
    try:
        images = convert_from_path(pdf_path, first_page=page_number, last_page=page_number)
        temp_img_path = f"temp_page_{page_number}.jpg"
        images[0].save(temp_img_path, 'JPEG')
        print(f"   ✅ Successfully converted PDF page to image: {temp_img_path}")
        
        # In the real version, we'd send this to AI. 
        # In mock mode, we just clean it up.
        os.remove(temp_img_path)
        
    except Exception as e:
        print(f"   ❌ Error converting PDF: {e}")
        return None

    print("   ⚠️  MOCK MODE: Skipping OpenAI API call.")
    
    # 2. Return Dummy Data instead of Real AI Data
    mock_transcription = (
        "ADULT CARDIAC ARREST PROTOCOL (MOCK DATA). "
        "Step 1: Verify cardiac arrest. "
        "Step 2: Start CPR immediately. Push hard and fast. "
        "Step 3: Apply AED or defibrillator as soon as possible. "
        "If shockable rhythm (VF/VT): Shock. Resume CPR for 2 minutes. "
        "If not shockable (Asystole/PEA): Resume CPR. Administer Epinephrine 1mg every 3-5 minutes. "
        "This is a placeholder text generated to test the database system."
    )
    
    return mock_transcription

if __name__ == "__main__":
    # Make sure the filename matches EXACTLY what is in your folder
    pdf_filename = "ems-protocol-manual.pdf" 
    
    # Run the mock parser
    protocol_text = parse_protocol_flowchart_MOCK(pdf_filename, 27)
    
    if protocol_text:
        data = {
            "title": "Adult Cardiac Arrest (Mock)",
            "raw_content": protocol_text
        }
        
        with open("database_seed.json", "w") as f:
            json.dump(data, f, indent=4)
            
        print("✅ Success! Saved mock data to 'database_seed.json'")
    else:
        print("❌ Failed to process protocol.")