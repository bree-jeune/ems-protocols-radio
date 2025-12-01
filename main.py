import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_db():
    try:
        with open("ems_protocols.json", "r") as f:
            data = json.load(f)
            # Support both old flat format and new nested format
            return data.get("protocols", data) 
    except FileNotFoundError:
        print("⚠️ DB not found.")
        return {}

PROTOCOL_DB = load_db()

class RadioRequest(BaseModel):
    protocol_id: str
    mode: str

@app.get("/protocols")
async def get_all_protocols():
    return [
        {
            "id": key, 
            "title": val["title"],
            "category": val.get("category", "Uncategorized")
        } 
        for key, val in PROTOCOL_DB.items()
    ]

@app.post("/generate-segment")
async def generate_radio_segment(request: RadioRequest):
    item = PROTOCOL_DB.get(request.protocol_id)
    
    if not item:
        if not PROTOCOL_DB: raise HTTPException(status_code=404, detail="DB Empty")
        item = PROTOCOL_DB[next(iter(PROTOCOL_DB))]

    # Format the text for better reading
    raw_text = item.get("raw_text", "")
    
    # Simple cleanup for the radio script
    # Remove excessive newlines
    script_body = raw_text.replace("\n", " ").replace("  ", " ")
    
    # Custom Intro
    if item.get("category") == "Formulary":
        intro = f"Formulary Drug: {item['title']}."
    else:
        intro = f"You are listening to the {request.mode.upper()} breakdown of {item['title']}."

    full_script = f"{intro}\n\n{script_body}"

    return {
        "title": item["title"],
        "mode": request.mode,
        "audio_url": "", 
        "script_text": full_script
    }