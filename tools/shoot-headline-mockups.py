#!/usr/bin/env python3
"""Shoot both off-season headline variants at a true 390px.

    python3 app.py &                             # in one shell
    python3 tools/shoot-headline-mockups.py      # in another

The variants are transformations of the RUNNING app (see
docs/overnight/mockups/headline-variants.html) rather than a parallel
stylesheet, so the shots cannot drift from what shipping would look like.
The one-origin proxy and headless runner live in tools/phone_harness.py.

Read-only against the app: GETs only, no user-data endpoint touched.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phone_harness import Harness, WIDTH   # noqa: E402

PAGE = "/headline-variants.html"

VARIANTS = [
    ("a", "sms-5-headline-a-nextgame"),
    ("b", "sms-5-headline-b-countdown"),
]


def main():
    failed = False
    with Harness({PAGE}) as h:
        for variant, name in VARIANTS:
            path = f"{PAGE}?w={WIDTH}&v={variant}"
            report = h.report(path, height=1200) or "(no report)"
            print(f"  {variant}: {report}")
            # The harness reports its own failure in words; a shot of a
            # half-built page is worse than no shot, so stop at the report.
            if "variant " + variant not in report:
                failed = True
                continue
            print("  shot  " + h.shot(path, name + ".png", height=2000))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
