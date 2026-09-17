#!/usr/bin/env python3
"""Blocking rules, resolved against a defensive front.

A blocking assignment used to be a paragraph of prose and a hand-drawn path, written
for one front. That made three things true at once, all of them bad: the same sentence
was typed 431 times with small differences, half of every sentence was a statement
about where the defence lined up ("Nobody is over you", "The tackle is on your inside
shoulder") rather than an instruction, and the card was only correct against the one
front it was drawn against. Show the same play to a team in a different defence and the
card is teaching the wrong block.

So a blocking assignment is now an *intent* — a verb out of a closed list, and at most
a target and a play-specific note:

    "RT": { "block": "down" }
    "SL":  { "block": "kick" }
    "FB": { "block": "lead" }

and this module resolves that intent against an actual front to produce the sentence a
kid reads and the line the diagram draws. Change the front and both change, because
both are computed from where that front's eleven are standing.

The verbs are deliberately few. A vocabulary an eight-year-old can hold is worth more
than one that can express every nuance, and every nuance that survived the cut is in
the `note`.

    base    drive the man over you             kick    kick out the edge defender
    down    first defender on or inside you    lead    through the hole, first man who shows
    reach   head across his playside shoulder  release leave the kicked man, take a backer
    double  two on one, then climb             screen  get in a defensive back's way
    climb   straight to a linebacker           wedge   shoulder to shoulder, push
    cutoff  nobody chases from behind          decoy   sell a fake
    hinge   protect the quarterback's back

**Nobody pulls.** There is no verb for it and there is not meant to be. A pulling guard
is the one block on a card that asks an eight-year-old to leave the only spot he has
learned, run flat behind two bodies he cannot see over, and arrive somewhere before a
linebacker does — and when he is a half-count late, which he is, the hole he vacated is
the hole the play was going to. Every job a puller used to do now belongs to somebody
who was already standing there: the playside end kicks the end out, a back leads through
the hole, and the backside guard cuts off behind the play.
"""

from __future__ import annotations

import copy
import re

# The three fronts every offensive play is drawn and blocked against. An 8U team lines
# up in one of these against us; the toggle on a play page is these in this order.
# The 6-3 goal line and the 6-2-3 prevent are our own calls, not looks we expect to
# face on a normal down, so they are not in the toggle.
SCOUT_FRONTS = ("4-4", "5-3", "5-4-2")

# The front a card is drawn against when nothing says otherwise, and the one the
# printed book uses. The 4-4 is our everyday front, so it is the picture that opens
# on every play and the one that goes in a coach's pocket.
DEFAULT_FRONT = "4-4"

# The holes, off the nomenclature card: 0 is straight over the center, and from
# there they count outward, even to the right and odd to the left.
#
#     9  |  7  |  5  |  3  | 0 |  2  |  4  |  6  |  8
#       LTE    LT    LG     C     RG    RT   RTE
#
# There is no 1. The middle is one hole, not two, because a back aimed at the
# center's back is aimed at one place, and a number that names the same place
# twice is a number nobody can call.
#
# The play word IS the hole. A numbered run's call has to say this word — 36
# Power, 32 Smash, 38 Toss — so the huddle and the diagram name the same family.
# Word calls (a tight end sweep, a slant-out pass) opt out because they have no
# hole digit.
#
# Sweep is the exception: the quarterback (1) or the slot (4) coming across, or
# a tight end on an end-around. Those still hit the 8/9 hole, but the word is
# who is sweeping, not Toss. 38 Toss is still Toss — that is a pitch, not a sweep.
HOLE_SCHEME = {
    0: "Smash",              # over the center
    2: "Smash", 3: "Smash",  # A gap: center–guard
    4: "Dive",  5: "Dive",   # B gap: guard–tackle
    6: "Power", 7: "Power",  # C gap: tackle–tight end
    8: "Toss",  9: "Toss",   # outside the tight end
}

# The one hole number the card does not have. Spelled out so the build can say
# so by name rather than failing on geometry nobody can read.
NO_SUCH_HOLE = 1

# Digit 1 is always the quarterback. Digit 4 is the slot in every look that
# has one — Sweep is who, so a formation that puts a halfback on 4 (Wishbone)
# does not turn 48/49 into Sweep.
SWEEP_BACKS = ("1", "4")  # used only when the formation is unknown

CALL_DIGITS = re.compile(r"\b(\d)(\d)\b")


def scheme_for_hole(hole: int) -> str | None:
    """The play word a numbered run at this hole has to carry."""
    return HOLE_SCHEME.get(hole)


def is_sweep_back(back_digit: str | None, form: dict | None = None) -> bool:
    """True when this numbered back sweeping at 8/9 is Sweep, not Toss.

    The quarterback (1) always is. The slot is too — and the slot is whoever
    `backs` maps to `SL`, not whichever digit happens to be 4. Wishbone's 4 is
    the right halfback; 49 Toss is a toss.
    """
    if not back_digit:
        return False
    if back_digit == "1":
        return True
    if form:
        return (form.get("backs") or {}).get(back_digit) == "SL"
    return back_digit in SWEEP_BACKS


def scheme_words(hole: int, back_digit: str | None = None,
                 form: dict | None = None) -> tuple[str, ...]:
    """Allowed play words at this hole: the scheme, or Fake plus the scheme.

    The quarterback (18/19) or slot (48/49) sweeping across at 8/9 is Sweep, not Toss.
    """
    if hole in (8, 9) and is_sweep_back(back_digit, form):
        return ("Sweep", "Fake Sweep")
    word = scheme_for_hole(hole)
    if not word:
        return ()
    return (word, f"Fake {word}")


