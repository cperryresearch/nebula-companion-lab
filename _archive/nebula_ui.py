import streamlit as st
import requests

# ⚠️ YOUR ACTIVE NGROK URL - INTEGRATED
API_URL = "https://glucosidal-peggy-submissively.ngrok-free.dev"

st.set_page_config(page_title="Nebula Zenith", layout="centered")

# --- CUSTOM CSS FOR APP FEEL ---
st.markdown("""
    <style>
    /* Main app background */
    .stApp { 
        background-color: #0b0812; 
        color: white; 
    }
    /* Hide the default Streamlit header for an app-like look */
    [data-testid="stHeader"] { 
        background: rgba(0,0,0,0); 
    }
    /* Styling for chat bubbles */
    .chat-bubble { 
        padding: 10px; 
        border-radius: 10px; 
        margin-bottom: 10px; 
    }
    /* Ensure text input is visible against dark background */
    .stTextInput input {
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🌌 Nebula Zenith")
st.caption("Connected to Hybrid Core via Secure Tunnel")

# Initialize Local Session Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- RENDER CHAT HISTORY ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- CHAT INPUT ---
if prompt := st.chat_input("Signal Nebula..."):
    # 1. Display User Message locally
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Call the Brain (FastAPI) via the ngrok Tunnel
    try:
        # Sending the POST request to the /chat endpoint of your brain
        response = requests.post(f"{API_URL}/chat", json={"user_input": prompt})
        
        if response.status_code == 200:
            reply = response.json().get("reply")
            # 3. Display Nebula's Response locally
            st.session_state.messages.append({"role": "assistant", "content": reply})
            with st.chat_message("assistant"):
                st.markdown(reply)
        else:
            st.error(f"Brain Error: {response.status_code} - Check if nebula_brain.py is running.")
            
    except Exception as e:
        st.error(f"Connection Lost: {e}. Ensure ngrok is active and the URL hasn't changed.")