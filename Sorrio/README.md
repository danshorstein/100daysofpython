# 🍄 Sorrio v3.0

A web-based, Mario-ish side scroller that **plays itself**. Sorrio runs,
jumps, bonks ?-blocks, stomps and combos on auto-pilot while a live
**bar graph** grades how the run is going — with a chiptune soundtrack,
power-ups, particles, screen shake, and a castle finale under fireworks.
Flip to Manual any time and take the wheel — on a phone, just touch the
screen: a **virtual joystick** appears under your left thumb.

New in v3: **double jump → FLIGHT** (tap jump mid-air to somersault,
then hold to beat his little wings until the fuel runs out), and
**😈 PSYCHO MODE** — an Unfair-Mario fever dream where the ground lies,
the coins bite, invisible blocks ambush your jumps, the flag grows legs
and runs away, and a chaos director periodically reverses your controls,
flips gravity, mirrors the world, rains Goombrians, or fakes the
victory screen just to laugh at you.

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

On touch devices the whole canvas is the controller: **left half** spawns
a floating joystick wherever your thumb lands; **right half** is jump —
tap again mid-air to double jump, **hold to fly**. Touching the screen
switches to Manual automatically; tap after a run to restart.

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

## 😈 Psycho Mode (press the purple button. or don't.)

- **Fake ground** — looks identical, crumbles underfoot
- **Mimic coins** — "GOTCHA!" they were Goombrians all along
- **Troll blocks** — invisible until they materialize on your head mid-jump
- **The fake flag** — sprouting little legs it absolutely should not have
- **A chaos director** rolling random events: reversed controls, moon /
  heavy gravity, Goombrian rain, disco fever, mirror world, pipe ambushes,
  speed demon, and a fake "STAGE CLEAR!" → "JUST KIDDING 😈"

## Double jump & flight

Jump once from the ground, tap again mid-air for a **somersault double
jump** — that unlocks Sorrio's wings. Hold jump to **fly** while the
WINGS meter drains; it refills whenever he's on solid ground. The
auto-pilot uses it too: watch him flap his way out of pits.

## Features

- 🎵 Original chiptune loop + synthesized sfx (WebAudio, no assets) —
  the tempo speeds up while Starrio power is active
- 🧠 Deterministic auto-pilot with pit lookahead, swoop-phase reading,
  running starts, power-up chasing, a stuck-watchdog — and now mid-air
  pit rescues on its own wings (validated headless: a 26-check parity
  suite covering auto/psycho runs, double jump, flight, and the
  joystick's synthetic touch events)
- 🎁 ?-blocks, pipes, day-to-golden-hour sky, parallax mountains,
  squash & stretch, hit-stop, screen shake, particles, score popups
- 🏰 Victory lap to the castle under fireworks; falling in a pit costs
  a heart instead of the whole run
- 📱 Full mobile support: floating joystick + jump zone, multi-touch,
  no page scroll/zoom during play, tap-to-restart, best-score memory

## Controls

- **Mode** button — toggle Auto-Pilot ↔ Manual
- **Pause / Restart / Sound / 😈 Psycho** buttons
- Keyboard: **←** **→** move, **Space** or **↑** to jump (*hold* for
  height — coyote time & jump buffering included), tap again mid-air to
  double jump, hold to fly
- Touch: left half = joystick, right half = jump / double jump / hold-to-fly
- **R** or tap the canvas to restart after a run

Built with plain `<canvas>`, vanilla JS and WebAudio.
