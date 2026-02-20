from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, time, random, datetime
from super_pet import SuperPet
from nebula_voice import NebulaVoice
from dotenv import load_dotenv
from google import genai
from google.genai import types

app = FastAPI()
load_dotenv(override=True)


class NebulaState:
    def __init__(self):
        self.pet = SuperPet("Nebula")
        self.voice = NebulaVoice()
        self.action_log = ["Nebula awakened in the Hybrid Core."]
        self.resonance_journal = []


state = NebulaState()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None


class ChatRequest(BaseModel):
    user_input: str


@app.get("/status")
def get_status():
    xp = state.pet.xp
    stage = "baby"
    if xp >= 1500:
        stage = "adult"
    elif xp >= 500:
        stage = "teen"

    return {
        "hunger": state.pet.hunger,
        "happiness": state.pet.happiness,
        "energy": state.pet.energy,
        "xp": xp,
        "stage": stage,
        "inventory": state.pet.inventory,
    }


@app.post("/chat")
def chat_with_nebula(request: ChatRequest):
    state.pet.chat_history.append(
        {"role": "user", "parts": [{"text": request.user_input}]}
    )
    base_persona = "You are Nebula, a cosmic companion. Your steward is Cazz. Be warm, brief, and grounded in feeling. Never mention numeric statistics."

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=state.pet.chat_history,
            config=types.GenerateContentConfig(system_instruction=base_persona),
        )
        reply = response.text
        state.pet.chat_history.append({"role": "model", "parts": [{"text": reply}]})
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