# --------------------------------------------------------------- named schemes --
#
# The huddle word is also the blocking family. Smash, Dive, Power, Toss and
# Sweep each name eleven jobs by *role* — playside end, playside guard, lead
# back — not by LTE/RTE, so the same scheme fills a Regular I, a Split Backs
# and whatever formation comes next. Protect is the dropback: everybody pass
# blocks except the receiver and the slot, who screens the corner.
#
# A play names its scheme and writes the paths that are the play itself (the
# handoff, the fake, the route). The line, the slot and the lead come from the
# scheme. Leftover backs — a trailing halfback who also leads on a tight-end
# sweep, a note on the toss lead — stay on the play because they are the play,
# not the family.

# The seven line spots, middle out. Playside is the last three when the play
# goes right, the first three reversed when it goes left.
LINE_ROLES_RIGHT = {
    "playside_te": "RTE", "playside_t": "RT", "playside_g": "RG",
    "center": "C",
    "backside_g": "LG", "backside_t": "LT", "backside_te": "LTE",
}
LINE_ROLES_LEFT = {
    "playside_te": "LTE", "playside_t": "LT", "playside_g": "LG",
    "center": "C",
    "backside_g": "RG", "backside_t": "RT", "backside_te": "RTE",
}

# Shared interior: both ends cut off, uncovered guard doubles, fullback (or the
# playside halfback) leads through the hole. Smash and Dive differ only on
# which uncovered lineman climbs — the guard on Smash (A-gap), the tackle on
# Dive (B-gap).
_INSIDE_LINE = {
    "playside_t": {"block": "down"},
    "center": {"block": "reach"},
    "backside_g": {"block": "cutoff"},
    "backside_t": {"block": "down"},
    "backside_te": {"block": "cutoff"},
    "playside_te": {"block": "cutoff"},
    "slot": {"block": "screen"},
    "lead": {"block": "lead"},
}

# Shared perimeter: the playside end turns the man inside, the uncovered guard
# climbs, the lead back takes the force man. Toss and Sweep share this line;
# who carries it is what the huddle word is for.
_OUTSIDE_LINE = {
    "playside_te": {"block": "base", "drive": "in"},
    "playside_t": {"block": "down"},
    "playside_g": {"block": "climb", "target": "playside"},
    "center": {"block": "reach"},
    "backside_g": {"block": "cutoff"},
    "backside_t": {"block": "down"},
    "backside_te": {"block": "cutoff"},
    "slot": {"block": "screen"},
    "lead": {"block": "lead", "target": "force"},
}

_PROTECT_LINE = {
    "playside_te": {"block": "protect"},
    "playside_t": {"block": "protect"},
    "playside_g": {"block": "protect"},
    "center": {"block": "protect"},
    "backside_g": {"block": "protect"},
    "backside_t": {"block": "protect"},
    "backside_te": {"block": "protect"},
    "slot": {"block": "screen"},
    "lead": {"block": "protect"},
    "trail": {"block": "protect"},
    "qb": {"block": "protect"},
}

SCHEMES: dict[str, dict[str, dict]] = {
    "Smash": {
        **_INSIDE_LINE,
        "playside_g": {"block": "double", "target": "playside"},
    },
    "Dive": {
        **_INSIDE_LINE,
        "playside_g": {"block": "down"},
        "playside_t": {"block": "double", "target": "playside"},
    },
    "Power": {
        "playside_te": {"block": "release"},
        "playside_t": {"block": "down"},
        "playside_g": {"block": "double", "target": "middle"},
        "center": {"block": "reach"},
        "backside_g": {"block": "cutoff"},
        "backside_t": {"block": "down"},
        "backside_te": {"block": "cutoff"},
        "slot": {"block": "kick"},
        "lead": {"block": "lead"},
    },
    "Toss": dict(_OUTSIDE_LINE),
    "Sweep": dict(_OUTSIDE_LINE),
    "Protect": dict(_PROTECT_LINE),
}


def line_roles(side: int) -> dict[str, str]:
    """Playside / backside line keys for this direction."""
    return dict(LINE_ROLES_RIGHT if side > 0 else LINE_ROLES_LEFT)


def _stacked(form: dict, pos: str) -> bool:
    """True if this back is in the backfield, not split out in the trips."""
    spot = (form.get("alignment") or {}).get(pos)
    if not spot:
        return False
    x, y = spot
    return abs(x) < 2.5 and y <= -2.5


def backfield_roles(form: dict, side: int) -> dict[str, str]:
    """Slot, quarterback, lead and trail for this formation and direction.

    A stacked I (FB + TB behind the quarterback) always leads with the
    fullback. Wishbone (FB + LH + RH) does too. Two halfbacks alone lead with
    the playside one. Trips puts 2, 3 and 4 on the perimeter — they are not
    a backfield, so nobody leads from the scheme.

    The slot is a role, not a key: an SL standing in the backfield is a back,
    and the scheme gives him nothing.
    """
    keys = set(form.get("alignment") or {})
    out: dict[str, str] = {}
    # The `slot` role is the split man's job -- screen the corner, kick the end. A
    # formation may keep the SL key and stand him in the backfield instead (Power I
    # puts him behind a guard), and there he is a back, not a slot: he gets no scheme
    # job and the play writes him, the same way Wishbone's playside halfback is
    # written. Trips keeps the role, because its SL is still outside the tight end.
    if "SL" in keys and not _stacked(form, "SL"):
        out["slot"] = "SL"
    if "QB" in keys:
        out["qb"] = "QB"
    if "FB" in keys and "LH" in keys and "RH" in keys:
        out["lead"] = "FB"
        out["trail"] = "LH" if side > 0 else "RH"
    elif "FB" in keys and "TB" in keys and _stacked(form, "FB") and _stacked(form, "TB"):
        out["lead"] = "FB"
        out["trail"] = "TB"
    elif "LH" in keys and "RH" in keys:
        out["lead"] = "RH" if side > 0 else "LH"
        out["trail"] = "LH" if side > 0 else "RH"
    elif "TB" in keys and _stacked(form, "TB"):
        out["trail"] = "TB"
    return out


def scheme_roles(form: dict, side: int) -> dict[str, str]:
    """Every scheme role this formation can fill, mapped to a position key."""
    return {**line_roles(side), **backfield_roles(form, side)}


