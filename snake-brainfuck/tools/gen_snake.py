#!/usr/bin/env python3
"""Generates snake.bf: the game of Snake written in pure BrainFuck.

This is a macro-assembler: Python here only *emits* BrainFuck once, at build
time. Every byte of game state and every game rule lives on the BF tape and
in BF control flow. The web page runs the emitted program with a dumb BF
interpreter whose whole job is I/O: keyboard bytes in via `,`, characters out
via `.`.

Game protocol
-------------
input  : one byte per game tick. 0 = no key, 1 = up, 2 = down, 3 = left,
         4 = right. The single `,` per main-loop iteration doubles as the
         game clock (the host feeds one byte per ~110ms).
output : each frame starts with a form feed (12), then a 16x16 board of
         '#' walls / 'O' snake / '*' food / ' ' empty with newlines, then a
         score bar: one '#' per snake segment, then newline. After death a
         "*** GAME OVER ***" banner is printed and the program halts.

Tape layout
-----------
  0..5    T0..T5   scratch
  6..15   X Y DIR LEN SEED FI ALIVE RAW HI GREW
  16..20  T6 T7 CHR T8 T9   (more scratch; CHR builds printable chars)
  28      R        array-op result / caravan landing cell
  29..31  padding
  32..815 grid: 196 elements of 4 cells (a b f v), element k = playfield
          cell (x=k%14, y=k//14). a/b: caravan lanes (rest 0), f: food
          marker, v: snake age (0 empty, else ticks until the segment fades)
  816..819 spare zero element (borrowed as scratch by the renderer)

Indexed grid access (the fun part)
----------------------------------
To touch element i at runtime, a counter walks the a-lane leaving a trail of
breadcrumb 1s while the payload rides along the b-lane:
    [-[->>>>+<<<<]+>[->>>>+<<<<]>>>]
At the target the op does its work, then a token walks the b-lane home,
eating the breadcrumbs, and always lands on cell 28:
    [->>>>>[-<<<<+>>>>]<<<<<<<<<]
So every indexed op starts and ends at statically known cells even though
the index is only known at runtime.
"""

from __future__ import annotations

import os
from contextlib import contextmanager

# ---------------------------------------------------------------- memory map
T0, T1, T2, T3, T4, T5 = 0, 1, 2, 3, 4, 5
X, Y, DIR, LEN, SEED, FI, ALIVE, RAW, HI, GREW = 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
T6, T7, CHR, T8, T9 = 16, 17, 18, 19, 20
R = 28          # array result / landing cell
A0, B0 = 32, 33  # a/b lanes of element 0 (op arguments are loaded here)

W = 14                 # playfield is W x W inside a 16x16 wall frame
NELEM = W * W          # 196


def ACELL(k: int) -> int:
    return 32 + 4 * k


def VCELL(k: int) -> int:
    return ACELL(k) + 3


def FCELL(k: int) -> int:
    return ACELL(k) + 2


CH_WALL, CH_SNAKE, CH_FOOD, CH_EMPTY, NL, FF = 35, 79, 42, 32, 10, 12

# LCG for food placement: full period mod 256 (a % 4 == 1, c odd)
LCG_A, LCG_C = 5, 17
SEED0 = 91
START_X, START_Y, START_LEN, START_DIR = 7, 7, 3, 4
FOOD0 = 7 * W + 10     # (x=10, y=7): three ticks straight ahead of the head

WALK_OUT = "[-[->>>>+<<<<]+>[->>>>+<<<<]>>>]"
WALK_BACK = "[->>>>>[-<<<<+>>>>]<<<<<<<<<]"


