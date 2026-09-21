#!/usr/bin/env python3
"""Named blocking schemes: templates, role mapping, fill, and the book.

A new formation drops in when its alignment uses the same seven line keys and
either FB+TB, LH+RH, or Wishbone's FB+LH+RH. These tests hold that contract so
a play that only names Power still gets a playside end who kicks the end out
and a lead back in front of the ball.

    python generator/test_schemes.py
"""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import blocking  # noqa: E402
import render  # noqa: E402

FAMILIES = ("Smash", "Dive", "Power", "Toss", "Sweep", "Protect")


def check_templates() -> list[str]:
    problems = []
    if tuple(blocking.SCHEMES) != FAMILIES and set(blocking.SCHEMES) != set(FAMILIES):
        problems.append(
            f"SCHEMES are {list(blocking.SCHEMES)}, expected {list(FAMILIES)}"
        )
    for name in FAMILIES:
        if name not in blocking.SCHEMES:
            problems.append(f"missing scheme {name}")
            continue
        if "playside_te" not in blocking.SCHEMES[name]:
            problems.append(f"{name} has no playside_te")
        if "lead" not in blocking.SCHEMES[name]:
            problems.append(f"{name} has no lead")
    want = {
        ("Power", "playside_te", "block"): "kick",
        ("Power", "slot", "block"): "screen",
        ("Smash", "playside_te", "drive"): "in",
        ("Smash", "slot", "block"): "screen",
        ("Dive", "playside_te", "drive"): "in",
        ("Toss", "lead", "target"): "force",
        ("Sweep", "lead", "target"): "force",
        ("Toss", "playside_te", "drive"): "in",
        ("Protect", "slot", "block"): "screen",
        ("Protect", "center", "block"): "protect",
    }
    for (name, role, key), value in want.items():
        got = blocking.SCHEMES[name].get(role, {}).get(key)
        if got != value:
            problems.append(f"{name}.{role}.{key} is {got!r}, expected {value!r}")
    if blocking.intent_core(blocking.SCHEMES["Toss"]["playside_te"]) != \
            blocking.intent_core(blocking.SCHEMES["Sweep"]["playside_te"]):
        problems.append("Toss and Sweep must share the outside line")
    # Every run scheme blocks GOD with all five interior linemen. This is the
    # contract that lets a boy learn one rule instead of five, so it is checked
    # rather than remembered -- a scheme that quietly hand-writes a line rule
    # again has taken that back off him.
    for name, scheme in blocking.SCHEMES.items():
        if name == "Protect":
            continue
        for role in ("playside_t", "playside_g", "center",
                     "backside_g", "backside_t"):
            got = scheme.get(role, {})
            if got.get("block") != "god" or len(got) != 1:
                problems.append(
                    f"{name}.{role} is {got!r}, but every run scheme blocks GOD "
                    "with the interior five"
                )
    return problems


def check_roles(formations) -> list[str]:
    problems = []
    by_id = {f["id"]: f for f in formations}
    i_form = by_id["i-form"]
    split = by_id["split-backs"]
    shotgun = by_id["shotgun"]
    i_right = blocking.scheme_roles(i_form, 1)
    i_left = blocking.scheme_roles(i_form, -1)
    if i_right.get("lead") != "FB" or i_right.get("trail") != "TB":
        problems.append(f"I-form right lead/trail is {i_right.get('lead')}/"
                        f"{i_right.get('trail')}, expected FB/TB")
    if i_left.get("lead") != "FB":
        problems.append("I-form lead is always the fullback, including left")
    if i_right.get("playside_te") != "Y" or i_left.get("playside_te") != "X":
        problems.append("playside_te did not follow the play's side")
    # The split backfield is the FB on the right and the TB on the left -- the same
    # two men the digits already name, 2 even and right, 3 odd and left. The lead is
    # the playside one, so it flips with the play while the I's never does.
    #
    # This is the assertion that protects the rename. The old names said which side a
    # back was on; FB and TB do not, and the roles are now read off the alignment
    # instead. Get that wrong and the Split Backs -- 2.2 yards off the ball, inside
    # the 2.5 that `_stacked` calls stacked -- resolve as an I and lead with the FB in
    # both directions. Every left-handed play would block the wrong edge and the build
    # would still pass, because nothing else in the book can tell.
    sb_right = blocking.scheme_roles(split, 1)
    sb_left = blocking.scheme_roles(split, -1)
    if sb_right.get("lead") != "FB" or sb_right.get("trail") != "TB":
        problems.append(f"Split right lead/trail is {sb_right.get('lead')}/"
                        f"{sb_right.get('trail')}, expected FB/TB")
    if sb_left.get("lead") != "TB" or sb_left.get("trail") != "FB":
        problems.append(f"Split left lead/trail is {sb_left.get('lead')}/"
                        f"{sb_left.get('trail')}, expected TB/FB")
    sg_right = blocking.scheme_roles(shotgun, 1)
    sg_left = blocking.scheme_roles(shotgun, -1)
    if sg_right.get("lead") != "FB" or sg_left.get("lead") != "TB":
        problems.append("Shotgun uses the same split-backfield roles as Split Backs")
    bone = by_id["wishbone"]
    wb_right = blocking.scheme_roles(bone, 1)
    if "slot" in wb_right:
        problems.append("Wishbone has no slot")
    if wb_right.get("lead") != "FB":
        problems.append(f"Wishbone lead is {wb_right.get('lead')}, expected FB")
    trips = by_id["trips"]
    tr = blocking.scheme_roles(trips, 1)
    if "lead" in tr:
        problems.append(f"Trips is empty; lead should be empty, got {tr.get('lead')}")
    if tr.get("slot") != "Z":
        problems.append(f"Trips slot is {tr.get('slot')}, expected Z")
    if tr.get("trail"):
        problems.append(f"Trips 2/3/4 are in the bunch, not a backfield trail ({tr.get('trail')})")
    return problems


