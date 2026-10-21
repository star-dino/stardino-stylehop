# -*- coding: utf-8 -*-
"""
audio_deps.py — 解析并加载可选的音频上游工具链
(optional audio upstream toolchain resolver)

本仓库的配乐 / 拟音脚本（`worlds/*/audio_*.py`）基于两个 MIT 协议的上游开源项目：

  1. lemo-opuscar   -> 提供 `core.audio.sampler` / `core.audio.pluck` / `core.audio.sfx`
  2. earshot        -> 提供 `earshot.forge.bank` 与 `master`（LLT 母带 / 侧链）

它们不随本仓库分发。使用前通过环境变量指向本地克隆目录：

    export LEMO_OPUSCAR_ROOT=/path/to/lemo-opuscar
    export EARSHOT_ROOT=/path/to/earshot

若未设置，脚本会依次尝试若干常见同级目录；
仍然找不到时，`require_audio_upstream()` 会抛出带修复指引的 RuntimeError，
而不是静默降级成无声轨道。
"""

import os
import sys

# ---------------------------------------------------------------------------
# 环境变量名
# ---------------------------------------------------------------------------
LEMO_ENV = "LEMO_OPUSCAR_ROOT"
EARSHOT_ENV = "EARSHOT_ROOT"


def _looks_like_lemo(root: str) -> bool:
    return bool(root) and os.path.isfile(os.path.join(root, "core", "audio", "sampler.py"))


def _looks_like_earshot(root: str) -> bool:
    return bool(root) and os.path.isfile(os.path.join(root, "earshot", "forge", "bank.py"))


def _search_candidates(env_var: str, looks_like, repo_root: str, extra_names):
    """按优先级返回候选目录：环境变量 > 仓库同级目录 > 常见姊妹目录。"""
    cands = []

    env_val = os.environ.get(env_var, "").strip()
    if env_val:
        cands.append(env_val)

    parent = os.path.dirname(os.path.abspath(repo_root))
    for name in extra_names:
        cands.append(os.path.join(parent, name))
        cands.append(os.path.join(parent, "技能", name))

    seen = set()
    out = []
    for c in cands:
        c = os.path.abspath(os.path.expanduser(c))
        if c in seen:
            continue
        seen.add(c)
        if looks_like(c):
            out.append(c)
    return out


def repo_root() -> str:
    """本文件所在目录即仓库根目录。"""
    return os.path.dirname(os.path.abspath(__file__))


def setup_audio_paths(verbose: bool = False):
    """
    把已找到的上游根目录插入 `sys.path`。

    返回 ``(lemo_root, earshot_root, master_dir)``；任一项未找到时为 ``None``。
    该函数幂等，可重复调用。
    """
    root = repo_root()

    lemo_root = None
    for c in _search_candidates(LEMO_ENV, _looks_like_lemo, root, ("lemo-opuscar",)):
        lemo_root = c
        break

    earshot_root = None
    for c in _search_candidates(EARSHOT_ENV, _looks_like_earshot, root, ("earshot",)):
        earshot_root = c
        break

    master_dir = None
    if earshot_root:
        cand = os.path.join(earshot_root, "skills", "real-sound", "scripts")
        if os.path.isfile(os.path.join(cand, "master.py")):
            master_dir = cand

    for p in (lemo_root, earshot_root, master_dir):
        if p and p not in sys.path:
            sys.path.insert(0, p)

    if verbose:
        print(f"[audio_deps] {LEMO_ENV}      = {lemo_root or '<not found>'}")
        print(f"[audio_deps] {EARSHOT_ENV}  = {earshot_root or '<not found>'}")
        print(f"[audio_deps] master module  = {master_dir or '<not found>'}")

    return lemo_root, earshot_root, master_dir


def require_audio_upstream():
    """
    需要真实合成音频时调用。缺失任一上游时抛出可执行的错误信息。
    """
    lemo_root, earshot_root, master_dir = setup_audio_paths()
    missing = []
    if not lemo_root:
        missing.append(
            f"  - lemo-opuscar (采样乐器 / 物理拨弦 / 拟音原语)\n"
            f"      git clone https://github.com/lemomo-ai/lemo-opuscar\n"
            f"      export {LEMO_ENV}=/abs/path/to/lemo-opuscar"
        )
    if not earshot_root:
        missing.append(
            f"  - earshot (拟合拟音库 / 响度母带)\n"
            f"      export {EARSHOT_ENV}=/abs/path/to/earshot"
        )
    elif not master_dir:
        missing.append(
            f"  - earshot 的 master.py 未找到（期望位于 "
            f"$EARSHOT_ROOT/skills/real-sound/scripts/master.py）"
        )
    if missing:
        raise RuntimeError(
            "音频上游工具链缺失，无法合成音轨。请先安装并设置环境变量：\n"
            + "\n".join(missing)
            + "\n\n（两个上游均为 MIT 协议；本仓库仅调用其 API，不重分发其代码。）"
        )
    return lemo_root, earshot_root, master_dir


if __name__ == "__main__":
    setup_audio_paths(verbose=True)
