#!/usr/bin/env python3
"""Measure the RUNNING app's phone CHROME at a true 390px.

    python3 app.py &                        # in one shell
    python3 tools/qa-phone-chrome.py        # in another

Sibling of tools/qa-phone-calendar.py — same one-origin proxy, different
asserts. That one measures the Calendar's month grid; this one measures the
frame around every view: masthead, sticky tab bar, filter pills, month
arrows, footer, plus the two things only a phone has — safe areas (notch,
home indicator) and a ~44px fingertip.

Why the proxy at all: headless Chrome will not give a viewport narrower than
500px on Linux (measured 2026-07-26, v150), so the page under test lives in
an iframe pinned to 390px, and reading into that iframe needs same origin.
This server serves the harness page out of docs/overnight/mockups/ and
forwards everything else to Flask, so both sit on one origin.

Stdlib only. Read-only against the app: GETs plus tab clicks, no user-data
endpoint is touched, so there is nothing to wipe afterwards.
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
LOCAL_FILES = {"/qa-chrome.html", "/qa-frame.html", "/frame.html"}

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


def chrome(args, timeout=300):
    with tempfile.TemporaryDirectory() as profile:
        cmd = [
            CHROME, "--headless", "--disable-gpu", "--no-sandbox",
            "--hide-scrollbars", "--user-data-dir=" + profile,
            "--virtual-time-budget=45000",
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
        qa = f"http://127.0.0.1:{port}/qa-chrome.html?w={WIDTH}"
        html = chrome([f"--window-size={WIDTH + 130},2600", "--dump-dom", qa])
        m = re.search(r'<pre id="qa-out"[^>]*>(.*?)</pre>', html, re.S)
        if not m:
            print("!! no harness output — the page did not run")
            return 1

        import html as htmlmod
        report = htmlmod.unescape(m.group(1)).strip()
        for line in report.splitlines():
            print("  " + line)

        if len(sys.argv) > 1 and sys.argv[1] == "--shot":
            # Notch simulation, scrolled far enough that the tab bar is
            # pinned — that is the only state where the tabs can hide
            # behind the status bar. Name it on the command line so a
            # before/after pair is two runs of the same command against
            # two versions of the stylesheet.
            name = sys.argv[2] if len(sys.argv) > 2 else "chrome-safearea"
            shot = os.path.join(SHOTS, name + ".png")
            chrome([f"--window-size={WIDTH + 130},{FOLD + 90}",
                    "--screenshot=" + shot,
                    qa + "&sa=1&scroll=700"])
            print(f"  shot  {os.path.relpath(shot, REPO)}")

        return 0 if "RESULT: ALL PASS" in report else 1
    finally:
        httpd.shutdown()


if __name__ == "__main__":
    sys.exit(main())
