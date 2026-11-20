#!/usr/bin/env python3
"""lmexp canvas helper.

Serves the drawing page on localhost, opens it in a browser window and waits
for the picture. Prints exactly one result line on stdout:

    SAVED <path to png>   the person pressed Ctrl+Enter
    CANCELLED             the person closed the canvas
    ERROR <reason>

Usage: canvas.py <output directory>
Set LMEXP_NO_BROWSER=1 to print the URL on stderr instead of opening a window.
"""

import os
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 30 * 1024 * 1024
KEEP_SECONDS = 7 * 24 * 3600
BROWSERS = ("chromium", "google-chrome-stable", "google-chrome", "brave", "microsoft-edge-stable")

here = Path(__file__).resolve().parent
token = secrets.token_urlsafe(16)
result = {"line": None}
done = threading.Event()


def finish(line):
    if result["line"] is None:
        result["line"] = line
        done.set()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body=b"", content_type="text/plain; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != f"/{token}/":
            return self.reply(404)
        self.reply(200, (here / "canvas.html").read_bytes(), "text/html; charset=utf-8")

    def do_POST(self):
        if self.path == f"/{token}/cancel":
            self.reply(200)
            return finish("CANCELLED")
        if self.path != f"/{token}/submit":
            return self.reply(404)
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= MAX_BYTES:
            return self.reply(413, b"picture too large")
        data = self.rfile.read(length)
        if not data.startswith(PNG_MAGIC):
            return self.reply(400, b"not a png")
        path = self.server.out_dir / time.strftime("lmexp-%Y%m%d-%H%M%S.png")
        path.write_bytes(data)
        self.reply(200)
        finish(f"SAVED {path}")


def prune(out_dir):
    cutoff = time.time() - KEEP_SECONDS
    for old in out_dir.glob("lmexp-*.png"):
        try:
            if old.stat().st_mtime < cutoff:
                old.unlink()
        except OSError:
            pass


def open_browser(url, out_dir):
    """Returns the browser process when its exit means the window closed."""
    for name in BROWSERS:
        exe = shutil.which(name)
        if exe:
            # A profile of its own keeps this window in its own process, so its
            # exit is the window closing and it can be closed from here.
            return subprocess.Popen(
                [
                    exe,
                    f"--app={url}",
                    f"--user-data-dir={out_dir / 'browser-profile'}",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--window-size=1280,860",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    opener = shutil.which("xdg-open") or shutil.which("open")
    if not opener:
        raise RuntimeError("no browser found to open the canvas")
    subprocess.Popen([opener, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return None


def main():
    if len(sys.argv) != 2:
        print("ERROR usage: canvas.py <output directory>", flush=True)
        return 2
    out_dir = Path(sys.argv[1]).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    prune(out_dir)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.out_dir = out_dir
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/{token}/"

    browser = None
    signal.signal(signal.SIGTERM, lambda *_: finish("CANCELLED"))
    try:
        if os.environ.get("LMEXP_NO_BROWSER"):
            print(url, file=sys.stderr, flush=True)
        else:
            browser = open_browser(url, out_dir)
        while not done.wait(0.3):
            if browser is not None and browser.poll() is not None:
                # The window closed; give a submit already on its way a moment.
                if not done.wait(0.5):
                    finish("CANCELLED")
    except KeyboardInterrupt:
        finish("CANCELLED")
    except Exception as error:  # noqa: BLE001
        finish(f"ERROR {error}")
    finally:
        if browser is not None and browser.poll() is None:
            time.sleep(0.4)  # let the page show that it was sent
            browser.terminate()
        server.shutdown()

    print(result["line"], flush=True)
    return 0 if result["line"].startswith("SAVED") else 1


if __name__ == "__main__":
    sys.exit(main())
