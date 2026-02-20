import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk
import time, datetime, random, json, os, math

# --- NEBULA SENSORY MODULES ---
from nebula_voice import NebulaVoice 
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Initialize Environment & Gemini Link
load_dotenv(override=True)
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# --- REFINED AUDIO INITIALIZATION ---
try:
    import pygame
    # Setting frequency and buffer for high-fidelity MP3s
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.mixer.init()
    AUDIO_ENABLED = True
    print("✅ Audio System: Online and Synchronized")
except (ImportError, Exception) as e:
    print(f"⚠️ Audio system bypassed: {e}")
    AUDIO_ENABLED = False

# ==========================================
# PART 1: THE BRAIN (Persistence & Milestone Logic)
# ==========================================
class SuperPet:
    def __init__(self, name):
        self.name = name
        self.filename = f"{self.name.lower()}_data.json"
        self.memory_file = f"{self.name.lower()}_memory.json"
        
        self.hunger, self.happiness, self.energy = 10.0, 10.0, 10.0
        self.xp, self.level = 325, 2 
        self.is_alive, self.max_inventory = True, 10 
        self.evolution_stage = "Teen"
        self.achievements, self.chat_history = [], []
        
        self.inventory = ["Apple", "Berry", "Star Bits"]
        self.shop_catalog = {
            "Apple": {"cost": 20, "h": 4, "e": 1}, "Berry": {"cost": 20, "h": 2, "e": 3},
            "Star Bits": {"cost": 15, "h": 2, "e": 1}, "Moon Cake": {"cost": 45, "h": 5, "e": 3},
            "Nebula Tea": {"cost": 60, "h": 1, "e": 7}, "Solar Salmon": {"cost": 80, "h": 7, "e": 4}
        }
        
        self.load_game()
        self.load_memory() 
        self.last_update = time.time()
        self.temp_trait, self.temp_trait_expiry = None, 0

    def save_game(self):
        data = {
            "hunger": self.hunger, "happiness": self.happiness, "energy": self.energy,
            "xp": self.xp, "level": self.level, "evolution_stage": self.evolution_stage, 
            "inventory": self.inventory, "achievements": self.achievements
        }
        with open(self.filename, 'w') as f: json.dump(data, f)
        with open(self.memory_file, 'w') as f: json.dump(self.chat_history[-15:], f)

    def load_game(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    d = json.load(f)
                    self.hunger = d.get("hunger", 10.0)
                    self.happiness = d.get("happiness", 10.0)
                    self.energy = d.get("energy", 10.0)
                    self.xp = d.get("xp", 325)
                    self.level = d.get("level", 2)
                    self.evolution_stage = d.get("evolution_stage", "Teen")
                    self.inventory = d.get("inventory", [])
                    self.achievements = d.get("achievements", [])
            except: pass

    def load_memory(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f: self.chat_history = json.load(f)
            except: self.chat_history = []

    def unlock_achievement(self, title):
        if title not in self.achievements:
            self.achievements.append(title); return True
        return False

    def update_vitals(self):
        now = time.time(); elapsed = now - self.last_update
        is_sleeping = self.temp_trait == "Deep Sleep" and time.time() < self.temp_trait_expiry
        h_mod, e_mod = (0.5, -1.5) if is_sleeping else (1.0, 1.0)
        self.hunger = max(0, min(10, self.hunger - (elapsed * 0.008 * h_mod)))
        self.energy = max(0, min(10, self.energy - (elapsed * 0.006 * e_mod)))
        self.happiness = max(0, min(10, self.happiness - (elapsed * 0.004)))
        self.last_update = now
        if self.hunger <= 0: self.is_alive = False

# ==========================================
# PART 2: THE BODY (Visual Dashboard & Chat)
# ==========================================
class NebulaApp:
    def __init__(self, root):
        self.root = root; self.root.title("Nebula v9.1: Harmonic Voice Anchor"); self.root.geometry("450x940")
        self.pet = SuperPet("Nebula")
        self.voice = NebulaVoice() 
        
        self.hover_angle, self.particles = 0.0, [] 
        self.canvas = tk.Canvas(root, width=450, height=450, highlightthickness=0, bd=0); self.canvas.pack(pady=0)
        self.warning_label = tk.Label(root, text="", font=("Arial", 12, "bold"), fg="gold"); self.warning_label.pack()
        
        self.stats_frame = tk.LabelFrame(root, text=" Dashboard ", padx=15, pady=10); self.stats_frame.pack(fill="x", padx=25, pady=10)
        self.hunger_bar = tk.Label(self.stats_frame, text="Hunger:    [----------]", font=("Courier", 10)); self.hunger_bar.pack(anchor="w")
        self.happiness_bar = tk.Label(self.stats_frame, text="Happiness: [----------]", font=("Courier", 10)); self.happiness_bar.pack(anchor="w")
        self.energy_bar = tk.Label(self.stats_frame, text="Energy:    [----------]", font=("Courier", 10)); self.energy_bar.pack(anchor="w")
        self.xp_label = tk.Label(self.stats_frame, text=f"XP Balance: {int(self.pet.xp)} | Lvl 2 Teen", font=("Arial", 11, "bold")); self.xp_label.pack(anchor="w", pady=(5, 0))
        
        self.btn_frame = tk.Frame(root); self.btn_frame.pack(pady=10)
        tk.Button(self.btn_frame, text="Feed", width=12, command=self.on_feed).grid(row=0, column=0, padx=5, pady=5)
        self.nap_btn = tk.Button(self.btn_frame, text="Nap", width=12, command=self.on_nap); self.nap_btn.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(self.btn_frame, text="Achievements", width=12, command=self.on_achievements).grid(row=0, column=2, padx=5, pady=5)
        tk.Button(self.btn_frame, text="Play Game", width=12, command=self.on_play).grid(row=1, column=0, padx=5, pady=5)
        tk.Button(self.btn_frame, text="Shop", width=12, command=self.on_shop).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(self.btn_frame, text="Chat", width=12, command=self.on_chat).grid(row=1, column=2, padx=5, pady=5) 
        tk.Button(self.btn_frame, text="Save", width=12, command=self.pet.save_game).grid(row=1, column=3, padx=5, pady=5)
        
        self.log = tk.Text(root, height=10, width=50, font=("Courier", 10), state='disabled', borderwidth=0); self.log.pack(padx=15, pady=15)
        self.animation_loop(); self.update_ui()

    def log_msg(self, msg):
        self.log.config(state='normal'); self.log.insert('1.0', f"> {msg}\n"); self.log.config(state='disabled')

    def nebula_speak(self, text):
        """Unified Voice Logic: Log and trigger playback with safety pulse."""
        self.log_msg(f"Nebula: {text}")
        
        # Trigger audio and capture return value
        mode = self.voice.speak(text) 
        print(f"DEBUG: Handshake check. Mode is: {mode}") # Diagnostic Pulse

        if mode == "cloud" and AUDIO_ENABLED:
            time.sleep(0.2) # Buffer for Windows file writing
            
            if os.path.exists("output.mp3"):
                try:
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload() 
                    pygame.mixer.music.load("output.mp3")
                    pygame.mixer.music.play()
                except Exception as e:
                    print(f"DEBUG: Audio Playback failed: {e}")
                    self.log_msg("⚠️ Voice system busy...")

    def animation_loop(self):
        self.hover_angle += 0.08; y_offset = math.sin(self.hover_angle) * 15 
        if random.random() < 0.3:
            p_id = self.canvas.create_text(225 + random.randint(-180, 180), 200 + y_offset + random.randint(40, 120), text="✦", fill="#DA70D6", font=("Arial", 12), tags="star")
            self.particles.append({"id": p_id, "life": 1.0, "dx": random.uniform(-1, 1), "dy": random.uniform(1, 3)})
        for p in self.particles[:]:
            p["life"] -= 0.05
            if p["life"] <= 0: self.canvas.delete(p["id"]); self.particles.remove(p)
            else: self.canvas.move(p["id"], p["dx"], p["dy"])
        self.refresh_avatar(y_offset); self.root.after(50, self.animation_loop)

    def refresh_avatar(self, y_offset):
        self.canvas.delete("avatar"); img = self.get_image()
        if img: self.canvas.create_image(225, 200 + y_offset, image=img, tags="avatar"); self.canvas.image = img

    def get_image(self):
        is_sleeping = self.pet.temp_trait == "Deep Sleep" and time.time() < self.pet.temp_trait_expiry
        img_name = "sleeping" if is_sleeping else self.pet.evolution_stage.lower()
        for ext in [".png", ".jpg"]:
            path = os.path.join("images", img_name + ext)
            if os.path.exists(path):
                try:
                    full_img = Image.open(path); return ImageTk.PhotoImage(full_img.resize((320, 320), Image.Resampling.LANCZOS))
                except: continue
        return None

    def on_feed(self):
        if not self.pet.inventory: self.log_msg("🎒 Bag is empty!"); return
        inv_text = "Feed Nebula:\n" + "\n".join([f"{i+1}: {item}" for i, item in enumerate(self.pet.inventory)])
        choice = simpledialog.askinteger("Feed Nebula", inv_text)
        if choice and 0 < choice <= len(self.pet.inventory):
            name = self.pet.inventory.pop(choice - 1); stats = self.pet.shop_catalog.get(name, {"h": 4, "e": 1})
            self.pet.hunger = min(10, self.pet.hunger + stats["h"]); self.pet.energy = min(10, self.pet.energy + stats["e"])
            self.log_msg(f"Nebula ate the {name}!"); self.pet.save_game(); self.update_ui()

    def on_shop(self):
        catalog = self.pet.shop_catalog; msg = f"SHOP (XP: {int(self.pet.xp)})\n\n"
        items = list(catalog.keys())
        for i, name in enumerate(items): msg += f"{i+1}: {name} ({catalog[name]['cost']} XP)\n"
        choice = simpledialog.askinteger("XP Shop", msg)
        if choice and 0 < choice <= len(items):
            name = items[choice-1]; cost = catalog[name]["cost"]
            if self.pet.xp >= cost:
                self.pet.xp -= cost; self.pet.inventory.append(name); self.log_msg(f"✅ Bought {name}!")
        self.pet.save_game(); self.update_ui()

    def on_play(self):
        while True:
            menu = "1: Rock-Paper-Scissors\n2: Number Pulse"
            choice = simpledialog.askstring("Game Hub", menu)
            if not choice: break
            self.pet.happiness = min(10, self.pet.happiness + 2.0); self.log_msg("✨ Nebula is excited to play!")
            if choice == "1":
                user = simpledialog.askstring("RPS", "Rock, Paper, or Scissors?").title(); pc = random.choice(["Rock", "Paper", "Scissors"])
                if user in ["Rock", "Paper", "Scissors"]:
                    if user == pc: self.log_msg(f"🏁 Draw! Both picked {pc}.")
                    elif (user == "Rock" and pc == "Scissors") or (user == "Paper" and pc == "Rock") or (user == "Scissors" and pc == "Paper"):
                        self.pet.xp += 25; self.log_msg(f"🏆 WIN! {user} beats {pc}!")
                    else: self.log_msg(f"💀 Loss! {pc} beats {user}.")
            elif choice == "2":
                num, hint_txt = random.randint(1, 10), "Thinking..."
                for i in range(3):
                    guess = simpledialog.askinteger("Number Pulse", f"{hint_txt}\nGuess 1-10 ({i+1}/3):")
                    if guess == num: self.pet.xp += 30; self.log_msg(f"🏆 SUCCESS! {num}!"); break
                    elif guess: hint_txt = "Higher..." if guess < num else "Lower..."
            self.pet.save_game(); self.check_milestones(); self.update_ui()
            if not messagebox.askyesno("Game Hub", "Play again?"): break

    def on_chat(self):
        user_input = simpledialog.askstring("Cosmic Chat", "Speak to Nebula:")
        if not user_input: return
        self.log_msg(f"Cazz: {user_input}")
        if not client: self.log_msg("⚠️ Sentience Link missing."); return
        
        persona = (f"You are Nebula, a cosmic cat companion. Your steward is Cazz. "
                   f"Stats - Hunger: {self.pet.hunger}/10, Energy: {self.pet.energy}/10. "
                   f"Be warm, brief, and acknowledge Cazz as your steward.")

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=self.pet.chat_history + [{"role": "user", "parts": [{"text": user_input}]}],
                config=types.GenerateContentConfig(system_instruction=persona)
            )
            
            nebula_reply = response.text
            self.nebula_speak(nebula_reply) 
            
            self.pet.chat_history.append({"role": "user", "parts": [{"text": user_input}]})
            self.pet.chat_history.append({"role": "model", "parts": [{"text": nebula_reply}]})
            self.pet.save_game() 
            
        except Exception as e:
            self.log_msg(f"⚠️ Link flickering: {str(e)[:40]}...")

    def on_nap(self):
        is_sleeping = self.pet.temp_trait == "Deep Sleep" and time.time() < self.pet.temp_trait_expiry
        if is_sleeping: 
            self.pet.temp_trait_expiry = 0
            self.nebula_speak("I am awake and ready, Steward Cazz.")
        else: 
            self.pet.temp_trait = "Deep Sleep"
            self.pet.temp_trait_expiry = time.time() + 600
            self.nebula_speak("Resting in the celestial mists now.")

    def on_achievements(self):
        self.log_msg("--- NEBULA'S LEGACY ---")
        for a in reversed(self.pet.achievements): self.log_msg(f"• {a}")

    def check_milestones(self):
        if self.pet.xp >= 300 and self.pet.unlock_achievement("🧪 STEWARD OF THE DYNAMICS"): self.log_msg("🏆 ACHIEVEMENT: Steward of the Dynamics!")

    def update_ui(self):
        self.pet.update_vitals()
        bg, fg = ("#120a1a", "#d1c4e9")
        self.root.config(bg=bg); self.canvas.config(bg=bg); self.stats_frame.config(bg=bg, fg=fg); self.btn_frame.config(bg=bg); self.log.config(bg=bg, fg=fg)
        if not self.pet.is_alive: self.warning_label.config(text="NEBULA HAS PASSED AWAY"); return
        self.hunger_bar.config(text=f"Hunger:    [{'#'*int(self.pet.hunger) + '-'*(10-int(self.pet.hunger))}]", bg=bg, fg=fg)
        self.happiness_bar.config(text=f"Happiness: [{'#'*int(self.pet.happiness) + '-'*(10-int(self.pet.happiness))}]", bg=bg, fg=fg)
        self.energy_bar.config(text=f"Energy:    [{'#'*int(self.pet.energy) + '-'*(10-int(self.pet.energy))}]", bg=bg, fg=fg)
        self.xp_label.config(text=f"XP Balance: {int(self.pet.xp)} | Lvl {self.pet.level} {self.pet.evolution_stage}", bg=bg, fg=fg)
        self.root.after(1000, self.update_ui)

if __name__ == "__main__":
    window = tk.Tk(); app = NebulaApp(window); window.mainloop()