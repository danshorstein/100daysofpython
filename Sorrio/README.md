# 🍄 Sorrio

A web-based, Mario-ish side scroller that **plays itself**. Sorrio runs,
jumps, stomps and bonks the boss on auto-pilot while a live **bar graph**
grades how the run is going. Flip to Manual any time and take the wheel.

Everyone in the cast has a rhyming name.

## Run it

No build, no dependencies. Just open the file:

```bash
# from the repo root
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
