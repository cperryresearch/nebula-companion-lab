import os
from PIL import Image, ImageDraw

# 1. Create the images folder if it doesn't exist
if not os.path.exists("images"):
    os.makedirs("images")
    print("Created 'images' folder!")

def create_nebula_orb(filename, color, style="awake"):
    """Draws a celestial orb and saves it to the images folder."""
    size = (400, 400) # High-res
    img = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw the main glow
    margin = 40
    draw.ellipse([margin, margin, size[0]-margin, size[1]-margin], fill=color, outline="white", width=5)
    
    # Add Celestial Eyes
    eye_y = 160
    if style == "awake":
        draw.ellipse([140, eye_y, 170, eye_y+30], fill="white") # Left
        draw.ellipse([230, eye_y, 260, eye_y+30], fill="white") # Right
    else:
        # Sleeping eyes (peaceful curves)
        draw.arc([140, eye_y, 170, eye_y+20], 0, 180, fill="white", width=4)
        draw.arc([230, eye_y, 260, eye_y+20], 0, 180, fill="white", width=4)

    # Add a Smile
    draw.arc([170, 220, 230, 260], 0, 180, fill="white", width=4)
    
    save_path = os.path.join("images", filename)
    img.save(save_path)
    print(f"Successfully created: {save_path}")

# 2. Forge the Wardrobe
create_nebula_orb("baby.png", (200, 180, 255, 255))      # Sweet Light Violet
create_nebula_orb("teen.png", (140, 110, 255, 255))      # Hyper Deep Indigo
create_nebula_orb("adult.png", (90, 20, 160, 255))       # Brilliant Celestial Purple
create_nebula_orb("sleeping.png", (70, 70, 90, 255), "sleep") # Deep Sleep Grey-Blue

print("\n✨ Nebula's wardrobe is ready, Cazz! You can now delete this script.")