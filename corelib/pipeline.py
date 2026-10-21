# -*- coding: utf-8 -*-
"""
纯工具类：视频编码管线（单流 / 多核并发分片推流）与质检缩略图（Contact Sheet）生成器。
绝对风格中立：只负责将 (H, W, 4) BGRA 或 (H, W, 3) RGB 帧数据高速推流给 FFmpeg 并合入音频。
"""

import os
import sys
import time
import shutil
import subprocess
import multiprocessing as mp
import numpy as np
from PIL import Image, ImageDraw

from .camera import get_font


def render_video_streaming(
    render_frame_fn,
    output_mp4: str,
    duration: float,
    fps: int = 30,
    width: int = 1920,
    height: int = 1080,
    audio_path: str = None,
    pix_fmt_in: str = "bgra",
    crf: int = 16,
    preset: str = "medium",
):
    """
    单进程流式编码器（最适合含 GPU ModernGL / OpenGL 上下文的渲染器，本身已在 50~150+ fps）。
    render_frame_fn(t: float) -> np.ndarray (uint8, shape=(height, width, 4 or 3)) or bytes.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_mp4)), exist_ok=True)
    total_frames = int(round(duration * fps))

    cmd = [
        "ffmpeg", "-y", "-hide_banner",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", pix_fmt_in,
        "-s", f"{width}x{height}",
        "-r", str(fps),
        "-i", "-",
    ]
    if audio_path and os.path.exists(audio_path):
        cmd.extend(["-i", audio_path, "-map", "0:v:0", "-map", "1:a:0"])
    else:
        cmd.extend(["-map", "0:v:0"])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-level", "4.1",
    ])
    if audio_path and os.path.exists(audio_path):
        cmd.extend(["-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2", "-shortest"])

    cmd.extend(["-movflags", "+faststart", output_mp4])

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    t0 = time.perf_counter()
    try:
        for frame_idx in range(total_frames):
            t = frame_idx / float(fps)
            frame = render_frame_fn(t)
            raw_bytes = frame.tobytes() if isinstance(frame, np.ndarray) else frame
            proc.stdin.write(raw_bytes)

            if (frame_idx + 1) % 150 == 0 or frame_idx == total_frames - 1:
                elapsed = time.perf_counter() - t0
                cur_fps = (frame_idx + 1) / max(elapsed, 1e-6)
                eta = (total_frames - (frame_idx + 1)) / max(cur_fps, 1e-6)
                pct = 100.0 * (frame_idx + 1) / total_frames
                print(
                    f"[{pct:5.1f}%] Frame {frame_idx + 1:4d}/{total_frames} "
                    f"(t={t:6.2f}s) | {cur_fps:5.1f} fps | ETA: {eta:4.1f}s",
                    flush=True,
                )
    finally:
        if proc.stdin:
            proc.stdin.close()

    stderr_bytes = proc.stderr.read() if proc.stderr else b""
    ret = proc.wait()
    if ret != 0:
        print(stderr_bytes.decode("utf-8", errors="replace"), file=sys.stderr)
        raise RuntimeError(f"FFmpeg exited with code {ret}")

    return output_mp4


def _parallel_chunk_worker(args: tuple) -> str:
    """子进程分片渲染 Worker：独立初始化渲染器并直接管道送入 FFmpeg。"""
    (
        chunk_id,
        start_f,
        end_f,
        fps,
        width,
        height,
        pix_fmt_in,
        crf,
        preset,
        chunk_mp4_path,
        worker_factory_fn,
    ) = args

    render_frame_fn = worker_factory_fn()
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", pix_fmt_in,
        "-s", f"{width}x{height}",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-g", str(fps),
        chunk_mp4_path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for f_idx in range(start_f, end_f):
            t = f_idx / float(fps)
            frame = render_frame_fn(t)
            raw_bytes = frame.tobytes() if isinstance(frame, np.ndarray) else frame
            proc.stdin.write(raw_bytes)
    finally:
        if proc.stdin:
            proc.stdin.close()

    stderr_bytes = proc.stderr.read() if proc.stderr else b""
    ret = proc.wait()
    if ret != 0:
        raise RuntimeError(f"Chunk {chunk_id} FFmpeg failed: {stderr_bytes.decode('utf-8', errors='replace')}")
    return chunk_mp4_path


def render_video_parallel(
    worker_factory_fn,
    output_mp4: str,
    duration: float,
    fps: int = 30,
    width: int = 1920,
    height: int = 1080,
    audio_path: str = None,
    num_workers: int = None,
    pix_fmt_in: str = "bgra",
    crf: int = 16,
    preset: str = "fast",
):
    """
    多核多进程分片并行渲染器（零磁盘 PNG I/O 开销，适合 CPU 密集型 PyCairo / PIL 绘图）。
    worker_factory_fn: 无参可调用对象（顶层函数），在每个子进程内调用並返回 `render_frame_fn(t: float)`。
    """
    out_dir = os.path.dirname(os.path.abspath(output_mp4))
    os.makedirs(out_dir, exist_ok=True)
    tmp_dir = os.path.join(out_dir, "_tmp_chunks")
    os.makedirs(tmp_dir, exist_ok=True)

    total_frames = int(round(duration * fps))
    if num_workers is None:
        num_workers = min(8, max(1, mp.cpu_count()))

    chunk_size = (total_frames + num_workers - 1) // num_workers
    tasks = []
    chunk_files = []

    for cid in range(num_workers):
        sf = cid * chunk_size
        ef = min(total_frames, (cid + 1) * chunk_size)
        if sf >= ef:
            break
        c_path = os.path.join(tmp_dir, f"chunk_{cid:03d}.mp4")
        chunk_files.append(c_path)
        tasks.append((cid, sf, ef, fps, width, height, pix_fmt_in, crf, preset, c_path, worker_factory_fn))

    t0 = time.perf_counter()
    print(f"=== Launching {len(tasks)}-Worker Parallel Video Render ({total_frames} frames @ {fps}fps) ===")
    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=len(tasks)) as pool:
        pool.map(_parallel_chunk_worker, tasks)

    concat_list_path = os.path.join(tmp_dir, "concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for cp in chunk_files:
            f.write(f"file '{cp}'\n")

    mux_cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", concat_list_path,
    ]
    if audio_path and os.path.exists(audio_path):
        mux_cmd.extend([
            "-i", audio_path,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
            "-shortest",
        ])
    else:
        mux_cmd.extend(["-c:v", "copy"])

    mux_cmd.extend(["-movflags", "+faststart", output_mp4])
    subprocess.run(mux_cmd, check=True)
    shutil.rmtree(tmp_dir, ignore_errors=True)

    elapsed = time.perf_counter() - t0
    print(f"=== Parallel Render Complete in {elapsed:.1f}s ({total_frames / max(elapsed, 1e-6):.1f} fps) -> {output_mp4} ===")
    return output_mp4


def generate_contact_sheet(
    render_frame_fn,
    timestamps: list[float],
    output_png: str,
    cols: int = 4,
    thumb_w: int = 480,
    aspect: tuple[int, int] = (16, 9),
    pix_fmt_in: str = "bgra",
):
    """
    自动抽取指定时间码列表 `timestamps` 的关键帧并拼接成带秒数角标的网格一览图（Contact Sheet），
    方便主代理或创作者一眼完成全片分镜视觉审阅。
    """
    if not timestamps:
        return None
    os.makedirs(os.path.dirname(os.path.abspath(output_png)), exist_ok=True)
    thumb_h = int(round(thumb_w * aspect[1] / float(aspect[0])))
    rows = (len(timestamps) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (10, 12, 18))
    font = get_font(18)

    for idx, t in enumerate(timestamps):
        arr = render_frame_fn(float(t))
        if pix_fmt_in == "bgra":
            rgb = arr[:, :, [2, 1, 0]].copy()
        else:
            rgb = arr[:, :, :3].copy()
        img = Image.fromarray(rgb, mode="RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(img)
        label = f"t = {t:.2f}s"
        draw.rectangle([8, 8, 122, 34], fill=(0, 0, 0))
        draw.text((14, 11), label, font=font, fill=(255, 220, 120))
        r = idx // cols
        c = idx % cols
        sheet.paste(img, (c * thumb_w, r * thumb_h))

    sheet.save(output_png, quality=92)
    return output_png
