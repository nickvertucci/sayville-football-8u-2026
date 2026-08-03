#!/usr/bin/env python3
"""Check the call sheet shows the right plays for every filter.

The filtering itself is nine lines of JavaScript and it is not where this goes wrong.
What goes wrong is the data underneath it: a row tagged with the wrong formation, a
chip for a value no play has, or — worst, because it is silent — a play carrying a
value that no chip offers, so the play becomes unreachable the moment anyone filters
by that group.

So this reads the generated calls.html back, compares every row against the play files
it came from, and then runs every single filter and every pair of filters against both,
asserting the same set of plays comes out.

    python generator/test_call_sheet.py

No dependencies, no browser. Run it after touching write_calls(), call_digits() or
anything that feeds them.
"""

import html
import itertools
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render          # noqa: E402
import site_build      # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GROUPS = ["form", "type", "zone", "dir", "carrier"]


def plays_from_source():
    """What the play files say, independently of any HTML."""
    out = {}
    for form in render.load_formations():
        for play in form["_plays"]:
            zone, direction = site_build.call_digits(play.get("call", ""))
            out[play["name"]] = {
                "form": form["id"],
                "type": play.get("type", ""),
                "zone": zone,
                "dir": direction,
                "carrier": play.get("ball_carrier", ""),
            }
    return out


def rows_from_html(page: str):
    """What the built page actually offers the browser."""
    out = {}
    for attrs, body in re.findall(r"<tr ([^>]*data-search[^>]*)>(.*?)</tr>", page, re.S):
        data = dict(re.findall(r'data-([a-z]+)="([^"]*)"', attrs))
        m = re.search(r'<td data-label="Play"><a [^>]*>(.*?)</a>', body)
        if not m:
            continue
        out[html.unescape(m.group(1))] = {g: data.get(g, "") for g in GROUPS}
    return out


def chips_from_html(page: str):
    """group -> the values the page lets you pick."""
    chips = {}
    for group, value in re.findall(
        r'<button class="chip" data-group="([^"]*)" data-value="([^"]*)"', page
    ):
        chips.setdefault(group, []).append(html.unescape(value))
    return chips


def matching(plays: dict, selection: dict) -> set:
    """The spec: OR inside a group, AND across groups. An empty group means 'any'."""
    return {
        name
        for name, p in plays.items()
        if all(not vals or p[g] in vals for g, vals in selection.items())
    }


def main() -> int:
    page = (ROOT / "calls.html").read_text(encoding="utf-8")
    source = plays_from_source()
    rows = rows_from_html(page)
    chips = chips_from_html(page)
    problems = []

    # 1. The page offers exactly the plays the play files define.
    for name in sorted(set(source) - set(rows)):
        problems.append(f"{name}: in the play files but not on the call sheet")
    for name in sorted(set(rows) - set(source)):
        problems.append(f"{name}: on the call sheet but not in the play files")

    # 2. Every row is tagged with what its play file actually says.
    for name in sorted(set(source) & set(rows)):
        for g in GROUPS:
            if source[name][g] != rows[name][g]:
                problems.append(
                    f"{name}: row says {g}={rows[name][g]!r}, "
                    f"the play file says {source[name][g]!r}"
                )

    # 3. No chip that matches nothing, and — the silent one — no play whose value has
    #    no chip, which would hide it from anyone filtering by that group.
    for g in GROUPS:
        offered = set(chips.get(g, []))
        present = {p[g] for p in source.values() if p[g]}
        for dead in sorted(offered - present):
            problems.append(f"chip {g}={dead!r} matches no play")
        for unreachable in sorted(present - offered):
            plays = sorted(n for n, p in source.items() if p[g] == unreachable)
            problems.append(
                f"{g}={unreachable!r} has no chip, so filtering by {g} hides "
                f"{len(plays)} play(s): {', '.join(plays)}"
            )

    # 4. Every single filter, and every pair, gives the same answer from the page's
    #    data as from the play files.
    singles = [{g: [v]} for g in GROUPS for v in chips.get(g, [])]
    pairs = [
        {a: [x], b: [y]}
        for a, b in itertools.combinations(GROUPS, 2)
        for x in chips.get(a, [])
        for y in chips.get(b, [])
    ]
    within = [
        {g: [x, y]}
        for g in GROUPS
        for x, y in itertools.combinations(chips.get(g, []), 2)
    ]
    checked = 0
    for selection in singles + pairs + within:
        checked += 1
        want = matching(source, selection)
        got = matching(rows, selection)
        if want != got:
            problems.append(
                f"{selection}: page shows {len(got)} play(s), the play files say "
                f"{len(want)} — missing {sorted(want - got)}, extra {sorted(got - want)}"
            )

    if problems:
        print(f"{len(problems)} problem(s):\n")
        for p in problems:
            print(f"  {p}")
        return 1
    print(
        f"{len(rows)} plays, {sum(len(v) for v in chips.values())} chips, "
        f"{checked} filter combinations — page and play files agree on every one."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