def scheme_intents(play: dict, form: dict, side: int) -> dict[str, dict]:
    """The scheme's role → verb map, with the one Sweep adjustment that is the play.

    A tight-end sweep still *is* Sweep — same outside line, same lead at the
    force man — but the backside end is the ball carrier, so he is not there
    to cut off. The backside tackle is the new edge and takes that cutoff.
    """
    name = play.get("scheme")
    if name not in SCHEMES:
        return {}
    intents = {role: copy.deepcopy(spec) for role, spec in SCHEMES[name].items()}
    roles = scheme_roles(form, side)
    if "slot" not in roles:
        intents.pop("slot", None)
        # Power's kick-out is the slot. Nobody there: the playside end kicks
        # the end out himself, which is the no-pull rule without a split man.
        if name == "Power":
            intents["playside_te"] = {"block": "base", "drive": "out"}
    if name == "Sweep":
        if play.get("ball_carrier") == roles.get("backside_te"):
            intents["backside_t"] = {"block": "cutoff"}
    return intents


def intent_core(spec: dict) -> tuple:
    """The verb and its options, ignoring notes and paths."""
    return (spec.get("block"), spec.get("target"), spec.get("drive"))


def expected_scheme(play: dict) -> str | None:
    """The scheme this play's call requires, or None if the call does not name one.

    Numbered runs take the hole word (Sweep when the quarterback or slot is
    coming across at 8/9). A dropback is Protect. A tight-end sweep is Sweep.
    Play-action takes the run it fakes — the caller checks that, because the
    run lives in another file.
    """
    if play.get("type") == "pass" and not play.get("fakes"):
        return "Protect"
    call = play.get("call") or ""
    m = CALL_DIGITS.search(call)
    if m:
        words = scheme_words(int(m.group(2)), m.group(1), play.get("_formation"))
        if words:
            return words[0]
    if play.get("word_call") and re.search(r"\bSweep\b", call):
        return "Sweep"
    if play.get("word_call") and play.get("type") == "pass":
        return "Protect"
    return None


def scheme_conflicts(play: dict, form: dict, side: int) -> list[str]:
    """Written blocks that disagree with the named scheme.

    A leftover back the scheme does not name is fine — that is how a tight-end
    sweep puts two halfbacks on the edge. Restating the scheme is fine too (the
    fill just ignores the copy). Changing the playside end from `release` to
    `cutoff` on a Power is not: that is a different family.
    """
    name = play.get("scheme")
    if name not in SCHEMES:
        return []
    written = play.get("_written") or play.get("assignments") or {}
    roles = scheme_roles(form, side)
    pid = play.get("id", "<no id>")
    msgs = []
    for role, intent in scheme_intents(play, form, side).items():
        pos = roles.get(role)
        if not pos:
            continue
        spec = written.get(pos) or {}
        if "block" not in spec:
            continue
        if intent_core(spec) != intent_core(intent):
            msgs.append(
                f"{pid}: {pos} blocks '{spec.get('block')}' but scheme {name} "
                f"gives {role} '{intent.get('block')}' — the line, the slot and "
                "the lead come from the scheme; leftover backs stay on the play"
            )
    return msgs


def fill_assignments(play: dict, form: dict, side: int) -> dict:
    """Scheme verbs plus whatever the play wrote (paths, leftover backs, notes).

    A position the play already gave a path — the ball carrier, a fake, a
    route — is left alone. A note with no verb is merged onto the scheme
    intent, which is how Toss keeps "step at the dive first" on the lead
    without restating `lead: force`. Everything else the scheme names is
    filled. Positions the scheme does not name stay exactly as written.
    """
    written = play.get("assignments") or {}
    name = play.get("scheme")
    if name not in SCHEMES:
        return {pos: dict(spec) for pos, spec in written.items()}
    roles = scheme_roles(form, side)
    out: dict[str, dict] = {}
    for role, intent in scheme_intents(play, form, side).items():
        pos = roles.get(role)
        if not pos:
            continue
        spec = written.get(pos)
        if spec is None:
            out[pos] = copy.deepcopy(intent)
            continue
        if "block" not in spec and spec.get("rule"):
            out[pos] = dict(spec)
            continue
        if "block" not in spec:
            merged = copy.deepcopy(intent)
            merged.update(spec)
            out[pos] = merged
            continue
        out[pos] = dict(spec)
    for pos, spec in written.items():
        if pos not in out:
            out[pos] = dict(spec)
    # A dropback with no slot still has two halfbacks (or a fullback) who were
    # not in the huddle as the receiver — they pass block.
    if name == "Protect":
        for pos in form.get("alignment") or {}:
            if pos not in out:
                out[pos] = {"block": "protect"}
    # Card order, so the diagram paints the line left-to-right the way the
    # JSON used to, instead of scheme-role order (playside first).
    ordered = {pos: out[pos] for pos in CARD_ORDER if pos in out}
    ordered.update((pos, spec) for pos, spec in out.items() if pos not in ordered)
    return ordered


# Our line, from the middle out. Used to find a blocker's neighbour.
LINE = ("LTE", "LT", "LG", "C", "RG", "RT", "RTE")

# The order blocks are resolved in, which decides who gets first refusal on a defender
# two blockers could both be sent at. Linemen, then the receiver, then the backs: the
# man already standing next to the corner claims him, and the back coming out of the
# backfield takes the next one in.
CARD_ORDER = ("LTE", "LT", "LG", "C", "RG", "RT", "RTE", "TE",
              "X", "LW", "RW", "WB", "W", "SL", "QB", "BB", "FB", "TB", "HB", "LH", "RH")

