#!/usr/bin/env python3
"""Check every block is drawn onto the man it names — in every front.

Every card is a picture an eight-year-old is asked to copy, and what the picture has to
make plain is who blocks whom. The line goes straight onto that man. Which shoulder to
take is in the words of the rule; drawing it as a finish off to one side of him made the
matchup harder to read, so the picture stopped trying.

This used to check one front, because a play was drawn against one front. Now a play is
drawn against three and its blocks are computed rather than typed, so the same four rules
are checked 168 times instead of 56. That is the point of computing them: a rule that is
right against the 5-3 and draws a guard into thin air against the 4-4 is exactly the bug
nobody would ever find by eye, and there are now three times as many chances to make it.

  A BLOCK NAMING A MAN finishes on him — at the edge of his X, not a yard off to one
  side and not in open grass. The engine marks each resolved block `aims: man` or
  `aims: space`, and the ones aimed at a spot — a wedge, a cut-off, "block the first
  wrong shirt you see" — are exempt, because the man they block is not there yet.

  A FAKE BLOCKS LIKE THE RUN IT SELLS. Where a play-action pass and the run it fakes
  give a lineman the same verb, it must resolve to the same block. Pass protection may
  differ — somebody has to protect a quarterback the run never had — but the same verb
  coming out two different ways means the play's side is wrong.

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

# How far from its man a block may finish: the stop short of his X, and a hair for
# rounding. Anything further is a line that does not land on anybody.
REACH = blocking.ON_MAN + 0.1


def endpoint(alignment, pos, spec):
    sx, sy = alignment[pos]
    path = spec.get("path") or []
    return (sx + path[-1][0], sy + path[-1][1]) if path else (sx, sy)


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
                            "the nearest defender — the line has to land on the man")
    return problems


# Our line, for the play-action check.
LINE = ("X", "LT", "LG", "C", "RG", "RT", "Y")


def check_play_action(play, defenses):
    """A fake has to block like the run it sells.

    Not identically — the boot-side tackle hinges and the centre cuts off, because
    somebody has to protect a quarterback the run never had. But where the fake and
    the run give a lineman THE SAME VERB, it has to resolve to the same block. If it
    does not, the play's side is wrong, and the line is drawing the mirror image of
    the run it is advertising. That is what "playside" meant before `fakes` existed:
    the direction the quarterback finished in, not the direction the fake went.
    """
    run = render.faked_play(play)
    if run is None:
        return []
    problems = []
    for fid in blocking.SCOUT_FRONTS:
        a = render.resolved_assignments(play, defenses[fid])
        b = render.resolved_assignments(run, defenses[fid])
        for pos in LINE:
            pa = play["assignments"].get(pos, {})
            pb = run["assignments"].get(pos, {})
            if pa.get("block") is None or pa.get("block") != pb.get("block"):
                continue
            # Compare the generated block, not the play-specific note appended after
            # it. "Sell it, this has to look like Power" is exactly the sort of thing a
            # fake SHOULD say and the run should not.
            note = pa.get("note") or pa.get("sell") or ""
            ra = a[pos]["rule"][:-len(note) - 1] if note and a[pos]["rule"].endswith(note) \
                else a[pos]["rule"]
            nb = pb.get("note") or pb.get("sell") or ""
            rb = b[pos]["rule"][:-len(nb) - 1] if nb and b[pos]["rule"].endswith(nb) \
                else b[pos]["rule"]
            if ra != rb:
                problems.append(
                    f"{pos} blocks '{pa['block']}' on both this and {run['id']}, but "
                    f"vs the {fid} they come out different — the fake is blocking the "
                    "mirror image of the run it sells")
    return problems


def check_slot_takes_a_back(play, resolved, alignment, front, fid) -> list[str]:
    """The Z screens a defensive back. Never a linebacker, in any front.

    This is a coaching rule, not a geometry result, which is exactly why it needs a
    test: it used to be decided by a seven-yard reach check, and against the 5-4-2 and
    the prevent -- the two fronts with no corner -- that check quietly handed the job
    to an outside linebacker instead. Nothing failed. The card just said something
    else, in the two fronts nobody drills against.
    """
    problems = []
    spec = resolved.get("Z") or {}
    if spec.get("type") != "block" or spec.get("aims") != "man":
        return problems          # carrying it, or no job from the scheme
    if (play.get("fronts") or {}).get(fid, {}).get("Z"):
        return problems          # the coach named the man himself
    # The engine does not record the man by name, so read him off the end of the line
    # the same way check_reaches does: the defender the block finishes on.
    ex, ey = endpoint(alignment, "Z", spec)
    everyone = (blocking.spots(front, "DL") + blocking.spots(front, "LB")
                + blocking.spots(front, "DB"))
    label, _x, _y = min(everyone, key=lambda s: (ex - s[1]) ** 2 + (ey - s[2]) ** 2)
    backs = {lb for lb, _bx, _by in blocking.spots(front, "DB")}
    if label not in backs:
        problems.append(
            f"the Z's block finishes on {label}, who is not a defensive back in this "
            "front — the slot screens the back on his side, whatever depth he plays")
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
            alignment = render.play_alignment(form, play)
            for fid in blocking.SCOUT_FRONTS:
                front = defenses[fid]
                resolved = render.resolved_assignments(play, front)
                checked += 1
                where = f"{play['id']} vs {fid}"
                for problem in check_reaches(play, resolved, alignment, front, frame):
                    failures.append(f"{where}: {problem}")
                for problem in check_slot_takes_a_back(play, resolved, alignment, front, fid):
                    failures.append(f"{where}: {problem}")
            for problem in check_play_action(play, defenses):
                failures.append(f"{play['id']}: {problem}")

    if failures:
        print(f"{len(failures)} blocking problem(s) across {checked} play/front pairs:\n")
        for f in failures:
            print(f"  {f}")
        return 1
    print(f"{checked} play/front pairs: every block that names a man lands on him, "
          "no block runs off the diagram, the Z screens a defensive back in every "
          "front, and every fake blocks like the run it sells.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
