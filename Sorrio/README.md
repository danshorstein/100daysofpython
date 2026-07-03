# 🍄 Sorrio v2.0

A web-based, Mario-ish side scroller that **plays itself**. Sorrio runs,
jumps, bonks ?-blocks, stomps and combos on auto-pilot while a live
**bar graph** grades how the run is going — now with a chiptune
soundtrack, power-ups, particles, screen shake, and a castle finale
under fireworks. Flip to Manual any time and take the wheel.

Everyone in the cast has a rhyming name.

It's a **single self-contained `index.html`** (HTML + CSS + JS + WebAudio
synth inlined, no dependencies), so it runs anywhere — including your phone.

## Try it on your phone

Because it's one static file, any HTML preview service can serve it.
Tap this on your phone (works while the branch is pushed):

```
https://htmlpreview.github.io/?https://github.com/danshorstein/100daysofpython/blob/claude/sorrio-side-scroller-lozsjy/Sorrio/index.html
```

For a permanent link, enable **GitHub Pages** for the repo
(Settings → Pages → deploy from this branch / `master`), then visit
`https://danshorstein.github.io/100daysofpython/Sorrio/`.

On touch devices, on-screen **◀ ▶ JUMP** buttons appear automatically —
tapping one drops you into Manual mode.

## Run it locally

```bash
open Sorrio/index.html        # macOS
xdg-open Sorrio/index.html    # Linux
# or serve it
python3 -m http.server -d Sorrio 8000   # then visit http://localhost:8000
```

## The cast

| Name             | Role                                                    |
|------------------|---------------------------------------------------------|
| **Sorrio**       | Our red-capped hero (the one you watch/control)         |
| **Florrio**      | The green rival who jogs alongside — and secretly tosses Sorrio a heart when he's hurting |
| **Goombrian**    | Waddling mushroom foe — stomp it                        |
| **Sporella**     | Spiky purple toad lady — do *not* land on her           |
| **Swoopio**      | Dive-bombing bird — stomp it on the downswing           |
| **Shroomio**     | Heart mushroom from ?-blocks (+1 ♥, max 5)              |
| **Starrio**      | Invincibility star — plow through everything, rainbow trail |
| **Lord Snortio** | The crowned boss hoarding the loins — bonk him 3×       |

## The bar graph

Five live meters plus an overall letter grade (F → S) and a persistent
best score:

- **Coins (Loins)** — how many you've grabbed
- **Distance** — how far across the stage
- **Stomps** — enemies squashed (chain them airborne for **COMBO x2, x3…**)
- **Health** — hearts remaining (start with 4, max 5)
- **Style** — jumps, bounces, combos and clutch moves

## Features

- 🎵 Original chiptune loop + synthesized sfx (WebAudio, no assets) —
  the tempo speeds up while Starrio power is active
- 🧠 Deterministic auto-pilot with pit lookahead, swoop-phase reading,
  running starts, power-up chasing and a stuck-watchdog
  (validated headless: ~68% clear rate over 120 generated levels,
  zero stalls)
- 🎁 ?-blocks, pipes, day-to-golden-hour sky, parallax mountains,
  squash & stretch, hit-stop, screen shake, particles, score popups
- 🏰 Victory lap to the castle under fireworks; falling in a pit costs
  a heart instead of the whole run
- 📱 Touch controls, tap-to-restart, best-score memory (localStorage)

## Controls

- **Mode** button — toggle Auto-Pilot ↔ Manual
- **Pause / Restart / Sound** buttons
- Manual: **←** **→** move, **Space** or **↑** to jump —
  *hold* jump to go higher (coyote time & jump buffering included)
- **R** or tap the canvas to restart after a run

Built with plain `<canvas>`, vanilla JS and WebAudio.
