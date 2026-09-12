#!/usr/bin/env python3
"""Print one play's assignments as they resolve against each front.

The whole point of writing blocking intents instead of prose is that one line of JSON
becomes three different blocks. That is only an improvement if somebody reads all three,
so this prints them side by side without rebuilding the book.

    python generator/preview.py i-power-r
    python generator/preview.py i-power-r --front 4-4
    python generator/preview.py --formation i-form     # every play in one formation

It also flags the two things that go wrong when an intent is chosen badly: two blockers
sent to the same defender, and a defender near the hole nobody is assigned to — down
linemen, linebackers and the corners, who on a wide play are the men the whole call
lives or dies on.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import blocking  # noqa: E402
import render  # noqa: E402

# How close a block has to finish to a defender to count as being on him. A stalk
# block stands off its man on purpose, so this matches the engine's own claim radius —
# at 1.1 a correctly executed screen was reported as leaving its man unblocked.
ON_HIM = 1.4
# Anything deeper than this is a defensive back, and nobody is expected to block him.
IN_THE_BOX = 4.0
# How close to the hole a defender has to be before leaving him unblocked is a problem.
NEAR_THE_HOLE = 2.0
# How much ground a blocker aimed at a spot rather than a man covers around it.
COVERS_SPACE = 1.7


def touches(alignment, pos, spec):
    """Every point on this blocker's path, in field coordinates.

    Every point and not just the last one: a double team's line goes to the man being
    doubled and then on to the linebacker, and crediting only where it stops would
    report the man two blockers just drove off the ball as unblocked.
    """
    sx, sy = alignment[pos]
    path = spec.get("path") or []
    return [(sx + dx, sy + dy) for dx, dy in path] or [(sx, sy)]


def audit(play, alignment, front, assignments) -> list[str]:
    """Who is blocked by two men who did not mean to be, and who is running free."""
    defenders = (blocking.spots(front, "DL") + blocking.spots(front, "LB")
                 + blocking.spots(front, "DB"))
    claimed: dict[str, list[str]] = {}
    for pos, spec in assignments.items():
        if spec.get("type") != "block":
            continue
        # A blocker sent to a spot rather than to a man does not claim whoever he
        # happens to finish nearest — "block the first wrong shirt you see" is an
        # instruction about a man who is not there yet.
        if spec.get("aims") != "man":
            continue
        # Where he FINISHES is who he is blocking. Counting every point he runs past
        # makes a lead blocker whose path clips a defensive tackle look like the third
        # man on a double team.
        fx, fy = touches(alignment, pos, spec)[-1]
        near = [(((fx - x) ** 2 + (fy - y) ** 2) ** 0.5, label) for label, x, y in defenders]
        dist, label = min(near)
        if dist <= ON_HIM:
            claimed.setdefault(label, []).append(pos)

    notes = []
    lbs = {s[0] for s in blocking.spots(front, "LB")}
    for label, blockers in sorted(claimed.items()):
        # Two on a down lineman is a double team and the point of several plays. Two on
        # a LINEBACKER is two blockers doing one job, and it was invisible while this
        # only complained at three.
        limit = 1 if label in lbs else 2
        if len(blockers) > limit:
            notes.append(f"{len(blockers)} blockers ({', '.join(blockers)}) are on "
                         f"{label} — one man does not need them")

    # A wedge blocks everyone in front of it and picks nobody — that is the definition
    # of the play. There is no man-by-man account to take, so there is nothing here to
    # report.
    if any(spec.get("block") == "wedge" for spec in play["assignments"].values()):
        return notes

    # A blocker sent to a spot still blocks whoever turns up in it. He does not *claim*
    # a defender — two of them aimed at the same hole are not a double team — but a
    # linebacker standing in the hole he is running to is not unblocked either.
    # Covered is a wider question than claimed: a man somebody runs through on the way
    # to his own block is not free, and a blocker sent to a spot covers whoever turns
    # up in it.
    covered = set(claimed)
    for pos, spec in assignments.items():
        if spec.get("type") != "block":
            continue
        reach = COVERS_SPACE if spec.get("aims") != "man" else ON_HIM
        for fx, fy in touches(alignment, pos, spec):
            for label, x, y in defenders:
                if (fx - x) ** 2 + (fy - y) ** 2 <= reach ** 2:
                    covered.add(label)

    side = render.play_side(play)
    # Where the ball ACTUALLY crosses the line, taken from the carrier's own path, not
    # from the hole table's midpoint. On a wide play those differ by a yard or more,
    # and a yard is the difference between a corner standing in the carrier's way and
    # one he was always going to run past.
    hole = render.play_hole(play)
    carrier = play.get("ball_carrier")
    if carrier and carrier in assignments:
        crossing = render.los_crossing(alignment, carrier, assignments[carrier])
        if crossing is not None:
            hole = crossing
    for label, x, y in (blocking.spots(front, "DL") + blocking.spots(front, "LB")
                        + blocking.spots(front, "DB")):
        if y > IN_THE_BOX or label in covered:
            continue
        # Only a defender near where the ball is actually going. A backside linebacker
        # is cut off rather than blocked, and an outside linebacker six yards wide of
        # an inside dive is beaten by the handoff, not by a blocker.
        # Every pass in this book is a boot or a waggle, and every one of them beats
        # the edge with the quarterback's legs rather than with a blocker. Reporting
        # the unblocked end on a bootleg is reporting the play. Inside the tackles is
        # still checked, because a pass rusher coming free up the middle is a bug.
        if play.get("type") == "pass" and abs(x) > 3.0:
            continue
        if x * side >= -1.0 and abs(x - hole) <= NEAR_THE_HOLE:
            notes.append(f"nobody blocks {label}, {abs(x - hole):.1f} yards from the hole")
    return notes


def show(play, front, verbose=True):
    alignment = render.play_alignment(play["_formation"], play)
    assignments = render.resolved_assignments(play, front)
    if verbose:
        print(f"  --- vs {front['name']} " + "-" * 46)
        for pos in render.ordered_positions(play):
            spec = assignments[pos]
            mark = "*" if pos == play.get("ball_carrier") else " "
            verb = play["assignments"][pos].get("block", spec.get("type", ""))
            print(f"  {mark}{pos:4} [{verb:7}] {spec['rule']}")
    for note in audit(play, alignment, front, assignments):
        print(f"  !! {front['id']}: {note}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("play", nargs="?", help="play id, e.g. i-power-r")
    ap.add_argument("--formation", help="every play in this formation")
    ap.add_argument("--front", help="just this front")
    ap.add_argument("--audit", action="store_true", help="only the warnings")
    args = ap.parse_args()

    defenses = render.load_defenses()
    formations = render.load_formations()
    fronts = ([defenses[args.front]] if args.front
              else [defenses[f] for f in blocking.SCOUT_FRONTS])

    plays = [p for form in formations for p in form["_plays"]
             if (args.play and p["id"] == args.play)
             or (args.formation and form["id"] == args.formation)
             or (not args.play and not args.formation)]
    if not plays:
        print("no such play", file=sys.stderr)
        return 1

    for play in plays:
        print(f"\n=== {play['id']}  {play['name']}  [{play.get('call', '')}]")
        for front in fronts:
            show(play, front, verbose=not args.audit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
