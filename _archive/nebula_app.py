import flet as ft
import requests
import datetime

# --- CORE CONFIGURATION ---
# Ensure this matches your active ngrok window exactly!
API_URL = "https://glucosidal-peggy-submissively.ngrok-free.dev"

def get_cosmic_bg():
    hour = datetime.datetime.now().hour
    if 6 <= hour < 10: return "#4a3b61" # Morning
    if 10 <= hour < 17: return "#1a152a" # Day
    if 17 <= hour < 21: return "#2c1e4a" # Evening
    return "#0b0812" # Night

def main(page: ft.Page):
    # 1. Framework Identity [cite: 2026-02-13]
    page.title = "Nebula Zenith - v11.9.11"
    page.bgcolor = get_cosmic_bg()
    page.window_width = 450
    page.window_height = 850
    page.padding = 20
    page.theme_mode = ft.ThemeMode.DARK

    # 2. Atomic HUD (Fixed Stat Bars) [cite: 2026-02-13]
    hunger_bar = ft.ProgressBar(value=0.7, color="#ff4d4d", bgcolor="#331a1a", height=8)
    happy_bar = ft.ProgressBar(value=0.9, color="#4dff4d", bgcolor="#1a331a", height=8)
    energy_bar = ft.ProgressBar(value=0.8, color="#4d4dff", bgcolor="#1a1a33", height=8)
    xp_text = ft.Text("0 XP", color="#da70d6", weight=ft.FontWeight.BOLD)

    hud = ft.Container(
        content=ft.Column([
            ft.Row([ft.Text("NEBULA STATUS", weight=ft.FontWeight.BOLD), xp_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Icon("restaurant", size=14), hunger_bar], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Icon("favorite", size=14), happy_bar], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Icon("bolt", size=14), energy_bar], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ], spacing=5),
        padding=15, bgcolor="#1a152a", border_radius=15, border=ft.border.all(1, "#332a4d")
    )

    # 3. Evolution Tier Avatar
    nebula_avatar = ft.Image(
        src="images/baby.png",
        width=280, height=280, 
        fit=ft.ImageFit.CONTAIN
    )

    # 4. Resonance Journal (Chat History) [cite: 2026-02-13]
    chat_log = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def sync_ui(data):
        xp = data.get("xp", 0)
        hunger_bar.value = data.get("hunger", 7.0) / 10.0
        happy_bar.value = data.get("happiness", 9.0) / 10.0
        energy_bar.value = data.get("energy", 8.0) / 10.0
        xp_text.value = f"{int(xp)} XP"
        
        # Evolution Tiering [cite: 2026-02-13]
        if xp >= 1500: nebula_avatar.src = "images/adult.png"
        elif xp >= 500: nebula_avatar.src = "images/teen.png"
        else: nebula_avatar.src = "images/baby.png"
        page.update()

    def signal_nebula(e):
        txt = user_input.value
        if not txt: return
        
        chat_log.controls.append(
            ft.Container(
                content=ft.Text(txt, color="#ffffff"),
                bgcolor="#2c1e4a", padding=12, border_radius=12,
                alignment=ft.alignment.center_right, margin=ft.margin.only(left=40, bottom=10)
            )
        )
        user_input.value = ""
        page.update()

        try:
            r = requests.post(f"{API_URL}/chat", json={"user_input": txt})
            if r.status_code == 200:
                data = r.json()
                reply = data.get("reply", "...")
                
                chat_log.controls.append(
                    ft.Row([
                        ft.Icon("auto_awesome", color="#da70d6"),
                        ft.Container(
                            content=ft.Text(reply, color="#d1c4e9"),
                            bgcolor="#1a152a", padding=12, border_radius=12,
                            margin=ft.margin.only(right=40, bottom=10)
                        )
                    ])
                )
                # Fetch status update after chat
                s_res = requests.get(f"{API_URL}/status")
                if s_res.status_code == 200:
                    sync_ui(s_res.json())
        except Exception as ex:
            chat_log.controls.append(ft.Text(f"Neural link severed: {ex}", color="red"))
        page.update()

    # 5. Input Controls
    user_input = ft.TextField(
        hint_text="Signal Nebula...", 
        expand=True, 
        on_submit=signal_nebula,
        bgcolor="#1a152a",
        border_color="#332a4d",
        color="#ffffff"
    )
    
    send_btn = ft.IconButton(
        icon="send", 
        icon_color="#da70d6", 
        on_click=signal_nebula
    )

    # 6. Assembly
    page.add(
        hud,
        ft.Container(content=nebula_avatar, alignment=ft.alignment.center, padding=20),
        chat_log,
        ft.Row([user_input, send_btn])
    )
    
    # Initial Sync
    try:
        init_res = requests.get(f"{API_URL}/status")
        if init_res.status_code == 200:
            sync_ui(init_res.json())
    except:
        pass

# Force Native Window Rendering
ft.app(target=main)