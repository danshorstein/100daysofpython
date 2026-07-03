/* Mashup Studio — DAW-style editor.
 *
 * All editing happens client-side against decoded audio buffers, with live
 * preview through the Web Audio API. The server is only asked to render the
 * final file (where the studio-quality, pitch-preserving stretch happens).
 *
 * Clip model (times in ms):
 *   trimStart/trimEnd  — cut points in SOURCE time
 *   offset             — clip position on the OUTPUT timeline
 *   gainDb             — lane fader
 *   envelope           — [{t, db}] volume points, t relative to clip start
 *                        in OUTPUT time (i.e. post-stretch, what you see)
 * Processing order everywhere: trim -> stretch -> fader gain -> envelope.
 */

"use strict";

// ------------------------------------------------------------------ state
const WAVE_COLORS = ["#6c8cff", "#00d4a0"];
const ENV_COLOR = "#ffb347";
const DB_TOP = 12;      // envelope value at the top edge of a lane
const DB_BOTTOM = -48;  // ...and at the bottom (treated as near-silence)
const EDGE_PX = 10;     // trim-handle hit zone
const POINT_PX = 12;    // envelope-point hit zone

const state = {
  tracks: [null, null],
  masterDb: 0,
  syncMode: "off",     // off | a | b
  pxPerSec: 40,
  playheadMs: 0,
  transport: null,      // set while playing
};

const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

const $ = (id) => document.getElementById(id);
const timelineWrap = $("timeline-wrap");
const timeline = $("timeline");
const rulerEl = $("ruler");
const waveEls = [$("wave0"), $("wave1")];
const playheadEl = $("playhead");

// ------------------------------------------------------------- utilities
const dbToLin = (db) => Math.pow(10, db / 20);
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const msToX = (ms) => (ms / 1000) * state.pxPerSec;
const xToMs = (x) => (x / state.pxPerSec) * 1000;

function fmtTime(ms) {
  const s = Math.max(0, ms) / 1000;
  const m = Math.floor(s / 60);
  return `${m}:${(s - m * 60).toFixed(1).padStart(4, "0")}`;
}

function toast(msg, isError) {
  const el = $("toast");
  el.textContent = msg;
  el.classList.toggle("error", !!isError);
  el.hidden = false;
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.hidden = true; }, isError ? 6000 : 3000);
}

// Stretch rate for track i under the current sync mode (>1 = play faster).
function stretchRate(i) {
  if (state.syncMode === "off") return 1;
  const target = state.tracks[state.syncMode === "a" ? 0 : 1];
  const self = state.tracks[i];
  if (!target || !self || !target.bpm || !self.bpm) return 1;
  return target.bpm / self.bpm;
}

// Duration of the clip as it appears on the output timeline.
function outDur(i) {
  const t = state.tracks[i];
  return t ? (t.trimEnd - t.trimStart) / stretchRate(i) : 0;
}

function totalMs() {
  let total = 0;
  state.tracks.forEach((t, i) => { if (t) total = Math.max(total, t.offset + outDur(i)); });
  return total;
}

// Envelope value (dB) at output time `t` relative to clip start.
function envAt(track, t) {
  const pts = track.envelope;
  if (!pts.length) return 0;
  if (t <= pts[0].t) return pts[0].db;
  const last = pts[pts.length - 1];
  if (t >= last.t) return last.db;
  for (let k = 1; k < pts.length; k++) {
    if (t <= pts[k].t) {
      const a = pts[k - 1], b = pts[k];
      return a.db + ((t - a.t) / (b.t - a.t)) * (b.db - a.db);
    }
  }
  return last.db;
}

