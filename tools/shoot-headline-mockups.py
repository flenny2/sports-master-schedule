#!/usr/bin/env python3
"""Shoot both off-season headline variants at a true 390px.

    python3 app.py &                             # in one shell
    python3 tools/shoot-headline-mockups.py      # in another

The variants are transformations of the RUNNING app (see
docs/overnight/mockups/headline-variants.html), so this proxies the app and
the harness page through one origin — Chrome clamps its window to 500px on
Linux, and reading into the pinned iframe needs same origin.

Read-only against the app: GETs only, no user-data endpoint touched.
Stdlib only, no new dependencies.
"""

import html as htmlmod
import http.server
import os
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOCKUPS = os.path.join(REPO, "docs", "overnight", "mockups")
SHOTS = os.path.join(REPO, "docs", "overnight", "shots")
APP = "http://127.0.0.1:5000"
WIDTH = 390
LOCAL_FILES = {"/headline-variants.html"}

VARIANTS = [
    ("a", "sms-5-headline-a-nextgame"),
    ("b", "sms-5-headline-b-countdown"),
]

CHROME = shutil.which("google-chrome") or shutil.which("chromium")


class Proxy(http.server.SimpleHTTPRequestHandler):
    """Serve the harness page locally; forward everything else to the app."""

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=MOCKUPS, **kw)

    def log_message(self, *a):
        pass

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in LOCAL_FILES:
            return super().do_GET()
        try:
            with urllib.request.urlopen(APP + self.path, timeout=120) as up:
                body = up.read()
                self.send_response(up.status)
                self.send_header("Content-Type",
                                 up.headers.get("Content-Type",
                                                "application/octet-stream"))
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        except urllib.error.HTTPError as e:
            body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            msg = f"proxy error: {e}".encode()
            self.send_response(502)
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


def chrome(args, timeout=300):
    with tempfile.TemporaryDirectory() as profile:
        return subprocess.run([
            CHROME, "--headless", "--disable-gpu", "--no-sandbox",
            "--hide-scrollbars", "--user-data-dir=" + profile,
            "--virtual-time-budget=40000",
            "--run-all-compositor-stages-before-draw",
        ] + args, capture_output=True, text=True, timeout=timeout).stdout


def main():
    if not CHROME:
        sys.exit("google-chrome not found on PATH")
    try:
        urllib.request.urlopen(APP + "/", timeout=15)
    except Exception as e:
        sys.exit(f"the app is not answering on {APP} — start it with "
                 f"`python3 app.py` first ({e})")

    os.makedirs(SHOTS, exist_ok=True)
    httpd = Server(("127.0.0.1", 0), Proxy)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]

    failed = False
    try:
        for variant, name in VARIANTS:
            url = (f"http://127.0.0.1:{port}/headline-variants.html"
                   f"?w={WIDTH}&v={variant}")
            dom = chrome([f"--window-size={WIDTH + 130},1200",
                          "--dump-dom", url])
            m = re.search(r'<pre id="qa-out"[^>]*>(.*?)</pre>', dom, re.S)
            report = htmlmod.unescape(m.group(1)).strip() if m else "(no report)"
            print(f"  {variant}: {report}")
            # The harness reports its own failure in words; a shot of a
            # half-built page is worse than no shot, so stop at the report.
            if "variant " + variant not in report:
                failed = True
                continue
            shot = os.path.join(SHOTS, name + ".png")
            chrome([f"--window-size={WIDTH + 130},2000",
                    "--screenshot=" + shot, url])
            print(f"  shot  {os.path.relpath(shot, REPO)}")
        return 1 if failed else 0
    finally:
        httpd.shutdown()


if __name__ == "__main__":
    sys.exit(main())
