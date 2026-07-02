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
├── run-mac.sh          # one-command setup + start on macOS
├── test_audio.py       # synthetic-audio test suite (no real files needed)
└── requirements.txt
```

## Quick start on a Mac (recommended)

```bash
git clone https://github.com/danshorstein/100daysofpython.git
cd 100daysofpython/mashup_app
./run-mac.sh
```

That's it. The script creates a virtualenv, installs everything (including
ffmpeg via Homebrew if available), starts the server, and prints the URLs —
including the one to open **on your phone** (same WiFi), e.g.
`http://your-mac.local:5000`. Add it to your phone's home screen for an
app-like icon.

Extras:

```bash
./run-mac.sh --install-autostart   # start automatically at login, keep alive
./run-mac.sh --remove-autostart    # undo
brew install rubberband            # optional: studio-quality time-stretch
                                   # (re-run ./run-mac.sh to enable)
```

To use it away from home, install [Tailscale](https://tailscale.com) (free) on
the Mac and your phone — the same URL then works from anywhere, privately.

> **A note on sharing:** this app is designed to be *run locally by each
> person* rather than hosted publicly. Point friends at this repo and the
> quick-start above. Everyone works with their own audio files on their own
> machine — use songs you own or have rights to.

## Manual setup (any OS)

```bash
cd mashup_app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
# open http://localhost:5000
```

**ffmpeg** is required (pydub uses it to read/write MP3). Either install it with
your OS package manager (`apt install ffmpeg`, `brew install ffmpeg`, …) or rely
on the bundled `imageio-ffmpeg` binary — `mashup/audio.py` auto-detects it when
no system ffmpeg is on `PATH`.

**Time-stretch quality:** if the `rubberband` CLI and `pyrubberband` are
installed, the app automatically uses Rubber Band (noticeably cleaner); it
falls back to librosa's phase vocoder otherwise.

## Test

```bash
python test_audio.py          # or: python -m pytest test_audio.py
```

The tests generate synthetic percussive tracks at known tempos, so they verify
BPM detection, time-stretching, volume automation and the full mashup pipeline
without needing any audio files committed to the repo.

## Hosting it publicly (optional)

Running locally on your own Mac (above) is the recommended setup. But the app
is a normal responsive web page, so it can also be hosted in the cloud if you
ever want a public instance. **Vercel is not suitable** — it's for
serverless/static sites, and this app needs a long-running Python server plus
ffmpeg and the large librosa/numba stack. Use a container host instead.

### Render (recommended, free tier)

A `Dockerfile` and `render.yaml` are included, so:

1. Push this repo to GitHub.
2. Go to <https://render.com> → **New → Blueprint** → select this repo.
3. Render reads `mashup_app/render.yaml`, builds the image (ffmpeg included)
   and deploys.
4. Open the `https://<name>.onrender.com` URL on your phone — add it to your
   home screen for an app-like icon.

The free instance sleeps after ~15 min idle (first request then takes ~30s to
wake). Upgrade to a paid instance to keep it always-on.

### Anywhere with Docker (Railway, Fly.io, a VPS)

```bash
cd mashup_app
docker build -t mashup-maker .
docker run -p 8000:8000 mashup-maker
# open http://localhost:8000  (or the host's public URL)
```

The container runs `gunicorn` with a 300s timeout so long songs don't get cut
off mid-processing.

> **Note:** uploaded files and generated mashups live on the container's
> ephemeral disk. That's fine for personal use (each mashup is produced on the
> fly), but files won't survive a restart. Add a persistent disk / object
> storage if you need them to stick around.

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
3. The track(s) are time-stretched to the target **without changing pitch** —
   via Rubber Band when installed, else librosa's phase vocoder.
4. Both tracks are normalised to a common sample rate / channel count and
   overlaid on a silent canvas, then exported.

## Notes & next steps (Phase 3 ideas)

- Key detection + pitch-matching for harmonically compatible mashups.
- A waveform editor (e.g. WaveSurfer.js) for drag-to-select trim/volume regions.
- Background job queue so long files don't block the web request.
