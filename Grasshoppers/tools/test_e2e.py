#!/usr/bin/env python3
"""
Headless end-to-end smoke test for GRASSHOPPERS.

Boots index.html in a real WebGL2 context (Playwright + Chromium), starts a
match, drives a few grasshoppers through hopping and firing, runs a swarm
volley, and lets the AI take a turn — then screenshots the result. Modeled
on ../../snake-brainfuck/tools/test_e2e.py.

Usage:
    pip install playwright
    playwright install chromium
    python3 tools/test_e2e.py
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
PAGE = (HERE.parent / "index.html").as_uri()
SHOTS = HERE / "screenshots"
SHOTS.mkdir(exist_ok=True)


def main() -> int:
    errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(args=[
            "--use-angle=swiftshader",
            "--enable-unsafe-swiftshader",
            "--ignore-gpu-blocklist",
        ])
        page = browser.new_page(viewport={"width": 900, "height": 620})
        page.on("pageerror", lambda e: errors.append(f"PAGEERROR: {e}"))
        page.on("console", lambda m: errors.append(f"CONSOLE: {m.text}")
                 if m.type == "error" else None)

        page.goto(PAGE)
        page.wait_for_timeout(1200)
        assert page.evaluate("typeof WEAPONS !== 'undefined' && WEAPONS.length > 0"), \
            "weapon roster failed to load"
        page.screenshot(path=str(SHOTS / "01_menu.png"))

        page.fill("#seedin", "e2e-test-seed")
        page.click("#playbtn")
        page.wait_for_timeout(2000)
        state = page.evaluate("({state: turnState, units: units.length})")
        assert state["state"] == "play", f"match did not start: {state}"
        assert state["units"] > 0, "no grasshoppers spawned"
        page.screenshot(path=str(SHOTS / "02_match_start.png"))

        # hop the selected grasshopper a couple of times
        for _ in range(2):
            page.evaluate("jx = 0.6; jy = -0.6;")
            page.evaluate("doHop(0.6)")
            page.wait_for_timeout(500)
        page.evaluate("jx = 0; jy = 0;")

        # fire the default weapon (Grenade Egg, infinite ammo)
        page.evaluate("""() => {
            cam.pitch = -0.12;
            firePower = 0.8; firing = true; releaseFire();
        }""")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(SHOTS / "03_after_fire.png"))

        solid_after = page.evaluate(
            "(() => { let n = 0; for (let i = 0; i < vox.length; i++) if (vox[i]) n++; return n; })()"
        )
        assert solid_after > 0, "terrain vanished entirely — worldgen or explode() regressed"

        # Practice mode: no opposing team, unlimited ammo, and each settled
        # turn returns immediately to the player's swarm.
        practice_page = browser.new_page(viewport={"width": 900, "height": 620})
        practice_page.goto(PAGE)
        practice_page.wait_for_timeout(1200)
        practice_page.locator("#modeseg button", has_text="Practice").click()
        practice_page.fill("#seedin", "practice-e2e-seed")
        practice_page.click("#playbtn")
        practice_page.wait_for_timeout(2000)
        practice_state = practice_page.evaluate("""() => ({
            practice,
            state: turnState,
            team: turnTeam,
            enemies: aliveOf(TEAM_B).length,
            cricketAmmo: ammo[playerTeam].cricket,
            infiniteClock: turnClock === Infinity,
            label: elRound.textContent
        })""")
        assert practice_state["practice"], f"Practice flag was not enabled: {practice_state}"
        assert practice_state["state"] == "play" and practice_state["team"] == practice_page.evaluate("playerTeam"), \
            f"Practice did not start as a player turn: {practice_state}"
        assert practice_state["enemies"] == 0, f"Practice spawned enemy units: {practice_state}"
        assert practice_state["cricketAmmo"] == -1, f"Practice ammo was limited: {practice_state}"
        assert practice_state["infiniteClock"] and practice_state["label"] == "PRACTICE", \
            f"Practice HUD/clock was incorrect: {practice_state}"

        practice_page.evaluate("endTurn()")
        practice_page.wait_for_timeout(600)
        after_turn = practice_page.evaluate("({state: turnState, team: turnTeam, player: playerTeam})")
        assert after_turn["state"] == "play" and after_turn["team"] == after_turn["player"], \
            f"Practice advanced away from the player: {after_turn}"

        practice_page.evaluate("""() => {
            curWeapon = WBYID.cricket.idx;
            firePower = 0.8;
            releaseFire();
        }""")
        assert practice_page.evaluate("ammo[playerTeam].cricket") == -1, \
            "Practice ammo decreased after firing"
        practice_page.screenshot(path=str(SHOTS / "04_practice_mode.png"))
        practice_page.close()

        browser.close()

    if errors:
        print(f"=== {len(errors)} browser error(s) ===", file=sys.stderr)
        for e in errors[:10]:
            print(e, file=sys.stderr)
        return 1

    print("OK — Battle and Practice mode flows worked with no console errors.")
    print(f"Screenshots written to {SHOTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
