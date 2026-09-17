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
    ("the real call",                 "i-form",   "i-power-r",  "I SL Right 34 Power", False),
    ("off tackle, called at the 0 hole", "i-form", "i-power-r", "I SL Right 30 Power", True),
    ("off tackle, called outside the end", "i-form", "i-power-r", "I SL Right 38 Power", True),
    ("off tackle right, numbered left", "i-form",  "i-power-r",  "I SL Right 35 Power", True),
    ("off tackle, credited to the fullback", "i-form", "i-power-r", "I SL Right 24 Power", True),
    ("off tackle, credited to the SL", "i-form",  "i-power-r",  "I SL Right 44 Power", True),
    ("a back number nobody defines",  "i-form",   "i-power-r",  "I SL Right 54 Power", True),
    ("no number at all",              "i-form",   "i-power-r",  "I SL Right Power",    True),
    ("off tackle left",               "i-form",   "i-power-l",  "I SL Left 35 Power",  False),
    ("off tackle left, numbered right", "i-form", "i-power-l",  "I SL Left 34 Power",  True),
    # The tight-end sweep is a word call: it opts in, so no digits is right for it — while
    # "no number at all" above still fails on a play that did not opt in. Digits added
    # to a word call are checked like any other, and there is no back 5.
    ("tight-end sweep, word call",      "i-form",   "i-te-sweep-r", "Regular I Slot Right LTE Sweep", False),
    ("tight-end sweep, numbered anyway", "i-form",  "i-te-sweep-r", "Regular I Slot Right 58 LTE Sweep", True),
    ("split toss right",              "split-backs", "sb-toss-r", "Split Backs Slot Right 38 Toss",  False),
    ("split toss, called off tackle", "split-backs", "sb-toss-r", "Split Backs Slot Right 34 Toss", True),
    ("split toss, credited to the SL", "split-backs", "sb-toss-r", "Split Backs Slot Right 48 Toss", True),
    ("split toss right, numbered left", "split-backs", "sb-toss-r", "Split Backs Slot Right 39 Toss", True),
    ("split toss left",               "split-backs", "sb-toss-l", "Split Backs Slot Left 29 Toss",   False),
    ("split toss left, wrong back",   "split-backs", "sb-toss-l", "Split Backs Slot Left 39 Toss",   True),
    ("off tackle called Smash",       "i-form", "i-power-r", "Regular I Slot Right 34 Smash", True),
    ("outside called Pitch",          "split-backs", "sb-toss-r", "Split Backs Slot Right 38 Pitch", True),
    ("slot sweep at 8/9",             "i-form", "i-sl-sweep-l", "Regular I Slot Right 49 Sweep", False),
    ("slot sweep called Toss",        "i-form", "i-sl-sweep-l", "Regular I Slot Right 49 Toss", True),
    ("QB sweep at 8/9",               "split-backs", "sb-qb-sweep-r", "Split Backs Slot Right 18 Sweep", False),
    ("QB sweep called Toss",          "split-backs", "sb-qb-sweep-r", "Split Backs Slot Right 18 Toss", True),
    ("wishbone power",                "wishbone", "wb-power-r", "Wishbone 44 Power", False),
    ("wishbone power on the 3-back",  "wishbone", "wb-power-r", "Wishbone 34 Power", True),
    ("wishbone smash",                "wishbone", "wb-smash-r", "Wishbone 20 Smash", False),
    ("wishbone dive",                 "wishbone", "wb-dive-r",  "Wishbone 22 Dive", False),
    ("wishbone toss at 4",            "wishbone", "wb-toss-l",  "Wishbone 49 Toss", False),
    ("wishbone 49 called Sweep",      "wishbone", "wb-toss-l",  "Wishbone 49 Sweep", True),
]


def main() -> int:
    forms = {f["id"]: f for f in render.load_formations()}
    defenses = render.load_defenses()
    wrong = 0

    for label, form_id, play_id, call, should_reject in CASES:
        form = forms[form_id]
        play = copy.deepcopy(next(p for p in form["_plays"] if p["id"] == play_id))
        play["call"] = call
        # The deep copy has its own (empty) resolve cache, so the back's path is
        # recomputed for this call rather than reused from the real play.
        errors = render.validate_call(play, form, defenses)
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
