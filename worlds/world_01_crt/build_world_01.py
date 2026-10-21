# -*- coding: utf-8 -*-
"""
World 01 · 矩阵终端序章 (build_world_01.py)
Orchestrates simulation, audio synthesis, contact sheet generation,
and 2-worker parallel video rendering.
Outputs:
- world_01_crt.mp4 (1920x1080 @ 30fps with 48kHz audio)
- contact_sheet_01.png (20 keyframe thumbnails)
"""

import os
import sys
import time

DIR_PATH = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(DIR_PATH))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if DIR_PATH not in sys.path:
    sys.path.insert(0, DIR_PATH)

from corelib.pipeline import render_video_parallel, generate_contact_sheet
from sim_01_crt import run_simulation
from level_01_crt import render_frame_from_state
from audio_01_crt import render_audio

MP4_PATH = os.path.join(DIR_PATH, "world_01_crt.mp4")
WAV_PATH = os.path.join(DIR_PATH, "world_01_crt.wav")
CONTACT_PATH = os.path.join(DIR_PATH, "contact_sheet_01.png")

# Global simulation states cache
_SIM_STATES = None

def get_sim_states():
    global _SIM_STATES
    if _SIM_STATES is None:
        _SIM_STATES, _ = run_simulation()
    return _SIM_STATES

def worker_factory():
    """Worker factory for render_video_parallel."""
    states = get_sim_states()
    def render_frame_fn(t: float):
        frame_idx = int(round(t * 30.0))
        frame_idx = max(0, min(len(states) - 1, frame_idx))
        return render_frame_from_state(states[frame_idx])
    return render_frame_fn

def main():
    t0 = time.perf_counter()
    print("==================================================================")
    print(" World 01 · 矩阵终端序章 (world_01_crt) 26.0s Build Pipeline")
    print("==================================================================")

    # 1. Run simulation
    print(">> Step 1: Running 780-frame simulation pass...")
    states, events = run_simulation()
    global _SIM_STATES
    _SIM_STATES = states
    print(f"   Simulation complete: {len(states)} frames, {len(events)} audio events.")

    # 2. Synthesize audio
    print(">> Step 2: Synthesizing 48kHz stereo DSP audio...")
    render_audio(events, WAV_PATH, duration_s=26.0)

    # 3. Generate Contact Sheet (20 representative keyframes)
    print(">> Step 3: Generating 20-frame Contact Sheet...")
    timestamps = [
        0.18, 0.55, 2.5, 3.5, 5.0, 6.4, 7.1, 9.6, 10.6, 12.0,
        13.0, 14.5, 16.8, 17.3, 18.0, 20.5, 21.3, 23.1, 24.2, 25.3
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

    # 4. Render Video via 2-worker parallel pipeline
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