class Gen:
    """Emits BrainFuck while statically tracking the tape pointer."""

    def __init__(self) -> None:
        self.buf: list[str] = []
        self.pos = 0
        self.depth = 0

    # -- raw emission ------------------------------------------------------
    def raw(self, s: str) -> None:
        """Emit code that is pointer-neutral or pure +-.,[] at current cell."""
        for c in s:
            if c in "<>":
                raise ValueError("raw() may not move the pointer; use goto()")
        self.depth += s.count("[") - s.count("]")
        self.buf.append(s)

    def raw_seq(self, s: str, end: int) -> None:
        """Emit a trusted sequence whose net pointer end position is `end`."""
        self.depth += s.count("[") - s.count("]")
        self.buf.append(s)
        self.pos = end

    def goto(self, cell: int) -> None:
        d = cell - self.pos
        self.buf.append(">" * d if d > 0 else "<" * (-d))
        self.pos = cell

    # -- arithmetic --------------------------------------------------------
    def add(self, cell: int, n: int) -> None:
        n %= 256
        if n == 0:
            return
        self.goto(cell)
        self.buf.append("+" * n if n <= 128 else "-" * (256 - n))

    def set(self, cell: int, n: int) -> None:
        self.goto(cell)
        self.raw("[-]")
        self.add(cell, n)

    # -- control flow ------------------------------------------------------
    @contextmanager
    def loop(self, cell: int):
        """while tape[cell] != 0: body   (body must keep loops balanced)"""
        self.goto(cell)
        self.raw("[")
        yield
        self.goto(cell)
        self.raw("]")

    @contextmanager
    def once(self, cell: int):
        """if tape[cell] != 0: body      (consumes the cell to 0)"""
        self.goto(cell)
        self.raw("[")
        yield
        self.set(cell, 0)
        self.goto(cell)
        self.raw("]")

    def if_else(self, cond: int, tmp: int, then, els) -> None:
        """Consumes cond; tmp must be 0. then/els are 0-arg callables."""
        self.set(tmp, 1)
        with self.once(cond):
            then()
            self.set(tmp, 0)
        with self.once(tmp):
            els()

    # -- data movement -----------------------------------------------------
    def move(self, src: int, *dsts: int) -> None:
        """dst += src for each dst; src ends 0."""
        with self.loop(src):
            self.add(src, -1)
            for d in dsts:
                self.add(d, 1)

    def copy(self, src: int, dst: int, tmp: int) -> None:
        """dst += src, src preserved; tmp must be 0 and ends 0."""
        self.move(src, dst, tmp)
        self.move(tmp, src)

    def eq_const(self, src: int, k: int, out: int, t1: int) -> None:
        """out = (src == k); src preserved; t1 must be 0. out overwritten."""
        self.set(out, 0)
        self.copy(src, out, t1)
        self.add(out, -k)
        self.move(out, t1)      # t1 = src - k (mod 256)
        self.set(out, 1)
        with self.once(t1):
            self.set(out, 0)

    # -- indexed grid ops (sealed: enter at A0, exit at R) -------------------
    def arr_read_v(self) -> None:
        """R = v[A0]; consumes A0. b-lane must be clean (it is, at rest)."""
        self.set(R, 0)
        self.goto(A0)
        self.raw_seq(
            WALK_OUT            # at a_i, crumbs behind
            + ">>>"             # v_i
            + "[-<<+<+>>>]"     # v -> (b_i, a_i)
            + "<<<"             # a_i
            + "[->>>+<<<]"      # restore v from a_i
            + ">+"              # b_i += 1 so the payload is never 0
            + "<<<<<"           # a_(i-1)
            + WALK_BACK         # payload walks home; lands at R
            + ">>>>>"           # b_0
            + "[-<<<<<+>>>>>]"  # b_0 -> R
            + "<<<<<-",         # undo the +1
            end=R,
        )

    def arr_write_v(self) -> None:
        """v[A0] = B0; consumes A0 and B0."""
        self.set(R, 0)
        self.goto(A0)
        self.raw_seq(
            WALK_OUT            # at a_i, payload rode along in b_i
            + ">>>[-]"          # v_i = 0
            + "<<"              # b_i
            + "[->>+<<]"        # b_i -> v_i
            + "+"               # walk-home token
            + "<<<<<"
            + WALK_BACK
            + ">>>>>[-]<<<<<",  # clear token at b_0
            end=R,
        )

    def arr_write_f(self, one: bool) -> None:
        """f[A0] = 1 or 0; consumes A0."""
        self.set(R, 0)
        self.goto(A0)
        self.raw_seq(
            WALK_OUT
            + ">>[-]" + ("+" if one else "")  # f_i = const
            + "<"               # b_i
            + "+"               # walk-home token
            + "<<<<<"
            + WALK_BACK
            + ">>>>>[-]<<<<<",
            end=R,
        )

    # -- output ------------------------------------------------------------
    def out(self, cell: int) -> None:
        self.goto(cell)
        self.raw(".")

    def code(self, width: int = 100) -> str:
        s = "".join(self.buf)
        return "\n".join(s[i:i + width] for i in range(0, len(s), width))


# ------------------------------------------------------------------- pieces
def init(g: Gen) -> None:
    g.add(ALIVE, 1)
    g.add(X, START_X)
    g.add(Y, START_Y)
    g.add(DIR, START_DIR)
    g.add(LEN, START_LEN)
    g.add(SEED, SEED0)
    g.add(FI, FOOD0)
    head = START_Y * W + START_X
    for age in range(START_LEN, 0, -1):          # head..tail ages L..1
        g.add(VCELL(head - (START_LEN - age)), age)
    g.add(FCELL(FOOD0), 1)


