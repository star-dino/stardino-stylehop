# -*- coding: utf-8 -*-
"""
World 06 · 哥特玫瑰彩窗圣殿 (build_world_06.py)
Parallel PyCairo Build & Render Pipeline for World 06 (26.0s, 1920x1080 @ 30fps).
"""

import os
import sys
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CUR_DIR))
sys.path.insert(0, ROOT_DIR)

from corelib.pipeline import render_video_parallel
from worlds.world_06_stainedglass.sim_06_stainedglass import run_simulation, FPS, DURATION, TOTAL_FRAMES
from worlds.world_06_stainedglass.level_06_stainedglass import render_frame_from_state
from worlds.world_06_stainedglass.audio_06_stainedglass import render_world_06_audio

OUT_WAV = os.path.join(CUR_DIR, "world_06_stainedglass.wav")
OUT_MP4 = os.path.join(CUR_DIR, "world_06_stainedglass.mp4")
OUT_SHEET = os.path.join(CUR_DIR, "contact_sheet_06.png")

# 20 Keyframes covering all 4 Zones & 4 Acts
KEY_TIMESTAMPS = [
    0.25, 0.95, 1.90, 2.80, 3.70,      # Row 1: Zoetrope harden, gallery turn, stomping 3 Floor Rosettes & lighting 3 Lancet Windows
    4.30, 4.95, 6.60, 7.45, 8.10,      # Row 2: Abyss [?], spotting Prism [!], headbutting Crystal Prism & 3-color laser refraction raising steps
    9.10, 10.00, 10.90, 11.80, 13.50,  # Row 3: Climbing 4 Beveled Diamond Steps & first leap pulling Golden Bell Rope
    15.65, 17.50, 18.60, 21.30, 25.10, # Row 4: Full-power headbutt on Giant Bell, concentric shockwaves, Token absorb, 7-Color Bridge & Rose Window Film Reel
]

_GLOBAL_STATES = None


def get_states():
    global _GLOBAL_STATES
    if _GLOBAL_STATES is None:
        _GLOBAL_STATES, _ = run_simulation()
    return _GLOBAL_STATES


def worker_factory():
    states = get_states()

    def render_frame_fn(t: float):
        idx = max(0, min(len(states) - 1, int(round(t * FPS))))
        pil_img = render_frame_from_state(states[idx])
        return np.asarray(pil_img, dtype=np.uint8)

    return render_frame_fn


def build_contact_sheet(states):
    print("[World 06] Rendering 20-keyframe contact sheet...")
    cols, rows = 5, 4
    tw, th = 384, 216
    sheet = Image.new("RGB", (cols * tw, rows * th), (10, 10, 16))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
    except Exception:
        font = ImageFont.load_default()

    for i, ts in enumerate(KEY_TIMESTAMPS):
        f_idx = max(0, min(len(states) - 1, int(round(ts * FPS))))
        img = render_frame_from_state(states[f_idx]).resize((tw, th), Image.Resampling.LANCZOS)
        c = i % cols
        r = i // cols
        x0, y0 = c * tw, r * th
        sheet.paste(img, (x0, y0))
        draw.rectangle([x0 + 6, y0 + 6, x0 + 108, y0 + 28], fill=(8, 9, 14))
        draw.text((x0 + 12, y0 + 9), f"t = {ts:05.2f}s", fill=(255, 224, 115), font=font)
        draw.rectangle([x0, y0, x0 + tw - 1, y0 + th - 1], outline=(245, 158, 11), width=1)

    sheet.save(OUT_SHEET)
    print(f"[World 06] Saved contact sheet: {OUT_SHEET}")


def main():
    t0 = time.time()
    print("=== Building World 06: Gothic Stained-Glass & Crystal Prism Cathedral ===")
    states, _ = run_simulation()
    global _GLOBAL_STATES
    _GLOBAL_STATES = states

    render_world_06_audio(OUT_WAV)
    build_contact_sheet(states)

    render_video_parallel(
        worker_factory_fn=worker_factory,
        output_mp4=OUT_MP4,
        duration=DURATION,
        fps=FPS,
        width=1920,
        height=1080,
        audio_path=OUT_WAV,
        num_workers=6,
        pix_fmt_in="rgb24",
        crf=17,
        preset="fast",
    )
    print(f"=== World 06 Complete in {time.time() - t0:.1f}s -> {OUT_MP4} ===")


if __name__ == "__main__":
    main()