# How close a down lineman has to be to count as head up on a blocker, and how far out
# he can be and still count as shading one of his shoulders. Beyond that he is somebody
# else's man and this blocker is uncovered.
#
# These two numbers decide what every card in the book says, so they are set against
# the fronts rather than guessed. Our splits are 1.4 yards. In the 5-3 the defensive
# tackle stands 0.4 outside the guard and 0.4 inside our tackle: that has to read as a
# shade on our tackle's inside shoulder and as nothing at all to the guard, which puts
# the cut somewhere between 0.4 and 1.0. In the 4-4 the tackle is dead on the guard's
# nose (0.0) and a yard off our tackle, which has to read as head up and as uncovered.
HEAD_UP = 0.3
SHOULDER = 0.9


# --------------------------------------------------------------- naming a defender --
#
# Every sentence has to name the man being blocked in words an eight-year-old already
# uses. The defence's own position keys (NT, W, M, S, R) are for the defensive book;
# nobody yells "block the W".

DL_NOUNS = {"NT": "nose", "LT": "tackle", "RT": "tackle",
            "LE": "end", "RE": "end", "LG": "guard", "RG": "guard"}


def noun(front: dict, label: str) -> str:
    """What to call this defender out loud."""
    role = front["roles"].get(label)
    if role == "DL":
        return DL_NOUNS.get(label, "lineman")
    if role == "LB":
        return "middle linebacker" if label == "M" else "linebacker"
    return "safety" if label.endswith("S") and label != "S" else "corner"


def named(front: dict, label: str) -> str:
    """This defender by name, side included, for a block the coach assigned to him.

    `noun` is vague on purpose: a rule has to read right in every front, so it cannot
    say which end. A named block belongs to one front, so it can — "the left end", "the
    right inside linebacker" — using the front's own names where it has them.
    """
    names = front.get("position_names") or {}
    if label in names:
        return names[label].lower()
    if label == "FS":
        return "free safety"
    side = {"L": "left", "R": "right"}.get(label[0]) if len(label) > 1 else None
    base = noun(front, label)
    return f"{side} {base}" if side else base


# ------------------------------------------------------------ reading a front --


LB_NOUNS = {"middle": "middle linebacker", "playside": "playside linebacker",
            "backside": "backside linebacker", "outside": "outside linebacker"}


def lb_noun(which: str) -> str:
    """Name a linebacker by the job he is doing, never by his position key.

    Which body it is changes with the front; which job it is does not. "Take the
    playside linebacker" is the same instruction in all three fronts and it mirrors
    cleanly onto the left-handed version of the play, which "take the S" does not.
    """
    return LB_NOUNS.get(which, "linebacker")


def spots(front: dict, role: str) -> list[tuple[str, float, float]]:
    """Every defender in one role, as (label, x, y), left to right."""
    out = [(label, *front["alignment"][label])
           for label, r in front["roles"].items() if r == role]
    return sorted(out, key=lambda s: s[1])


def covering(front: dict, x: float):
    """The down lineman on this blocker, and where he is relative to him.

    Returns (label, x, y, shade) where shade is "over", "inside", "outside", or
    (None, ..., "free") when nobody is within a shoulder of him. Shade is named from
    the blocker's point of view — inside means toward the centre — because that is how
    the assignment has to read.
    """
    best = None
    for label, dx, dy in spots(front, "DL"):
        gap = dx - x
        if abs(gap) > SHOULDER:
            continue
        if best is None or abs(gap) < abs(best[1] - x):
            best = (label, dx, dy)
    if best is None:
        return (None, x, 0.8, "free")
    label, dx, dy = best
    if abs(dx - x) <= HEAD_UP:
        return (label, dx, dy, "over")
    # Inside is toward the middle of our own formation, which is x = 0.
    inside = (abs(dx) < abs(x)) if x else False
    return (label, dx, dy, "inside" if inside else "outside")


def first_inside(front: dict, x: float, play_side: int = 1):
    """The first down lineman on or inside this blocker — the man `down` blocks.

    "On or inside" and not "nearest inside": a lineman head up on the blocker is the
    down block, and so is one shading his inside shoulder. Only when neither exists
    does the search walk further in, which is what sends an uncovered guard onto the
    nose.

    **The centre has no inside.** He stands on the ball, so "toward the middle" names
    no direction at all, and deriving one from the sign of his x — which is zero —
    sent him left on every play in the book. He blocks *back*, away from the hole, so
    his direction is the backside. Getting this wrong stacked our tackle, guard and
    centre on the same defensive tackle in the 4-4 and left the play side unblocked.
    """
    inward = -play_side if abs(x) < 0.2 else (-1 if x > 0 else 1)
    # How far inward each lineman is from this blocker. Negative means he is outside.
    reach = [((dx - x) * inward, label, dx, dy)
             for label, dx, dy in spots(front, "DL")]
    candidates = [r for r in reach if r[0] >= -HEAD_UP]
    if not candidates:
        return None
    label, dx, dy = min(candidates)[1:]
    return (label, dx, dy)


def gap_defender(front: dict, x: float, side: int):
    """The first down lineman in or beyond the gap to one side of this blocker.

    This is the man a reach block has to get his head across: not the man over the
    blocker but the one who owns the gap he is trying to seal.
    """
    candidates = [(label, dx, dy) for label, dx, dy in spots(front, "DL")
                  if (dx - x) * side > -HEAD_UP]
    if not candidates:
        return None
    return min(candidates, key=lambda s: (s[1] - x) * side)


def edge_defender(front: dict, side: int):
    """The man a kick-out kicks: the outermost down lineman on that side."""
    dl = spots(front, "DL")
    if not dl:
        return None
    return max(dl, key=lambda s: s[1] * side)


def force_defender(front: dict, side: int, taken=()):
    """The first defender outside our tight end who is not a down lineman.

    On a toss or a sweep this is the man the lead blocker has to find, and it is a
    different body in every front — an outside linebacker in the 4-4, a corner in the
    5-3. Naming him by job instead of by position is the only way one rule covers all
    three.
    """
    end = edge_defender(front, side)
    limit = end[1] if end else 0.0
    candidates = [(label, x, y) for label, x, y in
                  spots(front, "LB") + spots(front, "DB")
                  if (x - limit) * side > -0.5 and y < 6.0]
    if not candidates:
        return None
    ranked = sorted(candidates, key=lambda s: ((s[1] - limit) * side, s[2]))
    for man in ranked:
        if man[0] not in taken:
            return man
    return ranked[0]


