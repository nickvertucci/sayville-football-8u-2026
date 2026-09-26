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
    # backs -- and the digits went when the letters came, so the end-around is
    # "X Sweep Right": the letter has to be the man carrying it, and the last word has
    # to be the way he is going.
    ("end-around",                    "i-form",   "i-te-sweep-r", "Regular I Z Right X Sweep Right", False),
    ("end-around, the other end",     "i-form",   "i-te-sweep-r", "Regular I Z Right Y Sweep Right", True),
    ("end-around, no letter at all",  "i-form",   "i-te-sweep-r", "Regular I Z Right Sweep Right", True),
    ("end-around, back on its old digits", "i-form", "i-te-sweep-r", "Regular I Z Right 58 Sweep", True),
    # The direction word is the whole reason it is there: the X is the LEFT end and
    # this play sends him right, so a call that leaves the way out, or gets it
    # backwards, is the mistake a boy would actually make.
    ("end-around, no direction",      "i-form",   "i-te-sweep-r", "Regular I Z Right X Sweep", True),
    ("end-around, wrong direction",   "i-form",   "i-te-sweep-r", "Regular I Z Right X Sweep Left", True),
    ("end-around, direction but no word", "i-form", "i-te-sweep-r", "Regular I Z Right X Right", True),
    # The Z lines up right on this one and runs left, which is the other reason the
    # word is worth its six characters.
    ("the Z on the sweep",            "i-form",   "i-sl-sweep-l", "Regular I Z Right Z Sweep Left", False),
    ("the Z sweep called the way he lines up", "i-form", "i-sl-sweep-l", "Regular I Z Right Z Sweep Right", True),
    ("the Z sweep given to an end",   "i-form",   "i-sl-sweep-l", "Regular I Z Right X Sweep Left", True),
    # A pass is the same: its word is a route, and the letter says who is running it.
    ("the Y slant",                   "i-form",   "i-te-out-r", "Regular I Z Right Y Slant Pass Right", False),
    ("the Y slant given to the X",    "i-form",   "i-te-out-r", "Regular I Z Right X Slant Pass Right", True),
    ("a letter call in Trips",        "trips",    "tr-te-sweep-r", "Trips Right X Sweep Right", False),
    ("a letter call in Trips, wrong end", "trips", "tr-te-sweep-r", "Trips Right Y Sweep Right", True),
    ("a letter call in Trips, no direction", "trips", "tr-te-sweep-r", "Trips Right X Sweep", True),
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
    # The Z's phrase is his side only. Tight and Split came out of it, and an old call
    # still carrying one is stopped rather than quietly skipping the side check.
    ("Z Tight, the retired word",     "i-form",   "i-power-r",  "Regular I Z Tight Right 36 Handoff", True),
    ("Z Split, the retired word",     "split-backs", "sb-toss-r", "Split Backs Z Split Right 38 Toss", True),
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
    # The Single Back call sets two things -- which end is tight, and which side the
    # wing is on -- and each is checked against the diagram on its own. Neither is
    # implied by the geometry: the wing is a blocker, and which end is tight only
    # shows up in the blocking, so a call that gets either backwards would otherwise
    # leave every other check in the build perfectly happy.
    ("single back power",             "single-back", "sb1-power-r",
     "Single Back Tight Right Wing Right 26 Handoff", False),
    ("single back, wing on the wrong side", "single-back", "sb1-power-r",
     "Single Back Tight Right Wing Left 26 Handoff", True),
    ("single back, wrong end called tight", "single-back", "sb1-power-r",
     "Single Back Tight Left Wing Right 26 Handoff", True),
    # The Z is not called, because he has no choice: he goes out with whichever end
    # split. A call that names him anyway has to agree with where he actually is.
    ("single back naming the Z correctly", "single-back", "sb1-power-r",
     "Single Back Tight Right Z Left Wing Right 26 Handoff", False),
    ("single back naming the Z on the wrong side", "single-back", "sb1-power-r",
     "Single Back Tight Right Z Right Wing Right 26 Handoff", True),
    # The C gap is a real hole on the tight side and open grass on the split side, so
    # off tackle has to be numbered to the side the tight end is on.
    ("single back off tackle, numbered to the split side", "single-back", "sb1-power-r",
     "Single Back Tight Right Wing Right 27 Handoff", True),
    ("single back, credited to a back the formation does not have", "single-back",
     "sb1-power-r", "Single Back Tight Right Wing Right 36 Handoff", True),
    # A letter call still has to survive two alignment phrases in front of it.
    ("single back slant pass",        "single-back", "sb1-te-out-r",
     "Single Back Tight Right Wing Left Y Slant Pass Right", False),
    ("single back slant pass, wrong way", "single-back", "sb1-te-out-r",
     "Single Back Tight Right Wing Left Y Slant Pass Left", True),
    ("single back slant pass, wrong letter", "single-back", "sb1-te-out-r",
     "Single Back Tight Right Wing Left X Slant Pass Right", True),
    ("single back toss",              "single-back", "sb1-toss-r",
     "Single Back Tight Right Wing Right 28 Toss", False),
    ("single back toss called Handoff", "single-back", "sb1-toss-r",
     "Single Back Tight Right Wing Right 28 Handoff", True),
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

    # The one thing about a toss pass the call alone cannot say: he throws from
    # behind the line. A path that crosses it is a forward pass from past the line of
    # scrimmage -- a penalty, and a card showing a play nobody can run -- so the same
    # call has to be rejected the moment the diagram does that.
    form = forms["i-form"]
    play = copy.deepcopy(next(p for p in form["_plays"] if p["id"] == "i-toss-pass-r"))
    play["assignments"]["TB"]["path"] = [[2.2, 0.7], [5.4, 1.2], [7.6, 2.8], [8.2, 6.4]]
    if not render.validate_call(play, form, defenses):
        wrong += 1
        print("FAIL  toss pass thrown from past the line: should have been rejected")

    if wrong:
        print(f"\n{wrong} of {len(CASES) + 1} cases behaved unexpectedly.")
        return 1
    print(f"{len(CASES) + 1} call cases behaved as expected "
          f"({sum(1 for c in CASES if c[4]) + 1} rejected, "
          f"{sum(1 for c in CASES if not c[4])} accepted).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
