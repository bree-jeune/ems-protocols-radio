#This Python script takes a PDF version of the protocol, captures a specific page, and uses AI to turn the visual flowchart into a readable script

import base64
import json
from pdf2image import convert_from_path
from openai import OpenAI
import os

# Initialize OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not os.getenv("OPENAI_API_KEY"):
  raise RuntimeError("OPENAI_API_KEY environment variable not set")

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def parse_protocol_flowchart(pdf_path, page_number):
    print(f"📄 Processing Page {page_number} of {pdf_path}...")
    
    # 1. Convert PDF Page to Image
    images = convert_from_path(pdf_path, first_page=page_number, last_page=page_number)
    temp_img_path = f"temp_page_{page_number}.jpg"
    images[0].save(temp_img_path, 'JPEG')
    
    base64_image = encode_image(temp_img_path)

    # 2. Send to GPT-4o to "Read" the Flowchart
    # We ask it to output a structured script suitable for reading aloud
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "You are an expert EMS instructor. Look at this protocol flowchart. Convert it into a clear, linear textual explanation. Describe the flow of decisions logically. Capture every drug dose and step accurately. Return ONLY the raw text explanation."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        max_tokens=2000
    )
    
    transcription = response.choices[0].message.content
    print("✅ Protocol Transcribed!")
    
    # Clean up
    os.remove(temp_img_path)
    return transcription

# --- RUN THE INGESTION ---
if __name__ == "__main__":
    # Example: Extracting the Cardiac Arrest Protocol from Page 27
    protocol_text = parse_protocol_flowchart("ems-protocol-manual.pdf", 27)
    
    # Save to a JSON file (or push to your API DB)
    data = {
        "title": "Adult Cardiac Arrest",
        "raw_content": protocol_text
    }
    
    with open("database_seed.json", "w") as f:
        json.dump(data, f, indent=4)
        
    print("💾 Saved to database_seed.json")