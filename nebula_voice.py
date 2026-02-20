# nebula_voice.py — Refined Cloud Voice (Soft + Ethereal)

import os
from openai import OpenAI

class NebulaVoice:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set.")

        self.client = OpenAI(api_key=api_key)

        # Primary + fallback voice
        # shimmer = softer, ethereal
        # alloy = clearer, slightly firmer
        self.primary_voice = "shimmer"
        self.fallback_voice = "alloy"

    # -----------------------------
    # Light punctuation shaping
    # -----------------------------
    def _shape_text(self, text: str) -> str:
        """
        Adds subtle pacing cues without being dramatic.
        Makes delivery softer and less robotic.
        """
        if not text:
            return text

        shaped = text.strip()

        # Add gentle pauses after sentences
        shaped = shaped.replace(". ", ".  ")
        shaped = shaped.replace("! ", "!  ")
        shaped = shaped.replace("? ", "?  ")

        # Soft breath before affectionate phrases
        shaped = shaped.replace("I’m here", "I’m here…")
        shaped = shaped.replace("I'm here", "I'm here…")

        return shaped

    # -----------------------------
    # Speak (Cloud TTS)
    # -----------------------------
    def speak(self, text: str) -> str:
        """
        Generates output.mp3 using OpenAI Cloud TTS.
        Returns:
            "cloud" on success
            "fallback" if second voice used
            "error" on failure
        """

        shaped_text = self._shape_text(text)

        # Remove old file to force Streamlit autoplay
        if os.path.exists("output.mp3"):
            try:
                os.remove("output.mp3")
            except Exception:
                pass

        # Try primary voice
        try:
            with self.client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice=self.primary_voice,
                input=shaped_text,
            ) as response:
                response.stream_to_file("output.mp3")

            return "cloud"

        except Exception as e:
            print("Primary voice failed:", e)

        # Try fallback voice
        try:
            with self.client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice=self.fallback_voice,
                input=shaped_text,
            ) as response:
                response.stream_to_file("output.mp3")

            return "fallback"

        except Exception as e:
            print("Fallback voice failed:", e)
            return "error"