#!/usr/bin/env python3
"""Headless gameplay tests: drives snake.bf through the reference interpreter
and asserts real game behavior frame by frame."""

from __future__ import annotations

import os
import random
import sys

from bf import BF
from gen_snake import LCG_A, LCG_C, W, gen

UP, DOWN, LEFT, RIGHT, COAST = 1, 2, 3, 4, 0

FAILURES = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok  {name}")
    else:
        print(f"FAIL  {name}  {detail}")
        FAILURES.append(name)


class Frame:
    def __init__(self, text: str):
        self.text = text
        lines = text.split("\n")
        self.rows = lines[: W + 2]          # 16 board lines
        self.bar = lines[W + 2] if len(lines) > W + 2 else ""
        self.snake = set()
        self.food = set()
        for y in range(W):
            line = self.rows[1 + y] if len(self.rows) > 1 + y else ""
            for x in range(W):
                c = line[1 + x] if len(line) > 1 + x else "?"
                if c == "O":
                    self.snake.add((x, y))
                elif c == "*":
                    self.food.add((x, y))

    def walls_ok(self) -> bool:
        full = "#" * (W + 2)
        if len(self.rows) != W + 2:
            return False
        if self.rows[0] != full or self.rows[W + 1] != full:
            return False
        return all(
            len(r) == W + 2 and r[0] == "#" and r[-1] == "#"
            and set(r[1:-1]) <= {" ", "O", "*"}
            for r in self.rows[1: W + 1]
        )


class Game:
    """One byte in per tick, one frame out per tick."""

    def __init__(self, code: str):
        self.m = BF(code, block_on_input=True)
        self.raw_fed = 0
        status = self.m.run()
        assert status == "input", status

    def tick(self, byte: int) -> str:
        """Feed one byte; returns 'input' (next frame ready) or 'halt'."""
        self.m.feed(byte)
        self.raw_fed += byte
        status = self.m.run()
        assert status in ("input", "halt"), status
        return status

    def frames(self) -> list[str]:
        return self.m.output_text().split("\f")[1:]

    def frame(self) -> Frame:
        return Frame(self.frames()[-1])


def predict_food(seed: int, occupied: set[int]) -> int:
    while True:
        seed = (LCG_A * seed + LCG_C) % 256
        if seed < W * W and seed not in occupied:
            return seed


def head_of(prev: Frame, cur: Frame):
    new = cur.snake - prev.snake
    return next(iter(new)) if len(new) == 1 else None


VEC = {UP: (0, -1), DOWN: (0, 1), LEFT: (-1, 0), RIGHT: (1, 0)}


def steer_to_food(g: Game, max_ticks=60):
    """Drive the head onto the food without ever commanding a reversal.
    Returns (ate, head, dirv) — head/dirv as of the last frame."""
    prev = g.frame()
    start_len = len(prev.snake)
    if g.tick(COAST) == "halt":
        return False, None, None
    cur = g.frame()
    head, dirv = head_of(prev, cur), None
    for _ in range(max_ticks):
        if len(cur.snake) > start_len:
            return True, head, dirv
        food = next(iter(cur.food))
        hx, hy = head
        wish = []
        if food[0] != hx:
            wish.append(RIGHT if food[0] > hx else LEFT)
        if food[1] != hy:
            wish.append(DOWN if food[1] > hy else UP)
        wish += [m for m in (UP, DOWN, LEFT, RIGHT) if m not in wish]
        move = None
        for m in wish:
            v = VEC[m]
            if dirv and (v[0], v[1]) == (-dirv[0], -dirv[1]):
                continue  # reversal would be ignored: never command it
            nxt = (hx + v[0], hy + v[1])
            if not (0 <= nxt[0] < W and 0 <= nxt[1] < W):
                continue
            if nxt in cur.snake:
                continue
            move = m
            break
        if g.tick(move if move else COAST) == "halt":
            return False, head, dirv
        prev, cur = cur, g.frame()
        nh = head_of(prev, cur)
        if nh:
            dirv = (nh[0] - head[0], nh[1] - head[1])
            head = nh
    return False, head, dirv


