"""Audio mashup toolkit.

Phase 1: trim, volume control (including per-section automation) and overlay.
Phase 2: BPM detection and tempo-syncing time-stretch.
"""

from .audio import (
    AudioClip,
    TrackSpec,
    VolumeSegment,
    detect_bpm,
    build_mashup,
)

__all__ = [
    "AudioClip",
    "TrackSpec",
    "VolumeSegment",
    "detect_bpm",
    "build_mashup",
]
