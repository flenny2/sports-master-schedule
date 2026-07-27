#!/usr/bin/env python3
"""Measure and screenshot the RUNNING app's phone calendar at a true 390px.

    python3 app.py &                          # in one shell
    python3 tools/qa-phone-calendar.py        # in another

Why a proxy instead of just pointing Chrome at the app:

  Headless Chrome will not give a viewport narrower than 500px on Linux
  (measured 2026-07-26, v150, both headless modes), so a phone pass run
  that way silently measures 500px. Putting the app in an iframe fixes
  the width, but reading into that iframe needs SAME ORIGIN — and the
  harness page and the app would otherwise be on different ports.

  So this server does both jobs from one origin: it serves the harness
  page out of docs/overnight/mockups/ and forwards everything else to
  the Flask app. The harness can then touch the app's real DOM, click a
  real day cell, and assert what actually moved.

Stdlib only. Read-only against the app: it drives GETs and one click,
and touches no user-data endpoint, so there is nothing to wipe after.
"""

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
FOLD = 844
LOCAL_FILES = {"/qa-frame.html", "/frame.html"}

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
                ctype = up.headers.get("Content-Type", "application/octet-stream")
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        except urllib.error.HTTPError as e:
            body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:  # app down, ESPN hung, etc.
            msg = f"proxy error: {e}".encode()
            self.send_response(502)
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)


class Server(socketserver.ThreadingTCPServer):
    """Threaded: the harness page and the app's own XHRs are concurrent."""

    daemon_threads = True
    allow_reuse_address = True


def chrome(args, timeout=240):
    with tempfile.TemporaryDirectory() as profile:
        cmd = [
            CHROME, "--headless", "--disable-gpu", "--no-sandbox",
            "--hide-scrollbars", "--user-data-dir=" + profile,
            "--virtual-time-budget=30000",
            "--run-all-compositor-stages-before-draw",
        ] + args
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout).stdout


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

    try:
        qa = (f"http://127.0.0.1:{port}/qa-frame.html"
              f"?w={WIDTH}&src=" + urllib.parse.quote("/#week", safe=""))
        html = chrome([f"--window-size={WIDTH + 130},2200", "--dump-dom", qa])
        m = re.search(r'<pre id="qa-out"[^>]*>(.*?)</pre>', html, re.S)
        if not m:
            print("!! no harness output — the page did not run")
            return 1

        import html as htmlmod
        report = htmlmod.unescape(m.group(1)).strip()
        for line in report.splitlines():
            print("  " + line)

        for name, frag in (("calendar", "/#week"), ("home", "/#front")):
            url = (f"http://127.0.0.1:{port}/qa-frame.html"
                   f"?w={WIDTH}&src=" + urllib.parse.quote(frag, safe=""))
            path = os.path.join(SHOTS, f"sms-3-{name}-390.png")
            chrome([f"--window-size={WIDTH + 130},{FOLD + 60}",
                    "--screenshot=" + path, url])
            print(f"  shot  {os.path.relpath(path, REPO)}")

        return 0 if "RESULT: ALL PASS" in report else 1
    finally:
        httpd.shutdown()


if __name__ == "__main__":
    sys.exit(main())