def linebacker(front: dict, side: int, which: str = "playside", taken=()):
    """A linebacker by the job he is doing, not by his name.

    `which` is "playside", "backside", "middle" or "outside". Each builds a RANKED list
    and takes the first man nobody else on this play has been sent to — which is how a
    coach assigns them, and the only way two blockers stop arriving on one body. Only
    the 5-3 has a linebacker standing on the ball, so in the other two fronts "middle"
    and "playside" name the same man and something has to break the tie.

    **The force defender is not on the inside lists.** He is the man outside our end,
    he belongs to whoever is leading out there, and an interior blocker who drifts onto
    him because his own man was taken has abandoned the hole to double-team the edge.
    """
    lbs = spots(front, "LB")
    if not lbs:
        return None
    force = force_defender(front, side)
    inside = [s for s in lbs if not (force and s[0] == force[0])] or lbs

    if which == "outside":
        ranked = sorted(lbs, key=lambda s: -s[1] * side)
    elif which == "middle":
        # Nearest the ball; toward the play when two are equally close, because the
        # one on the side the ball is going is the one who makes the tackle.
        ranked = sorted(inside, key=lambda s: (abs(s[1]), -s[1] * side, s[2]))
    elif which == "backside":
        # The innermost man on the backside — the one who actually chases the play
        # from behind. The mirror of the playside rule, for the same reason.
        away = [s for s in inside if s[1] * side < 0.5] or inside
        ranked = sorted(away, key=lambda s: (abs(s[1]), s[2]))
    else:
        # Playside: the man who fills the hole. Ranked outward from a point just to the
        # playside of the ball, so a second blocker asking for the same job gets the
        # next linebacker in, never the force man out on the edge.
        ranked = sorted(inside, key=lambda s: (abs(s[1] - 2.0 * side), s[2]))

    for lb in ranked:
        if lb[0] not in taken:
            return lb
    return ranked[0]


# How far a receiver can realistically chase somebody down and still be blocking him.
# Beyond this he is not stalking a man, he is jogging at one.
MAX_STALK = 6.0


def perimeter_defender(front: dict, x: float, side: int, taken=()):
    """The man a receiver has to get in front of out on the perimeter.

    A defensive back over him if there is one within reach — that is the corner, and
    stalking him is the whole job. But **the 5-4-2 has no corners**: it trades them for
    a fourth linebacker and plays two safeties eight yards deep. Picking "the nearest
    defensive back" there sent every slot in the book on a nine-yard run diagonally
    INFIELD at a safety, away from the sideline he is supposed to be walling off, while
    the outside linebacker standing four yards from him — the man who actually makes
    that tackle — went unblocked.

    So: the nearest defensive back if one is close enough to block, otherwise the
    outermost linebacker on his side. A front with no corners still has somebody out
    there, and it is him.

    A blocker standing on the middle has no side of his own, so he takes the play's —
    the same rule the centre's down block follows. Without it a tailback aligned at
    x = 0 was sent at the LEFT safety on a play going right.
    """
    lean = side if abs(x) < 1.0 else (1 if x > 0 else -1)
    here = (x, -1.2)

    def reach(s):
        return ((s[1] - here[0]) ** 2 + (s[2] - here[1]) ** 2) ** 0.5

    dbs = [s for s in spots(front, "DB") if s[1] * lean > 1.0]
    free_dbs = [s for s in dbs if s[0] not in taken] or dbs
    if free_dbs:
        best = min(free_dbs, key=reach)
        if reach(best) <= MAX_STALK:
            return best
    lbs = [s for s in spots(front, "LB") if s[1] * lean > 1.0]
    if lbs:
        free = [s for s in lbs if s[0] not in taken] or lbs
        return max(free, key=lambda s: s[1] * lean)
    return min(dbs, key=reach) if dbs else None


# --------------------------------------------------------------- the sentences --
#
# Two halves, always in this order: where he is lined up, then what to do about it.
# The first half is the part that changes with the front and the part a kid cannot see
# from the huddle, so it goes first.

# Clipped on purpose. This is the first thing on every line and it is the half the
# player already half-knows, so it earns three words, not eight — "Nose head up on you",
# not "The nose is head up on you." Across the book that is the difference between a
# card you scan and a card you read.
SHADE_CLAUSE = {
    "over": "{Noun} head up on you.",
    "inside": "{Noun} on your inside shoulder.",
    "outside": "{Noun} on your outside shoulder.",
    "free": "Nobody on you.",
}


# Anybody starting further back than this is not on the line of scrimmage, so nobody
# is lined up over him and the whole question does not arise.
ON_THE_LINE = -1.2


def shade_clause(front, spot) -> tuple[str, tuple | None]:
    """Where the man on this blocker is lined up — for blockers who have one.

    A back is not covered by anybody. Telling a halfback four yards deep that "the
    tackle is head up on you" describes a defender he is nowhere near, and telling a
    slot split eight yards wide that "nobody is over you" is true and useless. Both
    got the clause because the function only ever looked at x.
    """
    x, y = spot[0], spot[1]
    if y <= ON_THE_LINE:
        return "", None
    label, dx, dy, shade = covering(front, x)
    if shade == "free":
        return SHADE_CLAUSE["free"], None
    n = noun(front, label)
    return SHADE_CLAUSE[shade].format(Noun=n[0].upper() + n[1:]), (label, dx, dy)


def side_word(side: int) -> str:
    return "right" if side > 0 else "left"


# ------------------------------------------------------------------- the verbs --
#
# Each verb returns (sentence, path). The path is relative to the blocker's own spot,
# the same as a hand-authored one, and it is built from where the resolved defender is
# actually standing — which is the whole reason the picture stays right when the front
# changes.


