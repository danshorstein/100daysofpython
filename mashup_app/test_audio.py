"""Tests for the mashup audio engine.

Run with: ``python -m pytest mashup_app/test_audio.py`` (or ``python test_audio.py``).
Generates synthetic percussive tracks so no real audio files are needed.
"""

import os
import tempfile

import numpy as np
import soundfile as sf

from mashup import TrackSpec, VolumeSegment, build_mashup, detect_bpm
from mashup.audio import (
    apply_volume_segments,
    float_to_segment,
    segment_to_float,
    time_stretch,
)
from pydub import AudioSegment

SR = 22050


def _drum_track(bpm, dur=8.0, base_hz=180.0, seed=0):
    """A percussive click track at a known tempo (detectable by librosa)."""
    rng = np.random.default_rng(seed)
    sig = np.zeros(int(SR * dur), dtype=np.float32)
    period = 60.0 / bpm
    for k in range(int(dur / period) + 1):
        start = int(k * period * SR)
        n = int(0.12 * SR)
        idx = slice(start, min(start + n, len(sig)))
        m = idx.stop - idx.start
        env = np.exp(-np.linspace(0, 8, m))
        tone = np.sin(2 * np.pi * base_hz * np.arange(m) / SR)
        noise = rng.standard_normal(m) * 0.3
        sig[idx] += (tone + noise) * env
    return (sig / np.max(np.abs(sig)) * 0.8).astype(np.float32)


def _write(path, bpm, **kw):
    sf.write(path, _drum_track(bpm, **kw), SR)


def test_roundtrip_float_conversion():
    s = float_to_segment(_drum_track(120), SR)
    y, sr = segment_to_float(s)
    assert sr == SR
    assert y.shape[0] == int(SR * 8)
    assert -1.0 <= y.min() and y.max() <= 1.0


def test_detect_bpm_is_close():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "a.wav")
        _write(p, 120)
        bpm = detect_bpm(p)
        assert 110 <= bpm <= 130, f"expected ~120, got {bpm}"


def test_time_stretch_changes_length():
    seg = float_to_segment(_drum_track(120, dur=4.0), SR)
    faster = time_stretch(seg, rate=2.0)   # twice as fast => ~half length
    assert len(faster) < len(seg)
    assert abs(len(faster) - len(seg) / 2) < 200  # within 200 ms


def test_volume_segments_reduce_loudness():
    seg = float_to_segment(_drum_track(120, dur=4.0), SR)
    quieted = apply_volume_segments(seg, [VolumeSegment(0, 2000, -20)])
    assert len(quieted) == len(seg)
    # first 2 s should be quieter than the original
    assert quieted[:2000].dBFS < seg[:2000].dBFS - 5


def test_build_mashup_end_to_end():
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "a.wav"), os.path.join(d, "b.wav")
        _write(a, 120, base_hz=180, seed=1)
        _write(b, 90, base_hz=120, seed=2)
        out = os.path.join(d, "mash.wav")
        res = build_mashup(
            TrackSpec(path=a, end_ms=4000, volume_segments=[VolumeSegment(0, 1000, -6)]),
            TrackSpec(path=b, gain_db=-3, offset_ms=200, fade_in_ms=300),
            out,
            sync=True,
            tempo_target="match_a",
            output_format="wav",
        )
        assert os.path.exists(out) and os.path.getsize(out) > 0
        assert 110 <= res.bpm_a <= 130
        assert res.applied_bpm == res.bpm_a
        assert res.duration_ms > 0


if __name__ == "__main__":
    import sys
    import traceback

    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception:
            failures += 1
            print(f"FAIL  {fn.__name__}")
            traceback.print_exc()
    sys.exit(1 if failures else 0)
