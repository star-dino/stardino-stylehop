# -*- coding: utf-8 -*-
"""
纯几何虚拟摄像机与坐标系变换工具（风格中立 / 零视觉设定）
仅负责：
- 镜头状态数据结构 (cam_x, cam_y, zoom, rot)
- 物理震动偏移计算 (shake)
- 将摄像机变换应用到 PyCairo Context
- 世界坐标 (wx, wy) 与屏幕像素坐标 (sx, sy) 的正逆投影转换
- 字体加载内存缓存（不规定任何具体字号、颜色或排版样式）
"""

import os
import math
from dataclasses import dataclass
from PIL import ImageFont

_FONT_CACHE = {}

# Portable font resolution: STARDINO_FONT_DIR or explicit paths win; otherwise the
# first installed CJK face is used, falling back to Pillow's bitmap font.
_FONT_DIR = os.environ.get("STARDINO_FONT_DIR", "").strip()


def _resolve(filenames, system_paths) -> str:
    cands = []
    if _FONT_DIR:
        cands.extend(os.path.join(_FONT_DIR, n) for n in filenames)
    cands.extend(system_paths)
    for p in cands:
        if p and os.path.exists(p):
            return p
    return ""


DEFAULT_FONT_MED = os.environ.get("STARDINO_FONT_CJK_MED", "").strip() or _resolve(
    ("NotoSansCJKsc-Medium.otf",),
    (
        os.path.join(os.path.expanduser("~"), ".fonts", "NotoSansCJKsc-Medium.otf"),
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Medium.otf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyh.ttc",
    ),
)
DEFAULT_FONT_REG = os.environ.get("STARDINO_FONT_CJK_REG", "").strip() or _resolve(
    ("NotoSansCJKsc-Regular.otf",),
    (
        os.path.join(os.path.expanduser("~"), ".fonts", "NotoSansCJKsc-Regular.otf"),
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyh.ttc",
    ),
)


def get_font(size: int, font_path: str = None) -> ImageFont.FreeTypeFont:
    """带内存缓存的字体加载工具，避免逐帧重复磁盘 I/O。"""
    path = font_path or DEFAULT_FONT_MED
    key = (path, int(size))
    if key not in _FONT_CACHE:
        if path and os.path.exists(path):
            _FONT_CACHE[key] = ImageFont.truetype(path, int(size))
        else:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


@dataclass
class Camera2D:
    """
    通用 2D 虚拟摄像机（以画面中心 (width/2, height/2) 为世界原点 (0,0)）。
    不包含任何特定视觉特效或滤镜，只做纯几何变换。
    """
    x: float = 0.0
    y: float = 0.0
    zoom: float = 1.0
    rot: float = 0.0  # 弧度 (radians)

    def add_impact_shake(
        self,
        dt: float,
        amp_px: float = 20.0,
        decay: float = 7.0,
        rot_amp: float = 0.02,
        freq_x: float = 52.0,
        freq_y: float = 43.0,
    ) -> "Camera2D":
        """在碰撞/爆发后的时间 dt (dt >= 0) 叠加指数衰减的物理震动。"""
        if dt < 0.0:
            return self
        env = math.exp(-dt * decay)
        self.x += env * amp_px * math.sin(dt * freq_x)
        self.y += env * amp_px * math.cos(dt * freq_y)
        self.rot += env * rot_amp * math.sin(dt * 38.0)
        return self

    def apply_to_cairo(self, ctx, screen_w: int, screen_h: int):
        """将当前摄像机矩阵应用到 PyCairo Context（调用前建议 ctx.save()）。"""
        ctx.translate(screen_w * 0.5, screen_h * 0.5)
        ctx.scale(self.zoom, self.zoom)
        if abs(self.rot) > 1e-7:
            ctx.rotate(self.rot)
        ctx.translate(-self.x, -self.y)

    def world_to_screen(self, wx: float, wy: float, screen_w: int, screen_h: int) -> tuple[float, float]:
        """将世界坐标 (wx, wy) 投影为屏幕像素坐标 (sx, sy)。"""
        dx = wx - self.x
        dy = wy - self.y
        cos_r = math.cos(self.rot)
        sin_r = math.sin(self.rot)
        sx = (dx * cos_r - dy * sin_r) * self.zoom + screen_w * 0.5
        sy = (dx * sin_r + dy * cos_r) * self.zoom + screen_h * 0.5
        return sx, sy

    def screen_to_world(self, sx: float, sy: float, screen_w: int, screen_h: int) -> tuple[float, float]:
        """将屏幕像素坐标 (sx, sy) 逆投影回世界坐标 (wx, wy)。"""
        z = max(self.zoom, 1e-6)
        px = (sx - screen_w * 0.5) / z
        py = (sy - screen_h * 0.5) / z
        cos_r = math.cos(-self.rot)
        sin_r = math.sin(-self.rot)
        wx = px * cos_r - py * sin_r + self.x
        wy = px * sin_r + py * cos_r + self.y
        return wx, wy

    def normalized_offset(self, ref_height: float = 1080.0) -> tuple[float, float]:
        """返回供 Shader 使用的归一化相机偏移量。"""
        return (self.x / ref_height, self.y / ref_height)
