# Nebula Companion Lab: Technical Framework

## Project Overview
Nebula is a cosmic AI companion application built on a Streamlit-based Python framework. This repository serves as the authoritative source of truth for the Nebula Methods Lab, prioritizing structural integrity and logic preservation.

## Core Foundation and Logic Priority
* **Execution Order**: AI Conversation and Audio Rendering logic are prioritized to execute before Visual Reruns to prevent interface latency or "brain-lag".
* **Audio Protocol**: Implementation utilizes Base64 injection with a mandatory "Hear Nebula" manual gesture fallback for mobile browser stability.
* **Sonic Filter**: Character responses must remain warm and brief. The system is strictly prohibited from mentioning numeric statistics in dialogue.

## Technical Specifications (v11.9.15)
* **Vitals Stability**: Biological stat decay (Hunger, Happiness, Energy) is clamped between 0.0 and 10.0. Stats are strictly locked to manual Sync Vitals triggers or specific user-initiated interactions to prevent drift.
* **Economy Engine**: The "Golden Ratio" economy is set at 20–80 XP per item. All game names (e.g., Rock Paper Scissors, Number Pulse) must be spelled out in full within the code and interface.
* **Visual HUD**: The Atomic HUD uses high-performance CSS to maintain a pinned position for character and vital bars during viewport scrolling.
* **Blink Cadence**: Autonomic blink animations are timed to occur every 30.0 to 60.0 seconds.

## Implementation Status
* **Phase 1 (Celestial Cycle)**: Diurnal background gradients (Dawn, Day, Twilight, Night) and time-aware cosmic thoughts are operational.
* **Phase 2 (Cosmic Cartography)**: Mission Control is active, supporting timed expeditions to the Asteroid Belt, Stellar Nursery, and Crab Nebula.
* **Phase 3 (The Astral Path)**: Evolution tiers are locked based on XP: Baby (0–500), Teen (500–1500), and Adult (1500+).
* **Phase 4 (Resonance Journal)**: The Atomic HUD is fixed to the top of the viewport. The Steward’s Log and "Echoes" recording systems are archived in the sidebar.

## Operational Guidelines
1. Always validate specifications against the current version (v11.9.15) before implementing code changes.
2. Maintain the one-time playback flag for audio to prevent mobile device echoes.
3. Ensure the "Dreaming Glow" CSS Pulse and reactive "Curious" assets are preserved during mood engine updates.
