import time
import random
import json
import os

class SuperPet:
    def __init__(self, name):
        self.name = name
        self.filename = f"{self.name.lower()}_data.json"
        
        # Stats & Rebalanced Limits
        self.hunger, self.happiness, self.energy = 10.0, 10.0, 10.0
        self.xp, self.level = 0, 1
        self.is_alive = True
        self.max_inventory = 8
        
        # Evolution & Personality
        self.base_trait = random.choice(["Chill", "Hyper", "Sweet"])
        self.temp_trait = None
        self.temp_trait_expiry = 0
        self.evolution_stage = "Baby"
        
        # Internal Memory & Social Core
        self.chat_history = [] # Universal Memory Slot for Web/Mobile
        
        # Starting Inventory
        self.inventory = ["Apple", "Apple", "Berry", "Berry", "Coffee"]
        self.journal = [f"{self.name} was born as a {self.base_trait} {self.evolution_stage}."]
        
        self.load_game()
        self.last_update = time.time()

    def save_game(self):
        """Saves current state and internal memory to JSON."""
        data = {
            "hunger": self.hunger, "happiness": self.happiness, "energy": self.energy,
            "xp": self.xp, "level": self.level, "base_trait": self.base_trait,
            "evolution_stage": self.evolution_stage, "inventory": self.inventory, 
            "journal": self.journal, "chat_history": self.chat_history
        }
        with open(self.filename, 'w') as f:
            json.dump(data, f)

    def load_game(self):
        """Restores state and memory from JSON."""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    data = json.load(f)
                    self.hunger, self.happiness, self.energy = data["hunger"], data["happiness"], data["energy"]
                    self.xp, self.level = data["xp"], data["level"]
                    self.base_trait, self.evolution_stage = data["base_trait"], data["evolution_stage"]
                    self.inventory, self.journal = data["inventory"], data["journal"]
                    self.chat_history = data.get("chat_history", []) # Restore memory
                print(f"📂 {self.name} loaded. Welcome back!")
            except:
                print(f"⚠️ Load failed. Starting fresh.")

    def update_vitals(self):
        """Reduced decay logic for easier survival."""
        now = time.time()
        elapsed = now - self.last_update
        trait = self.get_current_trait()

        # Decay modifiers
        h_mod = 1.3 if trait == "Sugar Rush" else 0.5 if trait == "Deep Sleep" else 1.0
        e_mod = 0.5 if trait == "Caffeinated" else -1.5 if trait == "Deep Sleep" else 1.2 if trait == "Hyper" else 1.0
        
        self.hunger -= elapsed * 0.05 * h_mod
        self.energy -= elapsed * 0.04 * e_mod
        self.happiness -= elapsed * 0.03
        
        self.last_update = now
        if self.hunger <= 0: self.is_alive = False
        
        # SLOWER EVOLUTION: Increased XP thresholds
        if self.xp >= 150 and self.level == 1: self.evolve("Teen")
        elif self.xp >= 400 and self.level == 2: self.evolve("Adult")

    def get_current_trait(self):
        if self.temp_trait and time.time() < self.temp_trait_expiry:
            return self.temp_trait
        return self.base_trait

    def evolve(self, stage):
        self.level += 1
        self.evolution_stage = stage
        self.base_trait = random.choice(["Stoic", "Wild", "Brilliant"])
        print(f"\n🌟 EVOLUTION! {self.name} is now a {self.evolution_stage}!")
        self.journal.append(f"Evolved into a {self.evolution_stage}.")
        self.save_game()

    def play(self):
        """Full game names for clarity."""
        print("\nChoose a Game:")
        print("1. Rock-Paper-Scissors")
        print("2. Number Pulse")
        print("3. Word Scramble")
        choice = input("Choice: ")
        if choice == "1": self.rps_game()
        elif choice == "2": self.number_pulse()
        elif choice == "3": self.word_scramble()

    def rps_game(self):
        choices = ["Rock", "Paper", "Scissors"]
        pc = random.choice(choices)
        user = input("Choose Rock, Paper, or Scissors: ").title()
        if user in choices:
            print(f"You: {user} | {self.name}: {pc}")
            if user == pc: 
                print("🏁 It's a DRAW!")
                self.xp += 10
            elif (user == "Rock" and pc == "Scissors") or (user == "Paper" and pc == "Rock") or (user == "Scissors" and pc == "Paper"):
                print("🏆 YOU WIN!"); self.xp += 25; self.happiness = min(10, self.happiness + 2)
            else:
                print("💀 YOU LOSE!"); self.xp += 15; self.happiness = min(10, self.happiness + 1)
            self.save_game()
        else: print("Invalid move.")

    def word_scramble(self):
        words = ["nebula", "python", "energy", "galaxy", "digital", "logic"]
        secret = random.choice(words)
        scrambled = "".join(random.sample(secret, len(secret)))
        print(f"--- Scramble: {scrambled} ---")
        if input("Guess: ").lower() == secret:
            print("🏆 Correct!"); self.xp += 40; self.happiness = min(10, self.happiness + 4)
        else: print(f"❌ No, it was {secret}."); self.xp += 10
        self.save_game()

    def number_pulse(self):
        num = random.randint(1, 10)
        success = False
        print(f"\n--- {self.name} is sending a Number Pulse (1-10)... ---")
        for i in range(3):
            try:
                guess = int(input(f"Try {i+1}/3 - Pulse Guess: "))
                if guess == num:
                    print("🏆 SUCCESS! You caught the pulse!"); self.xp += 30; self.happiness = min(10, self.happiness + 3)
                    success = True
                    self.save_game(); return
                print("Higher..." if guess < num else "Lower...")
            except: print("Numbers only!")
        
        if not success:
            print(f"❌ The pulse faded. The correct number was {num}.")
            self.xp += 10; self.save_game()

    def shop(self):
        print(f"\n--- XP SHOP (Balance: {self.xp} XP) ---")
        items = {"Apple": 20, "Berry": 20, "Coffee": 40, "Magic Cookie": 60}
        for item, price in items.items():
            print(f"- {item}: {price} XP")
        
        choice = input("What to buy? (Name or 'exit'): ").title()
        if choice in items:
            if self.xp >= items[choice] and len(self.inventory) < self.max_inventory:
                self.xp -= items[choice]; self.inventory.append(choice)
                print(f"✅ Bought {choice}!"); self.save_game()
            else: print("❌ Check your balance or bag space!")
        elif choice == "Exit": return

    def scavenge(self):
        if len(self.inventory) >= self.max_inventory:
            print("🎒 Bag is full!")
            return
        print(f"🔍 {self.name} is scouting...")
        self.energy -= 1; time.sleep(1)
        if random.random() < 0.7:
            found = random.choice(["Apple", "Berry"])
            self.inventory.append(found); print(f"🎁 Found a {found}!"); self.save_game()
        else: print("💨 Found nothing.")

    def status_report(self):
        self.update_vitals()
        trait = self.get_current_trait()
        face = " ( ^ _ ^ ) " if self.happiness > 7 else " ( ' _ ' ) "
        if self.hunger < 3: face = " ( > o < ) "
        print("\n" + "="*40)
        print(f"{face}  {self.name} | Lvl {self.level} {self.evolution_stage}")
        print(f"Trait: {trait} | XP/Bank: {self.xp}")
        for l, v in [("HUNGER", self.hunger), ("HAPPINESS", self.happiness), ("ENERGY", self.energy)]:
            print(f" {l:9}: [{'#' * int(max(0, v))}{'-' * (10-int(max(0, v)))}]")
        print(f" Bag ({len(self.inventory)}/{self.max_inventory}): {self.inventory}")
        print("="*40)

