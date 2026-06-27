# 🎚️ Mashup Maker

A small Flask web app that blends **two songs** into a mashup. Upload two audio
files, trim them, balance the volume (including per-section automation), and
**sync their tempos** so the beats line up.

This covers:

- **Phase 1** — upload, trim, overall + part-based volume control, fades, and
  overlaying the two tracks at chosen positions.
- **Phase 2** — automatic BPM detection and pitch-preserving time-stretching so
  the two songs can be tempo-matched before they're layered.

## Features

| Capability | How |
| --- | --- |
| Select / upload two tracks | MP3, WAV, OGG, FLAC, M4A, AAC |
| Trim each track | start / end (seconds) |
| Volume per track | overall gain in dB |
| Volume *throughout* the song | automation lines: `start-end: gain_dB` |
| Fades | fade in / fade out (seconds) |
| Placement | offset each track in the final mix |
| Tempo sync | detect BPM of both, time-stretch to match |
| Output | MP3 / WAV / OGG, playable in-browser + download |

## Project layout

```
mashup_app/
├── app.py              # Flask routes (web plumbing only)
├── mashup/
│   ├── __init__.py
│   └── audio.py        # all audio processing (testable without Flask)
├── templates/          # base / index / result pages
├── static/style.css
├── test_audio.py       # synthetic-audio test suite (no real files needed)
└── requirements.txt
```

## Setup

```bash
cd mashup_app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**ffmpeg** is required (pydub uses it to read/write MP3). Either install it with
your OS package manager (`apt install ffmpeg`, `brew install ffmpeg`, …) or rely
on the bundled `imageio-ffmpeg` binary — `mashup/audio.py` auto-detects it when
no system ffmpeg is on `PATH`.

## Run

```bash
python app.py
# open http://localhost:5000
```

## Test

```bash
python test_audio.py          # or: python -m pytest test_audio.py
```

The tests generate synthetic percussive tracks at known tempos, so they verify
BPM detection, time-stretching, volume automation and the full mashup pipeline
without needing any audio files committed to the repo.

## Volume automation syntax

In the "Volume automation" box for a track, one rule per line:

```
0-15:  -6      # quiet the first 15 seconds by 6 dB
30-45:  3      # boost 30s–45s by 3 dB
60-:  -120     # mute from 60s to the end (open-ended)
```

## How tempo sync works

1. `librosa.beat.beat_track` estimates each track's BPM.
2. The chosen target tempo is decided (match A, match B, or a fixed BPM).
3. `librosa.effects.time_stretch` (phase vocoder) stretches the track(s) to the
   target **without changing pitch**.
4. Both tracks are normalised to a common sample rate / channel count and
   overlaid on a silent canvas, then exported.

## Notes & next steps (Phase 3 ideas)

- Time-stretch uses a phase vocoder; for the best audio quality swap in
  `pyrubberband` (wraps the Rubber Band library) in `audio.time_stretch`.
- Key detection + pitch-matching for harmonically compatible mashups.
- A waveform editor (e.g. WaveSurfer.js) for drag-to-select trim/volume regions.
- Background job queue so long files don't block the web request.