// ------------------------------------------------------------- uploading
async function uploadTrack(i, file) {
  toast(`Analyzing "${file.name}" (detecting BPM)…`);
  const form = new FormData();
  form.append("file", file, file.name);
  let meta;
  try {
    const res = await fetch("/api/upload", { method: "POST", body: form });
    meta = await res.json();
    if (!res.ok) throw new Error(meta.error || res.statusText);
  } catch (err) {
    toast(`Upload failed: ${err.message}`, true);
    return;
  }
  let buffer;
  try {
    const raw = await (await fetch(meta.url)).arrayBuffer();
    buffer = await audioCtx.decodeAudioData(raw);
  } catch (err) {
    toast(`Could not decode audio in this browser: ${err.message}`, true);
    return;
  }
  const durationMs = buffer.duration * 1000;
  state.tracks[i] = {
    fileId: meta.id,
    name: file.name,
    bpm: meta.bpm,
    buffer,
    peaks: computePeaks(buffer),
    durationMs,
    trimStart: 0,
    trimEnd: durationMs,
    offset: 0,
    gainDb: 0,
    muted: false,
    envelope: [],
  };
  $(`tname${i}`).textContent = file.name;
  $(`tbpm${i}`).textContent = meta.bpm ? `${meta.bpm} BPM` : "BPM unknown";
  $(`tgain${i}`).value = 0;
  $(`tdb${i}`).textContent = "0.0";
  updateEnabled();
  zoomFit();
  toast(`Loaded "${file.name}" — ${meta.bpm ? meta.bpm + " BPM" : "tempo unknown"}`);
}

// Min/max pairs per ~4ms bucket, mono-mixed: enough detail to draw fast.
function computePeaks(buffer) {
  const bucket = Math.max(64, Math.floor(buffer.sampleRate * 0.004));
  const n = Math.ceil(buffer.length / bucket);
  const mins = new Float32Array(n), maxs = new Float32Array(n);
  const chans = [];
  for (let c = 0; c < buffer.numberOfChannels; c++) chans.push(buffer.getChannelData(c));
  for (let b = 0; b < n; b++) {
    let lo = 1, hi = -1;
    const end = Math.min(buffer.length, (b + 1) * bucket);
    for (let s = b * bucket; s < end; s++) {
      let v = 0;
      for (let c = 0; c < chans.length; c++) v += chans[c][s];
      v /= chans.length;
      if (v < lo) lo = v;
      if (v > hi) hi = v;
    }
    mins[b] = lo; maxs[b] = hi;
  }
  return { mins, maxs, bucketMs: (bucket / buffer.sampleRate) * 1000 };
}

// -------------------------------------------------------------- drawing
function laneGeom(i) {
  const t = state.tracks[i];
  if (!t) return null;
  return { x: msToX(t.offset), w: Math.max(2, msToX(outDur(i))) };
}

const dbToY = (db, h) => ((DB_TOP - db) / (DB_TOP - DB_BOTTOM)) * h;
const yToDb = (y, h) => clamp(DB_TOP - (y / h) * (DB_TOP - DB_BOTTOM), DB_BOTTOM, DB_TOP);

function sizeCanvas(cv, cssW, cssH) {
  const dpr = window.devicePixelRatio || 1;
  cv.width = Math.round(cssW * dpr);
  cv.height = Math.round(cssH * dpr);
  const ctx = cv.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return ctx;
}

function draw() {
  const widthMs = Math.max(totalMs() * 1.15, xToMs(timelineWrap.clientWidth));
  const cssW = Math.max(timelineWrap.clientWidth, msToX(widthMs));
  timeline.style.width = `${cssW}px`;
  drawRuler(cssW);
  for (let i = 0; i < 2; i++) drawLane(i, cssW);
  positionPlayhead();
}

function drawRuler(cssW) {
  const h = rulerEl.clientHeight || 26;
  const ctx = sizeCanvas(rulerEl, cssW, h);
  ctx.clearRect(0, 0, cssW, h);
  ctx.fillStyle = "#9aa0b4";
  ctx.strokeStyle = "#2c3140";
  ctx.font = "10px sans-serif";
  const step = state.pxPerSec >= 60 ? 1 : state.pxPerSec >= 25 ? 2 : state.pxPerSec >= 12 ? 5 : 10;
  for (let s = 0; s * state.pxPerSec <= cssW; s += step) {
    const x = s * state.pxPerSec;
    ctx.beginPath(); ctx.moveTo(x + 0.5, h); ctx.lineTo(x + 0.5, h - 8); ctx.stroke();
    ctx.fillText(fmtTime(s * 1000), x + 3, h - 10);
  }
}

