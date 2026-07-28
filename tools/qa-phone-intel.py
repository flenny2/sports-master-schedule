#!/usr/bin/env python3
"""Drive the tactical-read flow at a true 390px, at $0.

    python3 app.py &                      # in one shell
    python3 tools/qa-phone-intel.py       # in another
    python3 tools/qa-phone-intel.py --shot <name>

Fourth phone harness, and the one covering the app's most expensive feature:
pressing the read button spends money on the Anthropic API, and brief D3 makes
it the reason the hub exists. It had never been driven on a phone.

It costs nothing to run. With no ANTHROPIC_API_KEY in the environment the
server returns canned sections in the SAME shape a real read has, so the whole
pipeline — button, background thread, polling, rendering — is exercised without
a token spent. Setting that key is Dylan's step, not a lane's.

It DOES write: a generated read is stored in data/previews.json. That file is
gitignored user data, so the driver removes the row it created afterwards
(headless-qa rule 5 — wipe your tracks on user-data surfaces).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phone_harness import Harness, WIDTH, REPO   # noqa: E402

PAGE = "/qa-intel.html"
STORE = os.path.join(REPO, "data", "previews.json")


def drop_preview(game_id):
    """Remove the row this drive created, leaving any real ones alone."""
    if not game_id or not os.path.exists(STORE):
        return False
    try:
        with open(STORE, encoding="utf-8") as fh:
            data = json.load(fh)
    except (ValueError, OSError):
        return False
    if game_id not in data:
        return False
    del data[game_id]
    with open(STORE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return True


def main():
    with Harness({PAGE}) as h:
        qa = f"{PAGE}?w={WIDTH}"
        report = h.report(qa, height=3000, budget=150000)
        if report is None:
            print("!! no harness output — the page did not run")
            return 1
        for line in report.splitlines():
            print("  " + line)

        if len(sys.argv) > 1 and sys.argv[1] == "--shot":
            name = sys.argv[2] if len(sys.argv) > 2 else "intel-390"
            print("  shot  " + h.shot(qa + "&shot=1", name + ".png",
                                      height=2600, budget=150000))

        # The harness prints the game it drove so the wipe targets exactly
        # that row rather than truncating the whole store.
        drove = ""
        for line in report.splitlines():
            if line.startswith("DROVE GAME:"):
                drove = line.split(":", 1)[1].strip()
        if drop_preview(drove):
            print(f"  wiped  the read this drive generated for game {drove}")

        return 0 if "RESULT: ALL PASS" in report else 1


if __name__ == "__main__":
    sys.exit(main())
