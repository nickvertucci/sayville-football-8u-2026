#!/usr/bin/env python3
"""Check every formation is legal, and that the legality check refuses the ones that are not.

    python generator/test_formations.py

Seven on the line, the man on each end of it eligible, the five inside him not
(NFHS 7-2-1 and 7-2-5, which PAL plays by). The check is `formation_legality` in
render.py; this holds it to the real book and to a handful of deliberately broken
Wildcats, so a check that quietly stopped checking would fail here.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render  # noqa: E402

# (what it is, the spots to move, should the check reject it?)
CASES = [
    ("the Wildcat as drawn", {}, False),
    ("a wing on the line makes eight", {"QB": [-5.6, -0.5]}, True),
    ("the Y a yard off makes six", {"Y": [4.2, -1.5]}, True),
    # Legal: the Z steps up and becomes the end, the Y steps off and becomes a back.
    ("the Z on the line with the Y a yard off", {"Z": [5.6, -0.5], "Y": [4.2, -1.5]}, False),
    # The tackle left on the end and a receiver buried inside the line.
    ("a tackle on the end of the line",
     {"X": [-4.2, -1.5], "Y": [4.2, -1.5], "Z": [5.6, -0.5], "FB": [6.5, -0.5]}, True),
]


def main() -> int:
    forms = render.load_formations()
    bad = 0
    for form in forms:
        for err in render.formation_legality(form):
            print(f"FAIL  {err}")
            bad += 1
    wildcat = next((f for f in forms if f["id"] == "wildcat"), None)
    if wildcat is None:
        print("FAIL  no wildcat formation to break")
        return 1
    for what, move, should_reject in CASES:
        trial = copy.deepcopy(wildcat)
        trial["_plays"] = []
        trial["alignment"].update(move)
        rejected = bool(render.formation_legality(trial))
        if rejected != should_reject:
            print(f"FAIL  {what} was {'rejected' if rejected else 'accepted'}")
            bad += 1
    print(f"{len(forms)} formations legal; {len(CASES)} legality cases behaved as expected "
          f"({sum(c[2] for c in CASES)} rejected, {sum(not c[2] for c in CASES)} accepted).")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
