# 🍄 Sorrio

A web-based, Mario-ish side scroller that **plays itself**. Sorrio runs,
jumps, stomps and bonks the boss on auto-pilot while a live **bar graph**
grades how the run is going. Flip to Manual any time and take the wheel.

Everyone in the cast has a rhyming name.

It's a **single self-contained `index.html`** (HTML + CSS + JS inlined,
no dependencies), so it runs anywhere — including your phone.

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

| Name          | Role                                            |
|---------------|-------------------------------------------------|
| **Sorrio**    | Our red-capped hero (the one you watch/control) |
| **Florrio**   | The green rival who jogs alongside              |
| **Goombrian** | Waddling mushroom foe — stomp it                |
| **Sporella**  | Spiky purple toad lady — do *not* land on her   |
| **Lord Snortio** | The boss hoarding the loins — bonk him 3×    |

## The bar graph

Five live meters plus an overall letter grade (F → S):

- **Coins (Loins)** — how many you've grabbed
- **Distance** — how far across the stage
- **Stomps** — enemies squashed
- **Health** — hearts remaining
- **Style** — jumps, bounces and clutch moves

## Controls

- **Mode** button — toggle Auto-Pilot ↔ Manual
- **Pause / Restart** buttons
- Manual: **←** **→** to move, **Space** (or **↑**) to jump

Built with plain `<canvas>` and vanilla JS.
