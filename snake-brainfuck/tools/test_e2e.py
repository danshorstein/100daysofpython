#!/usr/bin/env python3
"""End-to-end browser test: loads index.html in headless Chromium, plays the
game through real key events, and screenshots it. The page's JS is only an
interpreter, so this exercises the BrainFuck program in its natural habitat."""

from __future__ import annotations

import glob
import os
import sys
import time

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = "file://" + os.path.abspath(os.path.join(HERE, "..", "index.html"))

FAILURES = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok  {name}")
    else:
        print(f"FAIL  {name}  {detail}")
        FAILURES.append(name)


def board(page) -> str:
    return page.locator("#screen").text_content()


def snake_cells(text: str) -> set:
    cells = set()
    for y, line in enumerate(text.split("\n")):
        for x, c in enumerate(line):
            if c == "O":
                cells.add((x, y))
    return cells


def chromium_path() -> str | None:
    for pat in ("/opt/pw-browsers/chromium-*/chrome-linux/chrome",
                "/opt/pw-browsers/chromium"):
        hits = glob.glob(pat)
        if hits:
            return hits[0]
    return None


def main():
    errors = []
    with sync_playwright() as pw:
        exe = chromium_path()
        browser = pw.chromium.launch(executable_path=exe) if exe \
            else pw.chromium.launch()
        page = browser.new_page(viewport={"width": 900, "height": 1100})
        page.on("console",
                lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(PAGE)

        # JS predicates over the live board keep the test event-driven: the
        # game clock waits for no one
        MIN_ROW = ("(() => { const L = document.getElementById('screen')"
                   ".textContent.split('\\n'); let m = 99; L.forEach((l,y) =>"
                   " { if (l.includes('O')) m = Math.min(m, y); }); return m;"
                   " })()")
        MIN_COL = ("(() => { const L = document.getElementById('screen')"
                   ".textContent.split('\\n'); let m = 99; L.forEach(l => {"
                   " const i = l.indexOf('O'); if (i >= 0) m = Math.min(m, i);"
                   " }); return m; })()")

        page.wait_for_function(
            "document.getElementById('screen').textContent.includes('####')")
        f0 = board(page)
        check("frame 0 renders", "OOO" in f0 and "*" in f0, repr(f0[:60]))
        check("frame 0 walls", f0.split("\n")[0] == "#" * 16,
              repr(f0.split("\n")[0]))

        page.wait_for_function(             # a couple of ticks: coasts right
            f"{MIN_COL} > 6", timeout=5_000)
        check("snake moves on its own", True)

        row0 = page.evaluate(MIN_ROW)
        page.keyboard.press("ArrowUp")      # steer up and wait for the turn
        page.wait_for_function(f"{MIN_ROW} < {row0}", timeout=5_000)
        check("ArrowUp steers the snake", True)

        col0 = page.evaluate(MIN_COL)
        page.keyboard.press("ArrowLeft")    # then steer left
        page.wait_for_function(f"{MIN_COL} < {col0}", timeout=5_000)
        check("ArrowLeft steers the snake", True)

        page.screenshot(path=os.path.join(HERE, "..", "screenshot.png"))

        page.wait_for_function(             # coasting into the left wall dies
            "document.getElementById('screen').textContent"
            ".includes('GAME OVER')", timeout=15_000)
        check("wall kill shows GAME OVER", True)
        check("death styling applied",
              page.evaluate("document.body.classList.contains('dead')"))
        dead_shot = os.path.join(HERE, "..", "screenshot-dead.png")
        page.screenshot(path=dead_shot)

        page.keyboard.press("r")            # reincarnate
        page.wait_for_timeout(300)
        f3 = board(page)
        check("R restarts", "GAME OVER" not in f3
              and len(snake_cells(f3)) == 3, repr(f3[-60:]))

        stats = page.locator("#s_steps").text_content()
        check("step counter runs", stats not in ("", "0"), stats)
        browser.close()

    check("no console/page errors", not errors, "; ".join(errors[:3]))
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {FAILURES}")
        sys.exit(1)
    print("all e2e browser tests passed")


if __name__ == "__main__":
    main()
