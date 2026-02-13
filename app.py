import streamlit as st
import os, time, random, base64, json, datetime
from nebula_voice import NebulaVoice
from super_pet import SuperPet
from google import genai
from google.genai import types

# --- PHASE 1: CORE ENGINE & APP CONFIG ---
st.set_page_config(page_title="Nebula Zenith Sanctuary", layout="wide", initial_sidebar_state="auto")

# Retrieve API Key from Streamlit Secrets
try:
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=GEMINI_KEY)
except:
    st.error("Neural Link Failed: GEMINI_API_KEY missing in Secrets.")
    st.stop()

# Framework Identity & State Initialization [cite: 2026-02-13]
if 'pet' not in st.session_state:
    st.session_state.pet = SuperPet("Nebula")
    st.session_state.voice = NebulaVoice()
    st.session_state.chat_history = []
    st.session_state.last_audio_b64 = None
    st.session_state.audio_played = True 
    st.session_state.next_blink_time = time.time() + random.uniform(30.0, 60.0)
    st.session_state.current_mood_text = "Nebula is observing the stars."
    st.session_state.is_currently_blinking = False

# --- PHASE 2: CELESTIAL CYCLE [cite: 2026-02-13] ---
now_hour = datetime.datetime.now().hour
if 6 <= now_hour < 10:
    bg_base, bg_style, accent = "#1a152a", "radial-gradient(circle, #4a3b61 0%, #1a152a 100%)", "#ffd700"
elif 10 <= now_hour < 17:
    bg_base, bg_style, accent = "#05030a", "radial-gradient(circle, #1a152a 0%, #05030a 100%)", "#da70d6"
elif 17 <= now_hour < 21:
    bg_base, bg_style, accent = "#0a0510", "radial-gradient(circle, #2c1e4a 0%, #0a0510 100%)", "#ff8c00"
else:
    bg_base, bg_style, accent = "#05030a", "radial-gradient(circle, #0b0812 0%, #05030a 100%)", "#4a148c"

# --- PHASE 3: EVOLUTION & VISUAL STATE [cite: 2026-02-13] ---
xp = st.session_state.pet.xp
stage = "adult" if xp >= 1500 else ("teen" if xp >= 500 else "baby")

if st.session_state.is_currently_blinking: 
    avatar_file = "images/nebula_blink.png"
else: 
    avatar_file = f"images/{stage}.png"

img_b64 = ""
if os.path.exists(avatar_file):
    with open(avatar_file, "rb") as f: 
        img_b64 = base64.b64encode(f.read()).decode()

# --- ECLIPSE CSS: ATOMIC HUD ANCHORING [cite: 2026-02-13] ---
st.markdown(f"""
    <style>
    html, body, [data-testid="stAppViewContainer"] {{ background-color: {bg_base} !important; }}
    .stApp {{ background: {bg_style}; color: #d1c4e9; }}
    .fixed-header {{
        position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
        background: linear-gradient(to bottom, {bg_base} 0%, {bg_base} 70%, rgba(0,0,0,0.4) 90%, rgba(0,0,0,0) 100%);
        backdrop-filter: blur(12px); padding: 40px 10px 80px 10px; text-align: center;
    }}
    .hud-image {{ width: 280px; margin: 5px auto; display: block; filter: drop-shadow(0 0 25px {accent}44); }}
    .chat-body {{ padding-top: 500px; padding-bottom: 100px; }} 
    </style>
    """, unsafe_allow_html=True)

# --- SECTION 4: ATOMIC HUD RENDERING [cite: 2026-02-13] ---
st.markdown(f"""
    <div class="fixed-header">
        <div style="font-size: 0.8rem; font-weight: bold; margin-bottom: 10px;">NEBULA STATUS | {int(xp)} XP</div>
        <img src="data:image/png;base64,{img_b64}" class="hud-image">
        <div style="font-size: 0.9rem; color: #b39ddb; margin-top: 5px;">✨ {st.session_state.current_mood_text}</div>
    </div>
    <div class="chat-body">
    """, unsafe_allow_html=True)

# --- SECTION 5: RESONANCE JOURNAL (CHAT) [cite: 2026-02-13] ---
for msg in st.session_state.chat_history[-10:]:
    with st.chat_message("assistant" if msg["role"] == "model" else "user"): 
        st.markdown(msg["parts"][0]["text"])

# Signal Processing: Logic Priority [Conversation > Audio > Visuals]
if prompt := st.chat_input("Signal Nebula..."):
    st.session_state.chat_history.append({"role": "user", "parts": [{"text": prompt}]})
    
    # Sonic Filter: Warm, brief, no numeric stats [cite: 2026-02-13]
    persona = "You are Nebula, a cosmic companion. Your steward is Cazz. Be warm and brief. Never mention stats."
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=st.session_state.chat_history, 
            config=types.GenerateContentConfig(system_instruction=persona)
        )
        
        # Audio Protocol Execution [cite: 2026-02-13]
        st.session_state.voice.speak(response.text)
        st.session_state.chat_history.append({"role": "model", "parts": [{"text": response.text}]})
        
        if os.path.exists("output.mp3"):
            with open("output.mp3", "rb") as f: 
                st.session_state.last_audio_b64 = base64.b64encode(f.read()).decode()
            st.session_state.audio_played = False
            
        # XP Gain: Golden Ratio [cite: 2026-02-13]
        st.session_state.pet.xp += 20
        st.session_state.pet.save_game()
        st.rerun()
    except Exception as e: 
        st.error(f"Neural Link Severed: {e}")

# Base64 Audio Injection [cite: 2026-02-13]
if st.session_state.last_audio_b64 and not st.session_state.audio_played:
    st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{st.session_state.last_audio_b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
    st.session_state.audio_played = True

st.markdown('</div>', unsafe_allow_html=True)

# Autonomic Blink Logic: 30-60s Cadence [cite: 2026-02-13]
now = time.time()
if now >= st.session_state.next_blink_time:
    st.session_state.is_currently_blinking = not st.session_state.is_currently_blinking
    st.session_state.next_blink_time = now + (0.2 if st.session_state.is_currently_blinking else random.uniform(30.0, 60.0))
    st.rerun()