# =================================================================
# THE SAFETY GATE: Everything below only runs in the Terminal
# =================================================================
if __name__ == "__main__":
    nebula = SuperPet("Nebula")
    while nebula.is_alive:
        nebula.status_report()
        cmd = input("\nAction (feed/play/nap/scavenge/shop/wait/quit): ").lower()
        
        if cmd == "feed":
            item = input(f"Feed what? {nebula.inventory}: ").title()
            if item in nebula.inventory:
                nebula.inventory.remove(item)
                if item == "Magic Cookie": 
                    nebula.temp_trait = "Sugar Rush"; nebula.temp_trait_expiry = time.time() + 30
                nebula.hunger = min(10, nebula.hunger + 5); nebula.save_game()
        elif cmd == "play": nebula.play()
        elif cmd == "nap":
            print("💤 Nebula settled down for a deep sleep...")
            nebula.temp_trait, nebula.temp_trait_expiry = "Deep Sleep", time.time() + 60
        elif cmd == "scavenge": nebula.scavenge()
        elif cmd == "shop": nebula.shop()
        elif cmd == "quit": nebula.save_game(); break
        elif cmd == "wait":
            if random.random() < 0.2 and len(nebula.inventory) < nebula.max_inventory:
                nebula.inventory.append("Apple"); nebula.save_game()

    if not nebula.is_alive:
        print(f"\nRIP {nebula.name}. Legacy: {nebula.xp} XP.")
        if os.path.exists(nebula.filename): os.remove(nebula.filename)
