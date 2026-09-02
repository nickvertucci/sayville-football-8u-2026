#!/usr/bin/env python3
"""Prove the call check actually rejects a call that does not match its diagram.

`render.py --check` passing tells you every call in the book is right. It does not
tell you the check would notice if one were wrong — a check that accepts everything
passes just as quietly. This runs the real validator against deliberately broken calls
and fails if any of them slips through.

    python generator/test_calls.py

No dependencies. Run it after touching validate_call(), hole_bounds() or a formation's
`backs` map.
"""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render  # noqa: E402

# (what it is, formation, play, the call to try, should the check reject it?)
CASES = [
    ("the real call",                 "i-form",   "i-iso-r",    "I Z Right 32 Iso",   False),
    ("iso, called at the 0 hole",     "i-form",   "i-iso-r",    "I Z Right 30 Iso",   True),
    ("iso, called outside the end",   "i-form",   "i-iso-r",    "I Z Right 36 Iso",   True),
    ("slant, off by one hole",        "i-form",   "i-slant-r",  "I Z Right 34 Slant", True),
    ("dive right, numbered left",     "i-form",   "i-dive-r",   "I Z Right 21 Dive",  True),
    ("toss left, numbered right",     "i-form",   "i-toss-l",   "I Z Right 38 Toss",  True),
    ("dive, credited to the tailback", "i-form",  "i-dive-r",   "I Z Right 30 Dive",  True),
    ("a back this formation lacks",   "i-form",   "i-iso-r",    "I Z Right 42 Iso",   True),
    ("a back number nobody defines",  "i-form",   "i-iso-r",    "I Z Right 52 Iso",   True),
    ("no number at all",              "i-form",   "i-iso-r",    "I Z Right Iso",      True),
    # The boot is the case the check has to get right for the right reason: the digits
    # describe the quarterback, while the ball carrier is the flanker he throws to.
    ("boot, quarterback at the 6",    "i-form",   "i-boot-r",   "I Z Right 16 Boot",  False),
    ("boot, called too wide",         "i-form",   "i-boot-r",   "I Z Right 18 Boot",  True),
    ("split power right",             "split-backs", "sb-power-r", "Split Z Right 24 Power",  False),
    ("split power, called a pitch",   "split-backs", "sb-power-r", "Split Z Right 28 Power",  True),
    ("split power, credited to the Z", "split-backs", "sb-power-r", "Split Z Right 44 Power", True),
    ("split pitch, called off tackle", "split-backs", "sb-pitch-r", "Split Z Right 24 Pitch", True),
    ("split dive right, numbered left", "split-backs", "sb-dive-r", "Split Z Right 31 Dive",  True),
    ("split waggle, quarterback at 6", "split-backs", "sb-waggle-r", "Split Z Right 16 Waggle", False),
    ("split waggle, called too wide",  "split-backs", "sb-waggle-r", "Split Z Right 18 Waggle", True),
    # Counter Left hands to the right back; the left one runs the pitch fake and never
    # crosses the line at all, so crediting him cannot be checked against a hole.
    ("split counter left",            "split-backs", "sb-counter-l", "Split Z Right 35 Counter", False),
    ("split counter left, wrong back", "split-backs", "sb-counter-l", "Split Z Right 24 Counter", True),
    # The Full House is symmetric, so its left-handed plays are mirrored. The tailback is
    # on the middle and mirrors to himself, so Power keeps its back digit both ways.
    ("house power left, mirrored",    "full-house", "fh-power-l", "House 35 Power",       False),
    ("house power left, unmirrored",  "full-house", "fh-power-l", "House 44 Power",       True),
    # Dive is the one pair whose two calls name different backs: mirroring trades the two
    # backs over the guards, so the digit has to travel with them.
    ("house dive left, mirrored",     "full-house", "fh-dive-l",  "House 41 Dive",        False),
    ("house dive left, digit unswapped", "full-house", "fh-dive-l", "House 21 Dive",      True),
]


def main() -> int:
    forms = {f["id"]: f for f in render.load_formations()}
    wrong = 0

    for label, form_id, play_id, call, should_reject in CASES:
        form = forms[form_id]
        play = copy.deepcopy(next(p for p in form["_plays"] if p["id"] == play_id))
        play["call"] = call
        errors = render.validate_call(play, form)
        rejected = bool(errors)
        if rejected != should_reject:
            wrong += 1
            wanted = "rejected" if should_reject else "accepted"
            print(f"FAIL  {label}: {call!r} should have been {wanted}")
            for e in errors:
                print(f"        {e}")

    if wrong:
        print(f"\n{wrong} of {len(CASES)} cases behaved unexpectedly.")
        return 1
    print(f"{len(CASES)} call cases behaved as expected "
          f"({sum(1 for c in CASES if c[4])} rejected, "
          f"{sum(1 for c in CASES if not c[4])} accepted).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
