#!/usr/bin/env python3
"""Measure the RUNNING app's game cards at a true 390px.

    python3 app.py &                      # in one shell
    python3 tools/qa-phone-cards.py       # in another
    python3 tools/qa-phone-cards.py --shot <name>   # + an open-card shot

Third of the phone harnesses, after the calendar (month grid) and the chrome
(the frame around every view). This one asks how much of a game CARD survives
390px — collapsed and expanded — and it counts two different losses:
text cut with no ellipsis (silently gone) and text cut with one (announced,
but still unreadable on your phone). Only the first fails.

Shared plumbing in tools/phone_harness.py. Read-only against the app: GETs
plus card clicks, no user-data endpoint touched.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phone_harness import Harness, WIDTH   # noqa: E402

PAGE = "/qa-cards.html"


def main():
    with Harness({PAGE}) as h:
        qa = f"{PAGE}?w={WIDTH}"
        report = h.report(qa, height=3000)
        if report is None:
            print("!! no harness output — the page did not run")
            return 1
        for line in report.splitlines():
            print("  " + line)

        if len(sys.argv) > 1 and sys.argv[1] == "--shot":
            name = sys.argv[2] if len(sys.argv) > 2 else "cards-390"
            # Leave the first card open: the expanded state is where the
            # density question actually bites, and a closed-card shot shows
            # none of it.
            # Tall on purpose: the day list sits below a full month grid, so
            # a fold-height shot shows the grid and none of the open card.
            print("  shot  " + h.shot(qa + "&expand=1", name + ".png",
                                      height=2600))

        return 0 if "RESULT: ALL PASS" in report else 1


if __name__ == "__main__":
    sys.exit(main())
