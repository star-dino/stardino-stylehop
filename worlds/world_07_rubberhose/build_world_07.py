# -*- coding: utf-8 -*-
"""
World 07 · 1930s 复古橡皮管爵士乐园 (build_world_07.py)
Orchestrates 26.0s 6-act simulation, 48kHz Big Band Swing audio synthesis,
20-frame contact sheet generation, and 2-worker parallel video rendering.

Outputs:
- world_07_rubberhose.mp4 (1920x1080 @ 30fps with 48kHz stereo Big Band audio)
- contact_sheet_07.png (20 keyframe thumbnails of the full 6-act journey)
"""

import os
import sys
import time

DIR_PATH = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(DIR_PATH))
for _p in (REPO_ROOT, DIR_PATH):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from corelib.pipeline import render_video_parallel, generate_contact_sheet
from sim_07_rubberhose import run_simulation
from level_07_rubberhose import render_frame_from_state
from audio_07_rubberhose import render_audio


MP4_PATH = os.path.join(DIR_PATH, "world_07_rubberhose.mp4")
WAV_PATH = os.path.join(DIR_PATH, "world_07_rubberhose.wav")
CONTACT_PATH = os.path.join(DIR_PATH, "contact_sheet_07.png")

# Global simulation cache
_SIM_STATES = None

def get_sim_states():
    global _SIM_STATES
    if _SIM_STATES is None:
        _SIM_STATES, _ = run_simulation()
    return _SIM_STATES

def worker_factory():
    """Worker factory for render_video_parallel and contact sheet."""
    states = get_sim_states()
    def render_frame_fn(t: float):
        frame_idx = int(round(t * 30.0))
        frame_idx = max(0, min(len(states) - 1, frame_idx))
        return render_frame_from_state(states[frame_idx])
    return render_frame_fn

def main():
    t0 = time.perf_counter()
    print("==================================================================")
    print(" World 07 · 1930s 复古橡皮管爵士乐园 (world_07_rubberhose) 26.0s Build Pipeline")
    print("==================================================================")

    # 1. Run simulation pass
    print(">> Step 1: Running 780-frame simulation pass...")
    states, events = run_simulation()
    global _SIM_STATES
    _SIM_STATES = states
    print(f"   Simulation complete: {len(states)} frames, {len(events)} audio events.")

    # 2. Synthesize audio
    print(">> Step 2: Synthesizing 48kHz stereo Big Band Swing audio...")
    render_audio(events, WAV_PATH, duration_s=26.0)
    print(f"   Audio complete -> {WAV_PATH} ({os.path.getsize(WAV_PATH) / 1024 / 1024:.2f} MB)")

    # 3. Generate Contact Sheet (20 keyframes across all 6 acts)
    print(">> Step 3: Generating 20-frame Contact Sheet...")
    timestamps = [
        0.8,   # Beat 1: Countdown "1" / Stage lights
        2.0,   # Beat 1: 132 BPM swing bounce, shoe tap, crank turn
        4.0,   # Beat 2: Boss deep inhale #1, chest puffed, horn pursed
        4.4,   # Beat 2: Boss spit blast #1: Note Critter 1 flying out of horn mouth!
        5.5,   # Beat 2: Boss spit blast #2: Note Critter 2 flying out!
        6.7,   # Beat 2: Boss spit blast #3: 3 Note Critters advancing!
        7.0,   # Beat 2: Slime screech brake leaning back looking down, pop '?'
        7.5,   # Beat 2: Note Critters kicking rubber-hose legs and marching towards slime!
        8.2,   # Beat 2: Slime sharp eyes, pop '!', deep squash charge
        10.2,  # Beat 3: Stomp 1 on Note Critter 1, splat pancake + ColorRing #1 blooms!
        12.0,  # Beat 3: Stomp 2 on Note Critter 2, ColorRing #2 blooms!
        13.9,  # Beat 3: Stomp 3 on Lead Critter, ColorRing #3 blooms full Technicolor!
        15.5,  # Beat 4: Slime leaps up and absorbs Token into body in mid-air
        17.0,  # Beat 4: Boss extreme rage shaking fists, slime on piano keys locked on Boss
        18.2,  # Beat 4: Rocket launch stretch streaking toward Boss horn forehead
        18.6,  # Beat 4: Direct Headbutt CLANG! Comic starburst on Boss horn forehead!
        20.0,  # Beat 5: Slime lands back squarely on wavy piano keys (foot_y=672, zero float!)
        21.5,  # Beat 5: Boss stunned: recoil wobble, X X spiral eyes, spinning stars, reverse vortex
        22.2,  # Beat 5: Reverse vacuum vortex: Guiding Star ✦ sucked into horn depths!
        23.6,  # Beat 6: Slime leaps from keys and dives into Boss horn mouth!
    ]
    render_fn = worker_factory()
    generate_contact_sheet(
        render_fn,
        timestamps,
        CONTACT_PATH,
        cols=4,
        thumb_w=480,
        aspect=(16, 9),
        pix_fmt_in="bgra"
    )
    print(f"   Saved contact sheet -> {CONTACT_PATH}")

    # 4. Render Video via 2-worker parallel pipeline (strict num_workers=2)
    print(">> Step 4: Parallel video rendering with num_workers=2...")
    render_video_parallel(
        worker_factory_fn=worker_factory,
        output_mp4=MP4_PATH,
        duration=26.0,
        fps=30,
        width=1920,
        height=1080,
        audio_path=WAV_PATH,
        num_workers=2,
        pix_fmt_in="bgra",
        crf=18,
        preset="fast"
    )

    t_total = time.perf_counter() - t0
    print("==================================================================")
    print(f" BUILD COMPLETE in {t_total:.1f}s!")
    print(f" Output Video: {MP4_PATH} ({os.path.getsize(MP4_PATH) / 1024 / 1024:.2f} MB)")
    print(f" Contact Sheet: {CONTACT_PATH}")
    print("==================================================================")

if __name__ == "__main__":
    main()
