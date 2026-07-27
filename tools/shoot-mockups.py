#!/usr/bin/env python3
"""Measure and screenshot the overnight calendar mockups at a true phone width.

Run from the repo root:  python3 tools/shoot-mockups.py

What it does, and why each step is there:

1. Serves `docs/overnight/mockups/` over a local HTTP server. The frame
   harness has to read inside its own iframe, and file:// iframes are
   cross-origin in Chrome, so the pages must share an http:// origin.

2. Loads each page inside `frame.html`, which pins it to 390px. Passing
   `--window-size=390,844` to headless Chrome does NOT produce a 390px
   viewport: Chrome clamps its window to a 500px minimum on Linux, which
   was measured on 2026-07-26 and silently widened an entire first pass.
   The iframe has no clamp.

3. Runs the measurement probe first and prints its report. A screenshot
   cannot show a sideways scroll (the image is clipped to the viewport)
   or a sub-44px tap target, so the numbers are the real check and the
   picture is for Dylan.

4. Shoots each mockup twice — once at its natural height so the whole
   page is in one image, once at 844px for the above-the-fold view,
   which is the only part that answers "can I see the next few weeks at
   a glance".

Stdlib only. No new dependencies (lane fence 4).
"""

import http.server
import json
import os
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import urllib.parse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOCKUPS = os.path.join(REPO, "docs", "overnight", "mockups")
SHOTS = os.path.join(REPO, "docs", "overnight", "shots")
WIDTH = 390
FOLD_HEIGHT = 844          # iPhone 14/15 logical viewport height

CHROME = shutil.which("google-chrome") or shutil.which("chromium")

TARGETS = [
    ("sms-1-mockup-a-replace", "calendar-a-replace.html", "replace"),
    ("sms-1-mockup-b-both", "calendar-b-both.html", "both"),
]


def serve(directory):
    """Start a quiet static server on an ephemeral port; return (port, httpd)."""
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=directory, **kw)

        def log_message(self, *a):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd.server_address[1], httpd


def chrome(args, timeout=90):
    """Run headless Chrome with a throwaway profile and return stdout."""
    with tempfile.TemporaryDirectory() as profile:
        cmd = [
            CHROME, "--headless", "--disable-gpu", "--no-sandbox",
            "--hide-scrollbars", "--user-data-dir=" + profile,
            # Chrome will not paint a font it has not finished loading;
            # the budget gives the inlined woff2 faces time to decode.
            "--virtual-time-budget=6000",
            "--run-all-compositor-stages-before-draw",
        ] + args
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return out.stdout


def frame_url(port, page, width, height):
    src = urllib.parse.quote(page, safe="")
    return (f"http://127.0.0.1:{port}/frame.html"
            f"?w={width}&h={height}&src={src}")


def dump(port, page, width):
    """Load `page` inside the frame and return the frame's report text."""
    url = frame_url(port, page, width, FOLD_HEIGHT)
    html = chrome(["--window-size=%d,%d" % (width + 120, 2000), "--dump-dom", url])
    m = re.search(r'<pre id="frame-out"[^>]*>(.*?)</pre>', html, re.S)
    if not m:
        return None
    import html as htmlmod
    return htmlmod.unescape(m.group(1)).strip()


def shoot(port, page, width, height, out_path):
    url = frame_url(port, page, width, height)
    chrome([
        "--window-size=%d,%d" % (width + 120, height),
        "--screenshot=" + out_path,
        url,
    ])
    return os.path.exists(out_path)


def main():
    if not CHROME:
        sys.exit("google-chrome not found on PATH")
    os.makedirs(SHOTS, exist_ok=True)
    port, httpd = serve(MOCKUPS)
    failures = 0

    try:
        for slug, page, mode in TARGETS:
            print("=" * 66)
            print(slug)
            print("=" * 66)

            report = dump(port, f"probe.html?mode={mode}", WIDTH)
            if not report:
                print("  !! no probe output")
                failures += 1
                continue
            for line in report.splitlines():
                print("  " + line)
            if "RESULT: ALL PASS" not in report:
                failures += 1

            inner = re.search(r"innerWidth=(\d+)", report)
            if not inner or int(inner.group(1)) != WIDTH:
                print(f"  !! frame did not pin to {WIDTH}px — measurements are not a phone")
                failures += 1

            # Full page: ask the frame how tall the content actually is,
            # then re-shoot the window at that height.
            page_report = dump(port, page, WIDTH)
            height = int(re.search(r"contentHeight=(\d+)", page_report).group(1))

            fold = os.path.join(SHOTS, slug + "-fold.png")
            full = os.path.join(SHOTS, slug + "-full.png")
            shoot(port, page, WIDTH, FOLD_HEIGHT, fold)
            shoot(port, page, WIDTH, min(height + 20, 6000), full)
            print(f"  shot  {os.path.relpath(fold, REPO)}  (390x{FOLD_HEIGHT} fold)")
            print(f"  shot  {os.path.relpath(full, REPO)}  (390x{height} full page)")
    finally:
        httpd.shutdown()

    print()
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