def render_cell(g: Gen, k: int) -> None:
    A, B, F = ACELL(k), ACELL(k) + 1, FCELL(k)
    V = VCELL(k)
    NA, NB = ACELL(k + 1), ACELL(k + 1) + 1      # next element's lanes (scratch)
    g.copy(V, B, A)                              # B = age copy, A back to 0
    g.add(NA, 1)
    with g.once(B):                              # snake here
        g.add(A, CH_SNAKE)
        g.set(NA, 0)
    with g.once(NA):                             # empty or food
        g.copy(F, B, A)
        g.add(NB, 1)
        with g.once(B):
            g.add(A, CH_FOOD)
            g.set(NB, 0)
        with g.once(NB):
            g.add(A, CH_EMPTY)
    g.out(A)
    g.set(A, 0)


def render(g: Gen) -> None:
    g.set(CHR, FF)
    g.out(CHR)
    g.set(CHR, CH_WALL)                          # top wall
    for _ in range(W + 2):
        g.out(CHR)
    g.set(CHR, NL)
    g.out(CHR)
    for row in range(W):
        left = ACELL(row * W)                    # print walls from element-local
        g.add(left, CH_WALL)                     # scratch to keep travel short
        g.out(left)
        g.set(left, 0)
        for col in range(W):
            render_cell(g, row * W + col)
        right = ACELL(row * W + W - 1)
        g.add(right, CH_WALL)
        g.out(right)
        g.add(right, NL - CH_WALL)
        g.out(right)
        g.set(right, 0)
    bottom = ACELL(NELEM - 1)                    # bottom wall
    g.add(bottom, CH_WALL)
    for _ in range(W + 2):
        g.out(bottom)
    g.add(bottom, NL - CH_WALL)
    g.out(bottom)
    g.set(bottom, 0)
    g.set(T0, 0)                                 # score bar: LEN wall chars
    g.copy(LEN, T0, T1)
    g.set(CHR, CH_WALL)
    with g.loop(T0):
        g.add(T0, -1)
        g.out(CHR)
    g.set(CHR, NL)
    g.out(CHR)


def age_cell(g: Gen, k: int) -> None:
    A, B, V = ACELL(k), ACELL(k) + 1, VCELL(k)
    g.copy(V, B, A)
    with g.once(B):
        g.add(V, -1)


def spawn(g: Gen) -> None:
    """Place a new food on a random empty cell.

    Rolls the LCG until it lands below 196 on an empty cell. If the snake
    fills the whole board, parks the food at 255 (off-board: you win, play
    out the endgame foodless). Scratch: T1, T4..T9; must not touch T0/T2/T3
    (in use by enclosing guards).
    """
    g.eq_const(LEN, NELEM, T5, T1)
    g.if_else(
        T5, T4,
        then=lambda: g.set(FI, 255),
        els=lambda: _spawn_roll(g),
    )


def _spawn_roll(g: Gen) -> None:
    g.set(T4, 1)
    with g.loop(T4):
        g.set(T4, 0)
        g.set(T5, 0)                             # SEED = SEED*5 + 17
        g.move(SEED, T5)
        with g.loop(T5):
            g.add(T5, -1)
            g.add(SEED, LCG_A)
        g.add(SEED, LCG_C)
        g.set(T6, 0)                             # T6 = candidate index
        g.copy(SEED, T6, T1)
        g.set(T7, 0)                             # T7 = max(cand - 195, 0)
        g.copy(T6, T7, T1)
        g.set(T8, NELEM - 1)
        with g.loop(T8):
            g.add(T8, -1)
            g.set(T9, 0)
            g.copy(T7, T9, T1)
            with g.once(T9):
                g.add(T7, -1)
        g.set(T5, 0)                             # T5 = cand out of range?
        with g.once(T7):
            g.set(T5, 1)
        g.if_else(
            T5, T9,
            then=lambda: g.set(T4, 1),           # out of range: reroll
            els=lambda: _spawn_check(g),
        )


def _spawn_check(g: Gen) -> None:
    g.copy(T6, A0, T1)
    g.arr_read_v()
    g.set(T5, 0)
    with g.once(R):
        g.set(T5, 1)
    g.if_else(
        T5, T9,
        then=lambda: g.set(T4, 1),               # occupied: reroll
        els=lambda: _spawn_commit(g),
    )


