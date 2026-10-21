# -*- coding: utf-8 -*-
"""
World 02 · 16-Bit 像素横版大闯关 (build_world_02.py)
Master Pipeline:
1. Simulates 28.0s (840 frames) physics & TAS sequence -> produces frames_state & audio_events.
2. Synthesizes 48kHz stereo Chiptune music & Foley SFX -> world_02_pixel.wav.
3. Renders full 1920x1080 @ 30fps video using render_video_parallel (num_workers=2) -> world_02_pixel.mp4.
4. Generates 6-beat inspection contact sheet (20 thumbnails, 5x4 grid) -> contact_sheet_02.png.
"""

import os
import sys
import numpy as np

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(CUR_DIR))
for _p in (CUR_DIR, REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from sim_02_pixel import simulate_world_02, TOTAL_FRAMES, FPS, DURATION
from level_02_pixel import render_frame_from_state
from audio_02_pixel import render_world_02_audio
from corelib.pipeline import render_video_parallel, generate_contact_sheet

# Global states cache for worker factory
_GLOBAL_STATES = None

def get_cached_states():
    global _GLOBAL_STATES
    if _GLOBAL_STATES is None:
        print("[Build World 02] Running deterministic simulation pass...")
        states, _ = simulate_world_02()
        _GLOBAL_STATES = states
    return _GLOBAL_STATES


def worker_factory():
    """Factory for multi-worker parallel renderer."""
    states = get_cached_states()

    def render_frame_at_t(t: float) -> np.ndarray:
        frame_idx = min(len(states) - 1, max(0, int(round(t * float(FPS)))))
        state = states[frame_idx]
        img = render_frame_from_state(state)
        return np.array(img, dtype=np.uint8)

    return render_frame_at_t


def main():
    print("=================================================================")
    print("  World 02 · 16-Bit 像素横版大闯关 (28.0s) Master Build Pipeline")
    print("=================================================================")

    # 1. Run simulation pass
    states, audio_events = simulate_world_02()
    print(f"-> Simulation complete: {len(states)} frames, {len(audio_events)} audio events.")

    # 2. Synthesize audio
    wav_path = os.path.join(CUR_DIR, "world_02_pixel.wav")
    render_world_02_audio(audio_events, wav_path)
    print(f"-> Audio export verified: {wav_path} ({os.path.getsize(wav_path) / 1024:.1f} KB)")

    # 3. Generate Contact Sheet across all 6 Beats (20 key moments, 5x4 grid)
    contact_sheet_path = os.path.join(CUR_DIR, "contact_sheet_02.png")
    timestamps = [
        0.4,    # Beat 1: Phosphor particles assembling into pipe
        1.2,    # Beat 1: Slime pops out of pipe (zero leftover green dots above pipe!)
        2.4,    # Beat 1: Slime landed at (86, 144), turns head back left to look at pipe
        3.5,    # Beat 1: Slime looks UP-right at leading Star ✦
        5.0,    # Beat 2: Parabolic attack leap toward Ladybug, Star leading ahead
        5.4,    # Beat 2: Exact stomp on Ladybug back (x=315, foot_y=132) +100
        6.65,   # Beat 2: Springboard compression (x=420, foot_y=139)
        7.5,    # Beat 2: High arc over Spike Pit, Star leading ahead
        9.20,   # Beat 3: Leading Star ✦ visibly diving INTO the Gold [?] Block (804, 26)!
        9.8,    # Beat 3: Slime failed jump to reach [?] Block
        11.5,   # Beat 3: Slime looks DOWN discovering Hidden Block twinkle [!] at (728, 108)
        12.53,  # Beat 3: Apex head strike on Hidden Block (y=112) -> Cloud Ladder grows
        14.1,   # Beat 4: Climbing Cloud Ladder (exact cloud top surface contact)
        16.07,  # Beat 4: Head-butting [?] Block on Brick Wall Top (796, 64), Star bursts out!
        17.3,   # Beat 4: Parabolic invincible leap off Brick Wall Top (796, 64) to ground
        19.4,   # Beat 5: Vaulting off Moving Cloud (1035, 124) & ramming Cloud Monster #2
        21.3,   # Beat 5: Continuous Super Jump grabbing Flagpole peak (1357, 78) +5000
        23.8,   # Beat 6: Hopping on ground (1412, 144) to absorb 16-Bit Arcade Coin
        26.08,  # Beat 6: Pitch-black void cutscene — Slime diving into bottom purple-laser portal
        27.0,   # Beat 6: Pitch-black void cutscene — Glowing Cyber Data Cubes overflowing upward!
    ]

    print("-> Generating 6-beat inspection contact sheet...")
    render_fn = worker_factory()
    generate_contact_sheet(
        render_frame_fn=render_fn,
        timestamps=timestamps,
        output_png=contact_sheet_path,
        cols=4,
        thumb_w=480,
        pix_fmt_in="rgb24",
    )
    print(f"-> Contact sheet saved: {contact_sheet_path}")

    # 4. Render final video with num_workers=2
    mp4_path = os.path.join(CUR_DIR, "world_02_pixel.mp4")
    print(f"-> Starting parallel video render (num_workers=2, crf=17)...")
    render_video_parallel(
        worker_factory_fn=worker_factory,
        output_mp4=mp4_path,
        duration=DURATION,
        fps=FPS,
        width=1920,
        height=1080,
        audio_path=wav_path,
        num_workers=2,
        pix_fmt_in="rgb24",
        crf=17,
        preset="fast",
    )
    print(f"-> Video render complete: {mp4_path} ({os.path.getsize(mp4_path) / 1024 / 1024:.2f} MB)")
    print("=================================================================")
    print("  World 02 All Deliverables Generated Successfully!")
    print("=================================================================")


if __name__ == "__main__":
    main()
