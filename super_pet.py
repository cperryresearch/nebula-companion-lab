import time
import random
import json
import os


class SuperPet:
    def __init__(self, name):
        self.name = name
        self.filename = f"{self.name.lower()}_data.json"

        # Stats & Limits
        self.hunger = 10.0
        self.happiness = 10.0
        self.energy = 10.0
        self.xp = 0
        self.level = 1
        self.is_alive = True
        self.max_inventory = 8

        # Evolution & Personality
        self.base_trait = random.choice(["Chill", "Hyper", "Sweet"])
        self.temp_trait = None
        self.temp_trait_expiry = 0
        self.evolution_stage = "Baby"

        # Memory
        self.chat_history = []

        # Inventory
        self.inventory = ["Apple", "Apple", "Berry", "Berry", "Coffee"]
        self.journal = [
            f"{self.name} was born as a {self.base_trait} {self.evolution_stage}."
        ]

        self.load_game()
        self.last_update = time.time()

    # -------------------------------------------------
    # SAVE / LOAD
    # -------------------------------------------------

    def save_game(self):
        data = {
            "hunger": self.hunger,
            "happiness": self.happiness,
            "energy": self.energy,
            "xp": self.xp,
            "level": self.level,
            "base_trait": self.base_trait,
            "evolution_stage": self.evolution_stage,
            "inventory": self.inventory,
            "journal": self.journal,
            "chat_history": self.chat_history,
            "temp_trait": self.temp_trait,
            "temp_trait_expiry": float(self.temp_trait_expiry),
            "last_update": float(self.last_update),
        }
        with open(self.filename, "w") as f:
            json.dump(data, f)

    def load_game(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r") as f:
                    data = json.load(f)

                self.hunger = data["hunger"]
                self.happiness = data["happiness"]
                self.energy = data["energy"]
                self.xp = data["xp"]
                self.level = data["level"]
                self.base_trait = data["base_trait"]
                self.evolution_stage = data["evolution_stage"]
                self.inventory = data["inventory"]
                self.journal = data["journal"]
                self.chat_history = data.get("chat_history", [])
                self.temp_trait = data.get("temp_trait", None)
                self.temp_trait_expiry = float(data.get("temp_trait_expiry", 0.0))
                self.last_update = float(data.get("last_update", time.time()))

                print(f"📂 {self.name} loaded. Welcome back!")

            except Exception:
                print("⚠️ Load failed. Starting fresh.")

    # -------------------------------------------------
    # COMPANION-MODE VITALS (Very slow + forgiving)
    # -------------------------------------------------

    def update_vitals(self):
        now = time.time()
        elapsed = now - self.last_update

        # Prevent extreme decay if app was closed
        elapsed = min(elapsed, 15 * 60)  # cap catch-up to 15 minutes

        trait = self.get_current_trait()
        minutes = elapsed / 60.0

        # Target drain (FULL 10→0):
        # hunger: ~12 hours
        # energy: ~16 hours
        # happiness: ~48 hours (and only really when other stats are low)
        HUNGER_PER_MIN = 10.0 / (12 * 60)
        ENERGY_PER_MIN = 10.0 / (16 * 60)
        HAPPY_PER_MIN = 10.0 / (48 * 60)

        # Gentle trait modifiers
        h_mod = (
            1.10 if trait == "Sugar Rush" else 0.30 if trait == "Deep Sleep" else 1.0
        )
        e_mod = (
            0.70
            if trait == "Caffeinated"
            else 0.10 if trait == "Deep Sleep" else 1.10 if trait == "Hyper" else 1.0
        )

        # Happiness decay should feel "emotional continuity", not a chore.
        # If hunger+energy are high, happiness barely drifts.
        wellbeing = (self.hunger + self.energy) / 20.0  # 0..1

        # When wellbeing=1.0 → multiplier ~0.05 (almost no decay)
        # When wellbeing=0.0 → multiplier ~1.00 (normal decay)
        happy_need_multiplier = max(0.05, 1.0 - wellbeing)

        # Apply decay
        self.hunger -= minutes * HUNGER_PER_MIN * h_mod
        self.energy -= minutes * ENERGY_PER_MIN * e_mod
        self.happiness -= minutes * HAPPY_PER_MIN * happy_need_multiplier

        # Clamp values safely
        self.hunger = max(0.0, min(10.0, self.hunger))
        self.energy = max(0.0, min(10.0, self.energy))
        self.happiness = max(0.0, min(10.0, self.happiness))

        self.last_update = now

        # Optional: in companion mode you can disable death entirely.
        # If you want "never die", comment these two lines.
        if self.hunger <= 0.0:
            self.is_alive = False

        # Evolution thresholds
        if self.xp >= 150 and self.level == 1:
            self.evolve("Teen")
        elif self.xp >= 400 and self.level == 2:
            self.evolve("Adult")

    # -------------------------------------------------
    # TRAITS
    # -------------------------------------------------

    def get_current_trait(self):
        if self.temp_trait and time.time() < self.temp_trait_expiry:
            return self.temp_trait
        return self.base_trait

    def get_mood(self):
        """
        Returns a mood string and display text based on current vital levels.
        Used to drive avatar state and HUD mood text dynamically.
        """
        trait = self.get_current_trait()

        # Deep Sleep overrides everything
        if trait == "Deep Sleep":
            return "Sleeping", "Nebula is deep in a cosmic dream... 💤"

        # Critical states first
        if self.hunger <= 2.0:
            return "Hungry", "Nebula is really hungry... her tummy is rumbling 🌙"

        if self.energy <= 2.0:
            return "Exhausted", "Nebula is exhausted... she needs rest soon 😴"

        if self.happiness <= 2.0:
            return "Sad", "Nebula feels a little lost in the stars... 💫"

        # Warning states
        if self.hunger <= 4.0:
            return "Peckish", "Nebula is getting a little hungry... 🍃"

        if self.energy <= 4.0:
            return "Tired", "Nebula is feeling a bit tired... ✨"

        # Happy states
        if self.happiness >= 8.0 and self.hunger >= 7.0 and self.energy >= 7.0:
            return "Radiant", "Nebula is glowing with cosmic joy! ✨💖"

        if self.happiness >= 6.0:
            return "Happy", "Nebula is happily observing the stars ⭐"

        # Neutral default
        return "Neutral", "Nebula is observing the stars 🌌"

    def get_avatar_state(self):
        """
        Returns the avatar image filename to display based on current state.
        Add new image files to the images/ folder and map them here.
        """
        trait = self.get_current_trait()

        # Sleep overrides everything
        if trait == "Deep Sleep":
            return "images/sleeping.png"

        # Critical vital states
        if self.hunger <= 2.0:
            return "images/hungry.png"

        if self.energy <= 2.0:
            return "images/tired.png"

        if self.happiness <= 2.0:
            return "images/sad.png"

        # Positive states
        if self.happiness >= 8.0 and self.hunger >= 7.0 and self.energy >= 7.0:
            return "images/radiant.png"

        # Neutral/idle fallback based on evolution stage
        xp = self.xp
        stage = "adult" if xp >= 1500 else ("teen" if xp >= 500 else "baby")
        return f"images/{stage}.png"

    def evolve(self, stage):
        self.level += 1
        self.evolution_stage = stage
        self.base_trait = random.choice(["Stoic", "Wild", "Brilliant"])
        print(f"🌟 EVOLUTION! {self.name} is now a {self.evolution_stage}!")
        self.journal.append(f"Evolved into a {self.evolution_stage}.")
        self.save_game()


if __name__ == "__main__":
    nebula = SuperPet("Nebula")

    while nebula.is_alive:
        nebula.update_vitals()
        print(
            f"Hunger: {nebula.hunger:.1f} | Energy: {nebula.energy:.1f} | Happiness: {nebula.happiness:.1f}"
        )
        cmd = input("Type 'wait' or 'quit': ").lower()

        if cmd == "quit":
            nebula.save_game()
            break

        time.sleep(5)

    if not nebula.is_alive:
        print(f"RIP {nebula.name}.")
        if os.path.exists(nebula.filename):
            os.remove(nebula.filename)
