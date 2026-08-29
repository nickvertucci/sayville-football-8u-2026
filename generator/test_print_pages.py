#!/usr/bin/env python3
"""Check every play prints on exactly one sheet, and the depth chart on exactly two.

A card that spills onto a second page is not a cosmetic problem: it is a coach at
practice holding page one and looking for the coaching points on page two. The print
CSS pins the diagram to a fixed height so that pagination is the same for a wide play
and a deep one, but that height was measured once by hand and the book has grown a lot
since. So measure it every time instead of trusting the comment.

    python generator/test_print_pages.py            # every play page and the print book
    python generator/test_print_pages.py --quick    # the print book only

Renders with headless Chrome and counts the pages in the PDF it produces. Chrome is
the only dependency and it is the thing that actually prints the book, so nothing else
would be a real answer.
"""

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CHROME_CANDIDATES = [
    Path(os.environ.get("CHROME", "")),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe",
    Path("/usr/bin/google-chrome"),
    Path("/usr/bin/chromium"),
    # Debian and Ubuntu have shipped the binary as chromium-browser for years, and the
    # snap puts it somewhere else again. Without these the test tells a contributor on
    # the most common Linux desktop that Chrome is not installed when it is.
    Path("/usr/bin/chromium-browser"),
    Path("/snap/bin/chromium"),
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
]


def find_chrome() -> Path | None:
    for c in CHROME_CANDIDATES:
        if c and c.is_file():
            return c
    for name in ("google-chrome", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def page_count(pdf: Path) -> int:
    """Pages in a Chrome-produced PDF.

    Chrome writes an uncompressed page tree, so the /Type /Page entries can simply be
    counted. /Count on the root Pages node is the cross-check.
    """
    blob = pdf.read_bytes()
    pages = len(re.findall(rb"/Type\s*/Page[^s]", blob))
    counts = [int(n) for n in re.findall(rb"/Count\s+(\d+)", blob)]
    if counts and max(counts) != pages:
        return max(counts)
    return pages


def stop(proc: subprocess.Popen) -> None:
    """Shut a render down, and the helper processes it forked with it.

    Killing the process we launched is not enough on its own: Chrome forks a zygote, a
    GPU process and a renderer, and on a full run this is called sixty times. Its own
    session means one signal reaches the lot. Windows has no process groups in that
    sense and no run of this test has ever needed them there, so it gets the plain
    terminate.
    """
    if proc.poll() is not None:
        return
    try:
        if hasattr(os, "killpg"):
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        else:
            proc.terminate()
    except (ProcessLookupError, PermissionError):
        return
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass


def render_once(chrome: Path, page: Path, out: Path, profile: Path,
                wait: float = 90.0) -> bool:
    """Render one page and say whether a finished PDF landed.

    Chrome is started and then abandoned rather than waited on. It writes the PDF and
    then, on current builds, simply sits there: the file is complete in a couple of
    seconds and the process never exits at all. Waiting on exit — which is what
    subprocess.run does, timeout or no timeout — therefore hangs for the whole timeout
    on a render that already finished, and the test cannot complete on a machine with
    Chrome 132 or newer. Measured against Chrome 151; the same command on the same page
    ran fine on the builds this test was written against, so the wait was never the
    thing being checked. The PDF is.

    So the file is the signal. Wait for it to appear and for its size to stop moving,
    then shut Chrome down. That also covers the older failure this replaces, where the
    parent exited before the child had flushed and left the caller looking at an empty
    directory — a process that has quit gets a moment to finish writing before it
    counts as a failure.
    """
    proc = subprocess.Popen(
        [
            str(chrome), "--headless", "--disable-gpu", "--no-sandbox",
            f"--user-data-dir={profile}",
            "--no-pdf-header-footer",
            "--virtual-time-budget=8000",
            f"--print-to-pdf={out}",
            page.as_uri(),
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=hasattr(os, "killpg"),
    )
    try:
        deadline = time.time() + wait
        size = -1
        quit_at = None
        while time.time() < deadline:
            if out.exists():
                now = out.stat().st_size
                if now > 0 and now == size:
                    return True
                size = now
            if proc.poll() is not None:
                quit_at = quit_at or time.time()
                if time.time() - quit_at > 5.0:
                    break
            time.sleep(0.25)
        return out.exists() and out.stat().st_size > 0
    finally:
        stop(proc)


def render(chrome: Path, page: Path, out: Path, profile_root: Path) -> int:
    """Page count for one document. Each render gets its own profile — sharing one
    across sequential runs races on the lock file and silently produces nothing."""
    attempts = 4
    for attempt in range(attempts):
        profile = profile_root / f"{page.stem}-{attempt}"
        if out.exists():
            out.unlink()
        if render_once(chrome, page, out, profile):
            return page_count(out)
        # A busy machine — a browser already open, or the previous render still
        # shutting down — makes Chrome give up without writing anything. Back off
        # rather than hammering it, which just fails four times in a row instead of one.
        time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(
        f"Chrome produced no PDF for {page.name} after {attempts} attempts. "
        "Close other Chrome windows and try again."
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true",
                    help="only render print.html, not every play page")
    args = ap.parse_args(argv)

    chrome = find_chrome()
    if not chrome:
        print("Chrome not found — set CHROME=/path/to/chrome. Skipping.", file=sys.stderr)
        return 0

    plays = sorted(ROOT.glob("p-*.html"))
    fronts = sorted(ROOT.glob("d-*.html"))
    expected_book = len(plays) + len(fronts)

    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        profile = tmp

        book = render(chrome, ROOT / "print.html", tmp / "book.pdf", profile)
        print(f"print.html: {book} pages (expected {expected_book})")
        if book != expected_book:
            failures.append(
                f"print.html renders {book} pages, expected {expected_book} — "
                f"{book - expected_book} card(s) spilling onto a second sheet"
            )

        # The depth chart is two sheets by design, one per side of the ball, each
        # carrying both rotations as columns: the offense sheet goes in one pocket
        # and the defense sheet in the other, and neither coordinator is holding a
        # page that is half somebody else's. It used to split the other way, one
        # sheet per rotation — same two sheets, and the count below did not move,
        # but a Purple sheet answered "who is on the field" while leaving "who
        # replaces him" on the other one.
        #
        # It is also the page most likely to drift to three. It grows a row every
        # time a position is added, and each side has gone over by a single row
        # already.
        depth = render(chrome, ROOT / "depth-chart.html", tmp / "depth.pdf", profile)
        print(f"depth-chart.html: {depth} pages (expected 2)")
        if depth != 2:
            failures.append(
                f"depth-chart.html renders {depth} pages, expected 2 — offense and "
                "defense must be one sheet each"
            )

        if not args.quick:
            for page in plays + fronts:
                n = render(chrome, page, tmp / f"{page.stem}.pdf", profile)
                flag = "" if n == 1 else f"  <-- {n} PAGES"
                print(f"  {page.name:<26} {n}{flag}")
                if n != 1:
                    failures.append(f"{page.name} prints on {n} pages, must be 1")

    if failures:
        print(f"\n{len(failures)} failure(s):")
        for f in failures:
            print(f"  {f}")
        return 1
    print("\nEvery card prints on exactly one sheet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