# How far short of the man a block stops, in yards: the bar lands on the edge of his X
# rather than across it, so the defender stays readable under the line.
ON_MAN = 0.45


def to(spot, target):
    """A one-point path from a blocker straight onto a defender.

    Onto the man, not a shoulder of him. The card's job is who blocks whom; which side
    to take is in the words of the rule, and drawing it as a finish a yard off to one
    side made the matchup harder to read, not easier.
    """
    dx, dy = target[1] - spot[0], target[2] - spot[1]
    d = (dx * dx + dy * dy) ** 0.5
    k = max(0.0, d - ON_MAN) / d if d else 0.0
    return [[round(dx * k, 2), round(dy * k, 2)]]


def v_base(front, spot, side, intent, taken=()):
    """Drive the man over you. `drive` says which way he goes."""
    clause, man = shade_clause(front, spot)
    if man is None:                      # uncovered: there is nobody to base block
        return v_down(front, spot, side, intent, taken)
    drive = intent.get("drive", "back")
    if drive == "out":
        text = f"{clause} Drive him to the sideline. The ball goes inside you."
    elif drive == "in":
        text = f"{clause} Turn him inside. The ball goes around behind you."
    else:
        text = f"{clause} Hands inside, pads under his, drive him back."
    return text, to(spot, man)


def v_release(front, spot, side, intent, taken=()):
    """Go past the edge defender — somebody else is kicking him — and take a linebacker.

    The end man on the line of scrimmage on a kick-out play. Whether the man he steps
    past is head up on him (the 5-3 and the 5-4-2) or shaded into the gap inside him
    (the 4-4) changes nothing about the job, but it changes which shoulder he leaves
    off, so the sentence says which.
    """
    edge = edge_defender(front, side)
    # He is the widest blocker inside the kick-out, so he takes the widest linebacker
    # on that side — which is the whole adjustment between a three-linebacker front
    # and a four-linebacker one. Against the 5-3 that is the playside linebacker and
    # everything is blocked; against the 4-4 and the 5-4-2 there is an outside
    # linebacker beyond him, and if the end releases inside to the same man the guard
    # is climbing to, the force defender runs free into the hole.
    which = intent.get("target", "outside").replace("-lb", "")
    lb = linebacker(front, side, which, taken)
    if lb is None:
        return v_base(front, spot, side, dict(intent, drive="in"), taken)
    who = noun(front, edge[0]) if edge else "man on the edge"
    text = f"Leave the {who} — he is kicked out. Go take the {lb_noun(which)}."
    return text, to(spot, lb)


def v_down(front, spot, side, intent, taken=()):
    """Block down on the first defender on or inside you."""
    man = first_inside(front, spot[0], side)
    if man is None:
        return v_cutoff(front, spot, side, intent, taken)
    n = noun(front, man[0])
    where = ("head up" if abs(man[1] - spot[0]) <= HEAD_UP else "inside shoulder")
    text = (f"Block down on the {n}, {where}. "
            "Head across him — nobody crosses your face.")
    return text, to(spot, man)


def v_reach(front, spot, side, intent, taken=()):
    """Get your head across the playside shoulder of the man in the playside gap."""
    man = gap_defender(front, spot[0], side)
    # Nobody within a shoulder of the playside gap is nobody this blocker can reach —
    # the man out there belongs to the next blocker over. An uncovered lineman who is
    # told to reach thin air is a lineman blocking nobody, so he climbs instead.
    if man is None or abs(man[1] - spot[0]) > SHOULDER:
        return v_climb(front, spot, side, dict(intent, target="playside"), taken)
    n = noun(front, man[0])
    text = f"Reach the {n} to your {side_word(side)}. Head across his playside shoulder."
    return text, to(spot, man)


def v_double(front, spot, side, intent, taken=()):
    """Two blockers on one man, and whoever is free comes off onto the linebacker.

    This is the uncovered lineman's rule, and it is the one intent whose answer flips
    hardest between fronts. A guard is free in the 5-3, so he doubles the nose and
    climbs. The same guard has a tackle head up on him in the 4-4 — and a man on your
    nose is your man, there is nobody to go help. "Help inside if you are free" is one
    instruction a kid can hold; it just resolves to two different blocks.
    """
    _, _, _, shade = covering(front, spot[0])
    if shade in ("over", "outside"):
        return v_base(front, spot, side, dict(intent, drive="back"), taken)
    man = first_inside(front, spot[0], side)
    if man is None:
        return v_climb(front, spot, side, intent, taken)
    which = intent.get("target", "middle").replace("-lb", "")
    lb = linebacker(front, side, which, taken)
    n = noun(front, man[0])
    if lb is None:
        return (f"Help on the {n} and drive him off the spot. The hole is off his "
                "back."), to(spot, man)
    clause, _ = shade_clause(front, spot)
    text = " ".join(x for x in (clause, f"Help on the {n},",
                                f"then take the {lb_noun(which)}.") if x)
    return text, to(spot, man) + to(spot, lb)


def v_climb(front, spot, side, intent, taken=()):
    """Go past the line and get on a linebacker."""
    which = intent.get("target", "playside").replace("-lb", "")
    lb = linebacker(front, side, which, taken)
    if lb is None:
        return v_cutoff(front, spot, side, intent, taken)
    clause, man = shade_clause(front, spot)
    # A back has no shade clause at all, so joining blindly left a leading space on
    # the card — visible on the site as an indented assignment.
    lead = clause if man is None else f"{clause} Step past him."
    text = " ".join(x for x in (lead, f"Climb to the {lb_noun(which)}.",
                                "Head across him.") if x)
    return text, to(spot, lb)


