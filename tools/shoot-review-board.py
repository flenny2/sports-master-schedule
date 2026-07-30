#!/usr/bin/env python3
"""Measure and screenshot the review board at a true 390px.

    python3 tools/build-overnight-artifact.py
    python3 tools/shoot-review-board.py

The board is the surface Dylan actually reads, on a phone, so it gets the
same treatment as the app itself: served over one origin and pinned inside
an iframe, because headless Chrome will not give a viewport narrower than
500px on Linux (measured 2026-07-26, v150).

The assert that matters is horizontal overflow. A proposal can quote a
terminal report or a long path, and a grid item defaults to `min-width:auto`
— so one wide child silently widens the whole page and every line of prose
starts running off the right edge of the phone. That happened on 2026-07-27
and a screenshot is a poor way to notice it: the image is clipped to the
viewport, so the missing words simply are not in the picture.

Stdlib only, no app required — the board is a static file.
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
import urllib.parse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OVERNIGHT = os.path.join(REPO, "docs", "overnight")
SHOTS = os.path.join(OVERNIGHT, "shots")
WIDTH = 390
CHROME = shutil.which("google-chrome") or shutil.which("chromium")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=OVERNIGHT, **kw)

    def log_message(self, *a):
        pass


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


# Measures inside the pinned frame. Kept here rather than in a harness page
# because the board is static: there is nothing to wait for beyond fonts.
PROBE = """
<!DOCTYPE html><html><head><meta charset="utf-8"><title>probe</title>
<style>html,body{margin:0;background:#B8C0CC}
#stage{width:max-content;margin:0 auto}iframe{display:block;border:0}
pre{font:12px monospace;padding:8px}</style></head><body>
<div id="stage"><iframe id="f" src="/review-board.html"></iframe></div>
<pre id="out">running…</pre>
<script>
var W = __W__;
var f = document.getElementById("f");
f.style.width = W + "px"; f.style.height = "844px";
f.addEventListener("load", function () {
    var d = f.contentDocument, w = f.contentWindow;
    function report() {
        var h = Math.max(d.documentElement.scrollHeight, d.body.scrollHeight);
        f.style.height = h + "px";
        var sw = d.documentElement.scrollWidth;
        var pageOk = sw <= w.innerWidth + 1;

        /* The page-level check is NOT enough, and finding that out cost a
           pass: `.prop` sets overflow:hidden for its rounded corners, so a
           child wider than the card is CLIPPED rather than pushing the page
           — scrollWidth stays 390 while whole words are cut off the right
           edge. A screenshot cannot show it either; the missing text simply
           is not in the image. So: any element that is hiding its own
           overflow while having some is a failure, unless it opted into
           scrolling (overflow-x:auto, e.g. the .term terminal quotes). */
        var clipped = [];
        d.querySelectorAll("*").forEach(function (n) {
            var over = n.scrollWidth - n.clientWidth;
            if (over <= 1) return;
            var cs = w.getComputedStyle(n);
            if (cs.overflowX !== "hidden" && cs.overflowX !== "clip") return;
            /* text-overflow:ellipsis is a deliberate truncation with a
               visible "…" — the specimens' team names use it on purpose.
               Clipping with no ellipsis is the silent kind. */
            if (cs.textOverflow === "ellipsis") return;
            clipped.push((n.tagName.toLowerCase() +
                (n.className ? "." + String(n.className).split(" ")[0] : "")) +
                " cuts " + over + "px");
        });

        var ok = pageOk && clipped.length === 0;
        document.getElementById("out").textContent =
            (ok ? "PASS" : "FAIL") + "  page width " + sw + " vs viewport " +
            w.innerWidth + " · height " + h +
            (pageOk ? "" : " · PAGE SCROLLS SIDEWAYS") +
            (clipped.length ? " · text cut off in " + clipped.length +
                              ": " + clipped.slice(0, 4).join(" · ") : "");
        document.title = ok ? "BOARD PASS" : "BOARD FAIL";
    }
    if (d.fonts && d.fonts.ready) d.fonts.ready.then(report, report);
    else setTimeout(report, 500);
});
</script></body></html>
"""


def main():
    if not CHROME:
        sys.exit("google-chrome not found on PATH")
    board = os.path.join(OVERNIGHT, "review-board.html")
    if not os.path.exists(board):
        sys.exit("no review-board.html — run tools/build-overnight-artifact.py")

    probe_path = os.path.join(OVERNIGHT, "board-probe.html")
    with open(probe_path, "w", encoding="utf-8") as fh:
        fh.write(PROBE.replace("__W__", str(WIDTH)))

    httpd = Server(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    url = f"http://127.0.0.1:{port}/board-probe.html"

    try:
        dom = chrome([f"--window-size={WIDTH + 130},1200", "--dump-dom", url])
        m = re.search(r'<pre id="out"[^>]*>(.*?)</pre>', dom, re.S)
        report = (m.group(1).strip() if m else "(no probe output)")
        print("  " + report)

        shot = os.path.join(SHOTS, "review-board-390.png")
        height = int(sys.argv[1]) if len(sys.argv) > 1 else 2600
        chrome([f"--window-size={WIDTH + 130},{height}",
                "--screenshot=" + shot, url])
        print(f"  shot  {os.path.relpath(shot, REPO)}")
        return 0 if report.startswith("PASS") else 1
    finally:
        httpd.shutdown()
        os.remove(probe_path)


if __name__ == "__main__":
    sys.exit(main())
