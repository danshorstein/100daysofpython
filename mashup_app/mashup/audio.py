"""Core audio processing for the mashup app.

Everything here is pure-Python and works on :class:`pydub.AudioSegment`
objects.  The web layer (``app.py``) only ever talks to this module, so the
processing logic can be unit-tested without Flask.

Phase 1  - trimming, overall gain, per-section volume automation, fades, overlay.
Phase 2  - BPM detection (librosa) and pitch-preserving time-stretch so two
           songs can be tempo-synced before they are layered.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
from pydub import AudioSegment

# ---------------------------------------------------------------------------
# Make pydub find an ffmpeg binary.
#
# In many environments ffmpeg is not on PATH.  The ``imageio-ffmpeg`` wheel
# ships a static binary, so fall back to it when the system one is missing.
# ---------------------------------------------------------------------------
def _configure_ffmpeg() -> None:
    from shutil import which

    if which("ffmpeg"):
        return
    try:
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        AudioSegment.converter = exe
        AudioSegment.ffmpeg = exe
        # imageio doesn't ship ffprobe; ffmpeg alone is enough to decode/encode.
        os.environ.setdefault("FFMPEG_BINARY", exe)
    except Exception:  # pragma: no cover - best effort only
        pass


_configure_ffmpeg()

# 16-bit audio is the lingua franca for everything we do.
_SAMPLE_WIDTH_DTYPE = {1: np.int8, 2: np.int16, 4: np.int32}


# ---------------------------------------------------------------------------
# Spec objects (what the UI sends us)
# ---------------------------------------------------------------------------
@dataclass
class VolumeSegment:
    """Apply ``gain_db`` to the region ``[start_ms, end_ms)`` of a track.

    ``end_ms is None`` means "to the end of the track".  Positive dB is louder,
    negative is quieter, ``-120`` is effectively silence.
    """

    start_ms: int
    end_ms: Optional[int]
    gain_db: float


@dataclass
class TrackSpec:
    """How a single source track should be prepared before mixing."""

    path: str
    start_ms: int = 0                       # trim: where the clip begins
    end_ms: Optional[int] = None            # trim: where the clip ends
    gain_db: float = 0.0                    # overall volume offset
    offset_ms: int = 0                      # placement in the final mashup
    fade_in_ms: int = 0
    fade_out_ms: int = 0
    volume_segments: List[VolumeSegment] = field(default_factory=list)


@dataclass
class AudioClip:
    """Thin convenience wrapper around a pydub ``AudioSegment``."""

    segment: AudioSegment

    @classmethod
    def load(cls, path: str) -> "AudioClip":
        return cls(AudioSegment.from_file(path))

    @property
    def duration_ms(self) -> int:
        return len(self.segment)

    def to_mono_float(self) -> tuple[np.ndarray, int]:
        """Return ``(mono_samples_in_[-1,1], sample_rate)`` for analysis."""
        y, sr = segment_to_float(self.segment)
        if y.ndim > 1:
            y = y.mean(axis=0)
        return y.astype(np.float32), sr


# ---------------------------------------------------------------------------
# pydub <-> numpy bridge
# ---------------------------------------------------------------------------
def segment_to_float(seg: AudioSegment) -> tuple[np.ndarray, int]:
    """Convert an ``AudioSegment`` to float32 samples in ``[-1, 1]``.

    Shape is ``(n,)`` for mono and ``(channels, n)`` for multi-channel, which
    is the layout librosa expects.
    """
    samples = np.array(seg.get_array_of_samples()).astype(np.float32)
    peak = float(1 << (8 * seg.sample_width - 1))
    samples /= peak
    if seg.channels > 1:
        samples = samples.reshape((-1, seg.channels)).T
    return samples, seg.frame_rate


def float_to_segment(y: np.ndarray, sr: int, sample_width: int = 2) -> AudioSegment:
    """Inverse of :func:`segment_to_float`."""
    if y.ndim == 1:
        y = y[np.newaxis, :]          # (1, n)
    channels = y.shape[0]
    interleaved = y.T                 # (n, channels)
    interleaved = np.clip(interleaved, -1.0, 1.0)
    peak = float(1 << (8 * sample_width - 1))
    dtype = _SAMPLE_WIDTH_DTYPE[sample_width]
    # scale to int range; (peak - 1) avoids wrap at exactly +1.0
    ints = (interleaved * (peak - 1)).astype(dtype)
    return AudioSegment(
        ints.tobytes(),
        frame_rate=sr,
        sample_width=sample_width,
        channels=channels,
    )


# ---------------------------------------------------------------------------
# Phase 2: tempo analysis & syncing
# ---------------------------------------------------------------------------
def detect_bpm(source) -> float:
    """Estimate tempo in BPM.

    ``source`` may be a file path, an ``AudioSegment`` or an ``AudioClip``.
    """
    import librosa

    if isinstance(source, str):
        clip = AudioClip.load(source)
    elif isinstance(source, AudioClip):
        clip = source
    else:  # AudioSegment
        clip = AudioClip(source)

    y, sr = clip.to_mono_float()
    if y.size == 0:
        return 0.0
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return float(np.atleast_1d(tempo)[0])


def _rubberband_available() -> bool:
    """True when both the ``rubberband`` CLI and pyrubberband are installed.

    Rubber Band produces noticeably cleaner stretches than a phase vocoder.
    On macOS: ``brew install rubberband && pip install pyrubberband``.
    """
    from shutil import which

    if which("rubberband") is None:
        return False
    try:
        import pyrubberband  # noqa: F401
    except ImportError:
        return False
    return True


def time_stretch(seg: AudioSegment, rate: float) -> AudioSegment:
    """Stretch ``seg`` by ``rate`` while preserving pitch.

    ``rate > 1`` makes the audio *faster* (higher tempo, shorter), ``rate < 1``
    makes it slower.  Prefers Rubber Band (studio quality) when installed and
    falls back to librosa's phase vocoder otherwise.
    """
    if rate <= 0:
        raise ValueError("rate must be positive")
    if abs(rate - 1.0) < 1e-3:
        return seg

    y, sr = segment_to_float(seg)

    if _rubberband_available():
        import pyrubberband

        # pyrubberband wants (n,) or (n, channels); we carry (channels, n).
        y_rb = y.T if y.ndim > 1 else y
        stretched = pyrubberband.time_stretch(y_rb, sr, rate)
        stretched = stretched.T if stretched.ndim > 1 else stretched
    else:
        import librosa

        stretched = librosa.effects.time_stretch(y, rate=rate)

    return float_to_segment(stretched, sr, sample_width=seg.sample_width)


def sync_tempo(
    seg: AudioSegment, source_bpm: float, target_bpm: float
) -> AudioSegment:
    """Time-stretch ``seg`` from ``source_bpm`` to ``target_bpm``."""
    if source_bpm <= 0 or target_bpm <= 0:
        return seg
    return time_stretch(seg, rate=target_bpm / source_bpm)


# ---------------------------------------------------------------------------
# Phase 1: editing primitives
# ---------------------------------------------------------------------------
def apply_volume_segments(
    seg: AudioSegment, segments: List[VolumeSegment]
) -> AudioSegment:
    """Apply part-based volume automation.

    Each :class:`VolumeSegment` boosts/cuts a non-overlapping region of the
    track.  Regions not covered by a segment are left untouched.
    """
    if not segments:
        return seg

    ordered = sorted(segments, key=lambda s: s.start_ms)
    out = AudioSegment.empty()
    cursor = 0
    length = len(seg)
    for vs in ordered:
        start = max(0, min(vs.start_ms, length))
        end = length if vs.end_ms is None else min(vs.end_ms, length)
        if start < cursor:           # skip overlaps with an already-applied region
            start = cursor
        if start > cursor:
            out += seg[cursor:start]
        if end > start:
            out += seg[start:end].apply_gain(vs.gain_db)
            cursor = end
    if cursor < length:
        out += seg[cursor:]
    return out


def prepare_track(spec: TrackSpec) -> AudioSegment:
    """Load a source file and apply trim, gain, automation and fades."""
    seg = AudioSegment.from_file(spec.path)

    end = spec.end_ms if spec.end_ms is not None else len(seg)
    seg = seg[spec.start_ms:end]

    if spec.gain_db:
        seg = seg.apply_gain(spec.gain_db)

    seg = apply_volume_segments(seg, spec.volume_segments)

    if spec.fade_in_ms:
        seg = seg.fade_in(min(spec.fade_in_ms, len(seg)))
    if spec.fade_out_ms:
        seg = seg.fade_out(min(spec.fade_out_ms, len(seg)))

    return seg


def _match_format(a: AudioSegment, b: AudioSegment) -> tuple[AudioSegment, AudioSegment]:
    """Force two segments to share frame rate and channel count for mixing."""
    frame_rate = max(a.frame_rate, b.frame_rate)
    channels = max(a.channels, b.channels)
    a = a.set_frame_rate(frame_rate).set_channels(channels)
    b = b.set_frame_rate(frame_rate).set_channels(channels)
    return a, b


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------
@dataclass
class MashupResult:
    output_path: str
    bpm_a: float
    bpm_b: float
    applied_bpm: Optional[float]
    duration_ms: int


def build_mashup(
    track_a: TrackSpec,
    track_b: TrackSpec,
    output_path: str,
    *,
    sync: bool = False,
    tempo_target: str = "match_a",   # "match_a" | "match_b" | a numeric BPM string
    output_format: Optional[str] = None,
) -> MashupResult:
    """Produce a mashup from two source tracks.

    Steps: analyse tempo (always, so the UI can report it) -> prepare each
    track (Phase 1 edits) -> optionally tempo-sync (Phase 2) -> overlay onto a
    common canvas -> export.
    """
    bpm_a = detect_bpm(track_a.path)
    bpm_b = detect_bpm(track_b.path)

    seg_a = prepare_track(track_a)
    seg_b = prepare_track(track_b)

    applied_bpm: Optional[float] = None
    if sync and bpm_a > 0 and bpm_b > 0:
        if tempo_target == "match_a":
            applied_bpm = bpm_a
            seg_b = sync_tempo(seg_b, bpm_b, bpm_a)
        elif tempo_target == "match_b":
            applied_bpm = bpm_b
            seg_a = sync_tempo(seg_a, bpm_a, bpm_b)
        else:
            try:
                target = float(tempo_target)
            except (TypeError, ValueError):
                target = bpm_a
            applied_bpm = target
            seg_a = sync_tempo(seg_a, bpm_a, target)
            seg_b = sync_tempo(seg_b, bpm_b, target)

    seg_a, seg_b = _match_format(seg_a, seg_b)

    total = max(track_a.offset_ms + len(seg_a), track_b.offset_ms + len(seg_b))
    canvas = AudioSegment.silent(duration=total, frame_rate=seg_a.frame_rate)
    canvas = canvas.set_channels(seg_a.channels)
    canvas = canvas.overlay(seg_a, position=track_a.offset_ms)
    canvas = canvas.overlay(seg_b, position=track_b.offset_ms)

    fmt = output_format or os.path.splitext(output_path)[1].lstrip(".") or "mp3"
    canvas.export(output_path, format=fmt)

    return MashupResult(
        output_path=output_path,
        bpm_a=bpm_a,
        bpm_b=bpm_b,
        applied_bpm=applied_bpm,
        duration_ms=len(canvas),
    )