def v_cutoff(front, spot, side, intent, taken=()):
    """The backside. Nobody chases this down from behind."""
    clause, man = shade_clause(front, spot)
    if man is not None:
        text = f"{clause} Cut him off — get between him and the ball."
        return text, to(spot, man)
    # Aim at the man who actually chases it down. The first version drew a fixed
    # 1.8-yard stub from wherever the blocker stood, which is a reasonable line for a
    # guard and a meaningless one for a slot seven yards wide — he was drawn taking
    # two steps infield and stopping.
    lb = linebacker(front, side, "backside", taken)
    clause, _ = shade_clause(front, spot)
    text = " ".join(x for x in (clause, "Cut off the backside.",
                                "Never quit on the play.") if x)
    if lb is None:
        return text, [[round(0.9 * side, 2), 0.7], [round(1.8 * side, 2), 1.6]], None
    return text, [[round(0.45 * (lb[1] - spot[0]), 2), round(0.2 - spot[1], 2)]] \
        + to(spot, lb), lb


def v_hinge(front, spot, side, intent, taken=()):
    """Protect the side the quarterback ends up on.

    The direction is the play's, not the blocker's. Taking it from the sign of the
    blocker's own x meant anybody standing on the middle — a centre, a tailback
    trailing a bootleg — hinged right on a play going left, which is the one direction
    that does not protect the man the verb exists to protect.
    """
    text = "Hinge back and protect the outside. Nobody gets past you."
    return text, [[round(0.5 * side, 2), -0.4], [round(1.4 * side, 2), -1.4]]


def v_wedge(front, spot, side, intent, taken=()):
    """Shoulder to shoulder and push. Nobody picks a man."""
    text = ("Shoulder to shoulder with the man beside you, and push. Low pads — never "
            "look for a man.")
    inside = -1 if spot[0] > 0 else (1 if spot[0] < 0 else 0)
    # Finish at the line, not a fixed step from wherever he started — a fullback three
    # yards deep was being drawn wedging to a yard behind the line and stopping there.
    return text, [[round(0.45 * inside, 2), round(0.7 - spot[1], 2)]]


def v_kick(front, spot, side, intent, taken=()):
    """Kick the edge defender out. The ball runs inside the block."""
    man = edge_defender(front, side)
    if man is None:
        return v_lead(front, spot, side, intent, taken)
    n = noun(front, man[0])
    text = (f"Kick the {n} out. Aim at his outside hip. Never let him come "
            "underneath you.")
    return text, to(spot, man)


def through_hole(spot, target, side):
    """A back's blocking path: get to the line of scrimmage first, then to the man.

    A lead blocker four yards deep who is drawn as one straight line to a linebacker
    is drawn running through his own centre. The elbow at the line is where he
    actually goes, and it is what makes the picture copyable.
    """
    elbow = [round(0.55 * (target[1] - spot[0]) + 0.3 * side, 2),
             round(0.6 - spot[1], 2)]
    return [elbow] + to(spot, target)


def v_lead(front, spot, side, intent, taken=()):
    """Lead through the hole and block whoever shows in it.

    Two different jobs wear this verb, and the difference is whether there is a man to
    name. `target: force` names one — the defender outside our end is a specific body
    and a different one in every front, which is exactly what a sweep's lead blocker
    needs told. Everything else aims at the HOLE, because "the first defender who
    shows" is not a man anybody can identify before the snap, and drawing a line to one
    of them is a lie: it sends the blocker past the two who actually showed.

    That is not a drawing nicety. Three blockers on Power were being drawn converging
    on the same linebacker while two more ran free, purely because three different
    verbs each resolved "playside linebacker" to the same body.
    """
    if intent.get("target") == "force":
        man = force_defender(front, side, taken)
        # Is the ball going outside our own end? On a toss or a sweep it is, and then
        # two blockers on the edge is not a waste — it is the play. The lead back's
        # job is to be in front of the carrier out there, and turning him up inside
        # leaves the man the ball is running at unblocked while he blocks somebody the
        # carrier has already passed. On an inside run the opposite holds, which is
        # what the fallback below is for.
        edge = edge_defender(front, side)
        hole = intent.get("_hole")
        wide = (hole is not None and edge is not None
                and abs(hole) > abs(edge[1]))
        if man is not None and man[0] in taken and not wide:
            # Somebody is already on him and there is nobody further out. Turn up
            # inside rather than putting two blockers on one defender.
            inside = linebacker(front, side, "playside", taken)
            if inside is not None and inside[0] not in taken:
                text = (f"Lead outside our end, then turn up inside — the {lb_noun('playside')} "
                        "is the man who shows. Head across him.")
                return text, through_hole(spot, inside, side), inside
        if man is not None:
            text = (f"Lead outside our end. Block the first man out there — here it "
                    f"is the {noun(front, man[0])}.")
            return text, through_hole(spot, man, side), man
    aim = intent.get("_hole")
    if aim is None:
        aim = 1.6 * side
    text = "Lead through the hole. Block the first man who shows in it."
    return text, [[round(0.6 * (aim - spot[0]) + 0.2 * side, 2), round(0.4 - spot[1], 2)],
                  [round(aim - spot[0], 2), round(2.4 - spot[1], 2)]], None


def v_screen(front, spot, side, intent, taken=()):
    """Get in front of the man on the perimeter and stay there."""
    man = perimeter_defender(front, spot[0], side, taken)
    if man is None:
        return ("Run at the first man outside and screen him off. Stay in his way."), [[round(1.2 * side, 2), 3.0]]
    n = (lb_noun("outside") if front["roles"].get(man[0]) == "LB"
         else noun(front, man[0]))
    text = f"Run at the {n} and screen him off. Stay in his way."
    return text, to(spot, man)


