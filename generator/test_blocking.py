#!/usr/bin/env python3
"""Check blocking lines are drawn to the correct side of the man they name.

Every card is a picture an eight-year-old is asked to copy. If the line is drawn to the
wrong side of the defender, the picture is teaching him to run into his own blocker, and
nothing else in the build notices — the play still has eleven assignments, the call still
matches the hole, the card still fits on a sheet.

Two rules, both about which side the blocker finishes on:

  THE CENTRE seals the nose away from the hole, so he steps TOWARD the playside. If he
  steps away, the nose ends up between him and the ball. The exception is a boot, a
  waggle or a sweep whose rule says in so many words to drive the nose away from the
  play — then away is the point.

  A KICK-OUT attacks the defender's inside shoulder and drives him out; the runner goes
  inside the block. So the blocker finishes INSIDE the man, at his depth. A line that
  stops in the backfield never reaches him, and a line that finishes outside him draws
  the blocker running past — letting the defender come underneath, which is the exact
  thing those rules warn against.

    python generator/test_blocking.py

No dependencies. Run it after adding a play or moving a path.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render  # noqa: E402

# How close the finish has to be to the man's own depth to count as reaching him.
DEPTH_TOLERANCE = 0.6

AWAY_ON_PURPOSE = ("away from the boot", "away from the waggle",
                   "away from where we are going")


def endpoint(alignment, pos, spec):
    sx, sy = alignment[pos]
    path = spec.get("path") or []
    return (sx + path[-1][0], sy + path[-1][1]) if path else (sx, sy)


def playside_of(play):
    """+1 if the call sends the ball right, -1 left."""
    m = re.search(r"\b(\d)(\d)\b", play.get("call", "") or "")
    return None if not m else (1 if int(m.group(2)) % 2 == 0 else -1)


def check_centre(play, alignment, side):
    spec = play["assignments"].get("C")
    if not spec or "nose" not in spec["rule"].lower():
        return None
    step = (spec.get("path") or [[0, 0]])[-1][0]
    rule = spec["rule"].lower()
    if any(p in rule for p in AWAY_ON_PURPOSE):
        if step * side >= 0:
            return ("the rule says drive the nose away from the play, "
                    f"but the centre steps {'right' if step > 0 else 'left'} "
                    f"into a play going {'right' if side > 0 else 'left'}")
        return None
    if abs(step) < 0.05:          # a wedge has no playside
        return None
    if step * side <= 0:
        return (f"centre steps {'right' if step > 0 else 'left'} on a play going "
                f"{'right' if side > 0 else 'left'} — that leaves the nose between him "
                "and the hole")
    return None


def check_kickouts(play, alignment, side, defence):
    """Only real kick-out assignments: the rule tells this blocker to kick somebody out."""
    problems = []
    end_key = "RE" if side > 0 else "LE"
    if end_key not in defence:
        return problems
    tx, ty = defence[end_key]
    for pos, spec in play["assignments"].items():
        if spec.get("type") != "block":
            continue
        rule = spec["rule"].lower()
        # Only the assignments that name the END. "Kick out the first defender who
        # shows" on a wide toss means the force man out in space, who is nowhere near
        # the defensive end and should not be measured against him.
        if not re.search(r"\bkick (?:the end out|out the end)\b", rule):
            continue
        # "the end over you is getting kicked out — leave him alone" is the opposite
        # instruction, and belongs to a different blocker.
        if "leave him alone" in rule:
            continue
        ex, ey = endpoint(alignment, pos, spec)
        if abs(ey - ty) > DEPTH_TOLERANCE:
            problems.append(f"{pos} is told to kick the end out but the line stops at "
                            f"y={ey:+.1f}, {abs(ty - ey):.1f} yards off the man at "
                            f"y={ty:+.1f}")
        if abs(ex) >= abs(tx):
            problems.append(f"{pos} finishes at x={ex:+.1f}, outside the end at "
                            f"x={tx:+.1f} — a kick-out finishes inside him")
    return problems


def main() -> int:
    defences = render.load_defenses()
    failures, checked = [], 0
    for form in render.load_formations():
        for play in form["_plays"]:
            side = playside_of(play)
            if side is None:
                continue
            alignment = render.play_alignment(form, play)
            defence = defences[play.get("defense", "5-3")]["alignment"]
            checked += 1
            problem = check_centre(play, alignment, side)
            if problem:
                failures.append(f"{play['id']}: {problem}")
            for problem in check_kickouts(play, alignment, side, defence):
                failures.append(f"{play['id']}: {problem}")

    if failures:
        print(f"{len(failures)} blocking problem(s) across {checked} plays:\n")
        for f in failures:
            print(f"  {f}")
        return 1
    print(f"{checked} plays: every centre steps to the correct side of the nose, and "
          "every kick-out finishes inside the man it names.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
