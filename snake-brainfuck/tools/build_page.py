#!/usr/bin/env python3
"""Builds ../index.html: snake.bf embedded in a self-contained page whose only
JavaScript is a BrainFuck interpreter and I/O shim (keys in, characters out).
No game logic outside the BrainFuck program."""

import os

HERE = os.path.dirname(os.path.abspath(__file__))

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SNAKE.BF — Snake in pure BrainFuck</title>
<style>
  :root { --green:#39ff6e; --dim:#1d8f44; --dark:#031607; }
  * { box-sizing:border-box; margin:0; padding:0; }
  html,body { background:#000; color:var(--green); font-family:ui-monospace,'Cascadia Mono',Menlo,Consolas,monospace; }
  body { min-height:100vh; display:flex; flex-direction:column; align-items:center; padding:14px; }
  body::after { content:""; position:fixed; inset:0; pointer-events:none;
    background:repeating-linear-gradient(0deg, rgba(0,0,0,0) 0 2px, rgba(0,0,0,.28) 2px 4px);
    mix-blend-mode:multiply; }
  h1 { font-size:clamp(18px,4vw,30px); letter-spacing:.35em; text-shadow:0 0 12px var(--green);
       margin:6px 0 2px; }
  h1 span { color:var(--dim); }
  .sub { color:var(--dim); font-size:12px; margin-bottom:12px; text-align:center; }
  .crt { background:var(--dark); border:2px solid var(--dim); border-radius:10px;
         box-shadow:0 0 30px rgba(57,255,110,.25), inset 0 0 40px rgba(0,0,0,.7);
         padding:16px 22px; }
  pre#screen { font-size:clamp(11px,2.6vw,20px); line-height:1.05; letter-spacing:.35em;
               text-shadow:0 0 6px var(--green); animation:hum 4s infinite; }
  @keyframes hum { 0%,100%{opacity:1} 50%{opacity:.94} }
  .dead #screen { animation:none; color:#ff5544; text-shadow:0 0 8px #ff5544; }
  .hint { margin-top:10px; font-size:12px; color:var(--dim); text-align:center; min-height:16px; }
  .hint b { color:var(--green); }
  .stats { display:flex; gap:18px; flex-wrap:wrap; justify-content:center; margin-top:10px;
           font-size:11px; color:var(--dim); }
  .stats b { color:var(--green); font-weight:normal; }
  canvas#tape { margin-top:10px; width:min(840px,94vw); height:46px; image-rendering:pixelated;
                border:1px solid var(--dim); border-radius:4px; background:#020a04; }
  .caption { font-size:10px; color:var(--dim); margin-top:3px; }
  .pad { display:grid; grid-template-columns:repeat(3,56px); gap:6px; margin-top:14px; }
  .pad button { height:44px; background:var(--dark); border:1px solid var(--dim); color:var(--green);
                border-radius:6px; font:inherit; font-size:18px; cursor:pointer; }
  .pad button:active { background:var(--dim); color:#000; }
  details { margin:18px 0 30px; width:min(840px,94vw); }
  summary { cursor:pointer; color:var(--dim); font-size:12px; }
  details pre { margin-top:8px; max-height:300px; overflow:auto; font-size:9px; line-height:1.3;
                color:var(--dim); border:1px solid var(--dim); border-radius:4px; padding:8px;
                white-space:pre-wrap; word-break:break-all; }
</style>
</head>
<body>
<h1>SNAKE<span>.BF</span></h1>
<div class="sub">the game logic is one BrainFuck program — the only JavaScript on this page is a
BrainFuck interpreter feeding it keystrokes<br>arrows / WASD to steer · R to restart</div>
<div class="crt"><pre id="screen">booting tape…</pre></div>
<div class="hint" id="hint"></div>
<div class="stats">
  <span>program <b id="s_raw">0</b> ops (<b id="s_ops">0</b> compiled)</span>
  <span>executed <b id="s_steps">0</b></span>
  <span>ip <b id="s_ip">0</b></span>
  <span>pointer <b id="s_ptr">0</b></span>
  <span>tick <b id="s_tick">0</b></span>
</div>
<canvas id="tape" width="840" height="46"></canvas>
<div class="caption">live tape: cells 0–839 · the four-cell grid elements start at 32 · watch the
snake crawl through memory</div>
<div class="pad">
  <span></span><button data-d="1">▲</button><span></span>
  <button data-d="3">◀</button><button data-d="2">▼</button><button data-d="4">▶</button>
</div>
<details><summary>show the entire BrainFuck program</summary><pre id="src"></pre></details>

<script type="text/brainfuck" id="prog">
@@BF@@
</script>

<script>
"use strict";
/* ---- the whole game above, the dumb machine below ---- */
const SRC = document.getElementById("prog").textContent;
const TICK_MS = 110, TAPE_LEN = 30000;

function compile(src) {
  const ops = [], arg = [];
  for (let i = 0; i < src.length; i++) {
    const c = src[i];
    if (c === "+" || c === "-") {
      let n = 0;
      while (i < src.length && (src[i] === "+" || src[i] === "-")) { n += src[i] === "+" ? 1 : -1; i++; }
      i--; ops.push(1); arg.push(n & 255);
    } else if (c === "<" || c === ">") {
      let n = 0;
      while (i < src.length && (src[i] === "<" || src[i] === ">")) { n += src[i] === ">" ? 1 : -1; i++; }
      i--; ops.push(2); arg.push(n);
    } else if (c === "[") { ops.push(3); arg.push(0); }
    else if (c === "]") { ops.push(4); arg.push(0); }
    else if (c === ".") { ops.push(5); arg.push(0); }
    else if (c === ",") { ops.push(6); arg.push(0); }
  }
  const st = [];
  for (let j = 0; j < ops.length; j++) {
    if (ops[j] === 3) st.push(j);
    else if (ops[j] === 4) { const k = st.pop(); arg[j] = k; arg[k] = j; }
  }
  if (st.length) throw new Error("unbalanced brackets");
  return { ops: Int32Array.from(ops), arg: Int32Array.from(arg) };
}

class VM {
  constructor(prog) {
    this.prog = prog; this.tape = new Uint8Array(TAPE_LEN);
    this.ptr = 0; this.ip = 0; this.steps = 0;
    this.inq = []; this.halted = false; this.cur = "";
  }
  run(budget = 100_000_000) {
    const { ops, arg } = this.prog, t = this.tape, n = ops.length;
    let ip = this.ip, ptr = this.ptr, s = 0;
    while (ip < n && s < budget) {
      switch (ops[ip]) {
        case 1: t[ptr] = (t[ptr] + arg[ip]) & 255; break;
        case 2: ptr += arg[ip]; break;
        case 3: if (!t[ptr]) ip = arg[ip]; break;
        case 4: if (t[ptr]) ip = arg[ip]; break;
        case 5: { const b = t[ptr]; if (b === 12) this.cur = ""; else this.cur += String.fromCharCode(b); break; }
        case 6:
          if (this.inq.length) { t[ptr] = this.inq.shift(); }
          else { this.ip = ip; this.ptr = ptr; this.steps += s; return "input"; }
          break;
      }
      ip++; s++;
    }
    this.ip = ip; this.ptr = ptr; this.steps += s;
    if (ip >= n) { this.halted = true; return "halt"; }
    return "budget";
  }
}

const prog = compile(SRC);
const screen = document.getElementById("screen"), hint = document.getElementById("hint");
const tapeCv = document.getElementById("tape"), tctx = tapeCv.getContext("2d");
const el = id => document.getElementById(id);
el("s_ops").textContent = prog.ops.length.toLocaleString();
el("s_raw").textContent = (SRC.match(/[+\-<>\[\].,]/g) || []).length.toLocaleString();
el("src").textContent = SRC.trim();

let vm, timer = null, tick = 0;
const keyq = [];

function drawTape() {
  tctx.fillStyle = "#020a04";
  tctx.fillRect(0, 0, 840, 46);
  for (let c = 0; c < 840; c++) {
    const v = vm.tape[c];
    if (!v) continue;
    const h = 4 + Math.round((v / 255) * 40);
    tctx.fillStyle = c < 32 ? "#ffd24a" : (c % 4 === 2 ? "#ff5f9e" : "#39ff6e");
    tctx.fillRect(c, 46 - h, 1, h);
  }
  tctx.fillStyle = "rgba(255,255,255,.75)";
  const p = Math.min(vm.ptr, 839);
  tctx.fillRect(p, 0, 1, 4);
}

function pump() {
  const r = vm.run();
  screen.textContent = vm.cur;
  el("s_steps").textContent = vm.steps.toLocaleString();
  el("s_ip").textContent = vm.ip;
  el("s_ptr").textContent = vm.ptr;
  el("s_tick").textContent = tick;
  drawTape();
  if (r === "halt") {
    document.body.classList.add("dead");
    hint.innerHTML = "the tape has spoken — press <b>R</b> to reincarnate";
    clearInterval(timer); timer = null;
  }
  return r;
}

function start() {
  document.body.classList.remove("dead");
  hint.textContent = "";
  vm = new VM(prog); tick = 0; keyq.length = 0;
  pump();                       // draw frame 0, park on the first `,`
  if (timer) clearInterval(timer);
  timer = setInterval(() => {
    if (vm.halted) return;
    vm.inq.push(keyq.length ? keyq.shift() : 0);
    tick++;
    pump();
  }, TICK_MS);
}

const KEYS = { ArrowUp: 1, ArrowDown: 2, ArrowLeft: 3, ArrowRight: 4,
               w: 1, s: 2, a: 3, d: 4, W: 1, S: 2, A: 3, D: 4 };
addEventListener("keydown", e => {
  if (e.key === "r" || e.key === "R") { start(); e.preventDefault(); return; }
  const d = KEYS[e.key];
  if (d) { if (keyq.length < 3) keyq.push(d); e.preventDefault(); }
});
for (const b of document.querySelectorAll(".pad button"))
  b.addEventListener("click", () => { if (keyq.length < 3) keyq.push(+b.dataset.d); });

start();
</script>
</body>
</html>
"""


def main() -> None:
    with open(os.path.join(HERE, "..", "snake.bf")) as fh:
        bf = fh.read().strip()
    html = TEMPLATE.replace("@@BF@@", bf)
    out = os.path.join(HERE, "..", "index.html")
    with open(out, "w") as fh:
        fh.write(html)
    print(f"index.html written: {len(html)} bytes")


if __name__ == "__main__":
    main()