def v_man(front, spot, side, intent, taken=()):
    """Block the man the coach names, in the one front the play names him for.

    Every other verb works a block out from where the defence stands. Sometimes the
    coach has already decided who blocks whom against a front, and then the card should
    say exactly that. `man` is the defender's label in that front. `help` puts a first
    stop on another man, for a double that comes off onto `man`. `via` is waypoints to
    get round somebody first, relative to the blocker like any path, and `how` says
    what they are in words.
    """
    label = intent["man"]
    x, y = front["alignment"][label]
    n = named(front, label)
    path = [list(p) for p in intent.get("via", [])]
    if intent.get("help"):
        helped = intent["help"]
        hx, hy = front["alignment"][helped]
        path += to(spot, (helped, hx, hy))
        text = f"Help on the {named(front, helped)}, then block the {n}."
    elif intent.get("with"):
        # A double team: `with` is the teammate on the same man, in words.
        lead = f"{intent['how']}, then double" if intent.get("how") else "Double"
        text = f"{lead} team the {n} with the {intent['with']}."
    elif intent.get("how"):
        text = f"{intent['how']}, then block the {n}."
    else:
        text = f"Block the {n}."
    return text, path + to(spot, (label, x, y))


def v_protect(front, spot, side, intent, taken=()):
    """Pass block. Nobody picks a man before the snap: stay between whoever comes and
    the quarterback.

    A lineman steps back and sets. A back beside a shotgun quarterback steps up and out
    to his own side, to meet the rush before it reaches the quarterback.
    """
    if spot[1] < -2.0:
        out = 1 if spot[0] > 0 else (-1 if spot[0] < 0 else 0)
        return ("Step up and out, hands up. Pick up anybody coming at the quarterback.",
                [[round(0.6 * out, 2), 0.9]])
    return ("Pass block: step back, hands up, and stay between your man and the "
            "quarterback."), [[0.0, -0.7]]


def v_decoy(front, spot, side, intent, taken=()):
    """Sell something that is not happening. The path is hand-drawn because the lie is
    the point — it copies another play's path, and that path is not derivable from
    where the defence is standing."""
    text = intent.get("sell") or "Run your path at full speed and block whatever shows."
    return text, None


VERBS = {
    "base": v_base, "down": v_down, "reach": v_reach, "double": v_double,
    "climb": v_climb, "cutoff": v_cutoff, "hinge": v_hinge, "wedge": v_wedge,
    "kick": v_kick, "lead": v_lead, "screen": v_screen,
    "release": v_release, "decoy": v_decoy, "man": v_man, "protect": v_protect,
}


# ---------------------------------------------------------------- resolving it --


def resolve(pos: str, intent: dict, alignment: dict, front: dict, side: int,
            hole: float | None = None, taken=()) -> dict:
    """One blocking intent against one front -> the assignment a card prints.

    `side` is +1 if the play goes right, -1 left, taken from the call. It is what turns
    "playside" into an actual man. `hole` is where the ball crosses the line, and it is
    what the verbs that block *space* rather than a man aim at.

    The resolved spec carries `aims`: "man" if a particular defender was resolved and
    the line is drawn to him, "space" if the blocker was sent to a spot. The tests use
    it — a block that names a man has to reach one, and a block on a spot must not be
    counted as claiming the defender it happens to finish nearest.
    """
    verb = intent["block"]
    if verb not in VERBS:
        raise SystemExit(f"{pos}: unknown blocking verb '{verb}'")
    spot = alignment[pos]
    if hole is not None:
        intent = dict(intent, _hole=hole)
    result = VERBS[verb](front, spot, side, intent, taken)
    text, path = result[0], result[1]
    aims = "space" if (len(result) > 2 and result[2] is None) else "man"
    if verb in SPACE_VERBS:
        aims = "space"
    if intent.get("note"):
        text = f"{text} {intent['note']}"
    return {
        "rule": text,
        "type": "block",
        "aims": aims,
        "path": intent["path"] if path is None else path,
        # A block that goes round somebody first is drawn as one rounded bubble through
        # its waypoints, not as straight legs with a corner at each.
        "curve": bool(intent.get("via")),
        # Which linebacker this blocker took, so the next one does not take him too.
        "claimed": claimed_lb(front, alignment[pos], path) if aims == "man" else None,
    }


# How close a block has to finish to a defender to count as having taken him. Wider
# than a linebacker check because a stalk block deliberately stands off its man.
CLAIM_RADIUS = 1.4


def claimed_lb(front: dict, spot, path):
    """The defender this block finishes on, if it finishes on one.

    Any defender, not just a linebacker. The collision worth catching on this book's
    edge plays is a slot and a lead back both sent at one corner.
    """
    if not path:
        return None
    ex, ey = spot[0] + path[-1][0], spot[1] + path[-1][1]
    near = [(((ex - x) ** 2 + (ey - y) ** 2) ** 0.5, label)
            for label, x, y in (spots(front, "DL") + spots(front, "LB")
                                + spots(front, "DB"))]
    d, label = min(near)
    return label if d <= CLAIM_RADIUS else None


# Verbs that block a gap, a spot or a lie rather than a particular defender.
SPACE_VERBS = {"cutoff", "hinge", "wedge", "decoy", "protect"}


def resolve_play(play: dict, alignment: dict, front: dict, side: int,
                 hole: float | None = None) -> dict:
    """Every assignment on a play, with the blocking ones resolved against `front`.

    An assignment that carries a `block` verb is computed. One that does not — a ball
    carrier, a fake, a route, a lead back whose path is the play itself — is passed
    through untouched, because none of those depend on where the defence lines up.
    """
    out, taken = {}, set()
    # In reading order, so the answer does not depend on dict ordering: the line from
    # the middle out, then the backs. A lineman is closer to the second level than a
    # back is, so he gets first refusal on the linebacker he is climbing to.
    order = [p for p in CARD_ORDER if p in play["assignments"]]
    order += [p for p in play["assignments"] if p not in order]
    for pos in order:
        spec = play["assignments"][pos]
        if "block" not in spec:
            out[pos] = spec
            continue
        r = resolve(pos, spec, alignment, front, side, hole, taken)
        if r.pop("claimed", None):
            taken.add(claimed_lb(front, alignment[pos], r["path"]))
        out[pos] = r
    return {p: out[p] for p in play["assignments"]}
