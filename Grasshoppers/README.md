# 🦗 GRASSHOPPERS — Worms, but the whole swarm goes at once, in 3D, in voxels

A browser-based, mobile-friendly artillery brawler in the spirit of *Worms* —
turn-based, destructible terrain, absurd weapons — except:

- **You command an entire army every turn**, not one worm at a time. Hop
  around and fire with every grasshopper you've got before you pass the turn.
- **The island is a fully 3D, hand-rolled voxel world**, procedurally
  generated from a text seed — floating rocks, caves, biomes, the works —
  and every explosion actually carves a hole out of it in three dimensions.
- **The weapons are unhinged.** A trebuchet that launches an actual furious
  grandmother. A cluster bomb that splits into bananas that split into
  vengeful bees. A kettle that is a live grenade 60% of the time and simply
  a nice cup of tea the rest.

No build step, no dependencies, no CDN — one `index.html` with a hand-written
WebGL2 renderer, procedural terrain generator, physics, AI, and a WebAudio
synth doing every sound effect, all inlined. It works offline, straight from
disk, on a phone.

## Play it

Open [`index.html`](index.html) in any modern browser (needs WebGL2 — recent
Chrome, Edge, Firefox, or Safari 15+):

```bash
python3 -m http.server -d Grasshoppers 8000
# then open http://localhost:8000
```

Or just double-click the file — it runs fine straight from `file://`.

## Controls

| | Touch | Keyboard / mouse |
|---|---|---|
| Move | left stick hops in the stick's direction | WASD / arrows, **Space** to hop |
| Look / camera | drag anywhere on screen | drag with mouse |
| Charge power | hold the stick / **HOLD TO FIRE** button | hold **Space** or **Enter** |
| Fire | release **HOLD TO FIRE** | release **Enter**, or hold **Shift**+click |
| Pick weapon | tap the weapon bar | **1–9**, or click the bar |
| Next hopper | tap a roster pip | **Tab** |
| Swarm volley | **🦗🦗 SWARM** button | **Q** |
| Rally the squad | **📣 RALLY** button | **R** |
| End turn | **⏭ END** button | **E** |
| Zoom | pinch | scroll wheel |
| Mute | — | **M** |

Each grasshopper gets its own hop budget and one shot per turn — but you
choose the order, and nothing stops you from firing every last one of them
before you pass the turn.

## The armory

Seventeen weapons, no two mechanically alike:

| | Weapon | What it actually does |
|---|---|---|
| 🥚 | Grenade Egg | Standard bouncing timed grenade. Infinite ammo. |
| 🏜️ | Pocket Sand | A blinding cone of sand that pushes enemies back and buries the ground. |
| 🦗 | Holy Hand Cricket | One shot, one enormous scorched crater, a choir. |
| 🧀 | Nuclear Cheese Wheel | Rolls downhill melting a trench, detonates on impact or timeout. |
| 🦡 | Sneezing Badger | Burrows into rock, tunnels blindly, sneezes a chain of small blasts. |
| 🍌 | Bee-nana Bomb | Splits into six bananas that split into homing bees. |
| 👵 | Grandma's Trebuchet | Drops an actual grandmother from orbit. She bounces. Three times. |
| 🌀 | Lawnmower Uprising | An autonomous mower that shaves a straight swath off the terrain. |
| 📯 | Vuvuzela of Doom | Pure sound. No crater — just a wall of force that punts everyone away. |
| 🐸 | Exploding Toad | Hops toward the nearest enemy on its own, then detonates. |
| 🕳️ | Gravity Hiccup | Inverts gravity in a huge sphere. Terrain and grasshoppers float. |
| 🕊️ | Airstrike: The Pigeons | A flock passes over and drops... something, several times. |
| 🗿 | Concrete Locust | Drills clean through the island and back, three times. |
| 🤸 | Antigravity Trampoline | A permanent bounce pad. Launches anything that touches it. Forever. |
| 🍬 | Mint Condition | Turns terrain to candy — brittle, so the next blast there is enormous. |
| ☕ | The Unstable Kettle | Whistles for 1–6s. 40% chance it's just tea. |
| 👑 | Call the Mother Locust | Every surviving grasshopper gets its turn back. |

## Under the hood

- **Rendering**: hand-written WebGL2 — a chunked voxel mesher (16³ chunks,
  per-face culling + baked ambient occlusion) plus one instanced-cube
  pipeline for grasshoppers, projectiles, debris and particles. No mesh
  libraries, no textures — everything is flat-shaded voxel colour.
- **Worldgen**: a seeded value-noise/fBm terrain generator (trilinear hash
  noise, no external noise library) picks a biome, carves an island with
  caves, and scatters trees, mushrooms, crystal spires and floating rocks.
- **Destruction**: explosions remove voxels in a jittered sphere (brittle
  materials like candy and ice blow out wider), mark affected chunks dirty
  for a fast remesh, and anything left with zero neighbors crumbles into
  tumbling debris.
- **AI**: the enemy swarm picks targets, hops into range, solves a ballistic
  arc (with wind correction) or aims direct/point weapons, and fires — with
  three difficulty tiers tuning aim error and weapon greed.
- **Audio**: every sound — explosions, whistles, honks, buzzing, the choir —
  is synthesised live with the WebAudio API. No audio files.

## Verifying it

[`tools/test_e2e.py`](tools/test_e2e.py) drives the page headlessly with
Playwright: boots it, starts a match, drives a few turns worth of hopping,
firing, and swarm volleys, and screenshots the result — the same pattern
used in [`../snake-brainfuck/tools/test_e2e.py`](../snake-brainfuck/tools/test_e2e.py).

```bash
pip install playwright && playwright install chromium
python3 tools/test_e2e.py
```
