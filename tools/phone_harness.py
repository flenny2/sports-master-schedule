"""Shared plumbing for the 390px phone harnesses.

Extracted 2026-07-27, when a fourth driver was about to paste the same proxy
server for the fourth time. The drivers themselves stay separate — each asks
a different question of the app — but they all need the same two things,
and both exist for reasons worth stating once rather than in four copies:

  1. A TRUE 390px viewport. `google-chrome --headless --window-size=390,844`
     does not give one: Chrome clamps its window to a 500px minimum on Linux
     (measured 2026-07-26, v150, both headless modes), so a phone pass driven
     that way silently measures 500px and reports green on a layout that
     breaks at 390. The fix is an iframe, which has no such clamp.

  2. ONE ORIGIN. Reading into that iframe needs same-origin, and the harness
     page and the Flask app would otherwise be on different ports. So the
     server below serves the harness pages out of docs/overnight/mockups/
     and forwards everything else to the app.

Stdlib only, no new dependencies. Import as:

    from phone_harness import Harness, WIDTH
"""

import http.server
import html as htmlmod
import os
import re
import shutil
import socketserver
import subprocess
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
FOLD = 844                 # iPhone 14/15 logical viewport height

CHROME = shutil.which("google-chrome") or shutil.which("chromium")


def _make_proxy(local_files):
    class Proxy(http.server.SimpleHTTPRequestHandler):
        """Serve the harness page locally; forward everything else to the app."""

        def __init__(self, *a, **kw):
            super().__init__(*a, directory=MOCKUPS, **kw)

        def log_message(self, *a):
            pass

        def do_GET(self):
            path = urllib.parse.urlparse(self.path).path
            if path in local_files:
                return super().do_GET()
            try:
                with urllib.request.urlopen(APP + self.path, timeout=120) as up:
                    body = up.read()
                    self.send_response(up.status)
                    self.send_header(
                        "Content-Type",
                        up.headers.get("Content-Type", "application/octet-stream"))
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
            except urllib.error.HTTPError as e:
                body = e.read()
                self.send_response(e.code)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:      # app down, ESPN hung, etc.
                msg = f"proxy error: {e}".encode()
                self.send_response(502)
                self.send_header("Content-Length", str(len(msg)))
                self.end_headers()
                self.wfile.write(msg)

    return Proxy


class _Server(socketserver.ThreadingTCPServer):
    """Threaded: the harness page and the app's own XHRs are concurrent."""

    daemon_threads = True
    allow_reuse_address = True


class Harness:
    """A one-origin proxy plus a headless Chrome runner.

    Use as a context manager so the server is always shut down:

        with Harness({"/qa-cards.html"}) as h:
            report = h.report("/qa-cards.html?w=390")
            h.shot("/qa-cards.html?w=390", "sms-8-cards.png")
    """

    def __init__(self, local_files, require_app=True):
        if not CHROME:
            raise SystemExit("google-chrome not found on PATH")
        if require_app:
            try:
                urllib.request.urlopen(APP + "/", timeout=15)
            except Exception as e:
                raise SystemExit(
                    f"the app is not answering on {APP} — start it with "
                    f"`python3 app.py` first ({e})")
        os.makedirs(SHOTS, exist_ok=True)
        self._httpd = _Server(("127.0.0.1", 0), _make_proxy(set(local_files)))
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()
        self.port = self._httpd.server_address[1]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._httpd.shutdown()

    def url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def chrome(self, args, timeout=300):
        """One headless run in a throwaway profile."""
        with tempfile.TemporaryDirectory() as profile:
            cmd = [
                CHROME, "--headless", "--disable-gpu", "--no-sandbox",
                "--hide-scrollbars", "--user-data-dir=" + profile,
                "--virtual-time-budget=45000",
                "--run-all-compositor-stages-before-draw",
            ] + args
            return subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=timeout).stdout

    def report(self, path, out_id="qa-out", height=2600):
        """Run the harness page and return the text it wrote into `out_id`.

        Returns None when the element is absent, which means the page did not
        run at all — a distinct failure from "ran and reported problems", and
        worth telling apart in the caller.
        """
        dom = self.chrome([f"--window-size={WIDTH + 130},{height}",
                           "--dump-dom", self.url(path)])
        m = re.search(r'<pre id="%s"[^>]*>(.*?)</pre>' % re.escape(out_id),
                      dom, re.S)
        return htmlmod.unescape(m.group(1)).strip() if m else None

    def shot(self, path, name, height=None):
        """Screenshot the harness page; returns the repo-relative path."""
        target = os.path.join(SHOTS, name)
        self.chrome([f"--window-size={WIDTH + 130},{height or FOLD + 60}",
                     "--screenshot=" + target, self.url(path)])
        return os.path.relpath(target, REPO)
