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
    ("the real call",                 "i-form",   "i-power-r",  "I Z Right 36 Handoff", False),
    ("off tackle, called over the center", "i-form", "i-power-r", "I Z Right 30 Handoff", True),
    ("off tackle, called in the A gap", "i-form", "i-power-r",  "I Z Right 32 Handoff", True),
    ("off tackle, called in the B gap", "i-form", "i-power-r",  "I Z Right 34 Handoff", True),
    ("off tackle, called outside the end", "i-form", "i-power-r", "I Z Right 38 Toss", True),
    ("off tackle right, numbered left", "i-form",  "i-power-r",  "I Z Right 37 Handoff", True),
    ("off tackle, credited to the fullback", "i-form", "i-power-r", "I Z Right 26 Handoff", True),
    ("off tackle, credited to a back nobody defines", "i-form", "i-power-r", "I Z Right 46 Handoff", True),
    ("a back number nobody defines",  "i-form",   "i-power-r",  "I Z Right 76 Handoff", True),
    ("no number at all",              "i-form",   "i-power-r",  "I Z Right Handoff",    True),
    ("off tackle left",               "i-form",   "i-power-l",  "I Z Left 37 Handoff", False),
    ("off tackle left, numbered right", "i-form", "i-power-l",  "I Z Left 36 Handoff", True),
    # The huddle word is the action, not the family: Smash, Dive and Power are all
    # Handoff to the boy carrying it, and the two digits are what tell them apart. The
    # old words are the schemes still, and a call that says one of them now fails.
    ("off tackle, called by its scheme", "i-form", "i-power-r",  "I Z Right 36 Power", True),
    ("A gap, called by its scheme",    "i-form",   "i-smash-r",  "Regular I Z Right 32 Smash", True),
    ("B gap, called by its scheme",    "wishbone", "wb-dive-r",  "Wishbone 24 Dive", True),
    ("a handoff called Toss",         "i-form",   "i-smash-r",  "Regular I Z Right 32 Toss", True),
    ("a toss called Handoff",         "split-backs", "sb-toss-r", "Split Backs Z Right 38 Handoff", True),
    # The call says which side the Z stands on, and the diagram has to agree -- he is a
    # blocker on most plays, so the wrong side passes every geometry check and only the
    # picture is wrong.
    ("Z on the side the call says",   "i-form",   "i-power-r",  "Regular I Z Right 36 Handoff", False),
    ("Z on the other side",           "i-form",   "i-power-r",  "Regular I Z Left 36 Handoff", True),
    # X, Y and Z name themselves. They had digits for a while -- 4, 5 and 6, after the
    # backs -- and the digits went when the letters came, so the end-around is "X Sweep"
    # and what has to hold is that the letter is the man carrying it.
    ("end-around",                    "i-form",   "i-te-sweep-r", "Regular I Z Right X Sweep", False),
    ("end-around, the other end",     "i-form",   "i-te-sweep-r", "Regular I Z Right Y Sweep", True),
    ("end-around, no letter at all",  "i-form",   "i-te-sweep-r", "Regular I Z Right Sweep", True),
    ("end-around, back on its old digits", "i-form", "i-te-sweep-r", "Regular I Z Right 58 Sweep", True),
    ("the Z on the sweep",            "i-form",   "i-sl-sweep-l", "Regular I Z Right Z Sweep", False),
    ("the Z sweep given to an end",   "i-form",   "i-sl-sweep-l", "Regular I Z Right X Sweep", True),
    # A pass is the same: its word is a route, and the letter says who is running it.
    ("the Y slant",                   "i-form",   "i-te-out-r", "Regular I Z Right Y Slant Pass", False),
    ("the Y slant given to the X",    "i-form",   "i-te-out-r", "Regular I Z Right X Slant Pass", True),
    ("a letter call in Trips",        "trips",    "tr-te-sweep-r", "Trips Right X Sweep", False),
    ("a letter call in Trips, wrong end", "trips", "tr-te-sweep-r", "Trips Right Y Sweep", True),
    # The A gap is 2/3, not 0/1, and there is no 1 hole at all: the middle is one hole,
    # so a call that names the old number has to fail rather than quietly measure a yard
    # and a half away and pass.
    ("A gap right",                   "i-form",   "i-smash-r",  "Regular I Z Right 32 Handoff", False),
    ("A gap right, called at the old 0", "i-form", "i-smash-r",  "Regular I Z Right 30 Handoff", True),
    ("A gap left",                    "i-form",   "i-smash-l",  "Regular I Z Left 33 Handoff", False),
    ("the 1 hole, which does not exist", "i-form", "i-smash-l",  "Regular I Z Left 31 Handoff", True),
    ("B gap right",                   "wishbone", "wb-dive-r",  "Wishbone 24 Handoff", False),
    ("B gap, called at the old 2",    "wishbone", "wb-dive-r",  "Wishbone 22 Handoff", True),
    ("split toss right",              "split-backs", "sb-toss-r", "Split Backs Z Right 38 Toss",  False),
    ("split toss, called off tackle", "split-backs", "sb-toss-r", "Split Backs Z Right 36 Toss", True),
    ("split toss, credited to a back nobody defines", "split-backs", "sb-toss-r", "Split Backs Z Right 48 Toss", True),
    ("split toss right, numbered left", "split-backs", "sb-toss-r", "Split Backs Z Right 39 Toss", True),
    ("split toss left",               "split-backs", "sb-toss-l", "Split Backs Z Left 29 Toss",   False),
    ("split toss left, wrong back",   "split-backs", "sb-toss-l", "Split Backs Z Left 39 Toss",   True),
    ("outside called Pitch",          "split-backs", "sb-toss-r", "Split Backs Z Right 38 Pitch", True),
    ("QB sweep at 8/9",               "split-backs", "sb-qb-sweep-r", "Split Backs Z Right 18 Sweep", False),
    ("QB sweep called Toss",          "split-backs", "sb-qb-sweep-r", "Split Backs Z Right 18 Toss", True),
    ("wishbone power",                "wishbone", "wb-power-r", "Wishbone 46 Handoff", False),
    ("wishbone power on the 3-back",  "wishbone", "wb-power-r", "Wishbone 36 Handoff", True),
    ("wishbone smash",                "wishbone", "wb-smash-r", "Wishbone 22 Handoff", False),
    ("wishbone toss at 4",            "wishbone", "wb-toss-l",  "Wishbone 49 Toss", False),
    ("wishbone 49 called Sweep",      "wishbone", "wb-toss-l",  "Wishbone 49 Sweep", True),
    # Trips has no numbered run left -- the bunch throws at 8/9 instead. A pass skips
    # the play-word check, so what still has to hold is the geometry: 39 is left, and
    # the tailback has to be the one going there.
    ("trips quick pass",              "trips", "tr-quick-pass-l", "Trips Left 39 Quick Pass", False),
    ("trips quick pass wrong side",   "trips", "tr-quick-pass-l", "Trips Left 38 Quick Pass", True),
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
