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
    "Z":  { "block": "kick" }
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

# The three fronts every offensive play is drawn and blocked against. An 8U team lines
# up in one of these against us; the toggle on a play page is these in this order.
# The 6-3 goal line and the 6-2-3 prevent are our own calls, not looks we expect to
# face on a normal down, so they are not in the toggle.
SCOUT_FRONTS = ("4-4", "5-3", "5-4-2")

# The front a card is drawn against when nothing says otherwise, and the one the
# printed book uses. The 5-3 is what an 8U team lines up in against us once the 6-2 is
# off the table, so it is the picture worth putting in a coach's pocket.
DEFAULT_FRONT = "5-3"

# Our line, from the middle out. Used to find a blocker's neighbour.
LINE = ("LTE", "LT", "LG", "C", "RG", "RT", "RTE")

# The order blocks are resolved in, which decides who gets first refusal on a defender
# two blockers could both be sent at. Linemen, then the receiver, then the backs: the
# man already standing next to the corner claims him, and the back coming out of the
# backfield takes the next one in.
CARD_ORDER = ("LTE", "LT", "LG", "C", "RG", "RT", "RTE", "TE",
              "X", "LW", "RW", "WB", "W", "Z", "QB", "BB", "FB", "TB", "HB", "LH", "RH")

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
    defensive back" there sent every flanker in the book on a nine-yard run diagonally
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
    flanker split eight yards wide that "nobody is over you" is true and useless. Both
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


def to(spot, target, bias_x=0.0, bias_y=0.0):
    """A one-point path from a blocker to a defender, with a shoulder bias."""
    return [[round(target[1] - spot[0] + bias_x, 2),
             round(target[2] - spot[1] + bias_y, 2)]]


def v_base(front, spot, side, intent, taken=()):
    """Drive the man over you. `drive` says which way he goes."""
    clause, man = shade_clause(front, spot)
    if man is None:                      # uncovered: there is nobody to base block
        return v_down(front, spot, side, intent, taken)
    drive = intent.get("drive", "back")
    out_side = 1 if spot[0] >= 0 else -1
    if drive == "out":
        text = f"{clause} Drive him to the sideline. The ball goes inside you."
        bias = 0.7 * out_side
    elif drive == "in":
        text = f"{clause} Turn him inside. The ball goes around behind you."
        bias = -0.7 * out_side
    else:
        text = f"{clause} Hands inside, pads under his, drive him back."
        bias = 0.0
    return text, to(spot, man, bias_x=bias, bias_y=0.35)


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
    return text, to(spot, lb, bias_x=0.2 * side, bias_y=-0.3)


def v_down(front, spot, side, intent, taken=()):
    """Block down on the first defender on or inside you."""
    man = first_inside(front, spot[0], side)
    if man is None:
        return v_cutoff(front, spot, side, intent, taken)
    n = noun(front, man[0])
    where = ("head up" if abs(man[1] - spot[0]) <= HEAD_UP else "inside shoulder")
    text = (f"Block down on the {n}, {where}. "
            "Head across him — nobody crosses your face.")
    inside = -1 if man[1] > spot[0] else 1
    return text, to(spot, man, bias_x=0.25 * inside, bias_y=0.3)


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
    return text, to(spot, man, bias_x=0.45 * side, bias_y=0.3)


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
                "back."), to(spot, man, bias_y=0.4)
    clause, _ = shade_clause(front, spot)
    text = " ".join(x for x in (clause, f"Help on the {n},",
                                f"then take the {lb_noun(which)}.") if x)
    return text, to(spot, man, bias_y=0.3) + to(spot, lb, bias_y=-0.4)


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
    return text, to(spot, lb, bias_x=0.3 * side, bias_y=-0.3)


def v_cutoff(front, spot, side, intent, taken=()):
    """The backside. Nobody chases this down from behind."""
    clause, man = shade_clause(front, spot)
    if man is not None:
        text = f"{clause} Cut him off — get between him and the ball."
        return text, to(spot, man, bias_x=0.4 * side, bias_y=0.3)
    # Aim at the man who actually chases it down. The first version drew a fixed
    # 1.8-yard stub from wherever the blocker stood, which is a reasonable line for a
    # guard and a meaningless one for a flanker seven yards wide — he was drawn taking
    # two steps infield and stopping.
    lb = linebacker(front, side, "backside", taken)
    clause, _ = shade_clause(front, spot)
    text = " ".join(x for x in (clause, "Cut off the backside.",
                                "Never quit on the play.") if x)
    if lb is None:
        return text, [[round(0.9 * side, 2), 0.7], [round(1.8 * side, 2), 1.6]], None
    return text, [[round(0.45 * (lb[1] - spot[0]), 2), round(0.2 - spot[1], 2)]] \
        + to(spot, lb, bias_x=0.3 * side, bias_y=-0.3), lb


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
    # Finish INSIDE the man at his own depth: a kick-out that finishes outside him
    # draws the blocker running past, and the defender comes underneath.
    return text, to(spot, man, bias_x=-0.8 * side, bias_y=0.0)


def through_hole(spot, target, side, bias_x=0.0, bias_y=0.0):
    """A back's blocking path: get to the line of scrimmage first, then to the man.

    A lead blocker four yards deep who is drawn as one straight line to a linebacker
    is drawn running through his own centre. The elbow at the line is where he
    actually goes, and it is what makes the picture copyable.
    """
    elbow = [round(0.55 * (target[1] - spot[0]) + 0.3 * side, 2),
             round(0.6 - spot[1], 2)]
    return [elbow] + to(spot, target, bias_x=bias_x, bias_y=bias_y)


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
        if man is not None and man[0] in taken:
            # Somebody is already on him and there is nobody further out. Turn up
            # inside rather than putting two blockers on one defender.
            inside = linebacker(front, side, "playside", taken)
            if inside is not None and inside[0] not in taken:
                text = (f"Lead outside our end, then turn up inside — the {lb_noun('playside')} "
                        "is the man who shows. Head across him.")
                return text, through_hole(spot, inside, side, bias_x=0.3 * side,
                                          bias_y=-0.5), inside
        if man is not None:
            text = (f"Lead outside our end. Block the first man out there — here it "
                    f"is the {noun(front, man[0])}.")
            return text, through_hole(spot, man, side, bias_x=0.3 * side, bias_y=-0.5), man
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
    return text, to(spot, man, bias_x=-0.9 * side, bias_y=-0.8)


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
    "release": v_release, "decoy": v_decoy,
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
        # Which linebacker this blocker took, so the next one does not take him too.
        "claimed": claimed_lb(front, alignment[pos], path) if aims == "man" else None,
    }


# How close a block has to finish to a defender to count as having taken him. Wider
# than a linebacker check because a stalk block deliberately stands off its man.
CLAIM_RADIUS = 1.4


def claimed_lb(front: dict, spot, path):
    """The defender this block finishes on, if it finishes on one.

    Any defender, not just a linebacker. The collision worth catching on this book's
    edge plays is a flanker and a lead back both sent at one corner.
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
SPACE_VERBS = {"cutoff", "hinge", "wedge", "decoy"}


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
