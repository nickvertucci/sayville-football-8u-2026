#!/usr/bin/env python3
"""Prove the call check actually rejects a call that does not match its diagram.

`render.py --check` passing tells you the 18 calls in the book are right. It does not
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
    ("bone power right",              "wishbone", "wb-power-r", "Bone 44 Power",      False),
    ("bone power, called a pitch",    "wishbone", "wb-power-r", "Bone 48 Power",      True),
    ("bone power, wrong halfback",    "wishbone", "wb-power-r", "Bone 34 Power",      True),
    ("bone pitch, called off tackle", "wishbone", "wb-pitch-r", "Bone 44 Pitch",      True),
    # Mirrored plays swap LH and RH, so the back digit swaps with them.
    ("bone power left, mirrored",     "wishbone", "wb-power-l", "Bone 35 Power",      False),
    ("bone power left, unmirrored",   "wishbone", "wb-power-l", "Bone 44 Power",      True),
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
