#!/usr/bin/env python3
"""Local dev server: serve the site, rebuild it when a source file changes,
and reload the browser tab you are looking at.

    python generator/dev.py            # http://localhost:8000
    python generator/dev.py --port 8123
    python generator/dev.py --no-open  # don't launch a browser

The generator writes its output into the repo root, which is exactly what
GitHub Pages publishes, so what you see here is the real page - not an
approximation of it. The only thing this script adds to a page is a small
reload script, and it is injected on the way out rather than written to disk,
so nothing it does can end up in a commit.

A build failure does not take the site down. The last good pages stay served
and the error is put on screen, so a half-typed JSON file is a red banner you
can read instead of a blank tab.
"""

from __future__ import annotations

import argparse
import http.server
import json
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RENDER = ROOT / "generator" / "render.py"

# What counts as source. Everything else in the tree is generated from these,
# so watching a generated file would only rebuild what the build just wrote.
WATCH_GLOBS = (
    "playbook/**/*.json",
    "defense/*.json",
    "generator/*.py",
    "rulebook/*.txt",
    "install.json",
    "roster.json",
    "favorites.json",
)

POLL_SECONDS = 0.3
# A save is not always one write. Wait for the tree to hold still before
# rebuilding, so a multi-file save is one build and not five.
SETTLE_SECONDS = 0.25

RELOAD_SNIPPET = """
<script>
(function () {
  var known = null;
  var box = null;
  function overlay(text) {
    if (!text) { if (box) { box.remove(); box = null; } return; }
    if (!box) {
      box = document.createElement('pre');
      box.style.cssText = 'position:fixed;inset:0;z-index:2147483647;margin:0;'
        + 'padding:24px;overflow:auto;background:#3b0d0d;color:#ffd7d7;'
        + 'font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;'
        + 'white-space:pre-wrap';
      document.body.appendChild(box);
    }
    box.textContent = 'Build failed - the page below is the last good build.\\n\\n' + text;
  }
  function poll() {
    fetch('/__dev/status', { cache: 'no-store' })
      .then(function (r) { return r.json(); })
      .then(function (s) {
        if (known === null) { known = s.build; }
        else if (s.build !== known) { location.reload(); return; }
        overlay(s.ok ? null : s.error);
      })
      .catch(function () { /* server restarting; try again next tick */ });
  }
  setInterval(poll, 500);
  poll();
})();
</script>
"""


class Builder:
    """Runs render.py and remembers how the last run went."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.build = 0
        self.ok = True
        self.error = ""

    def status(self) -> bytes:
        with self.lock:
            payload = {"build": self.build, "ok": self.ok, "error": self.error}
        return json.dumps(payload).encode("utf-8")

    def run(self) -> None:
        started = time.monotonic()
        proc = subprocess.run(
            [sys.executable, str(RENDER)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        elapsed = time.monotonic() - started
        with self.lock:
            self.build += 1
            self.ok = proc.returncode == 0
            self.error = "" if self.ok else (proc.stderr or proc.stdout).strip()
        stamp = time.strftime("%H:%M:%S")
        if self.ok:
            last = [ln for ln in proc.stdout.splitlines() if ln.strip()]
            print(f"[{stamp}] built in {elapsed:.1f}s - {last[-1] if last else 'ok'}")
        else:
            print(f"[{stamp}] BUILD FAILED in {elapsed:.1f}s", file=sys.stderr)
            print(self.error, file=sys.stderr)


def snapshot() -> dict[str, float]:
    seen: dict[str, float] = {}
    for pattern in WATCH_GLOBS:
        for path in ROOT.glob(pattern):
            try:
                seen[str(path)] = path.stat().st_mtime
            except OSError:
                pass
    return seen


def watch(builder: Builder, stop: threading.Event) -> None:
    previous = snapshot()
    while not stop.wait(POLL_SECONDS):
        current = snapshot()
        if current == previous:
            continue
        # Let the editor finish writing before reading anything.
        while True:
            time.sleep(SETTLE_SECONDS)
            settled = snapshot()
            if settled == current:
                break
            current = settled
        changed = sorted(
            Path(p).relative_to(ROOT).as_posix()
            for p in set(current) ^ set(previous)
            | {k for k in set(current) & set(previous) if current[k] != previous[k]}
        )
        head = ", ".join(changed[:3]) + (f" (+{len(changed) - 3} more)" if len(changed) > 3 else "")
        print(f"[{time.strftime('%H:%M:%S')}] changed: {head}")
        previous = current
        builder.run()


class Handler(http.server.SimpleHTTPRequestHandler):
    builder: Builder

    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, fmt: str, *args) -> None:
        # One line per file request is noise; the build lines are the signal.
        pass

    def end_headers(self) -> None:
        # A cached page is a page that does not show the edit you just made.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def do_GET(self) -> None:
        if self.path.split("?")[0] == "/__dev/status":
            body = self.builder.status()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        page = self._html_bytes()
        if page is None:
            super().do_GET()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def _html_bytes(self) -> bytes | None:
        """The requested page with the reload script in it, or None if this
        request is not for an HTML page we can read."""
        target = Path(self.translate_path(self.path.split("?")[0]))
        if target.is_dir():
            target = target / "index.html"
        if target.suffix.lower() not in (".html", ".htm") or not target.is_file():
            return None
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        if "</body>" in text:
            text = text.replace("</body>", RELOAD_SNIPPET + "</body>", 1)
        else:
            text += RELOAD_SNIPPET
        return text.encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Serve the site locally and rebuild on change.")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--no-open", action="store_true", help="don't open a browser")
    ap.add_argument("--no-watch", action="store_true", help="serve only, never rebuild")
    args = ap.parse_args()

    builder = Builder()
    print("Building once before serving...")
    builder.run()

    Handler.builder = builder
    server = http.server.ThreadingHTTPServer((args.host, args.port), Handler)

    stop = threading.Event()
    if not args.no_watch:
        threading.Thread(target=watch, args=(builder, stop), daemon=True).start()

    url = f"http://{args.host}:{args.port}/"
    print(f"Serving {ROOT} at {url}")
    print("Edit the JSON under playbook/ or defense/ and the open tab reloads itself.")
    print("Ctrl-C to stop.")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        stop.set()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
