"""Flask web app for the two-song mashup tool.

Workflow
--------
1.  Upload two audio files (or reuse ones already uploaded this session).
2.  For each track set trim points, volume, fades and part-based volume
    automation; choose where it sits in the final mix.
3.  Optionally tempo-sync the two songs (Phase 2).
4.  Get a playable / downloadable mashup plus the detected BPMs.

Heavy lifting lives in the :mod:`mashup` package; this file is just plumbing.
"""

from __future__ import annotations

import os
import uuid

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from mashup import TrackSpec, VolumeSegment, build_mashup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
ALLOWED_EXTENSIONS = {"mp3", "wav", "ogg", "flac", "m4a", "aac"}
MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 64 MB per request

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.secret_key = os.environ.get("MASHUP_SECRET_KEY", "dev-mashup-key")


# ---------------------------------------------------------------------------
# Small parsing helpers (form fields are all strings)
# ---------------------------------------------------------------------------
def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _f(name: str, default: float = 0.0) -> float:
    raw = request.form.get(name, "").strip()
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _seconds_to_ms(name: str, default=None):
    raw = request.form.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(float(raw) * 1000)
    except (TypeError, ValueError):
        return default


def _parse_volume_segments(prefix: str) -> list[VolumeSegment]:
    """Parse a textarea of ``start-end:gain`` lines (seconds, dB).

    Example::

        0-15: -6
        30-45: 3
        60-: -120     # mute from 60s to the end
    """
    raw = request.form.get(prefix, "").strip()
    segments: list[VolumeSegment] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        span, gain = line.split(":", 1)
        try:
            gain_db = float(gain.strip())
        except ValueError:
            continue
        span = span.strip()
        if "-" not in span:
            continue
        start_s, _, end_s = span.partition("-")
        try:
            start_ms = int(float(start_s) * 1000)
        except ValueError:
            continue
        end_ms = None
        if end_s.strip():
            try:
                end_ms = int(float(end_s) * 1000)
            except ValueError:
                end_ms = None
        segments.append(VolumeSegment(start_ms, end_ms, gain_db))
    return segments


def _save_upload(field: str) -> str | None:
    """Save an uploaded file and return its stored path, or ``None``."""
    file = request.files.get(field)
    if not file or not file.filename:
        return None
    if not _allowed(file.filename):
        flash(f"Unsupported file type for {field}: {file.filename}")
        return None
    name = secure_filename(file.filename)
    stored = f"{uuid.uuid4().hex}_{name}"
    path = os.path.join(UPLOAD_DIR, stored)
    file.save(path)
    return path


def _track_from_form(letter: str) -> TrackSpec | None:
    path = _save_upload(f"file_{letter}")
    if path is None:
        return None
    return TrackSpec(
        path=path,
        start_ms=_seconds_to_ms(f"start_{letter}", 0) or 0,
        end_ms=_seconds_to_ms(f"end_{letter}", None),
        gain_db=_f(f"gain_{letter}", 0.0),
        offset_ms=_seconds_to_ms(f"offset_{letter}", 0) or 0,
        fade_in_ms=_seconds_to_ms(f"fadein_{letter}", 0) or 0,
        fade_out_ms=_seconds_to_ms(f"fadeout_{letter}", 0) or 0,
        volume_segments=_parse_volume_segments(f"volseg_{letter}"),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/mashup", methods=["POST"])
def make_mashup():
    track_a = _track_from_form("a")
    track_b = _track_from_form("b")
    if track_a is None or track_b is None:
        flash("Please provide two audio files.")
        return redirect(url_for("index"))

    sync = request.form.get("sync") == "on"
    tempo_target = request.form.get("tempo_target", "match_a")
    output_format = request.form.get("output_format", "mp3")
    if output_format not in ALLOWED_EXTENSIONS:
        output_format = "mp3"

    out_name = f"mashup_{uuid.uuid4().hex}.{output_format}"
    out_path = os.path.join(OUTPUT_DIR, out_name)

    try:
        result = build_mashup(
            track_a,
            track_b,
            out_path,
            sync=sync,
            tempo_target=tempo_target,
            output_format=output_format,
        )
    except Exception as exc:  # surface processing errors to the user
        flash(f"Could not build mashup: {exc}")
        return redirect(url_for("index"))

    return render_template(
        "result.html",
        filename=out_name,
        bpm_a=round(result.bpm_a, 1),
        bpm_b=round(result.bpm_b, 1),
        applied_bpm=round(result.applied_bpm, 1) if result.applied_bpm else None,
        duration_s=round(result.duration_ms / 1000, 1),
        synced=sync,
    )


@app.route("/outputs/<path:filename>")
def serve_output(filename: str):
    return send_from_directory(OUTPUT_DIR, filename)


@app.route("/download/<path:filename>")
def download_output(filename: str):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("MASHUP_DEBUG") == "1",
    )
