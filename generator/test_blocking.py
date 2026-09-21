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


def check_god(play, resolved, alignment, front, fid) -> list[str]:
    """Every interior lineman blocks the man GOD sends him to. G, then O, then D.

    Worked out here from the raw alignments, independently of the engine, so this
    is a second opinion and not an echo: the gap between this blocker and the man
    inside him, then a half-yard band around his own nose, then a linebacker.

    The point of the rule is that a boy carries one order onto the field instead
    of a job per play, and the moment one play quietly hand-writes a line rule
    again he is back to memorising fifty-eight of them. So the build checks it.
    """
    problems = []
    if play.get("type") == "pass" and play.get("scheme") == "Protect":
        return problems          # dropback protection is not a GOD rule
    for pos in blocking.GOD_LINE:
        spec = resolved.get(pos) or {}
        if spec.get("type") != "block":
            continue
        if (play.get("fronts") or {}).get(fid, {}).get(pos):
            continue             # the coach named the man himself
        x = alignment[pos][0]
        dl = blocking.spots(front, "DL")
        want, letter = None, None
        gap = blocking.inside_gap(alignment, pos)
        if gap is not None:
            lo, hi = gap
            inside = [d for d in dl
                      if lo + blocking.ON_SHADE < d[1] < hi - blocking.ON_SHADE]
            if inside:
                want = min(inside, key=lambda d: abs(d[1] - x))
                letter = "G"
        if want is None:
            on = [d for d in dl if abs(d[1] - x) <= blocking.ON_SHADE]
            if on:
                want = min(on, key=lambda d: abs(d[1] - x))
                letter = "O"
        if want is None:
            continue             # D: which linebacker is first-come, checked below
        ex, ey = endpoint(alignment, pos, spec)
        got = min(dl + blocking.spots(front, "LB") + blocking.spots(front, "DB"),
                  key=lambda d: (ex - d[1]) ** 2 + (ey - d[2]) ** 2)
        if got[0] != want[0]:
            problems.append(
                f"{pos} has a {letter} on the {want[0]} and blocked the {got[0]} "
                f"instead — GOD is gap, then on, then downfield"
            )
        if not spec["rule"].startswith(f"{letter} —"):
            problems.append(
                f"{pos} blocks the {want[0]}, which is his {letter}, but the card "
                f"does not say so: {spec['rule'][:48]!r}"
            )
    # Nobody goes downfield to a linebacker another lineman already has.
    downfield = {}
    for pos in blocking.GOD_LINE:
        spec = resolved.get(pos) or {}
        if spec.get("type") == "block" and spec.get("rule", "").startswith("D —"):
            ex, ey = endpoint(alignment, pos, spec)
            lbs = blocking.spots(front, "LB")
            if not lbs:
                continue
            man = min(lbs, key=lambda d: (ex - d[1]) ** 2 + (ey - d[2]) ** 2)
            if man[0] in downfield:
                problems.append(
                    f"{pos} and {downfield[man[0]]} both went downfield to the "
                    f"{man[0]}, leaving a linebacker free"
                )
            downfield[man[0]] = pos
    return problems


# A made-up front, not one we play against. Every front in the book today stands
# its down linemen head up on somebody, so the G in GOD never fires on a real
# card -- 0 of 550 interior assignments -- and a branch the corpus cannot reach
# is a branch no corpus test can hold. This one puts a 3 technique in each B gap
# and a nose shaded onto the center's right shoulder, which is what a team that
# has watched film of us would do, and checks the order comes out G, O, D.
GAP_FRONT = {
    "roles": {"LDT": "DL", "NT": "DL", "RDT": "DL", "MLB": "LB",
              "LOLB": "LB", "ROLB": "LB"},
    "alignment": {"LDT": [-2.1, 0.8], "NT": [0.35, 0.8], "RDT": [2.1, 0.8],
                  "MLB": [0.0, 3.5], "LOLB": [-3.5, 3.5], "ROLB": [3.5, 3.5]},
    "position_names": {"LDT": "Left defensive tackle", "NT": "Nose tackle",
                       "RDT": "Right defensive tackle", "MLB": "Middle linebacker",
                       "LOLB": "Left outside linebacker",
                       "ROLB": "Right outside linebacker"},
}

LINE_SPOTS = {"LT": [-2.8, -0.5], "LG": [-1.4, -0.5], "C": [0.0, -0.5],
              "RG": [1.4, -0.5], "RT": [2.8, -0.5]}


