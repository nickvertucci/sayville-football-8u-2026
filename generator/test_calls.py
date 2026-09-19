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
    ("the real call",                 "i-form",   "i-power-r",  "I SL Right 36 Power", False),
    ("off tackle, called over the center", "i-form", "i-power-r", "I SL Right 30 Power", True),
    ("off tackle, called in the A gap", "i-form", "i-power-r",  "I SL Right 32 Power", True),
    ("off tackle, called in the B gap", "i-form", "i-power-r",  "I SL Right 34 Power", True),
    ("off tackle, called outside the end", "i-form", "i-power-r", "I SL Right 38 Power", True),
    ("off tackle right, numbered left", "i-form",  "i-power-r",  "I SL Right 37 Power", True),
    ("off tackle, credited to the fullback", "i-form", "i-power-r", "I SL Right 26 Power", True),
    ("off tackle, credited to the SL", "i-form",  "i-power-r",  "I SL Right 46 Power", True),
    ("a back number nobody defines",  "i-form",   "i-power-r",  "I SL Right 56 Power", True),
    ("no number at all",              "i-form",   "i-power-r",  "I SL Right Power",    True),
    ("off tackle left",               "i-form",   "i-power-l",  "I SL Left 37 Power",  False),
    ("off tackle left, numbered right", "i-form", "i-power-l",  "I SL Left 36 Power",  True),
    # The tight ends are numbered now -- 5 the left one, 6 the right -- so the end-around
    # is 58 Sweep and there is no word call left in the book. Coming across at 8/9 is
    # Sweep for a tight end the same as for the quarterback and the slot, and calling it
    # Toss fails on the word rather than on the geometry.
    ("tight-end sweep",                 "i-form",   "i-te-sweep-r", "Regular I Slot Right 58 Sweep", False),
    ("tight-end sweep, unnumbered",     "i-form",   "i-te-sweep-r", "Regular I Slot Right LTE Sweep", True),
    ("tight-end sweep, called Toss",    "i-form",   "i-te-sweep-r", "Regular I Slot Right 58 Toss", True),
    ("tight-end sweep, wrong end",      "i-form",   "i-te-sweep-r", "Regular I Slot Right 68 Sweep", True),
    ("tight-end sweep right, numbered left", "i-form", "i-te-sweep-r", "Regular I Slot Right 59 Sweep", True),
    # The slant out is numbered off the same two digits, and a pass skips the play-word
    # check, so what is left to hold is that the end named is the one running it.
    ("tight-end slant pass",            "i-form",   "i-te-out-r", "Regular I Slot Right 68 Slant Pass", False),
    ("tight-end slant pass, wrong end", "i-form",   "i-te-out-r", "Regular I Slot Right 58 Slant Pass", True),
    # The A gap is 2/3 now, not 0/1, and there is no 1 hole at all: the middle is one
    # hole, so a call that names the old number has to fail rather than quietly
    # measure a yard and a half away and pass.
    ("A gap right",                   "i-form",   "i-smash-r",  "Regular I Slot Right 32 Smash", False),
    ("A gap right, called at the old 0", "i-form", "i-smash-r",  "Regular I Slot Right 30 Smash", True),
    ("A gap left",                    "i-form",   "i-smash-l",  "Regular I Slot Left 33 Smash", False),
    ("the 1 hole, which does not exist", "i-form", "i-smash-l",  "Regular I Slot Left 31 Smash", True),
    ("A gap called Dive",             "i-form",   "i-smash-r",  "Regular I Slot Right 32 Dive", True),
    ("B gap right",                   "wishbone", "wb-dive-r",  "Wishbone 24 Dive", False),
    ("B gap, called at the old 2",    "wishbone", "wb-dive-r",  "Wishbone 22 Dive", True),
    ("B gap called Power",            "wishbone", "wb-dive-r",  "Wishbone 24 Power", True),
    ("split toss right",              "split-backs", "sb-toss-r", "Split Backs Slot Right 38 Toss",  False),
    ("split toss, called off tackle", "split-backs", "sb-toss-r", "Split Backs Slot Right 36 Toss", True),
    ("split toss, credited to the SL", "split-backs", "sb-toss-r", "Split Backs Slot Right 48 Toss", True),
    ("split toss right, numbered left", "split-backs", "sb-toss-r", "Split Backs Slot Right 39 Toss", True),
    ("split toss left",               "split-backs", "sb-toss-l", "Split Backs Slot Left 29 Toss",   False),
    ("split toss left, wrong back",   "split-backs", "sb-toss-l", "Split Backs Slot Left 39 Toss",   True),
    ("off tackle called Smash",       "i-form", "i-power-r", "Regular I Slot Right 36 Smash", True),
    ("outside called Pitch",          "split-backs", "sb-toss-r", "Split Backs Slot Right 38 Pitch", True),
    ("slot sweep at 8/9",             "i-form", "i-sl-sweep-l", "Regular I Slot Right 49 Sweep", False),
    ("slot sweep called Toss",        "i-form", "i-sl-sweep-l", "Regular I Slot Right 49 Toss", True),
    ("QB sweep at 8/9",               "split-backs", "sb-qb-sweep-r", "Split Backs Slot Right 18 Sweep", False),
    ("QB sweep called Toss",          "split-backs", "sb-qb-sweep-r", "Split Backs Slot Right 18 Toss", True),
    ("wishbone power",                "wishbone", "wb-power-r", "Wishbone 46 Power", False),
    ("wishbone power on the 3-back",  "wishbone", "wb-power-r", "Wishbone 36 Power", True),
    ("wishbone smash",                "wishbone", "wb-smash-r", "Wishbone 22 Smash", False),
    ("wishbone toss at 4",            "wishbone", "wb-toss-l",  "Wishbone 49 Toss", False),
    ("wishbone 49 called Sweep",      "wishbone", "wb-toss-l",  "Wishbone 49 Sweep", True),
    # Trips has no numbered run left -- the bunch throws at 8/9 instead. A pass skips
    # the play-word check (it is not a hole word), so what still has to hold is the
    # geometry: 39 is left, and the tailback has to be the one going there.
    ("trips quick pass",              "trips", "tr-quick-pass-l", "Trips Left 39 Quick Pass", False),
    ("trips quick pass wrong side",   "trips", "tr-quick-pass-l", "Trips Left 38 Quick Pass", True),
    # A pitch pass is numbered like the toss it is pretending to be, so the digits
    # name the back who takes the pitch -- and he never crosses the line. The hole is
    # where he took the ball to, measured at the point he got nearest the line, and
    # everything else about the number still has to be true.
    ("pitch pass right",              "i-form", "i-toss-pass-r", "Regular I Slot Right 38 Pitch Pass", False),
    ("pitch pass, called off tackle", "i-form", "i-toss-pass-r", "Regular I Slot Right 36 Pitch Pass", True),
    ("pitch pass right, numbered left", "i-form", "i-toss-pass-r", "Regular I Slot Left 39 Pitch Pass", True),
    ("pitch pass, credited to the SL", "i-form", "i-toss-pass-r", "Regular I Slot Right 48 Pitch Pass", True),
    ("split pitch pass left",         "split-backs", "sb-toss-pass-l", "Split Backs Slot Left 29 Pitch Pass", False),
    ("split pitch pass left, wrong back", "split-backs", "sb-toss-pass-l", "Split Backs Slot Left 39 Pitch Pass", True),
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

    # The one thing about a pitch pass the call alone cannot say: he throws from
    # behind the line. A path that crosses it is a forward pass from past the line of
    # scrimmage -- a penalty, and a card showing a play nobody can run -- so the same
    # call has to be rejected the moment the diagram does that.
    form = forms["i-form"]
    play = copy.deepcopy(next(p for p in form["_plays"] if p["id"] == "i-toss-pass-r"))
    play["assignments"]["TB"]["path"] = [[2.2, 0.7], [5.4, 1.2], [7.6, 2.8], [8.2, 6.4]]
    if not render.validate_call(play, form, defenses):
        wrong += 1
        print("FAIL  pitch pass thrown from past the line: should have been rejected")

    if wrong:
        print(f"\n{wrong} of {len(CASES) + 1} cases behaved unexpectedly.")
        return 1
    print(f"{len(CASES) + 1} call cases behaved as expected "
          f"({sum(1 for c in CASES if c[4]) + 1} rejected, "
          f"{sum(1 for c in CASES if not c[4])} accepted).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