def main():
    code = gen()

    # T1: initial frame
    g = Game(code)
    f = g.frame()
    check("initial walls", f.walls_ok(), repr(f.rows))
    check("initial snake", f.snake == {(5, 7), (6, 7), (7, 7)}, f.snake)
    check("initial food", f.food == {(10, 7)}, f.food)
    check("initial bar", f.bar == "###", repr(f.bar))

    # T2: coasting moves the snake right, length constant
    g.tick(COAST)
    f2 = g.frame()
    check("coast moves right", f2.snake == {(6, 7), (7, 7), (8, 7)}, f2.snake)
    check("tail follows", len(f2.snake) == 3 and f2.bar == "###", f2.bar)

    # T3: turn up
    g.tick(UP)
    f3 = g.frame()
    check("turn up", f3.snake == {(7, 7), (8, 7), (8, 6)}, f3.snake)

    # T4: reversal ignored (moving up, press down)
    g.tick(DOWN)
    f4 = g.frame()
    check("reversal ignored", f4.snake == {(8, 7), (8, 6), (8, 5)}, f4.snake)

    # T5: wall death: fresh game, hold right; head starts x=7, eats at x=10,
    # reaches x=13 on tick 6, dies stepping to x=14 on tick 7 and halts
    g = Game(code)
    status = None
    for t in range(1, 20):
        status = g.tick(COAST)
        if status == "halt":
            break
    check("wall death halts", status == "halt" and t == 7, f"t={t} {status}")
    check("game over banner", "*** GAME OVER ***" in g.frames()[-1],
          repr(g.frames()[-1][-40:]))
    last = Frame(g.frames()[-1])
    check("death frame keeps walls", last.walls_ok())

    # T6: eating: 3 coasts from the start reach the food at (10,7)
    g = Game(code)
    for _ in range(3):
        g.tick(COAST)
    f6 = g.frame()
    check("ate: grew to 4", len(f6.snake) == 4 and f6.bar == "####",
          f"{len(f6.snake)} {f6.bar!r}")
    check("ate: head on old food", (10, 7) in f6.snake, f6.snake)
    check("ate: one new food", len(f6.food) == 1 and f6.food != {(10, 7)},
          f6.food)
    # deterministic spawn: seed = 91 + sum(inputs so far), occupied = new body
    occupied = {y * W + x for (x, y) in f6.snake}
    want = predict_food(91 + g.raw_fed, occupied)
    got = next(iter(f6.food))
    check("ate: food matches LCG", got[1] * W + got[0] == want,
          f"got={got} want=({want % W},{want // W})")

    # T6b: on the eating tick the tail must NOT move (growth by head)
    g = Game(code)
    g.tick(COAST)
    g.tick(COAST)
    before = g.frame()
    g.tick(COAST)  # eat happens here
    after = g.frame()
    check("ate: tail frozen", before.snake < after.snake,
          f"{before.snake} -> {after.snake}")

    # T7a: tail chasing is legal: grow to 4, then 2x2 circles forever
    g = Game(code)
    for _ in range(3):
        g.tick(COAST)                      # eat, len 4, heading right
    alive = True
    for loop in range(3):
        for move in (UP, LEFT, DOWN, RIGHT):
            if g.tick(move) == "halt":
                alive = False
    check("tail chase legal at len 4", alive and len(g.frame().snake) == 4,
          f"alive={alive}")

    # T7b: real self collision: grow to 5 by chasing food, then circle tightly
    g = Game(code)
    for _ in range(3):
        g.tick(COAST)                      # first food, len 4
    ate, head, dirv = steer_to_food(g)
    check("greedy reached second food", ate and len(g.frame().snake) == 5,
          f"ate={ate} len={len(g.frame().snake)}")
    if ate:
        # 2x2 circle starting perpendicular to current motion, turned toward
        # the board interior so the only thing the head can hit is the body
        hx, hy = head
        dx, dy = dirv
        perp = None
        for cand in ((dy, -dx), (-dy, dx)):
            px, py = hx + cand[0] * 2, hy + cand[1] * 2
            bx, by = hx - dx * 2, hy - dy * 2
            if 0 <= px < W and 0 <= py < W and 0 <= bx < W and 0 <= by < W:
                perp = cand
                break
        inv = {v: m for m, v in VEC.items()}
        seq = [inv[perp], inv[(-dx, -dy)], inv[(-perp[0], -perp[1])],
               inv[(dx, dy)]] * 3
        died = False
        pos = (hx, hy)
        in_bounds_at_death = True
        for mv in seq:
            v = VEC[mv]
            pos = (pos[0] + v[0], pos[1] + v[1])
            if g.tick(mv) == "halt":
                died = True
                in_bounds_at_death = 0 <= pos[0] < W and 0 <= pos[1] < W
                break
        check("self collision kills at len 5", died, "survived 12 circling")
        check("death was by body, not wall", died and in_bounds_at_death,
              f"final head {pos}")
        if died:
            check("self death banner", "GAME OVER" in g.frames()[-1])

    # T8: long soak: greedy-but-safe play for many ticks, invariants on every
    # frame; exercises growth, LCG rerolls onto occupied cells, long bodies
    rng = random.Random(1234)
    g = Game(code)
    prev = g.frame()
    g.tick(COAST)
    cur = g.frame()
    head, dirv = head_of(prev, cur), (1, 0)
    eats, bad, died_at = 0, None, None
    for t in range(400):
        if not (cur.walls_ok() and len(cur.food) == 1
                and len(cur.snake) == len(cur.bar)):
            bad = (t, f"walls={cur.walls_ok()} food={cur.food} "
                      f"snake={len(cur.snake)} bar={len(cur.bar)}")
            break
        food = next(iter(cur.food))
        hx, hy = head
        wish = []
        if food[0] != hx:
            wish.append(RIGHT if food[0] > hx else LEFT)
        if food[1] != hy:
            wish.append(DOWN if food[1] > hy else UP)
        rest = [m for m in (UP, DOWN, LEFT, RIGHT) if m not in wish]
        rng.shuffle(rest)
        if rng.random() < 0.25:            # some chaos on top of the greed
            rng.shuffle(wish)
        move = None
        fallback = None
        for m in wish + rest:
            v = VEC[m]
            if (v[0], v[1]) == (-dirv[0], -dirv[1]):
                continue
            nxt = (hx + v[0], hy + v[1])
            if not (0 <= nxt[0] < W and 0 <= nxt[1] < W):
                continue
            if nxt in cur.snake:
                fallback = fallback or m   # tail may vacate; last resort
                continue
            move = m
            break
        if g.tick(move or fallback or COAST) == "halt":
            died_at = t
            break
        prev, cur = cur, g.frame()
        if len(cur.snake) > len(prev.snake):
            eats += 1
        nh = head_of(prev, cur)
        if nh:
            dirv = (nh[0] - head[0], nh[1] - head[1])
            head = nh
        # per-tick shape: exactly one new head, at most one vacated tail
        added, removed = cur.snake - prev.snake, prev.snake - cur.snake
        if len(added) != 1 or len(removed) > 1:
            bad = (t, f"added={added} removed={removed}")
            break
    check("soak invariants", bad is None, f"broken at {bad}")
    check("soak ate multiple foods", eats >= 2, f"eats={eats}")
    if died_at is not None:
        check("soak death has banner", "GAME OVER" in g.frames()[-1])
        print(f"  (soak died legally at tick {died_at}, eats={eats}, "
              f"len={len(cur.bar)})")
    else:
        print(f"  (soak survived 400 ticks, eats={eats}, "
              f"len={len(g.frame().bar)})")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {FAILURES}")
        sys.exit(1)
    print(f"all gameplay tests passed  ({0 if not g else g.m.steps:,} BF steps "
          f"in the last game)")


if __name__ == "__main__":
    main()