function drawLane(i, cssW) {
  const cv = waveEls[i];
  const h = cv.clientHeight || 132;
  const ctx = sizeCanvas(cv, cssW, h);
  ctx.clearRect(0, 0, cssW, h);
  const t = state.tracks[i];
  if (!t) {
    ctx.fillStyle = "#9aa0b4";
    ctx.font = "12px sans-serif";
    ctx.fillText("Load a track to start…", 14, h / 2);
    return;
  }
  const g = laneGeom(i);

  // clip body
  ctx.fillStyle = "rgba(108,140,255,0.10)";
  ctx.fillRect(g.x, 0, g.w, h);

  // waveform: each pixel column maps to a slice of SOURCE time
  const mid = h / 2, amp = h * 0.42;
  ctx.fillStyle = t.muted ? "#5a5f70" : WAVE_COLORS[i];
  const srcSpan = t.trimEnd - t.trimStart;
  for (let px = 0; px < g.w; px++) {
    const srcMs = t.trimStart + (px / g.w) * srcSpan;
    const b = Math.min(t.peaks.mins.length - 1, Math.floor(srcMs / t.peaks.bucketMs));
    const y1 = mid - t.peaks.maxs[b] * amp;
    const y2 = mid - t.peaks.mins[b] * amp;
    ctx.fillRect(g.x + px, y1, 1, Math.max(1, y2 - y1));
  }

  // clip border + trim handles
  ctx.strokeStyle = WAVE_COLORS[i];
  ctx.strokeRect(g.x + 0.5, 0.5, g.w - 1, h - 1);
  ctx.fillStyle = WAVE_COLORS[i];
  ctx.fillRect(g.x, 0, 4, h);
  ctx.fillRect(g.x + g.w - 4, 0, 4, h);

  // envelope line + points (drawn across the clip)
  ctx.strokeStyle = ENV_COLOR;
  ctx.lineWidth = 2;
  ctx.beginPath();
  const dur = outDur(i);
  const steps = Math.max(2, Math.floor(g.w / 4));
  for (let s = 0; s <= steps; s++) {
    const tt = (s / steps) * dur;
    const y = dbToY(envAt(t, tt), h);
    const x = g.x + (tt / dur) * g.w;
    s === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.stroke();
  ctx.lineWidth = 1;
  for (const p of t.envelope) {
    const x = g.x + (p.t / dur) * g.w;
    const y = dbToY(p.db, h);
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fillStyle = ENV_COLOR;
    ctx.fill();
    ctx.strokeStyle = "#0f1117";
    ctx.stroke();
  }
}

function positionPlayhead() {
  playheadEl.style.left = `${msToX(state.playheadMs)}px`;
  $("clock").textContent = fmtTime(state.playheadMs);
}

// ---------------------------------------------------------- interactions
let drag = null; // {type, track, ...}

function hitTest(i, x, y, h) {
  const t = state.tracks[i];
  if (!t) return null;
  const g = laneGeom(i);
  const dur = outDur(i);
  // envelope points first (they sit on top)
  for (let k = 0; k < t.envelope.length; k++) {
    const p = t.envelope[k];
    const px = g.x + (p.t / dur) * g.w;
    const py = dbToY(p.db, h);
    if (Math.abs(px - x) < POINT_PX && Math.abs(py - y) < POINT_PX) {
      return { type: "point", index: k };
    }
  }
  if (x < g.x - EDGE_PX || x > g.x + g.w + EDGE_PX) return null;
  if (Math.abs(x - g.x) < EDGE_PX) return { type: "trim-left" };
  if (Math.abs(x - (g.x + g.w)) < EDGE_PX) return { type: "trim-right" };
  return { type: "move" };
}

waveEls.forEach((cv, i) => {
  cv.addEventListener("pointerdown", (e) => {
    const t = state.tracks[i];
    if (!t) return;
    const rect = cv.getBoundingClientRect();
    const x = e.clientX - rect.left, y = e.clientY - rect.top;
    const hit = hitTest(i, x, y, rect.height);
    if (!hit) return;
    cv.setPointerCapture(e.pointerId);
    drag = {
      ...hit, track: i, startX: x, startY: y, moved: false,
      orig: { offset: t.offset, trimStart: t.trimStart, trimEnd: t.trimEnd },
      origPoint: hit.type === "point" ? { ...t.envelope[hit.index] } : null,
    };
  });

  cv.addEventListener("pointermove", (e) => {
    const rect = cv.getBoundingClientRect();
    const x = e.clientX - rect.left, y = e.clientY - rect.top;
    if (!drag || drag.track !== i) {
      if (state.tracks[i]) {
        const hit = hitTest(i, x, y, rect.height);
        cv.style.cursor = !hit ? "default"
          : hit.type === "move" ? "grab"
          : hit.type === "point" ? "ns-resize" : "ew-resize";
      }
      return;
    }
    const t = state.tracks[i];
    const dxMs = xToMs(x - drag.startX);
    if (Math.abs(x - drag.startX) + Math.abs(y - drag.startY) > 3) drag.moved = true;
    const rate = stretchRate(i);

    if (drag.type === "move") {
      t.offset = Math.max(0, drag.orig.offset + dxMs);
    } else if (drag.type === "trim-left") {
      const srcDelta = dxMs * rate;
      t.trimStart = clamp(drag.orig.trimStart + srcDelta, 0, t.trimEnd - 200);
      // keep the right edge visually anchored while trimming from the left
      t.offset = Math.max(0, drag.orig.offset + (t.trimStart - drag.orig.trimStart) / rate);
    } else if (drag.type === "trim-right") {
      const srcDelta = dxMs * rate;
      t.trimEnd = clamp(drag.orig.trimEnd + srcDelta, t.trimStart + 200, t.durationMs);
    } else if (drag.type === "point") {
      const dur = outDur(i);
      const p = t.envelope[drag.index];
      p.t = clamp(drag.origPoint.t + xToMs(x - drag.startX), 0, dur);
      p.db = yToDb(y, rect.height);
      t.envelope.sort((a, b) => a.t - b.t);
      drag.index = t.envelope.indexOf(p);
    }
    draw();
  });

  const finish = (e) => {
    if (!drag || drag.track !== i) return;
    drag = null;
    draw();
  };
  cv.addEventListener("pointerup", finish);
  cv.addEventListener("pointercancel", finish);

  // double-click: add envelope point, or delete one under the cursor
  cv.addEventListener("dblclick", (e) => {
    const t = state.tracks[i];
    if (!t) return;
    const rect = cv.getBoundingClientRect();
    const x = e.clientX - rect.left, y = e.clientY - rect.top;
    const hit = hitTest(i, x, y, rect.height);
    if (hit && hit.type === "point") {
      t.envelope.splice(hit.index, 1);
    } else if (hit) {
      const g = laneGeom(i), dur = outDur(i);
      const tt = clamp(((x - g.x) / g.w) * dur, 0, dur);
      t.envelope.push({ t: tt, db: yToDb(y, rect.height) });
      t.envelope.sort((a, b) => a.t - b.t);
    }
    draw();
  });
});

rulerEl.addEventListener("click", (e) => {
  const rect = rulerEl.getBoundingClientRect();
  const wasPlaying = !!state.transport;
  if (wasPlaying) stop();
  state.playheadMs = Math.max(0, xToMs(e.clientX - rect.left));
  positionPlayhead();
  if (wasPlaying) play();
});

// ------------------------------------------------------------- playback
function play() {
  if (state.transport) stop();
  if (!state.tracks.some(Boolean)) return;
  audioCtx.resume();

  const startCtx = audioCtx.currentTime + 0.08;
  const base = state.playheadMs;
  const master = audioCtx.createGain();
  master.gain.value = dbToLin(state.masterDb);
  master.connect(audioCtx.destination);

  const sources = [];
  state.tracks.forEach((t, i) => {
    if (!t || t.muted) return;
    const rate = stretchRate(i);
    const dur = outDur(i);
    const clipEnd = t.offset + dur;
    if (base >= clipEnd) return;

    const intoClip = Math.max(0, base - t.offset);       // output ms into clip
    const when = startCtx + Math.max(0, t.offset - base) / 1000;
    const srcOffsetMs = t.trimStart + intoClip * rate;   // source ms
    const srcRemainMs = t.trimEnd - srcOffsetMs;
    if (srcRemainMs <= 0) return;

    const src = audioCtx.createBufferSource();
    src.buffer = t.buffer;
    src.playbackRate.value = rate;

    const env = audioCtx.createGain();
    env.gain.setValueAtTime(dbToLin(envAt(t, intoClip)), when);
    for (const p of t.envelope) {
      if (p.t <= intoClip) continue;
      env.gain.linearRampToValueAtTime(dbToLin(p.db), startCtx + (t.offset + p.t - base) / 1000);
    }

    const fader = audioCtx.createGain();
    fader.gain.value = dbToLin(t.gainDb);
    t._faderNode = fader;

    src.connect(env).connect(fader).connect(master);
    src.start(when, srcOffsetMs / 1000, srcRemainMs / 1000);
    sources.push(src);
  });

  if (!sources.length) return;
  state.transport = { startCtx, base, sources, master, raf: 0 };
  $("play").disabled = true;
  $("stop").disabled = false;

  const end = totalMs();
  const tick = () => {
    if (!state.transport) return;
    state.playheadMs = base + Math.max(0, (audioCtx.currentTime - startCtx) * 1000);
    positionPlayhead();
    if (state.playheadMs >= end) { stop(); state.playheadMs = 0; positionPlayhead(); return; }
    state.transport.raf = requestAnimationFrame(tick);
  };
  tick();
}

function stop() {
  const tr = state.transport;
  if (!tr) return;
  cancelAnimationFrame(tr.raf);
  tr.sources.forEach((s) => { try { s.stop(); } catch (_) {} });
  tr.master.disconnect();
  state.tracks.forEach((t) => { if (t) t._faderNode = null; });
  state.transport = null;
  $("play").disabled = false;
  $("stop").disabled = true;
}

// --------------------------------------------------- loudness matching
function rmsDb(track) {
  const buf = track.buffer;
  const sr = buf.sampleRate;
  const s0 = Math.floor((track.trimStart / 1000) * sr);
  const s1 = Math.min(buf.length, Math.floor((track.trimEnd / 1000) * sr));
  let sum = 0, n = 0;
  const step = Math.max(1, Math.floor((s1 - s0) / 200000)); // sample sparsely
  for (let c = 0; c < buf.numberOfChannels; c++) {
    const data = buf.getChannelData(c);
    for (let s = s0; s < s1; s += step) { sum += data[s] * data[s]; n++; }
  }
  return n ? 10 * Math.log10(sum / n + 1e-12) : -90;
}

function matchLoudness() {
  const [a, b] = state.tracks;
  if (!a || !b) return;
  const delta = clamp(rmsDb(a) - rmsDb(b), -18, 18);
  b.gainDb = clamp(a.gainDb + delta, -24, 12);
  $("tgain1").value = b.gainDb;
  $("tdb1").textContent = b.gainDb.toFixed(1);
  if (b._faderNode) b._faderNode.gain.value = dbToLin(b.muted ? -120 : b.gainDb);
  toast(`Matched loudness: track B fader set to ${b.gainDb.toFixed(1)} dB`);
  draw();
}

// --------------------------------------------------------------- render
async function renderMix() {
  const clips = [];
  state.tracks.forEach((t, i) => {
    if (!t || t.muted) return;
    clips.push({
      file_id: t.fileId,
      trim_start_ms: Math.round(t.trimStart),
      trim_end_ms: Math.round(t.trimEnd),
      stretch_rate: stretchRate(i),
      gain_db: t.gainDb,
      offset_ms: Math.round(t.offset),
      envelope: t.envelope.map((p) => ({ t_ms: Math.round(p.t), gain_db: p.db })),
    });
  });
  if (!clips.length) { toast("Nothing to render.", true); return; }

  const btn = $("render");
  btn.disabled = true;
  btn.textContent = "Rendering…";
  toast("Rendering on the server (pitch-preserving stretch)…");
  try {
    const res = await fetch("/api/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        clips,
        master_gain_db: state.masterDb,
        normalize: true,
        output_format: $("format").value,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    $("result").hidden = false;
    $("result-audio").src = data.url;
    $("result-download").href = data.download_url;
    $("result").scrollIntoView({ behavior: "smooth" });
    toast(`Rendered ${fmtTime(data.duration_ms)} mix ✔`);
  } catch (err) {
    toast(`Render failed: ${err.message}`, true);
  } finally {
    btn.disabled = false;
    btn.textContent = "⬇ Render mix";
  }
}

// -------------------------------------------------------------- controls
function updateEnabled() {
  const any = state.tracks.some(Boolean);
  $("play").disabled = !any || !!state.transport;
  $("stop").disabled = !state.transport;
  $("render").disabled = !any;
  $("match-loudness").disabled = !(state.tracks[0] && state.tracks[1]);
}

function zoom(factor) {
  state.pxPerSec = clamp(state.pxPerSec * factor, 4, 400);
  draw();
}

function zoomFit() {
  const total = totalMs();
  if (total > 0) state.pxPerSec = clamp((timelineWrap.clientWidth - 20) / (total / 1000), 4, 400);
  draw();
}

document.querySelectorAll(".file-input").forEach((inp) => {
  inp.addEventListener("change", () => {
    if (inp.files[0]) uploadTrack(Number(inp.dataset.track), inp.files[0]);
    inp.value = "";
  });
});

document.querySelectorAll(".tgain").forEach((sl) => {
  sl.addEventListener("input", () => {
    const i = Number(sl.dataset.track);
    const t = state.tracks[i];
    if (!t) return;
    t.gainDb = Number(sl.value);
    $(`tdb${i}`).textContent = t.gainDb.toFixed(1);
    if (t._faderNode) t._faderNode.gain.value = dbToLin(t.muted ? -120 : t.gainDb);
  });
});

document.querySelectorAll(".mute").forEach((btn) => {
  btn.addEventListener("click", () => {
    const i = Number(btn.dataset.track);
    const t = state.tracks[i];
    if (!t) return;
    t.muted = !t.muted;
    btn.classList.toggle("on", t.muted);
    if (t._faderNode) t._faderNode.gain.value = dbToLin(t.muted ? -120 : t.gainDb);
    draw();
  });
});

$("master").addEventListener("input", (e) => {
  state.masterDb = Number(e.target.value);
  $("master-db").textContent = `${state.masterDb.toFixed(1)} dB`;
  if (state.transport) state.transport.master.gain.value = dbToLin(state.masterDb);
});

$("sync").addEventListener("change", (e) => {
  state.syncMode = e.target.value;
  if (state.transport) { stop(); play(); } else draw();
  if (state.syncMode !== "off") {
    toast("Tempo sync on — preview shifts pitch slightly; the final render doesn't.");
  }
  draw();
});

$("play").addEventListener("click", () => { play(); updateEnabled(); });
$("stop").addEventListener("click", () => { stop(); updateEnabled(); });
$("match-loudness").addEventListener("click", matchLoudness);
$("render").addEventListener("click", renderMix);
$("zoom-in").addEventListener("click", () => zoom(1.4));
$("zoom-out").addEventListener("click", () => zoom(1 / 1.4));
$("zoom-fit").addEventListener("click", zoomFit);
window.addEventListener("resize", draw);

draw();
