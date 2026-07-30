#!/usr/bin/env python3
"""Measure and screenshot the RUNNING app's phone calendar at a true 390px.

    python3 app.py &                          # in one shell
    python3 tools/qa-phone-calendar.py        # in another

The one-origin proxy and the headless runner live in tools/phone_harness.py,
which explains why both are needed (Chrome clamps its window to 500px on
Linux; reading into the pinned iframe needs same origin). What is left here
is this pass's own question: does the month grid lay out, is it Monday-first,
do the day marks stay inside their cells, and does tapping a day really move
the list underneath it.

Read-only against the app: it drives GETs and one click, and touches no
user-data endpoint, so there is nothing to wipe after.
"""

import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phone_harness import Harness, WIDTH, FOLD   # noqa: E402

PAGE = "/qa-frame.html"


def main():
    with Harness({PAGE, "/frame.html", "/qa-chrome.html"}) as h:
        qa = f"{PAGE}?w={WIDTH}&src=" + urllib.parse.quote("/#week", safe="")
        report = h.report(qa, height=2200)
        if report is None:
            print("!! no harness output — the page did not run")
            return 1
        for line in report.splitlines():
            print("  " + line)

        for name, frag in (("calendar", "/#week"), ("home", "/#front")):
            path = (f"{PAGE}?w={WIDTH}&src="
                    + urllib.parse.quote(frag, safe=""))
            print("  shot  " + h.shot(path, f"sms-3-{name}-390.png",
                                      height=FOLD + 60))

        return 0 if "RESULT: ALL PASS" in report else 1


if __name__ == "__main__":
    sys.exit(main())
