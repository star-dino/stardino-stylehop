"""Procedural score for the Mechanical Nautilus (Archive / 007) film:
a bathyal harmonic bed (Dm9 -> Bbmaj7 -> Gm9 -> Asus4 at 88 bpm), hydro-jet propulsion pulses,
MHD turbine hum, ballast valve thuds, and operator console clicks read from `timeline.json`.

    python3 run_sfx.py sims/nautilus-shared/score.py
"""

import os

from sfx.score_kit import airy, bed, chords, hz, motor, thud
from sfx.synth import click

TIMELINE = "../nautilus-film/timeline.json"
OUT = os.path.join(os.environ.get("TEARDOWN_OUT", "teardown-out"), "nautilus-score.wav")
TARGET_LUFS = -14.0
SEED = 7007

CHORDS = chords(
    "Dm9:D2 A2 C3 E3 F3/D1",
    "Bbmaj7:Bb1 F2 A2 C3 D3/Bb0",
    "Gm9:G1 D2 F2 A2 Bb2/G0",
    "Asus4:A1 E2 G2 D3 E3/A0",
)
MOTIF = [(0.5, hz("A4")), (1.5, hz("F5")), (2.5, hz("E5")), (3.5, hz("D5"))]


def score(mix, tl):
    dur = tl["duration"]
    b = tl["beats"]
    left, right, low, drums = bed(
        dur,
        88,
        CHORDS,
        MOTIF,
        motif_voice="epiano",
        kicks=(0, 2.0),
        snares=(),
        hats=8,
        swing=0.0,
        keys_vel=0.68,
        keys_lp=3200,
    )
    mix.put_stereo(0, left, right, 0.12)
    mix.put(0, low, 0.13)
    mix.put(0, drums, 0.042)

    # Hydro-jet water discharge whoosh + impeller spool at key sequence beats
    # beat names follow sims/nautilus-film/timeline.json
    for key in ("labels_on", "core_closeup", "septa_closeup", "tentacles_closeup", "jets_closeup", "hero_wide_return"):
        t0 = b[key]
        if t0 + 2.0 < dur:
            mix.put(t0, airy(1.8, 380, 1450, 0.55), 0.032)
            mix.put(t0 + 0.2, motor(1.9, 145, 980, 12), 0.018)

    # Hadal Dive ballast flood thud & Septa X-Ray engagement
    mix.put(b["septa_closeup"], thud(68, 0.06, 0.45), 0.085)

    # Close-up teardowns: a short servo as each subsystem opens
    for key in ("core_teardown_peak", "septa_teardown_peak", "tentacles_teardown_peak", "jets_teardown_peak"):
        mix.put(b[key] - 0.8, motor(1.0, 220, 1100, 13), 0.016)

    # Exploded shell unlatch servo & re-latch thud
    mix.put(b["full_explode_open"], motor(2.4, 180, 1280, 15), 0.024)
    mix.put(b["full_explode_close"], motor(1.8, 210, 960, 14), 0.022)
    mix.put(b["hero_reassembled"], thud(76, 0.05, 0.38), 0.08)

    # Console UI clicks on every timeline beat transition
    for k, t in b.items():
        if t > 0 and not k.endswith("_peak"):
            mix.put(t, click(2350, 0.024), 0.055)
