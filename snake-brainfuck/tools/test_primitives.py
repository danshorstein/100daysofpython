#!/usr/bin/env python3
"""Unit probes for the Gen primitives, especially the caravan array ops."""

import sys

from bf import BF
from gen_snake import A0, B0, R, VCELL, FCELL, Gen, NELEM

FAILURES = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok  {name}")
    else:
        print(f"FAIL  {name}  {detail}")
        FAILURES.append(name)


def run(g: Gen, inputs=None, max_steps=50_000_000) -> BF:
    m = BF(g.code())
    if inputs:
        m.feed(*inputs)
    status = m.run(max_steps)
    assert status == "halt", f"probe did not halt: {status}"
    return m


def test_move_copy_eq():
    g = Gen()
    g.set(0, 7)
    g.copy(0, 3, 4)          # 3 = 7, 0 preserved
    g.move(3, 5)             # 5 = 7
    g.eq_const(0, 7, 6, 4)   # 6 = 1
    g.eq_const(0, 8, 7, 4)   # 7 = 0
    g.eq_const(0, 255, 8, 4) # 8 = 0 (tests the mod-256 add path)
    m = run(g)
    check("copy+move", m.tape[0] == 7 and m.tape[3] == 0 and m.tape[5] == 7,
          f"tape={list(m.tape[:9])}")
    check("eq_const true", m.tape[6] == 1)
    check("eq_const false", m.tape[7] == 0 and m.tape[8] == 0)


def test_if_else():
    for cond, expect in ((0, 20), (5, 10)):
        g = Gen()
        g.set(0, cond)
        g.if_else(0, 1,
                  then=lambda: g.set(2, 10),
                  els=lambda: g.set(2, 20))
        m = run(g)
        check(f"if_else cond={cond}", m.tape[2] == expect and m.tape[0] == 0
              and m.tape[1] == 0, f"tape={list(m.tape[:3])}")


def probe_array(i, wval):
    """Write wval to v[i] via the caravan, then read it back and `.` it.
    Also pre-poke neighbours directly to prove they survive."""
    g = Gen()
    # sentinel values in nearby elements, poked at fixed addresses
    sentinels = {k: val
                 for k, val in ((0, 11), (1, 22), (i - 1, 33), (i + 1, 44),
                                (NELEM - 1, 55))
                 if 0 <= k < NELEM and k != i}
    for k, val in sentinels.items():
        g.set(VCELL(k), val)
    g.set(21, i)          # index staged in a scalar cell
    g.copy(21, A0, 22)
    g.set(B0, wval)       # payload staged directly in the b lane
    g.arr_write_v()
    g.set(21, i)
    g.copy(21, A0, 22)
    g.arr_read_v()
    g.out(R)
    m = run(g)
    got = m.out[-1] if m.out else None
    ok = got == wval
    # verify sentinels intact and lanes clean
    for k, val in sentinels.items():
        ok = ok and m.tape[VCELL(k)] == val
    lanes_clean = all(m.tape[a] == 0 and m.tape[a + 1] == 0
                      for a in (32 + 4 * k for k in range(NELEM)))
    check(f"array rw i={i} val={wval}", ok and lanes_clean,
          f"got={got} lanes_clean={lanes_clean}")


def test_write_f():
    g = Gen()
    g.set(21, 100)
    g.copy(21, A0, 22)
    g.arr_write_f(True)
    g.set(21, 100)
    g.copy(21, A0, 22)  # hmm: 21 consumed by copy? copy preserves src
    m = run(g)
    check("write_f sets marker", m.tape[FCELL(100)] == 1,
          f"f={m.tape[FCELL(100)]}")
    g2 = Gen()
    g2.set(21, 100)
    g2.copy(21, A0, 22)
    g2.arr_write_f(True)
    g2.set(21, 0)
    g2.set(21, 100)
    g2.copy(21, A0, 22)
    g2.arr_write_f(False)
    m2 = run(g2)
    check("write_f clears marker", m2.tape[FCELL(100)] == 0)


def main():
    test_move_copy_eq()
    test_if_else()
    for i in (0, 1, 7, 100, NELEM - 1):
        probe_array(i, wval=(i * 3 + 5) % 200 + 1)
    test_write_f()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {FAILURES}")
        sys.exit(1)
    print("all primitive probes passed")


if __name__ == "__main__":
    main()
