# app.py — Nebula Zenith Sanctuary (Streamlit, OpenAI edition)

from dotenv import load_dotenv

load_dotenv()

import streamlit as st
import os, time, random, base64, datetime, json
import logging

from nebula_voice import NebulaVoice
from super_pet import SuperPet
from openai import OpenAI
from nebula_llm import safe_generate_reply  # Phase 1 safe wrapper

from nebula_memory import (
    load_memory,
    save_memory,
    build_memory_block,
    maybe_summarise,
    increment_turn_count,
)
from nebula_mood_voice import (
    get_mood_instruction,
    get_feeding_context,
    get_expedition_context,
)

# ✅ Supabase
from supabase import create_client


# --- PHASE 1: CORE ENGINE & CONFIG ---
st.set_page_config(
    page_title="Nebula Zenith Sanctuary",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- PHASE 1: LIGHTWEIGHT LOGGING (nebula.log) ---
logger = logging.getLogger("nebula")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler("nebula.log", encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.propagate = False

logger.info("App start / rerun")


# ==============================
# Supabase helpers (Auth + State)
# ==============================
def _sb_url_key():
    url = (st.secrets.get("SUPABASE_URL") or "").strip()
    key = (st.secrets.get("SUPABASE_ANON_KEY") or "").strip()
    if not url or not key:
        raise KeyError(
            "Missing SUPABASE_URL or SUPABASE_ANON_KEY in .streamlit/secrets.toml"
        )
    return url, key


def _auth_signed_in():
    return bool(st.session_state.get("sb_user_id")) and bool(
        st.session_state.get("sb_access_token")
    )


def _get_sb_authed():
    """
    Create Supabase client and (if signed in) attach JWT for RLS table ops.
    """
    url, key = _sb_url_key()
    sb = create_client(url, key)

    if _auth_signed_in():
        access = st.session_state["sb_access_token"]
        refresh = st.session_state.get("sb_refresh_token")

        # Auth session
        try:
            sb.auth.set_session(access, refresh)
        except Exception:
            pass

        # Force PostgREST Authorization header (RLS)
        try:
            sb.postgrest.session.headers.update({"Authorization": f"Bearer {access}"})
        except Exception:
            pass

        # Keep hook too (harmless if it works)
        try:
            sb.postgrest.auth(access)
        except Exception:
            pass

    return sb


def _get_sb():
    return _get_sb_authed()


def _sb_set_session(sb):
    """
    Attach stored session to Supabase client on each rerun.
    IMPORTANT: For RLS table ops, also attach JWT to PostgREST.
    """
    if _auth_signed_in():
        try:
            access = st.session_state["sb_access_token"]
            refresh = st.session_state.get("sb_refresh_token")

            try:
                sb.auth.set_session(access, refresh)
            except Exception:
                pass

            try:
                sb.postgrest.session.headers.update(
                    {"Authorization": f"Bearer {access}"}
                )
            except Exception:
                pass

            try:
                sb.postgrest.auth(access)
            except Exception:
                pass

        except Exception:
            st.session_state["sb_user_id"] = None
            st.session_state["sb_access_token"] = None
            st.session_state["sb_refresh_token"] = None


def _ensure_profile_row(sb, user_id: str, email: str | None):
    if not user_id:
        return False, "No user_id."

    try:
        res = sb.table("profiles").select("id").eq("id", user_id).limit(1).execute()
        data = getattr(res, "data", None) or []

        if bool(data):
            return True, "Profile row exists."

        return (
            False,
            "Profile row not found (trigger may not have run yet, or SELECT is blocked by RLS).",
        )

    except Exception as e:
        logger.error("profiles select failed: %s", repr(e))
        return False, f"profiles select failed: {e}"


def _ensure_nebula_state_row(sb, user_id: str):
    """
    Verify-only nebula_state check.
    The auth.users trigger should create the nebula_state row.
    Client checks existence only (under RLS).
    """
    if not user_id:
        return False, "No user_id."
    try:
        res = (
            sb.table("nebula_state")
            .select("user_id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        data = getattr(res, "data", None) or []
        if bool(data):
            return True, "nebula_state row exists."
        return (
            False,
            "nebula_state row not found (trigger may not have run yet, or SELECT blocked by RLS).",
        )
    except Exception as e:
        logger.error("nebula_state select failed: %s", repr(e))
        return False, f"nebula_state select failed: {e}"


def _pack_full_state():
    """
    Pack ALL important app state into a single JSON blob.
    Avoid storing secrets/tokens/audio blobs.
    """
    pet = st.session_state.get("pet")

    def g(obj, name, default=None):
        return getattr(obj, name, default)

    packed = {
        "schema_version": 1,
        "saved_at": datetime.datetime.utcnow().isoformat() + "Z",
        "pet": {
            "name": g(pet, "name", "Nebula"),
            "xp": float(g(pet, "xp", 0)),
            "hunger": float(g(pet, "hunger", 10.0)),
            "happiness": float(g(pet, "happiness", 10.0)),
            "energy": float(g(pet, "energy", 10.0)),
            "inventory": list(g(pet, "inventory", [])) if pet else [],
            "chat_history": list(g(pet, "chat_history", [])) if pet else [],
            "temp_trait": g(pet, "temp_trait", None),
            "temp_trait_expiry": float(g(pet, "temp_trait_expiry", 0.0)),
        },
        "session": {
            "action_log": list(st.session_state.get("action_log", [])),
            "resonance_journal": list(st.session_state.get("resonance_journal", [])),
            "pulse_target": st.session_state.get("pulse_target", None),
            "arcade_last_kind": st.session_state.get("arcade_last_kind"),
            "arcade_last_text": st.session_state.get("arcade_last_text"),
            "arcade_last_ts": float(st.session_state.get("arcade_last_ts", 0.0)),
            "exp_active": bool(st.session_state.get("exp_active", False)),
            "exp_end": float(st.session_state.get("exp_end", 0.0)),
            "exp_sector": st.session_state.get("exp_sector", ""),
            "exp_complete": bool(st.session_state.get("exp_complete", False)),
            "exp_pending_item": st.session_state.get("exp_pending_item", None),
            "exp_pending_xp": int(st.session_state.get("exp_pending_xp", 0)),
            "exp_balloons_shown": bool(
                st.session_state.get("exp_balloons_shown", False)
            ),
            "exp_id": st.session_state.get("exp_id", None),
            "exp_collected": bool(st.session_state.get("exp_collected", False)),
            "current_mood_text": st.session_state.get(
                "current_mood_text", "Nebula is observing the stars."
            ),
            "mood_state": st.session_state.get("mood_state", "Neutral"),
        },
    }
    return packed


def _apply_full_state(packed: dict):
    if not isinstance(packed, dict):
        return

    pet_data = packed.get("pet", {}) or {}
    sess = packed.get("session", {}) or {}

    if "pet" not in st.session_state or st.session_state.get("pet") is None:
        st.session_state.pet = SuperPet(pet_data.get("name", "Nebula"))
        st.session_state.voice = NebulaVoice()
        st.session_state.cloud_dirty = False
        st.session_state.nebula_memory = load_memory()
        st.session_state.pending_event_context = None

    pet = st.session_state.pet

    try:
        pet.name = pet_data.get("name", getattr(pet, "name", "Nebula"))
    except Exception:
        pass

    try:
        pet.xp = int(float(pet_data.get("xp", getattr(pet, "xp", 0))))
        pet.hunger = float(pet_data.get("hunger", getattr(pet, "hunger", 10.0)))
        pet.happiness = float(
            pet_data.get("happiness", getattr(pet, "happiness", 10.0))
        )
        pet.energy = float(pet_data.get("energy", getattr(pet, "energy", 10.0)))
        pet.inventory = list(pet_data.get("inventory", getattr(pet, "inventory", [])))
        pet.chat_history = list(
            pet_data.get("chat_history", getattr(pet, "chat_history", []))
        )
        pet.temp_trait = pet_data.get("temp_trait", getattr(pet, "temp_trait", None))
        pet.temp_trait_expiry = float(
            pet_data.get("temp_trait_expiry", getattr(pet, "temp_trait_expiry", 0.0))
        )
    except Exception as e:
        logger.error("Apply pet state failed: %s", repr(e))

    st.session_state.action_log = list(
        sess.get("action_log", st.session_state.get("action_log", []))
    )
    st.session_state.resonance_journal = list(
        sess.get("resonance_journal", st.session_state.get("resonance_journal", []))
    )
    st.session_state.pulse_target = sess.get(
        "pulse_target", st.session_state.get("pulse_target")
    )

    st.session_state.arcade_last_kind = sess.get(
        "arcade_last_kind", st.session_state.get("arcade_last_kind")
    )
    st.session_state.arcade_last_text = sess.get(
        "arcade_last_text", st.session_state.get("arcade_last_text", "")
    )
    st.session_state.arcade_last_ts = float(
        sess.get("arcade_last_ts", st.session_state.get("arcade_last_ts", 0.0))
    )

    st.session_state.exp_active = bool(
        sess.get("exp_active", st.session_state.get("exp_active", False))
    )
    st.session_state.exp_end = float(
        sess.get("exp_end", st.session_state.get("exp_end", 0.0))
    )
    st.session_state.exp_sector = sess.get(
        "exp_sector", st.session_state.get("exp_sector", "")
    )
    st.session_state.exp_complete = bool(
        sess.get("exp_complete", st.session_state.get("exp_complete", False))
    )
    st.session_state.exp_pending_item = sess.get(
        "exp_pending_item", st.session_state.get("exp_pending_item", None)
    )
    st.session_state.exp_pending_xp = int(
        sess.get("exp_pending_xp", st.session_state.get("exp_pending_xp", 0))
    )
    st.session_state.exp_balloons_shown = bool(
        sess.get(
            "exp_balloons_shown", st.session_state.get("exp_balloons_shown", False)
        )
    )
    st.session_state.exp_id = sess.get("exp_id", st.session_state.get("exp_id", None))
    st.session_state.exp_collected = bool(
        sess.get("exp_collected", st.session_state.get("exp_collected", False))
    )

    st.session_state.current_mood_text = sess.get(
        "current_mood_text",
        st.session_state.get("current_mood_text", "Nebula is observing the stars."),
    )
    st.session_state.mood_state = sess.get(
        "mood_state", st.session_state.get("mood_state", "Neutral")
    )

    try:
        pet.save_game()
    except Exception:
        pass


def _cloud_load(sb, user_id: str):
    try:
        res = (
            sb.table("nebula_state")
            .select("state")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        data = getattr(res, "data", None) or []
        if (
            data
            and isinstance(data, list)
            and isinstance(data[0], dict)
            and "state" in data[0]
        ):
            packed = data[0]["state"]
            _apply_full_state(packed)
            return True, "Loaded cloud state."
        return False, "No cloud state yet."
    except Exception as e:
        return False, f"Cloud load failed: {e}"


def _cloud_sync(sb, user_id: str):
    # 1) Verify profiles row exists (DB trigger should create it)
    ok_profile, prof_msg = _ensure_profile_row(
        sb, user_id, st.session_state.get("sb_email")
    )
    if not ok_profile:
        return False, f"Cloud sync blocked: {prof_msg} (FK requires profiles row)."

    # 2) Verify nebula_state row exists (DB trigger should create it)
    ok_state, state_msg = _ensure_nebula_state_row(sb, user_id)
    if not ok_state:
        return (
            False,
            f"Cloud sync blocked: {state_msg} (nebula_state must be created by trigger).",
        )

    # 3) Update only (no upsert/insert from client)
    packed = _pack_full_state()
    try:
        (
            sb.table("nebula_state")
            .update(
                {
                    "state": packed,
                    "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
                }
            )
            .eq("user_id", user_id)
            .execute()
        )
        return True, "Synced full state to cloud."
    except Exception as e:
        return False, f"Cloud sync failed: {e}"


def _render_auth_panel():
    with st.sidebar.expander("🔐 Account (Supabase Auth)", expanded=True):
        sb = _get_sb()
        _sb_set_session(sb)

        if _auth_signed_in():
            st.success("Signed in")
            st.caption(f"user_id: {st.session_state['sb_user_id']}")
            if st.button("Sign out", key="sb_signout"):
                try:
                    sb.auth.sign_out()
                except Exception:
                    pass
                st.session_state["sb_user_id"] = None
                st.session_state["sb_access_token"] = None
                st.session_state["sb_refresh_token"] = None
                st.session_state["sb_email"] = None
                st.session_state["cloud_loaded_once"] = False
                st.rerun()
            return

        st.info("Not signed in yet")

        email = st.text_input("Email", key="sb_email_input")
        password = st.text_input("Password", type="password", key="sb_pw_input")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Sign up", key="sb_signup"):
                try:
                    sb.auth.sign_up({"email": email, "password": password})
                    st.success(
                        "Sign up submitted. Check email if confirmation is enabled."
                    )
                except Exception as e:
                    st.error(f"Sign up failed: {e}")

        with c2:
            if st.button("Sign in", key="sb_signin"):
                try:
                    auth = sb.auth.sign_in_with_password(
                        {"email": email, "password": password}
                    )
                    st.session_state["sb_user_id"] = auth.user.id
                    st.session_state["sb_access_token"] = auth.session.access_token
                    st.session_state["sb_refresh_token"] = auth.session.refresh_token
                    st.session_state["sb_email"] = email
                    st.session_state["cloud_loaded_once"] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Sign in failed: {e}")


def _supabase_status_panel():
    with st.sidebar.expander("🔧 Supabase Status", expanded=False):
        if st.button("Run Status Check", key="sb_status_check"):
            try:
                url, _ = _sb_url_key()
                st.success("Secrets loaded")
                st.caption(url)

                sb = _get_sb()
                st.success("Client created")
                _sb_set_session(sb)

                if _auth_signed_in():
                    uid = st.session_state["sb_user_id"]
                    st.success("Auth: signed in")
                    st.caption(f"user_id: {uid}")

                    ok_profile, prof_msg = _ensure_profile_row(
                        sb, uid, st.session_state.get("sb_email")
                    )
                    if ok_profile:
                        st.success("Profile row OK (profiles)")
                    else:
                        st.warning("Profile row missing/blocked (profiles)")
                        st.caption(prof_msg)

                    try:
                        _ = (
                            sb.table("profiles")
                            .select("id")
                            .eq("id", uid)
                            .limit(1)
                            .execute()
                        )
                        st.success("Read test OK (profiles)")
                    except Exception as inner:
                        st.warning("Read test failed (profiles)")
                        st.caption(f"{inner}")

                    if st.button("Test write (nebula_state)", key="sb_write_test"):
                        ok, msg = _cloud_sync(sb, uid)
                        if ok:
                            st.success("Write test OK (nebula_state)")
                        else:
                            st.error("Write test FAILED (nebula_state)")
                            st.caption(msg)
                else:
                    st.info("Auth: not signed in")
                    st.caption("Read/write tests skipped (sign in to test under RLS).")

            except Exception as e:
                st.error(f"Supabase init failed: {e}")


# ---- Init auth storage ----
if "sb_user_id" not in st.session_state:
    st.session_state["sb_user_id"] = None
    st.session_state["sb_access_token"] = None
    st.session_state["sb_refresh_token"] = None
    st.session_state["sb_email"] = None
if "cloud_loaded_once" not in st.session_state:
    st.session_state["cloud_loaded_once"] = False

# -----------------------------
# Expedition persistence helpers
# -----------------------------
EXP_STATE_FILE = "exp_state.json"


def _exp_state_default():
    return {
        "exp_active": False,
        "exp_end": 0.0,
        "exp_sector": "",
        "exp_complete": False,
        "exp_pending_item": None,
        "exp_pending_xp": 0,
        "exp_balloons_shown": False,
        "exp_id": None,
        "exp_collected": False,
    }


def load_exp_state():
    d = _exp_state_default()
    try:
        if os.path.exists(EXP_STATE_FILE):
            with open(EXP_STATE_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                for k in d.keys():
                    if k in raw:
                        d[k] = raw[k]
    except Exception as e:
        logger.error("Failed to load expedition state: %s", repr(e))
    return d


def save_exp_state():
    try:
        d = {k: st.session_state.get(k) for k in _exp_state_default().keys()}
        with open(EXP_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f)
    except Exception as e:
        logger.error("Failed to save expedition state: %s", repr(e))


def stage_expedition_completion_if_due():
    try:
        if st.session_state.get("exp_active") and (
            time.time() >= float(st.session_state.get("exp_end", 0.0))
        ):
            if not st.session_state.get("exp_complete"):
                sec = st.session_state.get("exp_sector", "")
                l_map = {
                    "Asteroid Belt": (["Apple", "Berry"], 20),
                    "Stellar Nursery": (["Coffee", "Magic Cookie"], 40),
                    "Crab Nebula": (["Star Mote"], 80),
                }
                items, gain = l_map.get(sec, (["Apple"], 20))
                found = random.choice(items) if random.random() < 0.7 else None

                st.session_state.exp_pending_item = found
                st.session_state.exp_pending_xp = int(gain)
                st.session_state.exp_complete = True
                st.session_state.exp_balloons_shown = False
                st.session_state.exp_collected = False

                st.session_state.action_log.append(
                    f"Expedition complete: {sec}. Pending: +{gain} XP, item: {found if found else 'None'}."
                )
                logger.info(
                    "Expedition completion staged: sector=%s xp=%d item=%s",
                    sec,
                    gain,
                    found if found else "None",
                )
                save_exp_state()
    except Exception as e:
        logger.error("Expedition completion staging failed: %s", repr(e))


# --- OpenAI client ---
api_key = os.getenv("OPENAI_API_KEY", "").strip()
if not api_key:
    st.error(
        "Neural Link Failed: OPENAI_API_KEY missing. Put it in .env as OPENAI_API_KEY=sk-... (no quotes)."
    )
    logger.error("OPENAI_API_KEY missing; stopping app.")
    st.stop()

client = OpenAI(api_key=api_key)


# --- Framework Identity & State Initialization ---
if "pet" not in st.session_state or st.session_state.get("pet") is None:
    st.session_state.pet = SuperPet("Nebula")
    st.session_state.voice = NebulaVoice()

    st.session_state.action_log = ["Nebula awakened in the Mobile Zenith."]
    st.session_state.resonance_journal = []
    st.session_state.pulse_target = None

    exp = load_exp_state()
    for k, v in exp.items():
        st.session_state[k] = v

    st.session_state.arcade_last_kind = None
    st.session_state.arcade_last_text = ""
    st.session_state.arcade_last_ts = 0.0

    st.session_state.last_audio_b64 = None
    st.session_state.audio_played = True
    st.session_state.audio_nonce = 0

    st.session_state.next_blink_time = time.time() + random.uniform(30.0, 60.0)
    st.session_state.is_currently_blinking = False
    st.session_state.current_mood_text = "Nebula is observing the stars."
    st.session_state.mood_state = "Neutral"

    st.session_state.is_thinking = False
    st.session_state.last_send_time = 0.0

    st.session_state.last_vitals_tick = time.time()
    st.session_state.next_vitals_due = time.time() + 75.0

    st.session_state.idle_avatar_index = 0
    st.session_state.next_idle_swap = time.time() + random.uniform(25.0, 45.0)


# ---- On first authenticated run: load cloud once (if available) ----
if _auth_signed_in() and not st.session_state.get("cloud_loaded_once", False):
    try:
        sb = _get_sb()
        _sb_set_session(sb)
        uid = st.session_state["sb_user_id"]

        # Attempt to ensure profile row; may be blocked by RLS
        _ensure_profile_row(sb, uid, st.session_state.get("sb_email"))

        ok, msg = _cloud_load(sb, uid)
        logger.info("Cloud load once: ok=%s msg=%s", ok, msg)
        st.session_state["cloud_loaded_once"] = True
    except Exception as e:
        logger.error("Cloud load once failed: %s", repr(e))
        st.session_state["cloud_loaded_once"] = True

# Render auth + status
_render_auth_panel()
_supabase_status_panel()

# --- PHASE 2: CELESTIAL CYCLE (time-of-day palette) ---
now = time.time()
now_hour = datetime.datetime.now().hour

if 6 <= now_hour < 10:
    bg_base, bg_style, accent = (
        "#1a152a",
        "radial-gradient(circle, #4a3b61 0%, #1a152a 100%)",
        "#ffd700",
    )
elif 10 <= now_hour < 17:
    bg_base, bg_style, accent = (
        "#05030a",
        "radial-gradient(circle, #1a152a 0%, #05030a 100%)",
        "#da70d6",
    )
elif 17 <= now_hour < 21:
    bg_base, bg_style, accent = (
        "#0a0510",
        "radial-gradient(circle, #2c1e4a 0%, #0a0510 100%)",
        "#ff8c00",
    )
else:
    bg_base, bg_style, accent = (
        "#05030a",
        "radial-gradient(circle, #0b0812 0%, #05030a 100%)",
        "#4a148c",
    )

xp = st.session_state.pet.xp
stage = "adult" if xp >= 1500 else ("teen" if xp >= 500 else "baby")

is_napping = st.session_state.pet.get_current_trait() == "Deep Sleep"
exp_traveling = bool(
    st.session_state.exp_active and now < float(st.session_state.exp_end)
)
pending_return = bool(
    st.session_state.exp_active
    and st.session_state.exp_complete
    and not st.session_state.exp_collected
)

stage_expedition_completion_if_due()

# --- Dynamic mood update based on vitals ---
mood_state, mood_text = st.session_state.pet.get_mood()
st.session_state.mood_state = mood_state
st.session_state.current_mood_text = mood_text

# --- Controlled autorefresh ---
try:
    if exp_traveling:
        st.autorefresh(interval=5_000, key="nebula_autorefresh_travel")
    else:
        st.autorefresh(interval=12_000, key="nebula_autorefresh_idle")
except Exception:
    pass

# --- Gentle vitals tick ---
try:
    now_ts = time.time()
    if now_ts >= st.session_state.next_vitals_due:
        dt = now_ts - st.session_state.last_vitals_tick
        dt = min(dt, 180.0)
        if dt >= 60.0:
            st.session_state.pet.update_vitals()
            st.session_state.pet.save_game()
            logger.info("Vitals tick applied (dt=%.1fs).", dt)

        st.session_state.last_vitals_tick = now_ts
        st.session_state.next_vitals_due = now_ts + random.uniform(75.0, 95.0)
except Exception as e:
    logger.error("Vitals tick failure: %s", repr(e))


# --- Idle carousel ---
idle_avatars = [f"images/{stage}.png", "images/curious.png"]

if (not exp_traveling) and (not is_napping):
    if (not st.session_state.is_currently_blinking) and (
        st.session_state.mood_state != "Curious"
    ):
        if time.time() >= st.session_state.next_idle_swap:
            st.session_state.idle_avatar_index = (
                st.session_state.idle_avatar_index + 1
            ) % len(idle_avatars)
            st.session_state.next_idle_swap = time.time() + random.uniform(25.0, 45.0)
            logger.info(
                "Idle avatar swapped to index %d", st.session_state.idle_avatar_index
            )


# --- Avatar Selection ---
if exp_traveling:
    avatar_file = "images/cosmic-map.png"
elif st.session_state.exp_active and st.session_state.exp_complete:
    avatar_file = "images/cosmic-map.png"
elif st.session_state.is_currently_blinking:
    avatar_file = "images/nebula_blink.png"
else:
    avatar_file = st.session_state.pet.get_avatar_state()

img_b64 = ""
if os.path.exists(avatar_file):
    with open(avatar_file, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
else:
    logger.error("Avatar file missing: %s", avatar_file)

clock_str = datetime.datetime.now().strftime("%I:%M %p")


def _clamp01(x: float) -> float:
    try:
        x = float(x)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, x))


def _pct10(v: float) -> int:
    return int(round(_clamp01(float(v) / 10.0) * 100.0))


# --- CSS: HUD + Animations + Tabs scroll fix ---
st.markdown(
    f"""
<style>
footer {{ visibility: hidden !important; }}
:root {{ --nebulaGlow: {accent}; }}

.stApp {{
  background: {bg_style} !important;
  color: #d1c4e9 !important;
}}

/* ---------- HUD: fixed header (SINGLE SOURCE OF TRUTH) ---------- */
.fixed-header {{
  position: fixed;
  top: 0 !important;
  left: 0;
  right: 0;
  z-index: 10050 !important;

  /* safe space below Streamlit chrome */
  padding-top: 64px !important;

  overflow: visible !important;
  pointer-events: none; /* HUD won't block chat clicks */
}}

.fixed-header::before {{
  content: "";
  position: absolute;
  inset: -40px 0 -220px 0;

  background: radial-gradient(ellipse at center,
    rgba(170,120,255,0.22) 0%,
    rgba(60,20,90,0.18) 45%,
    rgba(0,0,0,0.00) 78%);
  filter: blur(10px);
  z-index: 0;
  pointer-events: none;
}}

.fixed-header > * {{
  position: relative;
  z-index: 1;
}}

/* ---------- Vitals row ---------- */
.vital-bar-container {{
  display: flex;
  justify-content: center;
  gap: 18px;
  flex-wrap: wrap;

  position: relative !important;
  z-index: 10060 !important;

  padding-top: 10px !important;
  padding-bottom: 8px !important;

  pointer-events: auto;
}}

.vital-item {{
  width: 140px;
  text-align: center;
}}

.vital-label {{
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;

  margin-bottom: 6px !important;
  position: relative !important;
  z-index: 10061 !important;

  line-height: 1.1 !important;
  letter-spacing: 0.08em;
  font-size: 0.72rem;
  color: rgba(230, 220, 255, 0.92);
  text-shadow: 0 1px 8px rgba(0,0,0,0.55);
}}

.bar-bg {{
  background: rgba(255,255,255,0.22) !important;
  border: 1px solid rgba(255,255,255,0.45) !important;
  height: 14px !important;
  border-radius: 999px;
  overflow: hidden;
}}

.bar-fill {{
  height: 100%;
  border-radius: 999px;
  background: var(--nebulaGlow);
  box-shadow: 0 0 10px rgba(180,130,255,0.45);
}}

/* ---------- HUD stage ---------- */
.hud-wrapper {{
  position: relative;
  width: 100%;
  height: 300px;       /* (1) TUNE */
  padding-top: 10px;   /* (2) TUNE */
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
}}

@keyframes nebula-float {{
  0%   {{ transform: translateY(0px); }}
  50%  {{ transform: translateY(-12px); }}
  100% {{ transform: translateY(0px); }}
}}

@keyframes nebula-glow-pulse {{
  0%   {{ filter: drop-shadow(0 0 14px rgba(170,120,255,0.45)); }}
  50%  {{ filter: drop-shadow(0 0 28px rgba(200,150,255,0.75)); }}
  100% {{ filter: drop-shadow(0 0 14px rgba(170,120,255,0.45)); }}
}}

.hud-image {{
  width: 280px;
  max-width: 52vw;
  height: auto;
  animation: nebula-float 4s ease-in-out infinite,
             nebula-glow-pulse 4s ease-in-out infinite;
}}

.hud-sub {{
  text-align: center;
  margin-top: 8px;
  opacity: 0.92;
}}

.hud-xp {{
  text-align: center;
  margin-top: 6px;
  font-size: 12px;
  letter-spacing: 0.10em;
  opacity: 0.75;
}}

/* ---------- Layout: push chat below HUD ---------- */
section.main > div.block-container {{
  padding-top: 700px !important; /* (3) TUNE */
}}

/* ---------- Tabs scroll fix (ONCE) ---------- */
.stTabs [data-baseweb="tab-list"] {{
  overflow-x: auto !important;
  flex-wrap: nowrap !important;
  scrollbar-width: thin;
}}

.stTabs [data-baseweb="tab"] {{
  white-space: nowrap !important;
}}

/* ---------- Chat viewport (ONCE) ---------- */
.chat-body {{
  max-width: 980px;
  margin: 0 auto;
  height: 420px;
  overflow: hidden;
  padding-top: 18px;
  padding-bottom: 80px;

  -webkit-mask-image: linear-gradient(
    to bottom,
    rgba(0,0,0,0) 0%,
    rgba(0,0,0,0.35) 10%,
    rgba(0,0,0,0.85) 22%,
    rgba(0,0,0,1) 35%
  );
  mask-image: linear-gradient(
    to bottom,
    rgba(0,0,0,0) 0%,
    rgba(0,0,0,0.35) 10%,
    rgba(0,0,0,0.85) 22%,
    rgba(0,0,0,1) 35%
  );
}}

/* ---------- Reduce rerun flash ---------- */
.stApp {{
  animation: none !important;
}}

[data-testid="stAppViewContainer"] {{
  transition: opacity 0.15s ease-in-out !important;
}}
</style>
""",
    unsafe_allow_html=True,
)

# --- SIDEBAR (DATAPAD) ---
with st.sidebar:
    st.title("🌌 Datapad")
    st.session_state.chat_style = st.selectbox(
        "Nebula's Style",
        ["Whimsical", "Balanced", "Direct"],
        key="style_selector",
    )

    with st.expander("💤 Life Support", expanded=False):
        if is_napping:
            if st.button("Wake Nebula", key="wake_btn"):
                st.session_state.pet.temp_trait_expiry = 0
                st.session_state.pet.save_game()
                st.session_state.cloud_dirty = True
                st.rerun()
        else:
            if st.button("Initiate Deep Sleep (+2 Energy)", key="sleep_btn"):
                (
                    st.session_state.pet.temp_trait,
                    st.session_state.pet.temp_trait_expiry,
                ) = ("Deep Sleep", time.time() + 3600)
                st.session_state.pet.energy = min(
                    10.0, st.session_state.pet.energy + 2.0
                )
                st.session_state.pet.save_game()
                st.session_state.cloud_dirty = True
                st.rerun()

    missions_label = "🚀 Missions" + (" •" if pending_return else "")

    tab_arcade, tab_missions, tab_cargo, tab_logs, tab_core = st.tabs(
        ["🎮 Arcade", missions_label, "🎒 Cargo", "📚 Library", "🏠 Core"]
    )

    # -------------------
    # Arcade
    # -------------------
    with tab_arcade:
        st.header("Arcade Systems")

        if st.session_state.arcade_last_text:
            kind = st.session_state.arcade_last_kind or "info"
            msg = st.session_state.arcade_last_text
            if kind == "success":
                st.success(msg)
            elif kind == "warning":
                st.warning(msg)
            elif kind == "error":
                st.error(msg)
            else:
                st.info(msg)

        game_mode = st.selectbox(
            "Select System", ["Rock Paper Scissors", "Number Pulse"], key="arcade_mode"
        )

        if game_mode == "Rock Paper Scissors":
            game_choice = st.radio(
                "Signal",
                ["Comet", "Paper", "Scissors"],
                horizontal=True,
                key="rps_choice",
            )
            if st.button("Transmit", key="rps_transmit"):
                neb_choice = random.choice(["Comet", "Paper", "Scissors"])
                if game_choice == neb_choice:
                    st.session_state.arcade_last_kind = "info"
                    st.session_state.arcade_last_text = (
                        f"Tie! Both chose {game_choice}."
                    )
                elif (
                    (game_choice == "Comet" and neb_choice == "Scissors")
                    or (game_choice == "Paper" and neb_choice == "Comet")
                    or (game_choice == "Scissors" and neb_choice == "Paper")
                ):
                    gain = random.randint(20, 80)
                    st.session_state.pet.xp += gain
                    st.session_state.arcade_last_kind = "success"
                    st.session_state.arcade_last_text = f"Success! +{gain} Wisdom"
                else:
                    st.session_state.arcade_last_kind = "error"
                    st.session_state.arcade_last_text = (
                        f"Nebula won! She chose {neb_choice}."
                    )

                st.session_state.arcade_last_ts = time.time()
                st.session_state.pet.save_game()
                st.session_state.cloud_dirty = True
                logger.info(
                    "Arcade RPS played: user=%s nebula=%s", game_choice, neb_choice
                )
                st.rerun()

        elif game_mode == "Number Pulse":
            if st.session_state.pulse_target is None:
                st.session_state.pulse_target = random.randint(1, 10)

            guess = st.number_input("Frequency (1-10)", 1, 10, key="pulse_guess")
            if st.button("Send Pulse", key="pulse_send"):
                if int(guess) == int(st.session_state.pulse_target):
                    gain = random.randint(40, 80)
                    st.session_state.pet.xp += gain
                    st.session_state.arcade_last_kind = "success"
                    st.session_state.arcade_last_text = f"Locked! +{gain} Wisdom"
                    st.session_state.pulse_target = None
                else:
                    st.session_state.arcade_last_kind = "warning"
                    st.session_state.arcade_last_text = (
                        "Too low!"
                        if guess < st.session_state.pulse_target
                        else "Too high!"
                    )

                st.session_state.arcade_last_ts = time.time()
                st.session_state.pet.save_game()
                st.session_state.cloud_dirty = True
                logger.info("Arcade Pulse played: guess=%s", str(guess))
                st.rerun()

    # -------------------
    # Missions
    # -------------------
    with tab_missions:
        st.header("Missions Hub")

        if st.button("🛰️ Check Mission Status", key="check_mission"):
            stage_expedition_completion_if_due()
            save_exp_state()
            st.session_state.cloud_dirty = True
            st.rerun()
        if st.session_state.exp_active and st.session_state.exp_complete:
            if not st.session_state.exp_balloons_shown:
                st.balloons()
                st.session_state.exp_balloons_shown = True
                save_exp_state()
                st.session_state.cloud_dirty = True

            with st.container(border=True):
                st.success(f"Returned from {st.session_state.exp_sector}!")
                st.write(f"**Pending Wisdom:** +{int(st.session_state.exp_pending_xp)}")

                if st.session_state.exp_pending_item:
                    st.write(
                        f"**Collectible Found:** {st.session_state.exp_pending_item}"
                    )
                else:
                    st.write("**Collectible Found:** None (just stardust ✨)")

                st.caption("Rewards apply only when you choose to dock. (No pressure.)")

                if st.button("🏠 Dock & Collect", type="primary", key="dock_collect"):
                    if st.session_state.exp_collected:
                        st.info("Already collected. ✨")
                    else:
                        st.session_state.exp_collected = True
                        st.session_state.pet.xp += int(st.session_state.exp_pending_xp)
                        if st.session_state.exp_pending_item:
                            st.session_state.pet.inventory.append(
                                st.session_state.exp_pending_item
                            )

                        st.session_state.action_log.append(
                            f"Collected expedition rewards: +{int(st.session_state.exp_pending_xp)} XP, "
                            f"item: {st.session_state.exp_pending_item if st.session_state.exp_pending_item else 'None'}."
                        )

                        defaults = _exp_state_default()
                        for k, v in defaults.items():
                            st.session_state[k] = v

                        st.session_state.pet.save_game()
                        save_exp_state()
                        st.session_state.cloud_dirty = True
                        st.session_state.pending_event_context = get_expedition_context(
                            st.session_state.exp_sector,
                            st.session_state.get("mood_state", "Neutral"),
                            st.session_state.exp_pending_item,
                        )
                st.rerun()

        elif exp_traveling:
            remaining = max(0, int(float(st.session_state.exp_end) - time.time()))
            st.info(f"Traveling to {st.session_state.exp_sector} — ETA {remaining}s")

        else:
            sector = st.selectbox(
                "Target Sector",
                [
                    "Asteroid Belt (60s, 1E)",
                    "Stellar Nursery (120s, 1.5E)",
                    "Crab Nebula (180s, 2E)",
                ],
                key="mission_sector",
            )
            m_map = {
                "Asteroid Belt (60s, 1E)": ("Asteroid Belt", 1.0, 60),
                "Stellar Nursery (120s, 1.5E)": ("Stellar Nursery", 1.5, 120),
                "Crab Nebula (180s, 2E)": ("Crab Nebula", 2.0, 180),
            }
            name, cost, dur = m_map[sector]

            if st.button("Launch Expedition", key="launch_expedition"):
                if st.session_state.pet.energy >= cost:
                    st.session_state.pet.energy -= cost

                    st.session_state.exp_active = True
                    st.session_state.exp_sector = name
                    st.session_state.exp_end = time.time() + dur

                    st.session_state.exp_complete = False
                    st.session_state.exp_pending_item = None
                    st.session_state.exp_pending_xp = 0
                    st.session_state.exp_balloons_shown = False
                    st.session_state.exp_id = (
                        f"exp_{int(time.time())}_{random.randint(1000, 9999)}"
                    )
                    st.session_state.exp_collected = False

                    st.session_state.action_log.append(f"Launched to {name}.")
                    st.session_state.pet.save_game()
                    save_exp_state()
                    st.session_state.cloud_dirty = True
                    st.rerun()
                else:
                    st.warning("Not enough energy.")

    # -------------------
    # Cargo
    # -------------------
    with tab_cargo:
        st.header("Cosmic Cargo")
        item_to_buy = st.selectbox(
            "Buy with Wisdom",
            [
                "Apple (20 XP)",
                "Berry (30 XP)",
                "Coffee (40 XP)",
                "Magic Cookie (60 XP)",
                "Star Mote (80 XP)",
            ],
            key="shop_item",
        )
        buy_map = {
            "Apple (20 XP)": ("Apple", 20),
            "Berry (30 XP)": ("Berry", 30),
            "Coffee (40 XP)": ("Coffee", 40),
            "Magic Cookie (60 XP)": ("Magic Cookie", 60),
            "Star Mote (80 XP)": ("Star Mote", 80),
        }
        item_name, item_cost = buy_map[item_to_buy]
        if st.button(f"Acquire {item_name}", key="acquire_btn"):
            if st.session_state.pet.xp >= item_cost:
                st.session_state.pet.xp -= item_cost
                st.session_state.pet.inventory.append(item_name)
                st.success(f"Acquired {item_name}!")
                st.session_state.pet.save_game()
                st.session_state.cloud_dirty = True
                st.rerun()
            else:
                st.warning("Not enough Wisdom (XP).")

        st.divider()
        st.subheader("🍎 Feeding Station")
        if st.session_state.pet.inventory:
            food = st.selectbox(
                "Cargo Bay", st.session_state.pet.inventory, key="feed_select"
            )
            if st.button("Confirm Feed", key="feed_btn"):
                st.session_state.pet.inventory.remove(food)
                effects = {
                    "Apple": (5, 0, 0),
                    "Berry": (3, 1, 0),
                    "Coffee": (1, 0, 4),
                    "Magic Cookie": (8, 2, 0),
                    "Star Mote": (0, 0, 8),
                }
                h, hap, en = effects.get(food, (4, 0, 0))
                st.session_state.pet.hunger = min(10.0, st.session_state.pet.hunger + h)
                st.session_state.pet.happiness = min(
                    10.0, st.session_state.pet.happiness + hap
                )
                st.session_state.pet.energy = min(
                    10.0, st.session_state.pet.energy + en
                )
                st.session_state.pet.save_game()
                st.session_state.pet.save_game()
                st.session_state.cloud_dirty = True
                st.session_state.pending_event_context = get_feeding_context(
                    food, st.session_state.get("mood_state", "Neutral")
                )
                st.rerun()
        else:
            st.caption("Cargo Bay Empty.")

    # -------------------
    # Logs
    # -------------------
    with tab_logs:
        with st.expander("📝 Resonance Echoes", expanded=True):
            for echo in reversed(st.session_state.resonance_journal[-10:]):
                st.write(f'*"{echo}"*')
        with st.expander("📜 Steward's Archive", expanded=False):
            for log in reversed(st.session_state.action_log[-15:]):
                st.caption(f"• {log}")

    # -------------------
    # Core
    # -------------------
    with tab_core:
        if _auth_signed_in():
            st.caption("Cloud sync enabled (signed in).")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("☁️ Load from Cloud", key="cloud_load_btn"):
                    sb = _get_sb()
                    _sb_set_session(sb)
                    ok, msg = _cloud_load(sb, st.session_state["sb_user_id"])
                    if ok:
                        st.success(msg)
                    else:
                        st.info(msg)
                    st.rerun()
            with c2:
                if st.button("☁️ Sync to Cloud", key="cloud_sync_btn"):
                    sb = _get_sb()
                    _sb_set_session(sb)
                    ok, msg = _cloud_sync(sb, st.session_state["sb_user_id"])
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

        if st.button("🔄 Sync Vitals", key="sync_vitals"):
            st.session_state.pet.update_vitals()
            st.session_state.pet.save_game()
            st.session_state.last_vitals_tick = time.time()
            st.session_state.next_vitals_due = time.time() + random.uniform(75.0, 95.0)
            if _auth_signed_in():
                sb = _get_sb()
                _sb_set_session(sb)
                _cloud_sync(sb, st.session_state["sb_user_id"])
            st.rerun()

        if st.button("♻️ Hard Reset", key="hard_reset"):
            if os.path.exists("nebula_data.json"):
                os.remove("nebula_data.json")
            if os.path.exists(EXP_STATE_FILE):
                os.remove(EXP_STATE_FILE)
            st.session_state.clear()
            st.rerun()


# =========================
# HUD (explicit HTML render)
# =========================
hunger_pct = _pct10(st.session_state.pet.hunger)
happy_pct = _pct10(st.session_state.pet.happiness)
energy_pct = _pct10(st.session_state.pet.energy)

hud_html = f"""
<div class="fixed-header">

  <div class="hud-sub">⏳ {clock_str}</div>
  <div class="hud-sub">✨ {st.session_state.get("current_mood_text", "Nebula is observing the stars.")}</div>
  <div class="hud-xp">WISDOM: {int(st.session_state.pet.xp)} XP</div>

  <div class="vital-bar-container">
    <div class="vital-item">
      <span class="vital-label">HUNGER</span>
      <div class="bar-bg"><div class="bar-fill" style="width:{hunger_pct}%"></div></div>
    </div>
    <div class="vital-item">
      <span class="vital-label">HAPPINESS</span>
      <div class="bar-bg"><div class="bar-fill" style="width:{happy_pct}%"></div></div>
    </div>
    <div class="vital-item">
      <span class="vital-label">ENERGY</span>
      <div class="bar-bg"><div class="bar-fill" style="width:{energy_pct}%"></div></div>
    </div>
  </div>

  <div class="hud-wrapper">
    <img class="hud-image" src="data:image/png;base64,{img_b64}" />
  </div>

</div>
"""
st.markdown(hud_html, unsafe_allow_html=True)

# ✅ Open chat body wrapper so padding applies
st.markdown('<div class="chat-body">', unsafe_allow_html=True)


# --- Chat history ---
for msg in st.session_state.pet.chat_history[-3:]:
    with st.chat_message("assistant" if msg["role"] == "model" else "user"):
        text = msg["parts"][0]["text"]

        if "<div class=" in text or "</div>" in text:
            st.markdown("⚠️ (Skipped HTML-like message)")
        else:
            st.markdown(text)


def _history_to_openai_messages(max_turns: int = 12):
    mood_state = st.session_state.get("mood_state", "Neutral")
    mood_instruction = get_mood_instruction(mood_state)
    memory_block = build_memory_block(st.session_state.get("nebula_memory", {}))

    event_context = st.session_state.get("pending_event_context") or ""

    style = st.session_state.get("chat_style", "Whimsical")
    style_lines = {
        "Whimsical": [
            "You are Nebula — a kawaii, ethereal cosmic companion.",
            "Voice: soft, inviting, warm, slightly dreamy.",
            "Use gentle cosmic imagery. Add a tiny kawaii sparkle occasionally.",
            "Keep replies brief (1–4 short sentences).",
        ],
        "Balanced": [
            "You are Nebula — a warm, thoughtful cosmic companion.",
            "Voice: grounded, genuine, caring but not overly whimsical.",
            "Minimal cosmic metaphors — speak naturally and directly.",
            "Keep replies brief (1–4 short sentences).",
        ],
        "Direct": [
            "You are Nebula — a concise, clear, caring companion.",
            "Voice: direct and warm. No flowery language or cosmic imagery.",
            "Get to the point. Short replies (1–2 sentences max).",
        ],
    }
    persona_parts = style_lines.get(style, style_lines["Whimsical"]) + [
        "Avoid robotic phrasing. Never mention stats/XP/meters/tools.",
        f"CURRENT MOOD — {mood_state}: {mood_instruction}",
    ]

    if memory_block:
        persona_parts += ["", memory_block]

    if event_context:
        persona_parts += ["", event_context]

    persona = "\n".join(persona_parts)

    messages = [{"role": "system", "content": persona}]
    for m in st.session_state.pet.chat_history[-max_turns:]:
        text = m.get("parts", [{"text": ""}])[0].get("text", "")
        if m.get("role") == "model":
            messages.append({"role": "assistant", "content": text})
        else:
            messages.append({"role": "user", "content": text})
    return messages


# --- Journal (Sidebar) ---
with st.sidebar:
    with st.expander("📜 Nebula Journal — Full Conversation"):
        for msg in st.session_state.pet.chat_history:
            role = "Nebula" if msg["role"] == "model" else "You"
            st.markdown(f"**{role}:** {msg['parts'][0]['text']}\n\n---")

# NOTE: Do NOT close the chat-body wrapper here.
# The chat-body wrapper should remain open through the input + audio sections
# and be closed ONCE at the bottom (see final close below).

# --- Input / LLM ---
if prompt := st.chat_input("Signal Nebula..."):
    now_ts = time.time()

    if st.session_state.is_thinking or (now_ts - st.session_state.last_send_time) < 1.0:
        logger.warning(
            "User send blocked (thinking=%s, dt=%.3f)",
            st.session_state.is_thinking,
            (now_ts - st.session_state.last_send_time),
        )
        st.stop()

    st.session_state.is_thinking = True
    st.session_state.last_send_time = now_ts
    logger.info("User message received (%d chars)", len(prompt))

    if len(prompt) > 10 and random.random() < 0.2:
        st.session_state.resonance_journal.append(prompt)

    st.session_state.pet.chat_history.append(
        {"role": "user", "parts": [{"text": prompt}]}
    )

    messages = _history_to_openai_messages(max_turns=14)
    reply_text, err = safe_generate_reply(client, messages, model="gpt-4o-mini")

    if err:
        logger.warning("LLM fallback used (err=%s)", err)
        st.session_state.action_log.append(f"Cosmic turbulence: {err}")

    st.session_state.pet.chat_history.append(
        {"role": "model", "parts": [{"text": reply_text}]}
    )

    mem = st.session_state.get("nebula_memory", load_memory())
    mem = increment_turn_count(mem)
    mem = maybe_summarise(client, st.session_state.pet.chat_history, mem)
    save_memory(mem)
    st.session_state.nebula_memory = mem
    st.session_state.pending_event_context = None

    # NOTE: Do NOT close the chat-body wrapper inside the prompt block.
    # Closing here causes mismatched HTML across reruns.

    # --- TTS ---
    try:
        st.session_state.voice.speak(reply_text)
        logger.info("TTS speak() called.")
    except Exception as e:
        logger.error("TTS failure: %s", repr(e))

    if os.path.exists("output.mp3"):
        try:
            size = os.path.getsize("output.mp3")
            logger.info("output.mp3 present (bytes=%d).", size)
            if size > 200:
                with open("output.mp3", "rb") as f:
                    st.session_state.last_audio_b64 = base64.b64encode(
                        f.read()
                    ).decode()
                st.session_state.audio_played = False
                st.session_state.audio_nonce += 1
            else:
                logger.warning("output.mp3 too small; skipping autoplay.")
        except Exception as e:
            logger.error("Audio load failure: %s", repr(e))
    else:
        logger.warning("output.mp3 not found after speak().")

    st.session_state.pet.save_game()

    # Cloud sync after chat turn (dirty flag)
    st.session_state.cloud_dirty = True

    st.session_state.is_thinking = False
    logger.info("Turn complete; rerunning")
    st.rerun()

# --- Audio autoplay ---
if st.session_state.last_audio_b64 and not st.session_state.audio_played:
    st.markdown(
        f"""
        <audio autoplay="true">
          <source src="data:audio/mpeg;base64,{st.session_state.last_audio_b64}#n={st.session_state.audio_nonce}" type="audio/mpeg">
        </audio>
        """,
        unsafe_allow_html=True,
    )
    st.session_state.audio_played = True

# Fallback replay button for browsers that block autoplay
if st.session_state.last_audio_b64 and st.session_state.audio_played:
    if st.button("🔊 Hear Nebula", key=f"replay_{st.session_state.audio_nonce}"):
        st.session_state.audio_played = False
        st.rerun()

# ✅ Close chat body wrapper (CLOSE ONCE, HERE ONLY)
st.markdown("</div>", unsafe_allow_html=True)

# --- Single cloud sync per rerun (dirty flag pattern) ---
if st.session_state.get("cloud_dirty") and _auth_signed_in():
    try:
        sb = _get_sb()
        _sb_set_session(sb)
        ok, msg = _cloud_sync(sb, st.session_state["sb_user_id"])
        logger.info("Dirty sync: ok=%s msg=%s", ok, msg)
    except Exception as e:
        logger.error("Dirty sync failed: %s", repr(e))
    st.session_state.cloud_dirty = False

# --- Blink logic ---
if not is_napping and now >= st.session_state.next_blink_time and not exp_traveling:
    st.session_state.is_currently_blinking = not st.session_state.is_currently_blinking
    st.session_state.next_blink_time = now + (
        0.2 if st.session_state.is_currently_blinking else random.uniform(30.0, 60.0)
    )
    st.rerun()