def _spawn_commit(g: Gen) -> None:
    g.set(FI, 0)
    g.copy(T6, FI, T1)
    g.copy(FI, A0, T1)
    g.arr_write_f(True)


def tick(g: Gen) -> None:
    g.goto(RAW)
    g.raw(",")                                   # the game clock
    g.set(T0, 0)
    g.copy(RAW, T0, T1)
    g.move(T0, SEED)                             # keystroke timing stirs the RNG
    g.set(T0, 0)
    g.copy(RAW, T0, T1)
    with g.once(T0):                             # a key was pressed
        g.set(T2, 0)                             # T2 = DIR + RAW; exact reversals
        g.copy(DIR, T2, T1)                      # sum to 3 (1+2) or 7 (3+4) and
        g.copy(RAW, T2, T1)                      # are ignored
        g.set(T4, 0)
        g.copy(T2, T4, T1)
        g.add(T4, -3)
        g.set(T3, 1)
        with g.once(T4):
            g.set(T3, 0)
        g.add(T2, -7)
        g.set(T4, 1)
        with g.once(T2):
            g.set(T4, 0)
        g.move(T4, T3)                           # T3 = reversal?
        g.if_else(
            T3, T4,
            then=lambda: None,
            els=lambda: (g.set(DIR, 0), g.copy(RAW, DIR, T1)),
        )
    for d, cell, delta in ((1, Y, -1), (2, Y, 1), (3, X, -1), (4, X, 1)):
        g.eq_const(DIR, d, T2, T1)
        with g.once(T2):
            g.add(cell, delta)
    for cell in (X, Y):                          # walls: leaving 0..13 kills
        for k in (W, 255):
            g.eq_const(cell, k, T2, T1)
            with g.once(T2):
                g.set(ALIVE, 0)
    g.set(T0, 0)
    g.copy(ALIVE, T0, T1)
    with g.once(T0):                             # still alive: update the grid
        g.set(HI, 0)                             # HI = Y*14 + X
        g.set(T2, 0)
        g.copy(Y, T2, T1)
        with g.loop(T2):
            g.add(T2, -1)
            g.add(HI, W)
        g.copy(X, HI, T1)
        g.set(GREW, 0)
        g.set(T2, 0)                             # ate the food?  HI == FI
        g.copy(HI, T2, T1)
        g.set(T3, 0)
        g.copy(FI, T3, T1)
        with g.loop(T3):
            g.add(T3, -1)
            g.add(T2, -1)
        g.set(T4, 1)
        with g.once(T2):
            g.set(T4, 0)
        with g.once(T4):
            g.set(GREW, 1)
            g.add(LEN, 1)
            g.copy(HI, A0, T1)
            g.arr_write_f(False)                 # swallow the marker
        g.set(T2, 0)                             # age every segment, except on
        g.copy(GREW, T2, T1)                     # the tick we grow (tail stays)
        g.set(T3, 1)
        with g.once(T2):
            g.set(T3, 0)
        with g.once(T3):
            for k in range(NELEM):
                age_cell(g, k)
        g.copy(HI, A0, T1)                       # bit ourselves?
        g.arr_read_v()
        with g.once(R):
            g.set(ALIVE, 0)
        g.set(T2, 0)
        g.copy(ALIVE, T2, T1)
        with g.once(T2):
            g.copy(HI, A0, T1)                   # stamp the head
            g.copy(LEN, B0, T1)
            g.arr_write_v()
            g.set(T3, 0)
            g.copy(GREW, T3, T1)
            with g.once(T3):
                spawn(g)


def banner(g: Gen) -> None:
    for ch in "\n*** GAME OVER ***\n":
        g.set(CHR, ord(ch))
        g.out(CHR)


def gen() -> str:
    g = Gen()
    init(g)
    with g.loop(ALIVE):
        render(g)
        tick(g)
    banner(g)
    assert g.depth == 0, f"unbalanced brackets: depth {g.depth}"
    return g.code()


HEADER = """\
SNAKE in pure BrainFuck
16x16 walled board and a 14x14 playfield of 4 cell elements on the tape
one input byte per tick is the game clock: 0 coast 1 up 2 down 3 left 4 right
emitted by tools/gen_snake py which documents the tape layout and caravans
"""


def main() -> None:
    code = gen()
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "snake.bf")
    with open(path, "w") as fh:
        fh.write(HEADER)
        fh.write(code)
        fh.write("\n")
    ops = sum(code.count(c) for c in "+-<>[],.")
    print(f"snake.bf written: {ops} operations, {len(code)} bytes")


if __name__ == "__main__":
    main()
