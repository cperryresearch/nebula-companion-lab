import os
import pyttsx3
from google.cloud import texttospeech

# Point to your EXACT .json filename
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "nebula-ai-companion-101e8593f300.json"

class NebulaVoice:
    def __init__(self):
        # --- THE HARDWARE SHIELD ---
        # Logic: Attempt to start the offline engine. If no sound hardware is found (Cloud), 
        # the app skips this instead of crashing [cite: 2026-02-13].
        try:
            self.offline_engine = pyttsx3.init()
            self.offline_available = True
        except Exception:
            self.offline_available = False
        
        try:
            self.cloud_client = texttospeech.TextToSpeechClient()
            self.cloud_available = True
        except Exception:
            self.cloud_available = False

    def speak(self, text):
        """Returns the mode used so the GUI can trigger playback."""
        if os.path.exists("output.mp3"):
            try: os.remove("output.mp3")
            except: pass

        if self.cloud_available:
            try:
                self._generate_cloud_audio(text)
                return "cloud" # Handshake Signal
            except Exception:
                self._speak_offline(text)
                return "offline"
        else:
            self._speak_offline(text)
            return "offline"

    def _generate_cloud_audio(self, text):
        input_text = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Neural2-F", 
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            pitch=0.0,
            speaking_rate=0.95
        )
        response = self.cloud_client.synthesize_speech(
            request={"input": input_text, "voice": voice, "audio_config": audio_config}
        )
        with open("output.mp3", "wb") as out:
            out.write(response.audio_content)

    def _speak_offline(self, text):
        # Logic: Only execute if hardware was successfully initialized
        if self.offline_available:
            try:
                self.offline_engine.say(text)
                self.offline_engine.runAndWait()
            except:
                pass
