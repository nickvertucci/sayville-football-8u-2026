#!/usr/bin/env python3
"""Sayville 8U play-card generator.

Reads the JSON play files under `playbook/<formation>/plays/` and writes:

    playbook/<formation>/cards/<play-id>.svg          full printable card
    playbook/<formation>/cards/<play-id>-field.svg    diagram only, used by the website
    playbook/<formation>/cards/<formation-id>-icon.svg  alignment only, no play — the
                                                       formation icon used on cards
    playbook/<formation>/README.md                    formation index
    PLAYBOOK.md                                       the whole book, in install order

and hands off to site_build.py, which writes the multi-page website (home, call
sheet, a page per formation, a page per play, and the print build).

Usage:
    python generator/render.py            # rebuild everything
    python generator/render.py --check    # validate the JSON only, write nothing

Coordinate system used in the JSON files
----------------------------------------
Field yards. x is positive to the RIGHT, y is positive DOWNFIELD (toward the
defense). The line of scrimmage is y = 0, so the offensive line sits at
y = -0.5 and the fullback at y = -4.0.

A player's "path" is a list of points expressed as offsets from that player's
own alignment spot, so a play can be authored without doing field math:

    "LG": {"rule": "Pull, wrap", "type": "block", "path": [[0.3, -1.0], [5.3, 1.5]]}

means the left guard goes 0.3 right / 1.0 back, then on to 5.3 right / 1.5
downfield of where he lined up.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import blocking  # noqa: E402
import site_build  # noqa: E402
from common import CARD_ORDER, esc, form_label, ordered_positions, slug  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PLAYBOOK_DIR = ROOT / "playbook"
DEFENSE_DIR = ROOT / "defense"

# ---------------------------------------------------------------- geometry --

SCALE = 27.0            # px per yard
X_MIN, X_MAX = -13.0, 13.0
Y_MIN, Y_MAX = -7.0, 12.0

FIELD_W = (X_MAX - X_MIN) * SCALE
FIELD_H = (Y_MAX - Y_MIN) * SCALE

TITLE_H = 58
# Width of one character of the band's bold title, per point of font size, measured off
# a rendered card. Only ever used to decide whether the title still fits beside the call.
NAME_CHAR_W = 0.47
BAND_GAP = 14
PAD = 18
LINE_H = 17

# Which alignment keys are linemen (drawn as squares) vs backs and receivers (circles).
LINEMEN = {"LTE", "LT", "LG", "C", "RG", "RT", "RTE", "TE"}

COLORS = {
    "ink": "#111318",
    "muted": "#5b6472",
    "line": "#c8cdd6",
    "offense": "#14213d",
    "carrier": "#b3001b",
    "defense": "#9aa2ae",
    "los": "#3a4150",
    "card": "#ffffff",
    "band": "#14213d",
    "ghost": "#c2c8d2",
}


def fx(x: float) -> float:
    return (x - X_MIN) * SCALE


def fy(y: float) -> float:
    return (Y_MAX - y) * SCALE


# ------------------------------------------------------------------- model --


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


# The rulebook limits for 8- and 9-year-olds (PAL 9.02). The league's own wording is in
# rulebook/2025-PAL-RULE-BOOK.txt; what it did to this playbook is in RULES.md.
MAX_DOWN_LINEMEN = 6
MIN_LINEBACKERS = 3
MIN_LB_DEPTH = 2.0
MIN_DB_DEPTH = 2.0


def load_defenses() -> dict:
    """Each defense/<id>.json is a defensive front and a page of the defensive book."""
    fronts = {}
    for f in sorted(DEFENSE_DIR.glob("*.json")):
        front = load_json(f)
        fronts[f.stem] = front
    return dict(sorted(fronts.items(), key=lambda kv: (kv[1].get("order", 99), kv[0])))


def base_defense(defenses: dict) -> dict | None:
    """The front we play unless there is a reason not to.

    It is whichever front sorts first, because `order` is the teaching order and the
    base comes first — the same rule the formations use. Naming it here rather than
    hardcoding an id is what let the base move from the 5-3 to the 4-4 without the
    depth chart quietly staying on the old front.
    """
    return next(iter(defenses.values()), None)


def validate_defenses(defenses: dict) -> list[str]:
    """Refuse to publish a front the league would flag.

    Getting this wrong is not a cosmetic bug — an illegal front is a 15-yard
    unsportsmanlike penalty on the head coach, and a second one gets him ejected. So
    the generator checks it rather than trusting whoever authored the JSON.
    """
    errors = []
    for fid, front in defenses.items():
        alignment = front.get("alignment", {})
        roles = front.get("roles", {})
        if len(alignment) != 11:
            errors.append(f"defense {fid}: {len(alignment)} players aligned, must be 11")
        missing = set(alignment) - set(roles)
        if missing:
            errors.append(
                f"defense {fid}: no role (DL/LB/DB) for {', '.join(sorted(missing))}"
            )
        if front.get("assignments") is not None:
            unassigned = set(alignment) - set(front["assignments"])
            if unassigned:
                errors.append(
                    f"defense {fid}: no assignment for {', '.join(sorted(unassigned))}"
                )

        dl = [p for p, r in roles.items() if r == "DL"]
        lb = [p for p, r in roles.items() if r == "LB"]
        db = [p for p, r in roles.items() if r == "DB"]
        if len(dl) > MAX_DOWN_LINEMEN:
            errors.append(
                f"defense {fid}: {len(dl)} down linemen, the league allows at most "
                f"{MAX_DOWN_LINEMEN}"
            )
        exempt = set(front.get("exempt", []))
        if exempt and not front.get("exempt_reason"):
            errors.append(
                f"defense {fid}: claims an exemption without an exempt_reason citing the "
                "rule that grants it"
            )
        if len(lb) < MIN_LINEBACKERS and "MIN_LINEBACKERS" not in exempt:
            errors.append(
                f"defense {fid}: {len(lb)} linebackers, the league requires at least "
                f"{MIN_LINEBACKERS}"
            )
        for pos in lb:
            depth = alignment.get(pos, [0, 0])[1]
            if depth < MIN_LB_DEPTH:
                errors.append(
                    f"defense {fid}: linebacker {pos} is {depth} yards off, the minimum "
                    f"is {MIN_LB_DEPTH}"
                )
        for pos in db:
            depth = alignment.get(pos, [0, 0])[1]
            if depth < MIN_DB_DEPTH:
                errors.append(
                    f"defense {fid}: defensive back {pos} is {depth} yards off, the "
                    f"minimum is {MIN_DB_DEPTH}"
                )
    return errors


_PLAYS_BY_ID: dict[str, dict] = {}


def load_formations() -> list[dict]:
    """Each playbook/<dir>/formation.json is a formation; its plays live alongside."""
    formations = []
    for form_file in sorted(PLAYBOOK_DIR.glob("*/formation.json")):
        form = load_json(form_file)
        form["_dir"] = form_file.parent
        form["_plays"] = resolve_plays(form_file.parent / "plays", form)
        formations.append(form)
    # `order` is the teaching order, not the alphabet — the base formation comes first.
    formations.sort(key=lambda f: (f.get("order", 99), f.get("name", "")))
    return formations


def resolve_plays(plays_dir: Path, form: dict) -> list[dict]:
    raw = {}
    if plays_dir.is_dir():
        raw = {p.stem: load_json(p) for p in sorted(plays_dir.glob("*.json"))}
    plays = list(raw.values())
    for p in plays:
        p["_formation"] = form
        _PLAYS_BY_ID[p["id"]] = p
    plays.sort(key=lambda p: (p.get("order", 99), p.get("name", ""), p.get("id", "")))
    return plays


# --------------------------------------------------------- the calling language --
#
# A call carries two digits: who runs it and where he goes. The point of numbering the
# holes off the linemen rather than off abstract gaps is that a call names the two
# blockers the ball goes between — which is only true if somebody checks it. Nothing
# stops an author from writing "36" on a play drawn up the middle, and a call sheet that
# lies is worse than no call sheet, so the build checks every call against its own
# diagram.
#
# The digits describe the player the FIRST digit names, not the ball carrier. On a pass
# they are the same only by accident: I SL Right 16 Boot is the quarterback at the 6 hole,
# while `ball_carrier` is the slot he throws to.

CALL_DIGITS = re.compile(r"\b(\d)(\d)\b")


def play_side(play: dict) -> int:
    """+1 if the call sends the ball right, -1 left.

    Taken from the call rather than from the `direction` field because the call is the
    thing the build already checks against the diagram. "Playside" in a blocking rule
    and "the hole the call names" therefore cannot disagree.
    """
    m = CALL_DIGITS.search(play.get("call", "") or "")
    if not m:
        return 1 if (play.get("direction") or "right") == "right" else -1
    return 1 if int(m.group(2)) % 2 == 0 else -1


def play_hole(play: dict) -> float:
    """Where the ball crosses the line of scrimmage, in field x.

    Taken from the hole the call names, measured against this play's own alignment, so
    it follows the formation's splits rather than a table of guessed numbers. It is
    what the blockers who are told to block "whoever shows" are aimed at — the hole is
    a place, and the man in it is not knowable before the snap.
    """
    form = play["_formation"]
    alignment = play_alignment(form, play)
    m = CALL_DIGITS.search(play.get("call", "") or "")
    if not m:
        return 1.5 * play_side(play)
    hole = int(m.group(2))
    low, high = hole_bounds(alignment, "R" if hole % 2 == 0 else "L", hole // 2)
    if high == float("inf"):
        high = low + 2.0
    return (low + high) / 2 * (1 if hole % 2 == 0 else -1)


def faked_play(play: dict):
    """The run this play-action pass is pretending to be, if it is one."""
    pid = play.get("fakes")
    if not pid:
        return None
    return _PLAYS_BY_ID.get(pid)


def resolved_assignments(play: dict, front: dict) -> dict:
    """This play's eleven assignments, blocking rules resolved against one front.

    Cached per (play, front) because the card, the diagram, the web page, the print
    book and PLAYBOOK.md all ask for the same thing, and resolving is where every
    sentence in the book now comes from.
    """
    key = front["id"]
    cache = play.setdefault("_resolved", {})
    if key not in cache:
        form = play["_formation"]
        # A play-action pass blocks like the run it fakes, not like the direction the
        # quarterback ends up running. Taking the side from the boot inverted every
        # playside/backside rule on the line: the fake advertised itself by blocking
        # the mirror image of the play it was selling. `fakes` names the run, and the
        # blockers take that run's side and its hole.
        run = faked_play(play) or play
        # A play may name who blocks whom against one front. Those assignments replace
        # the rule-derived ones for that front only; every other front still works its
        # blocks out from the rules.
        overrides = (play.get("fronts") or {}).get(key) or {}
        subject = (dict(play, assignments={**play["assignments"], **overrides})
                   if overrides else play)
        cache[key] = blocking.resolve_play(
            subject, play_alignment(form, play), front,
            play_side(run), play_hole(run)
        )
    return cache[key]


def play_alignment(form: dict, play: dict) -> dict:
    """Where the eleven actually line up for this play.

    A formation has one alignment, but a formation is not always one picture. The
    The SL is split right on almost every snap, but Power is built on his kick-out and
    Jet needs him with a formation to cross, so those two move him. A play may say
    which, and the call says it out loud — `Regular I SL Left 35 Power` — so nobody is
    moved silently.

    An override may only move somebody the formation already has. It cannot add a
    twelfth player or invent a position, and validate() rejects both.
    """
    alignment = {pos: list(spot) for pos, spot in form.get("alignment", {}).items()}
    for pos, spot in (play.get("alignment") or {}).items():
        if pos in alignment:
            alignment[pos] = list(spot)
    return alignment

# Holes 0/1 sit between the center and the guard, 2/3 guard to tackle, 4/5 tackle to end,
# 6/7 outside the end and 8/9 wider still. The first three zones are the real gaps in the
# line, so they are measured off the formation's own alignment and follow its splits.
HOLE_INTERIOR = [("C", "G"), ("G", "T"), ("T", "TE")]

# The line from the middle out, as position-key suffixes after the side letter. Spelled
# out rather than built from the hole names, because the tight end's key is LTE/RTE while
# the defensive end's is LE/RE and a suffix of "E" would silently pick the wrong one.
LINE_OUT = ("G", "T", "TE")

# How far off his aiming point a carrier may cross and still count as hitting the hole.
# Half a line split — enough that a back bending to daylight passes, tight enough that a
# call naming the wrong gap fails.
HOLE_TOLERANCE = 0.4


def hole_bounds(alignment: dict, side: str, pair: int) -> tuple[float, float]:
    """The |x| window a carrier must cross in to have hit this hole.

    `pair` is the hole number halved: 0 is the center-guard gap, 3 is outside the end,
    4 is everything wider than that.
    """
    edges = [abs(alignment["C"][0])]
    for suffix in LINE_OUT:
        edges.append(abs(alignment[side + suffix][0]))
    split = (edges[3] - edges[0]) / 3.0
    if pair < len(HOLE_INTERIOR):
        return edges[pair] - HOLE_TOLERANCE, edges[pair + 1] + HOLE_TOLERANCE
    # Outside the end there is no next lineman to measure against, so the two outer
    # zones are one and two line splits wide.
    outside = edges[3] + 2 * split
    if pair == 3:
        return edges[3] - HOLE_TOLERANCE, outside + HOLE_TOLERANCE
    return outside - HOLE_TOLERANCE, float("inf")


def los_crossing(alignment: dict, pos: str, spec: dict) -> float | None:
    """Where this player crosses the line of scrimmage, in field x. None if he never does."""
    start = alignment[pos]
    points = [(start[0], start[1])]
    points += [(start[0] + dx, start[1] + dy) for dx, dy in (spec.get("path") or [])]
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if (y1 < 0 <= y2) or (y1 <= 0 < y2):
            t = 0.0 if y2 == y1 else (0 - y1) / (y2 - y1)
            return x1 + t * (x2 - x1)
    return None


def validate_call(play: dict, form: dict, defenses: dict) -> list[str]:
    """Check a play's call against the play's own diagram."""
    call = play.get("call")
    if not call:
        return []
    pid = play.get("id", "<no id>")
    backs = form.get("backs") or {}
    if not backs:
        return [f"formation {form.get('id')}: has plays with calls but no 'backs' map, so "
                "the numbering in those calls cannot be checked"]

    m = CALL_DIGITS.search(call)
    # A word call: the ball goes to somebody the numbering has no digit for (a tight end
    # on an end-around), so the call names him instead of a hole. The play has to opt in,
    # so a forgotten number on any other play still fails, and it has to say its
    # direction, because with no hole digit that is where its playside comes from.
    if not m and play.get("word_call"):
        if play.get("direction") not in ("left", "right"):
            return [f"{pid}: word call '{call}' needs a direction, left or right"]
        return []
    if not m:
        return [f"{pid}: call '{call}' has no two-digit back-and-hole number"]
    back_digit, hole_digit = m.group(1), m.group(2)

    pos = backs.get(back_digit)
    if not pos:
        return [f"{pid}: call '{call}' names back {back_digit}, which this formation does "
                f"not define (it has {', '.join(sorted(backs))})"]
    alignment = play_alignment(form, play)
    if pos not in alignment:
        return [f"{pid}: call '{call}' names back {back_digit} = {pos}, who is not in the "
                "formation"]

    # The digits name the back who handles the ball, so the back they name has to be
    # one. This used to be implied: a blocker's path was hand-drawn, so a call naming
    # him almost never crossed the line in the hole it claimed and the geometry check
    # caught it. Now every blocker's path is derived from the front, and a pulling
    # guard's wrap crosses the line right where the ball does — which made a wrong
    # call measurably true. Saying it outright is both stronger and honest.
    source = play.get("assignments", {}).get(pos, {})
    if "block" in source:
        return [f"{pid}: call '{call}' names back {back_digit} = {pos}, who is blocking "
                "on this play — the digits name the back who handles the ball"]

    spec = resolved_assignments(play, defenses[blocking.DEFAULT_FRONT]).get(pos, {})
    crossing = los_crossing(alignment, pos, spec)
    if crossing is None:
        return [f"{pid}: call '{call}' says {pos} runs the {hole_digit} hole, but his path "
                "never crosses the line of scrimmage"]

    hole = int(hole_digit)
    side = "R" if hole % 2 == 0 else "L"
    going_right = hole % 2 == 0
    if (crossing > 0) != going_right:
        where = "right" if crossing > 0 else "left"
        return [f"{pid}: call '{call}' says the {hole_digit} hole, which is to the "
                f"{'right' if going_right else 'left'}, but {pos} crosses to the {where} "
                f"(x = {crossing:+.1f})"]

    low, high = hole_bounds(alignment, side, hole // 2)
    if not (low <= abs(crossing) <= high):
        window = (f"anything wider than {low:.2f} yards" if high == float("inf")
                  else f"{low:.2f} to {high:.2f} yards")
        return [f"{pid}: call '{call}' says the {hole_digit} hole, which is {window} "
                f"out from the middle, but {pos} crosses the line at "
                f"{abs(crossing):.2f}"]
    return []


def load_install() -> dict:
    """The practice-by-practice install schedule, if there is one."""
    path = ROOT / "install.json"
    return load_json(path) if path.is_file() else {}


def load_favorites() -> dict:
    """The bread-and-butter plays pinned to the top of the call sheet, if any."""
    path = ROOT / "favorites.json"
    return load_json(path) if path.is_file() else {}


def validate_favorites(favorites: dict, formations: list[dict]) -> list[str]:
    if not favorites:
        return []
    errors = []
    plays = {p["id"] for f in formations for p in f["_plays"]}
    for i, entry in enumerate(favorites.get("plays", [])):
        for side in ("right", "left"):
            pid = entry.get(side)
            if not pid:
                errors.append(f"favorites[{i}]: missing '{side}'")
            elif pid not in plays:
                errors.append(f"favorites[{i}]: no such play '{pid}' ({side})")
    return errors


def load_roster() -> dict:
    """The depth chart, if the coach has started one."""
    path = ROOT / "roster.json"
    return load_json(path) if path.is_file() else {}


def validate_roster(roster: dict, formations: list[dict], defenses: dict) -> list[str]:
    """Positions only — never a headcount. A depth chart is never fully cast in
    August, and a build that refused to publish an open slot would mean you could
    not publish at all."""
    if not roster:
        return []
    errors = []
    offense_keys = {pos for f in formations for pos in f["alignment"]}
    # Every spot any front aligns, not just the base one — the same rule the offense
    # side follows. A coach who has named a nose tackle should not have that name
    # rejected the week we make a front without one the base.
    defense_keys = {pos for front in defenses.values() for pos in front["alignment"]}
    for side, valid in (("offense", offense_keys), ("defense", defense_keys)):
        for pos, names in roster.get(side, {}).items():
            if pos not in valid:
                errors.append(f"roster.{side}: no such position '{pos}'")
            elif not isinstance(names, list):
                errors.append(f"roster.{side}.{pos}: must be a list of names")

    # A package only overrides the spots that actually change for it — the line
    # doesn't move for Jumbo, so it has no business appearing here at all.
    for i, pkg in enumerate(roster.get("offense_packages", [])):
        if not pkg.get("name"):
            errors.append(f"offense_packages[{i}]: missing 'name'")
        for pos, names in pkg.get("positions", {}).items():
            if pos not in offense_keys:
                errors.append(f"offense_packages[{i}] '{pkg.get('name')}': "
                              f"no such position '{pos}'")
            elif not isinstance(names, list):
                errors.append(f"offense_packages[{i}] '{pkg.get('name')}'.{pos}: "
                              "must be a list of names")
    return errors


def validate_install(schedule: dict, formations: list[dict], defenses: dict) -> list[str]:
    """A schedule that teaches a play before the thing it is built on is worse than no
    schedule: it sends a coach to practice to install misdirection off a play the team
    has never run. The dependencies are written in the plays' own coaching points, so
    they are declared here and checked rather than left to whoever reads carefully.
    """
    if not schedule:
        return []
    errors = []
    plays = {p["id"] for f in formations for p in f["_plays"]}
    fronts = set(defenses)
    form_ids = {f["id"] for f in formations}
    practices = schedule.get("practices", [])

    numbers = [p.get("n") for p in practices]
    if numbers != sorted(numbers) or len(set(numbers)) != len(numbers):
        errors.append("install: practice numbers must be unique and in order")

    installed_at: dict[str, int] = {}
    for practice in practices:
        n = practice.get("n")
        for pid in practice.get("plays", []):
            if pid not in plays:
                errors.append(f"install practice {n}: no such play '{pid}'")
            elif pid in installed_at:
                errors.append(f"install: '{pid}' is installed twice, at practices "
                              f"{installed_at[pid]} and {n}")
            else:
                installed_at[pid] = n
        for fid in practice.get("fronts", []):
            if fid not in fronts:
                errors.append(f"install practice {n}: no such defensive front '{fid}'")
            elif fid in installed_at:
                errors.append(f"install: front '{fid}' is installed twice, at practices "
                              f"{installed_at[fid]} and {n}")
            else:
                installed_at[fid] = n
        # A review is a play this practice runs again rather than teaches. It has to
        # exist, it has to have been installed at an EARLIER practice — reviewing
        # something nobody has been taught is the mistake this is here to catch — and
        # it may not also be installed today, which would be both at once.
        for pid in practice.get("review", []):
            if pid not in plays:
                errors.append(f"install practice {n}: no such play '{pid}' to review")
            elif pid in practice.get("plays", []):
                errors.append(f"install practice {n}: '{pid}' is both installed and "
                              "reviewed on the same day")
            elif pid not in installed_at:
                errors.append(f"install practice {n}: reviews '{pid}', which is not "
                              "installed at any earlier practice")
        for fmid in practice.get("formations", []):
            if fmid not in form_ids:
                errors.append(f"install practice {n}: no such formation '{fmid}'")
        phase = practice.get("phase")
        if phase and phase not in schedule.get("phases", {}):
            errors.append(f"install practice {n}: unknown phase '{phase}'")

    # Dates are ISO so the site can put the practice on a calendar and compute the
    # weekday from it. A hand-typed "Mon, Aug 11" cannot be placed, and — the reason
    # this is checked rather than tolerated — a hand-typed weekday can disagree with
    # the date printed beside it, which is exactly the mistake a coach acts on.
    days = []
    for practice in practices:
        n = practice.get("n")
        raw = str(practice.get("date", "")).strip()
        if not raw:
            continue
        try:
            days.append((n, date.fromisoformat(raw)))
        except ValueError:
            errors.append(f"install practice {n}: date '{raw}' is not YYYY-MM-DD")
    for (n1, d1), (n2, d2) in zip(days, days[1:]):
        if d2 < d1:
            errors.append(f"install practice {n2} ({d2}) is dated before practice "
                          f"{n1} ({d1}) — practices run in number order")

    # Not everything has to be scheduled. The plan is built out a practice at a time,
    # and a half-written schedule is the normal state of one in August — failing the
    # build over it would mean you could not publish until you had planned the whole
    # season. What must not happen is a play going missing in silence, so the page
    # lists whatever is not on the schedule yet instead.

    for practice in practices:
        n = practice.get("n")
        for need in practice.get("requires", []):
            if need not in installed_at:
                errors.append(f"install practice {n}: requires '{need}', which is "
                              "never installed")
            elif installed_at[need] >= n:
                errors.append(
                    f"install practice {n}: requires '{need}', but that is not "
                    f"installed until practice {installed_at[need]}"
                )
    return errors


def validate(formations: list[dict], defenses: dict) -> list[str]:
    errors = []
    # Play ids must be unique across the whole book: each one becomes a flat p-<id>.html
    # page, so a collision between two formations would silently overwrite a play.
    seen: dict[str, str] = {}
    codes: dict[str, str] = {}
    for form in formations:
        for play in form["_plays"]:
            pid = play.get("id", "")
            if pid in seen:
                errors.append(
                    f"{pid}: duplicate play id, also used in '{seen[pid]}' — ids must be "
                    "unique across every formation"
                )
            seen[pid] = form.get("id", "?")
    # Teaching order has to be a sequence, not a tie. Two formations sharing an `order`
    # sort by name, which is the alphabet wearing a teaching order's clothes.
    by_order: dict[int, list[str]] = {}
    for form in formations:
        by_order.setdefault(form.get("order", 99), []).append(form.get("id", "?"))
    for order, ids in sorted(by_order.items()):
        if len(ids) > 1:
            errors.append(
                f"formations {', '.join(sorted(ids))} all claim order {order} — teaching "
                "order must be unambiguous"
            )
    for form in formations:
        seen_play_order: dict[int, list[str]] = {}
        for play in form["_plays"]:
            seen_play_order.setdefault(play.get("order", 99), []).append(
                play.get("id", "?"))
        for order, ids in sorted(seen_play_order.items()):
            if len(ids) > 1:
                errors.append(
                    f"formation {form.get('id')}: plays {', '.join(sorted(ids))} all claim "
                    f"order {order} — teaching order must be unambiguous"
                )

    for form in formations:
        for field in ("id", "name", "alignment"):
            if field not in form:
                errors.append(f"formation {form['_dir'].name}: missing '{field}'")
        if form.get("id") != form["_dir"].name:
            errors.append(
                f"formation {form['_dir'].name}: id '{form.get('id')}' must match the folder name"
            )
        if len(form.get("alignment", {})) != 11:
            errors.append(
                f"formation {form.get('id')}: {len(form.get('alignment', {}))} players aligned, "
                "must be 11 (this is 11v11 tackle)"
            )
        for play in form["_plays"]:
            pid = play.get("id", "<no id>")
            for field in ("id", "name", "assignments"):
                if field not in play:
                    errors.append(f"{pid}: missing required field '{field}'")
            if play.get("formation") and play["formation"] != form.get("id"):
                errors.append(
                    f"{pid}: formation '{play['formation']}' does not match its folder "
                    f"'{form.get('id')}'"
                )
            if play.get("fakes") and play["fakes"] not in _PLAYS_BY_ID:
                errors.append(
                    f"{pid}: fakes '{play['fakes']}', which is not a play in this book"
                )
            if play.get("fakes") == pid:
                errors.append(f"{pid}: fakes itself")
            # A play-action pass takes its blocking side from the run it fakes. A pass
            # that fakes nothing (a quick throw out of the shotgun) takes it from its own
            # direction, so it has to have one.
            if play.get("type") == "pass" and not play.get("fakes") \
                    and play.get("direction") not in ("left", "right"):
                errors.append(
                    f"{pid}: is a pass that neither says what it fakes nor gives a "
                    "direction — add `fakes` for play-action, or `direction` for a "
                    "straight drop-back, or its line cannot tell which side is playside"
                )
            if play.get("defense") and play["defense"] not in defenses:
                errors.append(f"{pid}: unknown defense '{play['defense']}'")
            missing = set(form.get("alignment", {})) - set(play.get("assignments", {}))
            if missing:
                errors.append(f"{pid}: no assignment for {', '.join(sorted(missing))}")
            extra = set(play.get("assignments", {})) - set(form.get("alignment", {}))
            if extra:
                errors.append(f"{pid}: assignment for unknown position {', '.join(sorted(extra))}")
            # An assignment is either a blocking intent this build knows how to
            # resolve, or a hand-drawn path. Anything else is a card with a blank spot
            # on it, which is worse than no card.
            for pos, spec in (play.get("assignments") or {}).items():
                if "block" in spec:
                    if spec["block"] == "pull":
                        errors.append(
                            f"{pid}: {pos} pulls. Nobody pulls in this book — a puller "
                            "is a half-count late and the hole he left is the hole the "
                            "play wanted. The playside end kicks out, a back leads, the "
                            "backside guard cuts off."
                        )
                    elif spec["block"] not in blocking.VERBS:
                        errors.append(
                            f"{pid}: {pos} has unknown blocking verb "
                            f"'{spec['block']}' — the verbs are "
                            f"{', '.join(sorted(blocking.VERBS))}"
                        )
                    if spec["block"] == "lead" and spec.get("target") not in (
                            None, "force"):
                        errors.append(
                            f"{pid}: {pos} leads with target '{spec['target']}', which "
                            "this verb ignores — a lead aims at the hole, and only "
                            "'force' names a man"
                        )
                    if spec["block"] == "decoy" and not spec.get("path"):
                        errors.append(
                            f"{pid}: {pos} sells a fake but has no path — a decoy copies "
                            "another play's path, which cannot be derived from the front"
                        )
                    if spec["block"] == "man":
                        errors.append(
                            f"{pid}: {pos} names a man to block, which only means "
                            "something against one front — put it under `fronts`"
                        )
                elif not spec.get("rule"):
                    errors.append(
                        f"{pid}: {pos} has neither a blocking verb nor a written rule"
                    )
            # Who blocks whom against one front. A named man has to be standing in that
            # front, or the block resolves to nobody and the card is wrong in silence.
            for fid, over in (play.get("fronts") or {}).items():
                if fid not in defenses:
                    errors.append(f"{pid}: blocks against unknown front '{fid}'")
                    continue
                labels = defenses[fid].get("alignment", {})
                for pos, spec in over.items():
                    if pos not in form.get("alignment", {}):
                        errors.append(f"{pid} vs {fid}: assignment for unknown position {pos}")
                    if spec.get("block") and spec["block"] not in blocking.VERBS:
                        errors.append(f"{pid} vs {fid}: {pos} has unknown blocking verb "
                                      f"'{spec['block']}'")
                    if spec.get("block") == "man" and not spec.get("man"):
                        errors.append(f"{pid} vs {fid}: {pos} blocks a man but names nobody")
                    for k in ("man", "help"):
                        if spec.get(k) and spec[k] not in labels:
                            errors.append(f"{pid} vs {fid}: {pos} blocks '{spec[k]}', who "
                                          f"is not in the {fid}")
            # A pitch is drawn to a point on the receiver's path, so he has to be in the
            # formation and his path has to reach the waypoint it names.
            pitch = play.get("pitch")
            if pitch:
                for k in ("from", "to"):
                    who = pitch.get(k, "QB" if k == "from" else None)
                    if who not in form.get("alignment", {}):
                        errors.append(f"{pid}: pitch {k} '{who}', who is not in this formation")
                receiver = (play.get("assignments") or {}).get(pitch.get("to"), {})
                if len(receiver.get("path") or []) < pitch.get("at", 1):
                    errors.append(f"{pid}: pitch is caught at waypoint {pitch.get('at', 1)} "
                                  f"of {pitch.get('to')}'s path, which is not that long")
            # The play's code — "I-1", "S-3" — is what a coach calls it by and what is
            # printed big on its card, so it has to belong to its formation and be one of a
            # kind across the whole book.
            code = play.get("code")
            if code:
                letter = form.get("code_prefix")
                if not letter or not re.fullmatch(rf"{re.escape(letter)}-\d+", code):
                    errors.append(f"{pid}: code '{code}' should be '{letter}-<number>' "
                                  f"for the {form.get('name')} formation")
                if code in codes:
                    errors.append(f"{pid}: code '{code}' is already {codes[code]}'s")
                codes.setdefault(code, pid)
            carrier = play.get("ball_carrier")
            if carrier and carrier not in form.get("alignment", {}):
                errors.append(f"{pid}: ball_carrier '{carrier}' is not in the formation")
            # An alignment override moves somebody the formation already has. It may
            # not add a twelfth player, and a typo'd key would otherwise be ignored
            # in silence — the play would render at the unmoved spot and look fine.
            for pos in play.get("alignment", {}):
                if pos not in form.get("alignment", {}):
                    errors.append(
                        f"{pid}: alignment moves '{pos}', who is not in this formation"
                    )
            for pos, spot in play.get("alignment", {}).items():
                if not (isinstance(spot, list) and len(spot) == 2):
                    errors.append(
                        f"{pid}: alignment for '{pos}' must be [x, y] in field yards"
                    )
            if not missing and not extra:
                errors.extend(validate_call(play, form, defenses))
    return errors


# ------------------------------------------------------------------ drawing --


def polyline(points, color, width=2.6, dashed=False, dotted=False, smooth=False):
    if smooth and len(points) >= 3:
        # One rounded curve through every point: each leg a cubic whose handles follow
        # the neighbouring points (Catmull-Rom), so there is no corner at a waypoint.
        # The last leg leaves along the last straight direction, which keeps a block's
        # end bar square to where he arrives.
        P = [(fx(x), fy(y)) for x, y in points]
        d = f"M{P[0][0]:.1f},{P[0][1]:.1f}"
        for i in range(len(P) - 1):
            p0, p1, p2 = P[max(i - 1, 0)], P[i], P[i + 1]
            p3 = P[min(i + 2, len(P) - 1)]
            c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
            c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
            d += (f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} "
                  f"{p2[0]:.1f},{p2[1]:.1f}")
    else:
        d = " ".join(
            ("M" if i == 0 else "L") + f"{fx(p[0]):.1f},{fy(p[1]):.1f}"
            for i, p in enumerate(points)
        )
    # A near-zero dash with a round cap is a dot the width of the line.
    dash = (' stroke-dasharray="7 5"' if dashed
            else ' stroke-dasharray="0.1 7"' if dotted else "")
    return (
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
        f'stroke-linecap="round" stroke-linejoin="round"{dash}/>'
    )


def arrow_head(p_prev, p_end, color, size=0.42):
    x0, y0 = fx(p_prev[0]), fy(p_prev[1])
    x1, y1 = fx(p_end[0]), fy(p_end[1])
    ang = math.atan2(y1 - y0, x1 - x0)
    s = size * SCALE
    pts = [
        (x1 + s * math.cos(ang + math.pi - 0.42), y1 + s * math.sin(ang + math.pi - 0.42)),
        (x1 + s * math.cos(ang + math.pi + 0.42), y1 + s * math.sin(ang + math.pi + 0.42)),
    ]
    poly = f"{x1:.1f},{y1:.1f} " + " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    return f'<polygon points="{poly}" fill="{color}"/>'


def block_cap(p_prev, p_end, color, width=2.6, size=0.34):
    """The perpendicular bar that marks a block in standard playbook notation."""
    x0, y0 = fx(p_prev[0]), fy(p_prev[1])
    x1, y1 = fx(p_end[0]), fy(p_end[1])
    ang = math.atan2(y1 - y0, x1 - x0) + math.pi / 2
    s = size * SCALE
    dx, dy = s * math.cos(ang), s * math.sin(ang)
    return (
        f'<line x1="{x1-dx:.1f}" y1="{y1-dy:.1f}" x2="{x1+dx:.1f}" y2="{y1+dy:.1f}" '
        f'stroke="{color}" stroke-width="{width+0.6}" stroke-linecap="round"/>'
    )


def title_band(x0: float, width: float, name: str, meta: str, call: str) -> str:
    """Header strip: the play's name on the left, the huddle call in a badge on the right.

    Both go on every card on purpose — the name is what a coach says while teaching it,
    the call is what he yells on Saturday, and the card is where the two get connected.
    """
    # Nothing measures text in an SVG we write by hand, so both halves of the band
    # estimate their width from the character count — the badge always has, and the name
    # has to as well. Without it the longest name and the longest call meet in the middle
    # with no gap between them, which is a layout bug you only find by rendering the one
    # card that has both. The name gives way rather than the call: the call is what gets
    # yelled on Saturday, and it is the half that must stay legible across a field.
    bw = 9.2 * len(call) + 22 if call else 0.0
    name_fs = 19.0
    if call and name:
        room = width - 2 * PAD - bw - BAND_GAP
        if NAME_CHAR_W * name_fs * len(name) > room:
            name_fs = max(13.0, room / (NAME_CHAR_W * len(name)))

    out = [
        f'<rect x="{x0:.0f}" y="0" width="{width:.0f}" height="{TITLE_H}" '
        f'fill="{COLORS["band"]}"/>',
        f'<text x="{x0 + PAD:.0f}" y="26" font-size="{name_fs:.1f}" font-weight="700" '
        f'fill="#ffffff">{esc(name)}</text>',
        f'<text x="{x0 + PAD:.0f}" y="45" font-size="11.5" '
        f'fill="#a9b4c7">{esc(meta)}</text>',
    ]
    if call:
        bx = x0 + width - PAD - bw
        out.append(
            f'<rect x="{bx:.1f}" y="13" width="{bw:.1f}" height="31" rx="6" '
            f'fill="#ffffff" fill-opacity="0.12" stroke="#8593ad" stroke-width="1"/>'
        )
        out.append(
            f'<text x="{bx + bw / 2:.1f}" y="34" text-anchor="middle" font-size="14.5" '
            f'font-weight="700" fill="#ffffff" letter-spacing="0.5">{esc(call)}</text>'
        )
    return "\n".join(out)


def draw_field() -> str:
    out = [
        f'<rect x="0" y="0" width="{FIELD_W:.0f}" height="{FIELD_H:.0f}" fill="{COLORS["card"]}"/>'
    ]
    for yd in (-5.0, 5.0):
        out.append(
            f'<line x1="0" y1="{fy(yd):.1f}" x2="{FIELD_W:.0f}" y2="{fy(yd):.1f}" '
            f'stroke="{COLORS["line"]}" stroke-width="1"/>'
        )
    out.append(
        f'<line x1="0" y1="{fy(0):.1f}" x2="{FIELD_W:.0f}" y2="{fy(0):.1f}" '
        f'stroke="{COLORS["los"]}" stroke-width="2" stroke-dasharray="9 6"/>'
    )
    out.append(
        f'<ellipse cx="{fx(0):.1f}" cy="{fy(0):.1f}" rx="9" ry="5.5" '
        f'fill="#6b4a2b" stroke="#3a2716" stroke-width="1.2"/>'
    )
    return "\n".join(out)


def draw_defense(defense: dict) -> str:
    out = []
    r = 0.55 * SCALE
    for label, (x, y) in defense["alignment"].items():
        cx, cy = fx(x), fy(y)
        a = r * 0.62
        out.append(
            f'<line x1="{cx-a:.1f}" y1="{cy-a:.1f}" x2="{cx+a:.1f}" y2="{cy+a:.1f}" '
            f'stroke="{COLORS["defense"]}" stroke-width="3.6"/>'
            f'<line x1="{cx+a:.1f}" y1="{cy-a:.1f}" x2="{cx-a:.1f}" y2="{cy+a:.1f}" '
            f'stroke="{COLORS["defense"]}" stroke-width="3.6"/>'
        )
        out.append(
            f'<text x="{cx:.1f}" y="{cy - r - 3:.1f}" text-anchor="middle" font-size="12.5" '
            f'fill="{COLORS["defense"]}" font-weight="600">{esc(label.strip())}</text>'
        )
    return "\n".join(out)


def draw_paths(assignments: dict, alignment: dict, carrier: str | None) -> str:
    out = []
    for pos, spec in assignments.items():
        path = spec.get("path")
        if not path:
            continue
        ax, ay = alignment[pos]
        pts = [[ax, ay]] + [[ax + p[0], ay + p[1]] for p in path]
        kind = spec.get("type", "block")
        is_carrier = pos == carrier
        color = COLORS["carrier"] if is_carrier else COLORS["offense"]
        dashed = kind in ("motion", "pass", "fake")
        # The man with the ball is the line to find first, and on a black-and-white
        # printout red is just another grey — so he is told apart by weight, not colour.
        width = 4.6 if is_carrier else 2.4
        # A bubble block and a ball carrier's run both draw as one rounded curve: a
        # runner bends round a corner, he does not stop and turn ninety degrees.
        out.append(polyline(pts, color, width=width, dashed=dashed,
                            dotted=kind == "rollout",
                            smooth=spec.get("curve", False) or kind == "run"))
        if kind == "block":
            out.append(block_cap(pts[-2], pts[-1], color, width=width))
        else:
            out.append(arrow_head(pts[-2], pts[-1], color,
                                  size=0.56 if is_carrier else 0.42))
    return "\n".join(out)


def draw_pitch(play: dict, alignment: dict) -> str:
    """The ball, pitched: a dotted line from the man who pitches it to where it is caught.

    Where is a point on the receiver's own path — `at` counts his waypoints from 1 —
    so the pitch meets his line and his line carries on from there. No arrowhead: it
    is the ball's flight, not somebody running.
    """
    pitch = play.get("pitch")
    if not pitch:
        return ""
    sx, sy = alignment[pitch.get("from", "QB")]
    rx, ry = alignment[pitch["to"]]
    path = play["assignments"][pitch["to"]].get("path") or []
    at = pitch.get("at", 1)
    catch = [rx + path[at - 1][0], ry + path[at - 1][1]] if path else [rx, ry]
    return polyline([[sx, sy], catch], COLORS["carrier"], width=3.2, dotted=True)


def draw_offense(play: dict, alignment: dict) -> str:
    out = []
    carrier = play.get("ball_carrier")
    for pos, (x, y) in alignment.items():
        cx, cy = fx(x), fy(y)
        fill = COLORS["carrier"] if pos == carrier else COLORS["offense"]
        # As big as the I allows: the quarterback stands a yard behind the centre, so
        # the square's half and the circle's radius together have to stay under that.
        if pos in LINEMEN:
            s = 0.5 * SCALE
            out.append(
                f'<rect x="{cx-s:.1f}" y="{cy-s:.1f}" width="{2*s:.1f}" height="{2*s:.1f}" '
                f'rx="3" fill="#ffffff" stroke="{fill}" stroke-width="2.6"/>'
            )
        else:
            out.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{0.5*SCALE:.1f}" '
                f'fill="#ffffff" stroke="{fill}" stroke-width="2.6"/>'
            )
        out.append(
            f'<text x="{cx:.1f}" y="{cy+4.5:.1f}" text-anchor="middle" font-size="13" '
            f'font-weight="700" fill="{fill}">{esc(pos)}</text>'
        )
    return "\n".join(out)


def wrap(text, width: int) -> list[str]:
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if len(trial) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def draw_code(play: dict, half: float, top: float) -> str:
    """The play's code — "#I-1" — big in the top-right corner of the field.

    It is what a coach points at on a printed sheet and shouts across the practice
    field, so it is sized to read from arm's length on paper. A white plate behind it
    keeps the yard lines from cutting through the letters.
    """
    code = play.get("code")
    if not code:
        return ""
    label = f"#{code}"
    fs = 40.0
    w = 0.62 * fs * len(label) + 20
    h = fs + 12
    x1, y0 = fx(half) - 8, fy(top) + 8
    return (
        f'<rect x="{x1 - w:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" rx="8" '
        f'fill="#ffffff" stroke="{COLORS["ink"]}" stroke-width="3"/>'
        f'<text x="{x1 - w / 2:.1f}" y="{y0 + h / 2 + fs * 0.35:.1f}" text-anchor="middle" '
        f'font-size="{fs:.0f}" font-weight="800" fill="{COLORS["ink"]}">{esc(label)}</text>'
    )


def draw_name(play: dict, half: float, top: float) -> str:
    """The play's name, small in the top-left corner, across from its code.

    A printed diagram gets separated from its page, so it carries its own name. It gives
    way to the code: the name shrinks before it is allowed to run under the code's box.
    """
    name = play.get("name", "")
    if not name:
        return ""
    code_w = 0.62 * 40 * (len(play.get("code", "")) + 1) + 20 if play.get("code") else 0
    room = fx(half) - fx(-half) - code_w - 60
    fs = min(17.0, room / (0.54 * len(name)))  # bold runs wider than NAME_CHAR_W
    return (
        f'<text x="{fx(-half) + 12:.1f}" y="{fy(top) + 40:.1f}" font-size="{fs:.1f}" '
        f'font-weight="700" fill="{COLORS["ink"]}">{esc(name)}</text>'
    )


def render_card(play: dict, defense: dict, frame: tuple[float, float, float]) -> str:
    form = play["_formation"]
    alignment = play_alignment(form, play)
    assignments = resolved_assignments(play, defense)

    # Same frame as the web diagrams, so a card and a diagram of the same play are
    # drawn at the same scale with the formation in the same place.
    fr_half, fr_top, fr_bot = frame
    card_w = (2 * fr_half) * SCALE
    field_h = (fr_top - fr_bot) * SCALE
    off_x, off_y = -fx(-fr_half), -fy(fr_top)

    # Column text width follows the card width instead of assuming the old canvas.
    chars = max(24, int(((card_w - 2 * PAD) / 2 - 34) / 6.5))

    ordered = ordered_positions(play)
    entries = [(pos, wrap(assignments[pos]["rule"], chars)) for pos in ordered]
    half = math.ceil(len(entries) / 2)
    columns = [entries[:half], entries[half:]]
    col_lines = max((sum(len(e[1]) for e in col) for col in columns), default=0)

    coach_lines = []
    for c in play.get("coaching_points", []):
        coach_lines.extend(wrap(c, int(chars * 2.2)))

    assign_h = col_lines * LINE_H + 34
    coach_h = (len(coach_lines) * LINE_H + 40) if coach_lines else 0
    total_h = TITLE_H + field_h + assign_h + coach_h + PAD

    meta_bits = [play.get("type", "").upper(), form_label(form)]
    if defense:
        meta_bits.append(f"vs {defense['name']}")
    meta = "  •  ".join(b for b in meta_bits if b)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{card_w:.0f}" height="{total_h:.0f}" '
        f'viewBox="0 0 {card_w:.0f} {total_h:.0f}" '
        f'font-family="Segoe UI, Helvetica, Arial, sans-serif">',
        f'<rect width="100%" height="100%" fill="{COLORS["card"]}"/>',
        title_band(0, card_w, play["name"], meta, play.get("call", "")),
        # Clip so the shared frame crops the field the same way it does on the website.
        f'<clipPath id="fieldclip"><rect x="0" y="{TITLE_H}" width="{card_w:.0f}" '
        f'height="{field_h:.0f}"/></clipPath>',
        f'<g clip-path="url(#fieldclip)">'
        f'<g transform="translate({off_x:.1f},{TITLE_H + off_y:.1f})">',
        draw_field(),
    ]
    svg.append(draw_defense(defense))
    svg.append(draw_paths(assignments, alignment, play.get("ball_carrier")))
    svg.append(draw_pitch(play, alignment))
    svg.append(draw_offense(play, alignment))
    svg.append(draw_code(play, fr_half, fr_top))
    svg.append("</g></g>")

    y0 = TITLE_H + field_h
    svg.append(
        f'<line x1="{PAD}" y1="{y0+10:.0f}" x2="{card_w-PAD:.0f}" y2="{y0+10:.0f}" '
        f'stroke="{COLORS["line"]}" stroke-width="1"/>'
    )
    svg.append(
        f'<text x="{PAD}" y="{y0+30:.0f}" font-size="11" font-weight="700" '
        f'fill="{COLORS["muted"]}" letter-spacing="1">ASSIGNMENTS</text>'
    )

    for ci, col in enumerate(columns):
        x = PAD + ci * (card_w - 2 * PAD) / 2
        cy = y0 + 48
        for pos, lines in col:
            svg.append(
                f'<text x="{x:.0f}" y="{cy:.0f}" font-size="12" font-weight="700" '
                f'fill="{COLORS["ink"]}">{esc(pos)}</text>'
            )
            for i, line in enumerate(lines):
                svg.append(
                    f'<text x="{x+34:.0f}" y="{cy + i*LINE_H:.0f}" font-size="12" '
                    f'fill="{COLORS["ink"]}">{esc(line)}</text>'
                )
            cy += len(lines) * LINE_H

    if coach_lines:
        cy = y0 + assign_h + 18
        svg.append(
            f'<line x1="{PAD}" y1="{cy-14:.0f}" x2="{card_w-PAD:.0f}" y2="{cy-14:.0f}" '
            f'stroke="{COLORS["line"]}" stroke-width="1"/>'
        )
        svg.append(
            f'<text x="{PAD}" y="{cy+4:.0f}" font-size="11" font-weight="700" '
            f'fill="{COLORS["muted"]}" letter-spacing="1">COACHING POINTS</text>'
        )
        for i, line in enumerate(coach_lines):
            svg.append(
                f'<text x="{PAD}" y="{cy + 24 + i*LINE_H:.0f}" font-size="12" '
                f'fill="{COLORS["ink"]}">{esc(line)}</text>'
            )

    svg.append("</svg>")
    return "\n".join(svg)


# The offense a defensive card is drawn against: a balanced two-tight-end set, so the
# picture does not imply we only ever face one formation.
GENERIC_OFFENSE = {
    "LTE": [-4.2, -0.5], "LT": [-2.8, -0.5], "LG": [-1.4, -0.5], "C": [0.0, -0.5],
    "RG": [1.4, -0.5], "RT": [2.8, -0.5], "RTE": [4.2, -0.5],
    "QB": [0.0, -1.5], "FB": [0.0, -3.3], "LH": [-2.9, -4.9], "RH": [2.9, -4.9],
}

DEF_LINEMEN = {"LE", "LT", "LG", "NT", "RG", "RT", "RE"}


def draw_ghost_offense() -> str:
    """The opposition, drawn faintly — on a defensive card they are scenery."""
    out = []
    for pos, (x, y) in GENERIC_OFFENSE.items():
        cx, cy = fx(x), fy(y)
        if pos in LINEMEN:
            s = 0.5 * SCALE
            out.append(
                f'<rect x="{cx-s:.1f}" y="{cy-s:.1f}" width="{2*s:.1f}" height="{2*s:.1f}" '
                f'rx="3" fill="#ffffff" stroke="{COLORS["ghost"]}" stroke-width="2"/>'
            )
        else:
            out.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{0.5*SCALE:.1f}" '
                f'fill="#ffffff" stroke="{COLORS["ghost"]}" stroke-width="2"/>'
            )
    return "\n".join(out)


def draw_defenders(front: dict) -> str:
    """Our defenders: the subject of the card, so they are drawn solid and labelled."""
    out = []
    r = 0.57 * SCALE
    for pos, (x, y) in front["alignment"].items():
        cx, cy = fx(x), fy(y)
        a = r * 0.66
        color = COLORS["offense"]
        out.append(
            f'<line x1="{cx-a:.1f}" y1="{cy-a:.1f}" x2="{cx+a:.1f}" y2="{cy+a:.1f}" '
            f'stroke="{color}" stroke-width="4" stroke-linecap="round"/>'
            f'<line x1="{cx+a:.1f}" y1="{cy-a:.1f}" x2="{cx-a:.1f}" y2="{cy+a:.1f}" '
            f'stroke="{color}" stroke-width="4" stroke-linecap="round"/>'
        )
        out.append(
            f'<text x="{cx:.1f}" y="{cy - r - 4:.1f}" text-anchor="middle" font-size="13.5" '
            f'font-weight="700" fill="{color}">{esc(pos)}</text>'
        )
    return "\n".join(out)


def draw_defense_paths(front: dict) -> str:
    """Charges are solid, reads and drops are dashed."""
    out = []
    for pos, spec in front.get("assignments", {}).items():
        path = spec.get("path")
        if not path:
            continue
        ax, ay = front["alignment"][pos]
        pts = [[ax, ay]] + [[ax + p[0], ay + p[1]] for p in path]
        dashed = spec.get("type") != "attack"
        color = COLORS["carrier"] if spec.get("type") == "attack" else COLORS["offense"]
        out.append(polyline(pts, color, width=2.4, dashed=dashed))
        out.append(arrow_head(pts[-2], pts[-1], color))
    return "\n".join(out)


def render_defense_diagram(front: dict, frame: tuple[float, float, float]) -> str:
    half, y_top, y_bot = frame
    vb_x, vb_y = fx(-half), fy(y_top)
    vb_w, vb_h = fx(half) - vb_x, fy(y_bot) - vb_y
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{vb_w:.0f}" height="{vb_h:.0f}" '
        f'viewBox="{vb_x:.0f} {vb_y:.0f} {vb_w:.0f} {vb_h:.0f}" '
        f'font-family="Segoe UI, Helvetica, Arial, sans-serif" role="img">',
        f'<title>{esc(front["name"])} — {esc(front.get("call", ""))}</title>',
        draw_field(),
        draw_ghost_offense(),
        draw_defense_paths(front),
        draw_defenders(front),
        "</svg>",
    ])


def render_formation_diagram(form: dict) -> str:
    """Eleven spots, no play, no routes — the icon used on formation cards.

    Deliberately not drawn in the shared book frame: that frame fits the deepest
    route in the whole playbook, which would leave an alignment icon mostly blank
    grass. This crops tight to the formation's own eleven spots instead, since there
    is exactly one of these per formation and nothing to keep in scale against.
    """
    xs = [x for x, _ in form["alignment"].values()]
    ys = [y for _, y in form["alignment"].values()]
    margin = 1.15
    left, right = min(xs) - margin, max(xs) + margin
    top, bottom = max(ys) + margin, min(ys) - margin
    vb_x, vb_y = fx(left), fy(top)
    vb_w, vb_h = fx(right) - vb_x, fy(bottom) - vb_y
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{vb_w:.0f}" height="{vb_h:.0f}" '
        f'viewBox="{vb_x:.0f} {vb_y:.0f} {vb_w:.0f} {vb_h:.0f}" '
        f'font-family="Segoe UI, Helvetica, Arial, sans-serif" role="img">',
        f'<title>{esc(form["name"])} — alignment</title>',
        draw_field(),
        draw_offense({}, form["alignment"]),
        "</svg>",
    ])


def diagram_frame(formations: list[dict], defenses: dict) -> tuple[float, float, float]:
    """One frame that fits every play in the book.

    Every diagram is drawn in this same window, so all of them share a scale and the
    line of scrimmage, the formation and the defense land on the same spot on every
    card. Cropping each play to its own content made better use of the pixels but
    made the book look like it had been assembled from different sources — the same
    play drawn at two sizes reads as two different plays.

    Returned as (half-width, top, bottom) in yards; the frame is symmetric about the
    middle of the formation so a play and its mirror are framed identically.
    """
    xs = [x for x, _ in GENERIC_OFFENSE.values()]
    ys = [y for _, y in GENERIC_OFFENSE.values()]
    for front in defenses.values():
        xs += [x for x, _ in front["alignment"].values()]
        ys += [y for _, y in front["alignment"].values()]
        for pos, spec in front.get("assignments", {}).items():
            ax, ay = front["alignment"][pos]
            xs += [ax + p[0] for p in spec.get("path", [])]
            ys += [ay + p[1] for p in spec.get("path", [])]
    for form in formations:
        alignment = form["alignment"]
        xs += [x for x, _ in alignment.values()]
        ys += [y for _, y in alignment.values()]
        for play in form["_plays"]:
            spots = play_alignment(form, play)
            xs += [x for x, _ in spots.values()]
            ys += [y for _, y in spots.values()]
            # Every front the play is drawn against, not just one: a blocking path is
            # computed from where that front's eleven are standing, so the widest
            # version of a pull or a kick-out only exists in one of the three. Framing
            # on the default front alone would crop the other two.
            for fid in blocking.SCOUT_FRONTS:
                for pos, spec in resolved_assignments(play, defenses[fid]).items():
                    ax, ay = spots[pos]
                    xs += [ax + p[0] for p in spec.get("path", [])]
                    ys += [ay + p[1] for p in spec.get("path", [])]

    def up(v, step=0.5):
        return math.ceil(v / step) * step

    margin = 0.8
    half = min(-X_MIN, up(max(abs(min(xs)), abs(max(xs))) + margin))
    top = min(Y_MAX, up(max(ys) + margin))
    bottom = max(Y_MIN, -up(-min(ys) + margin))
    return half, top, bottom


def render_diagram(play: dict, defense: dict, frame: tuple[float, float, float]) -> str:
    """Diagram only — no assignment text baked in.

    The web page pairs this with real HTML so the words reflow on a phone instead of
    shrinking into an unreadable block. Drawn in the shared frame from
    diagram_frame() so every play in the book lines up with every other one.
    """
    form = play["_formation"]
    assignments = resolved_assignments(play, defense)

    # Crop to what this play actually uses. A front with no deep safety would otherwise
    # leave six yards of blank grass at the top, which on a phone is six yards of nothing.
    half, y_top, y_bot = frame
    vb_x = fx(-half)
    vb_w = fx(half) - vb_x
    vb_y = fy(y_top)
    vb_h = fy(y_bot) - vb_y

    # No title band here: the page always renders the name and call as real HTML above
    # the diagram, and repeating them inside the image just wastes phone screen.
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{vb_w:.0f}" height="{vb_h:.0f}" '
        f'viewBox="{vb_x:.0f} {vb_y:.0f} {vb_w:.0f} {vb_h:.0f}" '
        f'font-family="Segoe UI, Helvetica, Arial, sans-serif" role="img">',
        f'<title>{esc(play["name"])} — {esc(play.get("call", ""))} vs '
        f'{esc(defense["name"])}</title>',
        draw_field(),
    ]
    svg.append(draw_defense(defense))
    alignment = play_alignment(form, play)
    svg.append(draw_paths(assignments, alignment, play.get("ball_carrier")))
    svg.append(draw_pitch(play, alignment))
    svg.append(draw_offense(play, alignment))
    svg.append(draw_code(play, half, y_top))
    svg.append(draw_name(play, half, y_top))
    svg.append("</svg>")
    return "\n".join(svg)


# ------------------------------------------------------------------ outputs --



def play_section(play: dict, card_rel: str, defenses: dict) -> list[str]:
    title = play["name"]
    out = ["---", "", f"## {title}", ""]
    if play.get("call"):
        out += [f"**Call it:** `{play['call']}`", ""]
    out += [f"![{title}]({card_rel})", ""]
    out += ["| Position | Assignment |", "|---|---|"]
    assignments = resolved_assignments(play, defenses[blocking.DEFAULT_FRONT])
    ordered = [x for x in CARD_ORDER if x in assignments]
    for pos in ordered:
        carrier = " **(ball)**" if pos == play.get("ball_carrier") else ""
        out.append(f"| **{pos}**{carrier} | {assignments[pos]['rule']} |")
    out.append("")
    if play.get("coaching_points"):
        out += ["**Coaching points**", ""]
        out += [f"- {c}" for c in play["coaching_points"]]
        out.append("")
    return out


def write_formation_readme(form: dict, defenses: dict) -> str:
    heading = form_label(form)
    out = [
        f"# {heading}",
        "",
        "_Generated by `generator/render.py`. Edit the JSON in `plays/`, not this file._",
        "",
        form.get("notes", ""),
        "",
        "**Alignment** (yards; x positive to the right, y positive downfield, LOS = 0)",
        "",
        "| Position | x | y |",
        "|---|---|---|",
    ]
    for pos, (x, y) in form["alignment"].items():
        out.append(f"| {pos} | {x} | {y} |")
    out.append("")
    if form.get("coaching_notes"):
        out += ["**Formation coaching notes**", ""]
        out += [f"- {c}" for c in form["coaching_notes"]]
        out.append("")
    out += ["## Plays", "", "| Play | Call | Type | Ball |", "|---|---|---|---|"]
    for p in form["_plays"]:
        title = p["name"]
        out.append(
            f"| [{title}](#{slug(title)}) | `{p.get('call', '')}` | {p.get('type', '')} "
f"| {p.get('ball_carrier', '—')} |"
        )
    out.append("")
    for p in form["_plays"]:
        out += play_section(p, f"cards/{p['id']}-{blocking.DEFAULT_FRONT}.svg",
                            defenses)
    return "\n".join(out) + "\n"


def write_playbook(formations: list[dict], defenses: dict) -> str:
    out = [
        "# Sayville 8U Playbook",
        "",
        "_Generated by `generator/render.py`. Edit the JSON under `playbook/`, not this file._",
        "",
        "Terminology and authoring rules: [playbook/CLAUDE.md](playbook/CLAUDE.md)",
        "",
        "| # | Play | Call | Type | Formation | Ball |",
        "|---|---|---|---|---|---|",
    ]
    n = 0
    for form in formations:
        for p in form["_plays"]:
            n += 1
            title = p["name"]
            out.append(
                f"| {n} | [{title}](#{slug(title)}) | `{p.get('call', '')}` "
                f"| {p.get('type', '')} | {form['name']} "
                f"| {p.get('ball_carrier', '—')} |"
            )
    out.append("")
    for form in formations:
        label = form_label(form)
        out += [f"# {label}", ""]
        for p in form["_plays"]:
            out += play_section(
                p,
                f"playbook/{form['id']}/cards/{p['id']}-{blocking.DEFAULT_FRONT}.svg",
                defenses)
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Render Sayville 8U play cards from JSON.")
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    args = ap.parse_args()

    defenses = load_defenses()
    formations = load_formations()

    schedule = load_install()
    favorites = load_favorites()
    roster = load_roster()
    errors = (validate_defenses(defenses) + validate(formations, defenses)
              + validate_install(schedule, formations, defenses)
              + validate_favorites(favorites, formations)
              + validate_roster(roster, formations, defenses))
    if errors:
        for e in errors:
            print(f"ERROR  {e}", file=sys.stderr)
        return 1

    total = sum(len(f["_plays"]) for f in formations)
    print(f"{total} plays across {len(formations)} formation(s) validated.")
    if args.check:
        return 0

    # Resolve every play against every front once, up front. site_build reads the
    # results off the play rather than importing render back — which it cannot do,
    # because render imports it.
    for form in formations:
        for play in form["_plays"]:
            for fid in blocking.SCOUT_FRONTS:
                resolved_assignments(play, defenses[fid])

    # One frame for the whole book, so no two diagrams are drawn at different scales.
    frame = diagram_frame(formations, defenses)
    print(f"Diagram frame: {frame[0]*2:.1f} yards wide, {frame[2]:.1f} to {frame[1]:.1f} deep")

    for form in formations:
        cards_dir = form["_dir"] / "cards"
        cards_dir.mkdir(exist_ok=True)
        # Sweep out cards this build no longer writes. When a play was drawn against
        # one front its card was <play>.svg; it is now <play>-<front>.svg, and 112 of
        # the old ones simply stayed — tracked in git, still on disk, still teaching
        # pulling guards months after the pulls were removed, and still reachable from
        # the path the README hands a coach. A generated directory that only ever
        # gains files is one where the wrong answer outlives the right one.
        keep = {f"{form['id']}-icon.svg"}
        for p in form["_plays"]:
            for fid in blocking.SCOUT_FRONTS:
                keep.add(f"{p['id']}-{fid}.svg")
                keep.add(f"{p['id']}-{fid}-field.svg")
        for stale in cards_dir.glob("*.svg"):
            if stale.name not in keep:
                stale.unlink()
        for p in form["_plays"]:
            for fid in blocking.SCOUT_FRONTS:
                front = defenses[fid]
                (cards_dir / f"{p['id']}-{fid}.svg").write_text(
                    render_card(p, front, frame), encoding="utf-8")
                (cards_dir / f"{p['id']}-{fid}-field.svg").write_text(
                    render_diagram(p, front, frame), encoding="utf-8")
        (cards_dir / f"{form['id']}-icon.svg").write_text(
            render_formation_diagram(form), encoding="utf-8"
        )
        (form["_dir"] / "README.md").write_text(
            write_formation_readme(form, defenses), encoding="utf-8")

    cards = DEFENSE_DIR / "cards"
    cards.mkdir(exist_ok=True)
    for fid, front in defenses.items():
        # A scout front has no page in the defensive book, so it has no card either.
        # It is drawn inside every offensive diagram instead, which is the only place
        # anybody looks at it.
        if front.get("scout"):
            continue
        (cards / f"{fid}-field.svg").write_text(
            render_defense_diagram(front, frame), encoding="utf-8"
        )

    (ROOT / "PLAYBOOK.md").write_text(
        write_playbook(formations, defenses), encoding="utf-8")

    # The site is flat files at the repo root so Pages can serve from "/" and every page
    # can reference the cards in place, with no second copy of any SVG.
    pages = site_build.write_all(formations, defenses, ROOT)

    n = total * len(blocking.SCOUT_FRONTS)
    print(
        f"Wrote {n} cards (+{n} diagrams) — {total} plays against "
        f"{len(blocking.SCOUT_FRONTS)} fronts — {len(defenses)} defensive fronts, "
        f"{len(formations)} formation README(s), PLAYBOOK.md and {pages} site pages"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
