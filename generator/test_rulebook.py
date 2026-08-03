#!/usr/bin/env python3
"""Check the rules page still says exactly what the rulebook says.

The value of that page is that it can be read aloud to an official. That only holds if
nobody has quietly reworded it, and the page is generated through a renderer that wraps
the text in a good deal of markup — headings split into two spans, rule numbers turned
into chips, list markers pulled out for hanging indents. All of that is presentation and
none of it may change a character.

So: strip every tag out of the rendered block and compare what is left to the extracted
text, character for character with whitespace normalised. Then confirm the officers'
names are gone from both.

    python generator/test_rulebook.py

No dependencies. Run it after touching rulebook_html(), the print or page CSS, or
extract_rulebook.py.
"""

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import site_build  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def squeeze(s: str) -> str:
    return re.sub(r"\s+", "", s)


def rendered_text(page: str) -> str:
    """The text a reader sees in the rulebook block, with all markup removed."""
    m = re.search(r'<div class="rulebook">\n(.*?)\n</div>', page, re.S)
    if not m:
        raise SystemExit("rules.html has no rulebook block")
    block = m.group(1)
    # Drop the back-to-top links — they are navigation we added, not the document.
    block = re.sub(r'<a class="rb-top".*?</a>', "", block, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", block))


def main() -> int:
    source = (ROOT / "rulebook" / site_build.RULEBOOK_TXT).read_text(encoding="utf-8")
    page = (ROOT / "rules.html").read_text(encoding="utf-8")
    problems = []

    want, got = squeeze(source), squeeze(rendered_text(page))
    if want != got:
        problems.append(
            f"the page reproduces {len(got):,} characters, the source has {len(want):,}"
        )
        # Point at the first divergence rather than making somebody diff 52,000 chars.
        for i, (a, b) in enumerate(zip(want, got)):
            if a != b:
                problems.append(f"first difference at character {i}: "
                                f"source {want[i:i+60]!r} vs page {got[i:i+60]!r}")
                break

    # Redaction has to hold in both the extracted text and the page built from it.
    from extract_rulebook import REDACTED_NAMES  # noqa: E402
    for name in REDACTED_NAMES:
        for label, blob in (("the extracted text", source), ("rules.html", page)):
            if name in blob:
                problems.append(f"{label} still contains the officer name {name!r}")
        surname = name.split()[-1].rstrip(".")
        for label, blob in (("the extracted text", source), ("rules.html", page)):
            if surname in blob:
                problems.append(f"{label} still contains the surname {surname!r}")

    # The roles are the part worth keeping, so notice if a redaction ate them.
    for role in ("SCPAL Football President", "SCPAL Police Officer"):
        if role not in source:
            problems.append(f"redaction removed the role {role!r} as well as the name")

    if problems:
        print(f"{len(problems)} problem(s):")
        for p in problems:
            print(f"  {p}")
        return 1
    print(f"rules.html reproduces all {len(want):,} characters of the rulebook; "
          f"{len(REDACTED_NAMES)} officer names removed, roles intact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