def check_god_progression() -> list[str]:
    """G before O before D, and the letter on the card matches the man."""
    problems = []
    want = {
        # The 3 techniques sit in the tackles' inside gaps, so both tackles
        # have a G. The guards have nothing in their gaps and nobody on them.
        "LT": ("G", "LDT"), "RT": ("G", "RDT"),
        "LG": ("D", None), "RG": ("D", None),
        # A nose shaded 0.35 off the center is still ON him, not in a gap.
        "C": ("O", "NT"),
    }
    taken = set()
    for pos in ("LT", "LG", "C", "RG", "RT"):
        spec = blocking.resolve(pos, {"block": "god"}, LINE_SPOTS, GAP_FRONT, 1,
                                taken=taken)
        letter, man = want[pos]
        if not spec["rule"].startswith(f"{letter} —"):
            problems.append(
                f"GAP_FRONT {pos} should be a {letter}: {spec['rule'][:52]!r}"
            )
        if man is not None:
            ex = LINE_SPOTS[pos][0] + spec["path"][-1][0]
            ey = LINE_SPOTS[pos][1] + spec["path"][-1][1]
            got = min(blocking.spots(GAP_FRONT, "DL") + blocking.spots(GAP_FRONT, "LB"),
                      key=lambda d: (ex - d[1]) ** 2 + (ey - d[2]) ** 2)
            if got[0] != man:
                problems.append(
                    f"GAP_FRONT {pos} should block the {man}, blocked the {got[0]}"
                )
        got_lb = blocking.claimed_lb(GAP_FRONT, LINE_SPOTS[pos], spec["path"])
        if got_lb:
            taken.add(got_lb)
    # Both guards climb here, and the second must not climb to the man the
    # first already has. Compared by the MAN, not by the path: two blockers
    # standing 2.8 yards apart reach the same linebacker on different lines.
    lg = blocking.resolve("LG", {"block": "god"}, LINE_SPOTS, GAP_FRONT, 1)
    lg_man = blocking.claimed_lb(GAP_FRONT, LINE_SPOTS["LG"], lg["path"])
    rg = blocking.resolve("RG", {"block": "god"}, LINE_SPOTS, GAP_FRONT, 1,
                          taken={lg_man})
    rg_man = blocking.claimed_lb(GAP_FRONT, LINE_SPOTS["RG"], rg["path"])
    if lg_man is None or rg_man is None:
        problems.append(f"a climbing guard reached nobody: {lg_man}, {rg_man}")
    elif lg_man == rg_man:
        problems.append(f"both guards climbed to the {lg_man}")
    # A center with nobody on him has no inside gap to check, so he climbs.
    bare = {**GAP_FRONT, "alignment": {k: v for k, v in GAP_FRONT["alignment"].items()
                                       if k != "NT"},
            "roles": {k: v for k, v in GAP_FRONT["roles"].items() if k != "NT"}}
    spec = blocking.resolve("C", {"block": "god"}, LINE_SPOTS, bare, 1)
    if not spec["rule"].startswith("D —"):
        problems.append(f"an uncovered center should climb: {spec['rule'][:52]!r}")
    if blocking.inside_gap(LINE_SPOTS, "C") is not None:
        problems.append("the center must have no inside gap")
    # The inside gap is the one toward the CENTER, on his own side of the ball.
    if blocking.inside_gap(LINE_SPOTS, "LG") != (-1.4, 0.0):
        problems.append(
            f"left guard's inside gap is {blocking.inside_gap(LINE_SPOTS, 'LG')}"
        )
    if blocking.inside_gap(LINE_SPOTS, "RT") != (1.4, 2.8):
        problems.append(
            f"right tackle's inside gap is {blocking.inside_gap(LINE_SPOTS, 'RT')}"
        )
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
                for problem in check_god(play, resolved, alignment, front, fid):
                    failures.append(f"{where}: {problem}")
            for problem in check_play_action(play, defenses):
                failures.append(f"{play['id']}: {problem}")
    failures += check_god_progression()

    if failures:
        print(f"{len(failures)} blocking problem(s) across {checked} play/front pairs:\n")
        for f in failures:
            print(f"  {f}")
        return 1
    print(f"{checked} play/front pairs: every block that names a man lands on him, "
          "no block runs off the diagram, every interior lineman blocks GOD and no "
          "two of them climb to the same linebacker, the Z screens a defensive back "
          "in every front, and every fake blocks like the run it sells.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
