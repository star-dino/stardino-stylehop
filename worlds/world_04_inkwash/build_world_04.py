#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
World 04 · 水墨宣纸千里长卷 (build_world_04.py)
End-to-end Master Build Pipeline:
  1. Fixed-step 30fps physics simulation & 6-act state machine (sim_04_inkwash.py)
  2. 48kHz stereo procedural Chinese soundtrack & event-driven Foley (audio_04_inkwash.py)
  3. 2-worker parallel video rendering (level_04_inkwash.py + pipeline.render_video_parallel)
  4. 16-frame Contact Sheet inspection sheet (contact_sheet_04.png)
"""

import os
import sys
import time

WORLD_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(WORLD_DIR))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if WORLD_DIR not in sys.path:
    sys.path.insert(0, WORLD_DIR)

from corelib.pipeline import render_video_parallel, generate_contact_sheet

_CACHED_STATES = None


def get_or_create_states():
    global _CACHED_STATES
    if _CACHED_STATES is None:
        from sim_04_inkwash import run_simulation
        _CACHED_STATES, _ = run_simulation()
    return _CACHED_STATES


def inkwash_worker_factory():
    """Worker factory for multi-process rendering (zero disk I/O streaming to FFmpeg)."""
    states = get_or_create_states()
    from level_04_inkwash import render_frame_from_state

    def render_frame_fn(t: float):
        idx = int(round(t * 30.0))
        idx = max(0, min(len(states) - 1, idx))
        return render_frame_from_state(states[idx])

    return render_frame_fn


def main():
    t_start = time.perf_counter()
    print("================================================================================")
    print("  World 04 · 水墨宣纸千里长卷 (world_04_inkwash) 28.0s Master Build Pipeline")
    print("================================================================================")

    # 1. Run simulation
    print("\n>>> Step 1/4: Running 840-frame physics simulation & state machine...")
    from sim_04_inkwash import run_simulation
    states, events = run_simulation()
    print(f"Simulation completed: {len(states)} frames, {len(events)} Foley events.")

    # 2. Synthesize audio
    print("\n>>> Step 2/4: Synthesizing 48kHz stereo traditional Chinese soundtrack & Foley...")
    from audio_04_inkwash import build_world_04_soundtrack
    wav_path = os.path.join(WORLD_DIR, "world_04_inkwash.wav")
    build_world_04_soundtrack(events, wav_path)

    # 3. Parallel video rendering
    print("\n>>> Step 3/4: Rendering 28.0s video with 6 parallel workers (num_workers=6)...")
    mp4_path = os.path.join(WORLD_DIR, "world_04_inkwash.mp4")
    render_video_parallel(
        worker_factory_fn=inkwash_worker_factory,
        output_mp4=mp4_path,
        duration=28.0,
        fps=30,
        width=1920,
        height=1080,
        audio_path=wav_path,
        num_workers=6,
        pix_fmt_in="bgra",
        crf=16,
        preset="fast",
    )

    # 4. Generate Contact Sheet
    print("\n>>> Step 4/4: Generating 20-frame Contact Sheet for visual review...")
    contact_sheet_path = os.path.join(WORLD_DIR, "contact_sheet_04.png")
    timestamps = [
        0.55, 1.85, 2.45, 3.85, 4.80,
        6.10, 7.15, 7.90, 8.80, 9.45,
        11.25, 12.50, 15.30, 16.70, 17.98,
        19.00, 20.30, 21.45, 23.60, 27.10,
    ]
    render_fn = inkwash_worker_factory()
    generate_contact_sheet(
        render_frame_fn=render_fn,
        timestamps=timestamps,
        output_png=contact_sheet_path,
        cols=5,
        thumb_w=480,
        pix_fmt_in="bgra",
    )
    print(f"Contact Sheet saved -> {contact_sheet_path}")

    elapsed = time.perf_counter() - t_start
    print(f"\n================================================================================")
    print(f"  BUILD SUCCESSFUL in {elapsed:.1f}s!")
    print(f"  Video:         {mp4_path}")
    print(f"  Contact Sheet: {contact_sheet_path}")
    print(f"  Soundtrack:    {wav_path}")
    print(f"================================================================================")


if __name__ == "__main__":
    main()
