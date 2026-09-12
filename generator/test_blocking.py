#!/usr/bin/env python3
"""Check every block is drawn to the right side of the man it names — in every front.

Every card is a picture an eight-year-old is asked to copy. If the line is drawn to the
wrong side of the defender, the picture is teaching him to run into his own blocker, and
nothing else in the build notices — the play still has eleven assignments, the call still
matches the hole, the card still fits on a sheet.

This used to check one front, because a play was drawn against one front. Now a play is
drawn against three and its blocks are computed rather than typed, so the same four rules
are checked 168 times instead of 56. That is the point of computing them: a rule that is
right against the 5-3 and draws a guard into thin air against the 4-4 is exactly the bug
nobody would ever find by eye, and there are now three times as many chances to make it.

  THE CENTRE seals the nose away from the hole, so he steps TOWARD the playside. If he
  steps away, the nose ends up between him and the ball. The exception is a boot, a
  waggle or a sweep whose rule says in so many words to drive the nose away from the
  play — then away is the point.

  A KICK-OUT attacks the defender's inside shoulder and drives him out; the runner goes
  inside the block. So the blocker finishes INSIDE the man, at his depth. A line that
  stops in the backfield never reaches him, and a line that finishes outside him draws
  the blocker running past — letting the defender come underneath, which is the exact
  thing those rules warn against.

  A BLOCK NAMING A MAN has to reach one. A path that finishes in open grass is a blocker
  told to block nobody. The engine marks each resolved block `aims: man` or `aims:
  space`, and the ones aimed at a spot — a wedge, a cut-off, "block the first wrong
  shirt you see" — are exempt, because the man they block is not there yet.

  A BLOCK STAYS ON THE FIELD. A derived path that runs off the frame is a drawing bug,
  not a block.

    python generator/test_blocking.py

No dependencies. Run it after adding a play, changing an intent, or touching the engine.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import blocking  # noqa: E402
import render  # noqa: E402

# How close the finish has to be to the man's own depth to count as reaching him.
DEPTH_TOLERANCE = 0.6

# How far from every defender a block may finish before it is a block on nobody.
REACH = 1.6

AWAY_ON_PURPOSE = ("away from the boot", "away from the waggle",
                   "away from where we are going", "away from the play")


def endpoint(alignment, pos, spec):
    sx, sy = alignment[pos]
    path = spec.get("path") or []
    return (sx + path[-1][0], sy + path[-1][1]) if path else (sx, sy)


def check_centre(play, resolved, alignment, side):
    spec = resolved.get("C")
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


def check_kickouts(play, resolved, alignment, side, front):
    """Every assignment whose rule tells this blocker to kick the edge man out."""
    problems = []
    man = blocking.edge_defender(front, side)
    if man is None:
        return problems
    _, tx, ty = man
    for pos, spec in resolved.items():
        if spec.get("type") != "block":
            continue
        rule = spec["rule"].lower()
        if "kick the" not in rule or "out" not in rule:
            continue
        # "is getting kicked out — leave him alone" is the opposite instruction, and
        # belongs to a different blocker.
        if "leave him alone" in rule:
            continue
        ex, ey = endpoint(alignment, pos, spec)
        if abs(ey - ty) > DEPTH_TOLERANCE:
            problems.append(f"{pos} is told to kick the edge man out but the line stops "
                            f"at y={ey:+.1f}, {abs(ty - ey):.1f} yards off the man at "
                            f"y={ty:+.1f}")
        if abs(ex) >= abs(tx):
            problems.append(f"{pos} finishes at x={ex:+.1f}, outside the man at "
                            f"x={tx:+.1f} — a kick-out finishes inside him")
    return problems


def check_reaches(play, resolved, alignment, front, frame):
    """A block that names a man has to arrive somewhere near one, and stay on the field."""
    problems = []
    defenders = (blocking.spots(front, "DL") + blocking.spots(front, "LB")
                 + blocking.spots(front, "DB"))
    half, top, bottom = frame
    for pos, spec in resolved.items():
        if spec.get("type") != "block":
            continue
        ex, ey = endpoint(alignment, pos, spec)
        if abs(ex) > half or ey > top or ey < bottom:
            problems.append(f"{pos} finishes at ({ex:+.1f}, {ey:+.1f}), off the "
                            "diagram — the line is drawn outside the frame")
        # The engine says which blocks name a man. One aimed at a spot — "block the
        # first wrong shirt you see" — has nobody to reach by design.
        if spec.get("aims") != "man":
            continue
        verb = play["assignments"][pos].get("block")
        near = min(((ex - x) ** 2 + (ey - y) ** 2) ** 0.5 for _, x, y in defenders)
        if near > REACH:
            problems.append(f"{pos} blocks '{verb}' but finishes {near:.1f} yards from "
                            "the nearest defender — that is a block on nobody")
    return problems


def main() -> int:
    defenses = render.load_defenses()
    formations = render.load_formations()
    for form in formations:
        for play in form["_plays"]:
            for fid in blocking.SCOUT_FRONTS:
                render.resolved_assignments(play, defenses[fid])
    frame = render.diagram_frame(formations, defenses)

    failures, checked = [], 0
    for form in formations:
        for play in form["_plays"]:
            side = render.play_side(play)
            alignment = render.play_alignment(form, play)
            for fid in blocking.SCOUT_FRONTS:
                front = defenses[fid]
                resolved = render.resolved_assignments(play, front)
                checked += 1
                where = f"{play['id']} vs {fid}"
                problem = check_centre(play, resolved, alignment, side)
                if problem:
                    failures.append(f"{where}: {problem}")
                for problem in check_kickouts(play, resolved, alignment, side, front):
                    failures.append(f"{where}: {problem}")
                for problem in check_reaches(play, resolved, alignment, front, frame):
                    failures.append(f"{where}: {problem}")

    if failures:
        print(f"{len(failures)} blocking problem(s) across {checked} play/front pairs:\n")
        for f in failures:
            print(f"  {f}")
        return 1
    print(f"{checked} play/front pairs: every centre steps to the correct side of the "
          "nose, every kick-out finishes inside the man it names, and every block that "
          "names a man reaches one.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
