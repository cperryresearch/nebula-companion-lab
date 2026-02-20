"""
nebula_memory.py — Nebula Zenith Sanctuary
Manages a rolling summary of past conversations so Nebula remembers things
the steward has told her. Memory is persisted in nebula_memory.json and
injected into her system prompt each turn.
"""

import json
import os
import logging
from typing import Optional

logger = logging.getLogger("nebula")

MEMORY_FILE = "nebula_memory.json"

# How many recent exchanges to keep in full before we summarise
RECENT_TURNS_TO_KEEP = 6

# Hard cap on how many summary bullets we retain (keeps token cost low)
MAX_MEMORY_BULLETS = 12

# We only attempt a summarisation call when the full-history window overflows
SUMMARISE_AFTER_TURNS = 20


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def _empty_memory() -> dict:
    return {
        "schema_version": 1,
        "summary_bullets": [],  # list[str] — compact facts about the steward
        "total_turns": 0,  # running count of user turns ever sent
        "last_summarised_at_turn": 0,
    }


def load_memory() -> dict:
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception as e:
            logger.error("nebula_memory load failed: %s", repr(e))
    return _empty_memory()


def save_memory(mem: dict):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(mem, f, indent=2)
    except Exception as e:
        logger.error("nebula_memory save failed: %s", repr(e))


# ---------------------------------------------------------------------------
# Memory block for prompt injection
# ---------------------------------------------------------------------------


def build_memory_block(mem: dict) -> str:
    """
    Returns a compact string to embed in Nebula's system prompt.
    Empty string if there's nothing worth injecting.
    """
    bullets = mem.get("summary_bullets", [])
    if not bullets:
        return ""

    lines = ["Things you remember about your steward:"]
    for b in bullets[-MAX_MEMORY_BULLETS:]:
        lines.append(f"- {b}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Summarisation (called from app.py after every N turns)
# ---------------------------------------------------------------------------


def maybe_summarise(client, chat_history: list, mem: dict) -> dict:
    """
    If enough new turns have accumulated since the last summary, call the LLM
    to extract new memory bullets and merge them in.

    Returns the (possibly updated) memory dict. Caller is responsible for saving.
    """
    total = mem.get("total_turns", 0)
    last = mem.get("last_summarised_at_turn", 0)

    if (total - last) < SUMMARISE_AFTER_TURNS:
        return mem  # not time yet

    # Build a plain-text transcript of recent history to summarise
    transcript_lines = []
    for m in chat_history[-40:]:
        role = "Steward" if m.get("role") == "user" else "Nebula"
        text = m.get("parts", [{"text": ""}])[0].get("text", "")
        transcript_lines.append(f"{role}: {text}")
    transcript = "\n".join(transcript_lines)

    extraction_prompt = (
        "You are a memory curator for an AI companion called Nebula.\n"
        "Read the conversation transcript below and extract compact facts "
        "about the STEWARD (the human) only — their name if given, "
        "preferences, things they've shared about their life, feelings, or "
        "interests. Write each fact as a single short bullet (≤12 words). "
        "Output ONLY the bullet list, one per line, no numbering, no preamble.\n\n"
        f"TRANSCRIPT:\n{transcript}"
    )

    try:
        from openai import OpenAI  # local import to avoid circular deps

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": extraction_prompt}],
            max_tokens=300,
            temperature=0.3,
        )
        raw = resp.choices[0].message.content or ""
        new_bullets = [
            line.lstrip("•-– ").strip()
            for line in raw.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

        # Merge: keep existing bullets + append new, capped
        existing = mem.get("summary_bullets", [])
        merged = existing + new_bullets
        # Deduplicate loosely (exact string match)
        seen = set()
        deduped = []
        for b in merged:
            key = b.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(b)

        mem["summary_bullets"] = deduped[-MAX_MEMORY_BULLETS:]
        mem["last_summarised_at_turn"] = total
        logger.info(
            "Memory summarised: %d bullets retained.", len(mem["summary_bullets"])
        )

    except Exception as e:
        logger.error("Memory summarisation failed: %s", repr(e))

    return mem


def increment_turn_count(mem: dict) -> dict:
    mem["total_turns"] = mem.get("total_turns", 0) + 1
    return mem