def check_fill(formations) -> list[str]:
    problems = []
    i_form = next(f for f in formations if f["id"] == "i-form")
    play = {
        "id": "x-power-r",
        "scheme": "Power",
        "call": "Regular I Z Right 36 Handoff",
        "direction": "right",
        "assignments": {
            "QB": {"rule": "Hand it.", "type": "fake", "path": [[1.0, -0.5]]},
            "TB": {"rule": "Run it.", "type": "run", "path": [[1.2, 1.5], [3.4, 5.6]]},
        },
    }
    filled = blocking.fill_assignments(play, i_form, 1)
    if filled.get("Y", {}).get("block") != "kick":
        problems.append(f"minimal Power did not kick with the playside end: {filled.get('Y')}")
    if filled.get("Z", {}).get("block") != "screen":
        problems.append(f"minimal Power did not screen with the slot: {filled.get('Z')}")
    if filled.get("FB", {}).get("block") != "lead":
        problems.append(f"minimal Power did not lead with the fullback: {filled.get('FB')}")
    if "block" in filled.get("TB", {}):
        problems.append("minimal Power overwrote the tailback's path")
    if set(i_form["alignment"]) - set(filled) != set():
        missing = set(i_form["alignment"]) - set(filled)
        problems.append(f"minimal Power left {sorted(missing)} unfilled")
    # Both Sweeps block the line the same way, whoever is carrying it. The
    # end-around used to pull its backside tackle off GOD and onto a cutoff
    # because the end beside him had left; the line does not change when the
    # ball carrier does, and that exception is what GOD exists to delete.
    for pid in ("i-te-sweep-r", "i-sl-sweep-r"):
        sw = next(p for p in i_form["_plays"] if p["id"] == pid)
        if sw["assignments"].get("LT", {}).get("block") != "god":
            problems.append(
                f"{pid} backside tackle should block GOD, got {sw['assignments'].get('LT')}"
            )
    bone = next(f for f in formations if f["id"] == "wishbone")
    wb_power = {
        "id": "x-wb-power",
        "scheme": "Power",
        "call": "Wishbone 44 Power",
        "direction": "right",
        "assignments": {
            "QB": {"rule": "Hand it.", "type": "fake", "path": [[1.0, -0.5]]},
            "RH": {"rule": "Run it.", "type": "run", "path": [[0.6, 1.8], [1.4, 5.6]]},
            "LH": {"rule": "Fake it.", "type": "fake", "path": [[-1.8, 0.2]]},
        },
    }
    wb_filled = blocking.fill_assignments(wb_power, bone, 1)
    if wb_filled.get("Y", {}).get("block") != "kick":
        problems.append(
            f"Wishbone Power must kick with the playside end, got {wb_filled.get('Y')}"
        )
    if "Z" in wb_filled:
        problems.append("Wishbone Power filled a slot the formation does not have")
    if wb_filled.get("FB", {}).get("block") != "lead":
        problems.append(
            f"Wishbone Power must lead with the fullback, got {wb_filled.get('FB')}"
        )
    # A note on the lead merges; a leftover trail stays.
    noted = copy.deepcopy(play)
    noted["assignments"]["FB"] = {"note": "Hit downhill."}
    noted["assignments"]["X"] = {"block": "cutoff"}  # leftover? that's scheme backside_te
    merged = blocking.fill_assignments(noted, i_form, 1)
    if merged["FB"].get("block") != "lead" or merged["FB"].get("note") != "Hit downhill.":
        problems.append(f"lead note did not merge onto Power: {merged.get('FB')}")
    return problems


def check_book(formations) -> list[str]:
    problems = []
    for form in formations:
        for play in form["_plays"]:
            pid = play["id"]
            if play.get("scheme") not in blocking.SCHEMES:
                problems.append(f"{pid}: scheme {play.get('scheme')!r} is not a named family")
                continue
            expected = blocking.expected_scheme(play)
            if expected and play["scheme"] != expected:
                problems.append(f"{pid}: scheme {play['scheme']} vs call {expected}")
            missing = set(form["alignment"]) - set(play["assignments"])
            if missing:
                problems.append(f"{pid}: fill left {sorted(missing)} without a job")
            for msg in blocking.scheme_conflicts(play, form, render.play_side(play)):
                problems.append(msg)
    return problems


def check_validate_rejects_wrong_scheme(formations) -> list[str]:
    problems = []
    form = next(f for f in formations if f["id"] == "i-form")
    defenses = render.load_defenses()
    play = copy.deepcopy(next(p for p in form["_plays"] if p["id"] == "i-power-r"))
    play["scheme"] = "Smash"
    form["_plays"] = [
        play if p["id"] == "i-power-r" else p for p in form["_plays"]
    ]
    errors = render.validate([form], defenses)
    if not any("does not match the call" in e and "i-power-r" in e for e in errors):
        problems.append(
            "validate did not reject Power numbered 36 with scheme Smash: "
            + "; ".join(errors[:5])
        )
    return problems


def main() -> int:
    formations = render.load_formations()
    problems = []
    problems += check_templates()
    problems += check_roles(formations)
    problems += check_fill(formations)
    problems += check_book(formations)
    problems += check_validate_rejects_wrong_scheme(formations)
    if problems:
        print(f"{len(problems)} scheme problem(s):\n")
        for p in problems:
            print(f"  {p}")
        return 1
    n = sum(len(f["_plays"]) for f in formations)
    print(f"{len(FAMILIES)} schemes, {n} plays filled from them, "
          "and a 36 Smash scheme is rejected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
