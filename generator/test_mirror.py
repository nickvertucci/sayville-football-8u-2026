#!/usr/bin/env python3
"""Prove the symmetry check would notice a formation that is no longer symmetric.

`mirror_of` turns four lines of JSON into a whole play by flipping a right-handed one.
That is only honest if the formation really is a mirror of itself — otherwise the flipped
play draws two backs standing on spots the formation does not have, and nothing else in
the build notices. The play still has eleven assignments, the call still matches its own
flipped diagram, the card still fits on a sheet.

So this moves one back at a time in a formation that mirrors its plays and fails if
validate_mirror() shrugs.

    python generator/test_mirror.py

No dependencies. Run it after touching validate_mirror(), MIRROR, or a formation's
`mirror` map.
"""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render  # noqa: E402

MIRRORING_FORMATION = "full-house"

# (what it is, how to break the formation, should the check reject it?)
CASES = [
    ("the formation as shipped", lambda f: None, False),

    # The mistake this check exists for: the backfield moves and nobody updates the
    # mirroring, so two backs keep pairings that stopped being reflections.
    ("a paired back moved off his mirror",
     lambda f: f["alignment"].__setitem__("FB", [2.6, -3.3]), True),
    ("a paired back moved to a different depth",
     lambda f: f["alignment"].__setitem__("Z", [-1.4, -4.6]), True),
    ("the back on the middle nudged off it",
     lambda f: f["alignment"].__setitem__("TB", [0.6, -4.2]), True),

    # And the ways the map itself can be wrong.
    ("a back left out of the mirror map",
     lambda f: f["mirror"].pop("TB"), True),
    ("a mirror that does not undo itself",
     lambda f: f["mirror"].__setitem__("FB", "TB"), True),
    ("a mirror pointing at somebody who is not here",
     lambda f: f["mirror"].__setitem__("TB", "HB"), True),

    # Half a foot of slop in a hand-typed alignment is not a broken formation.
    ("a back a rounding error off centre",
     lambda f: f["alignment"].__setitem__("TB", [0.01, -4.2]), False),
]


def main() -> int:
    forms = {f["id"]: f for f in render.load_formations()}
    if MIRRORING_FORMATION not in forms:
        print(f"FAIL  no formation '{MIRRORING_FORMATION}' to test against")
        return 1
    wrong = 0

    for label, break_it, should_reject in CASES:
        form = copy.deepcopy(forms[MIRRORING_FORMATION])
        if not any("mirror_of" in p for p in form.get("_raw_plays", [])):
            print(f"FAIL  {MIRRORING_FORMATION} no longer mirrors any play, so this test "
                  "is checking nothing — point it at a formation that does")
            return 1
        break_it(form)
        errors = render.validate_mirror(form)
        rejected = bool(errors)
        if rejected != should_reject:
            wrong += 1
            wanted = "rejected" if should_reject else "accepted"
            print(f"FAIL  {label}: should have been {wanted}")
            for e in errors:
                print(f"        {e}")

    if wrong:
        print(f"\n{wrong} of {len(CASES)} cases behaved unexpectedly.")
        return 1
    print(f"{len(CASES)} symmetry cases behaved as expected "
          f"({sum(1 for c in CASES if c[2])} rejected, "
          f"{sum(1 for c in CASES if not c[2])} accepted).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
