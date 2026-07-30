#!/usr/bin/env python3
"""Measure the RUNNING app's phone CHROME at a true 390px.

    python3 app.py &                        # in one shell
    python3 tools/qa-phone-chrome.py        # in another
    python3 tools/qa-phone-chrome.py --shot <name>   # + a notch simulation

Sibling of tools/qa-phone-calendar.py — same one-origin proxy (now shared,
tools/phone_harness.py), different asserts. That one measures the Calendar's
month grid; this one measures the frame around every view: masthead, sticky
tab bar, filter pills, month arrows, footer, plus the two things only a phone
has — safe areas (notch, home indicator) and a ~44px fingertip.

Read-only against the app: GETs plus tab clicks, no user-data endpoint is
touched, so there is nothing to wipe afterwards.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phone_harness import Harness, WIDTH, FOLD, REPO   # noqa: E402

PAGE = "/qa-chrome.html"


def main():
    with Harness({PAGE, "/qa-frame.html", "/frame.html"}) as h:
        qa = f"{PAGE}?w={WIDTH}"
        report = h.report(qa, height=2600)
        if report is None:
            print("!! no harness output — the page did not run")
            return 1
        for line in report.splitlines():
            print("  " + line)

        if len(sys.argv) > 1 and sys.argv[1] == "--shot":
            # Notch simulation, scrolled far enough that the tab bar is
            # pinned — the only state where the tabs can hide behind the
            # status bar. Named on the command line so a before/after pair
            # is two runs of the same command against two stylesheets.
            name = sys.argv[2] if len(sys.argv) > 2 else "chrome-safearea"
            print("  shot  " + h.shot(qa + "&sa=1&scroll=700",
                                      name + ".png", height=FOLD + 90))

        return 0 if "RESULT: ALL PASS" in report else 1


if __name__ == "__main__":
    sys.exit(main())
