#!/usr/bin/env python3
"""Sayville 8U play-card generator.

Reads the JSON play files under `playbook/<formation>/plays/` and writes:

    playbook/<formation>/cards/<play-id>.svg          full printable card
    playbook/<formation>/cards/<play-id>-field.svg    diagram only, used by the website
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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

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
PAD = 18
LINE_H = 17

# Which alignment keys are linemen (drawn as squares) vs backs and receivers (circles).
LINEMEN = {"LTE", "LT", "LG", "C", "RG", "RT", "RTE", "TE"}

# Only used by plays that declare `mirror_of`. A position with no counterpart maps to
# itself, which is only correct when it aligns on the middle of the formation — so
# formations with a one-sided back or receiver author both directions by hand instead.
MIRROR = {
    "LTE": "RTE", "RTE": "LTE",
    "LT": "RT", "RT": "LT",
    "LG": "RG", "RG": "LG",
    "LW": "RW", "RW": "LW",
    "LH": "RH", "RH": "LH",
    "C": "C", "QB": "QB", "FB": "FB", "TB": "TB",
}

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


def mirror_point(pt):
    return [-pt[0], pt[1]]


def swap_hands(text: str) -> str:
    """Flip left/right wording when mirroring a play."""
    swaps = [
        ("right", "\x00"), ("Right", "\x01"), ("RIGHT", "\x02"),
        ("left", "right"), ("Left", "Right"), ("LEFT", "RIGHT"),
        ("\x00", "left"), ("\x01", "Left"), ("\x02", "LEFT"),
    ]
    for a, b in swaps:
        text = text.replace(a, b)
    return text


def build_mirror(play: dict, source: dict) -> dict:
    """Produce a left-handed copy of a right-handed play (or vice versa)."""
    out = json.loads(json.dumps(source))
    out.update({k: v for k, v in play.items() if k != "mirror_of"})

    out["assignments"] = {}
    for pos, spec in source["assignments"].items():
        spec = json.loads(json.dumps(spec))
        if spec.get("path"):
            spec["path"] = [mirror_point(p) for p in spec["path"]]
        spec["rule"] = swap_hands(spec["rule"])
        out["assignments"][MIRROR.get(pos, pos)] = spec

    if source.get("ball_carrier"):
        out["ball_carrier"] = MIRROR.get(source["ball_carrier"], source["ball_carrier"])
    out["coaching_points"] = [swap_hands(c) for c in source.get("coaching_points", [])]
    if source.get("purpose"):
        out["purpose"] = swap_hands(source["purpose"])
    out["direction"] = "left" if source.get("direction") == "right" else "right"
    return out


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

    resolved: dict[str, dict] = {}
    for pid, play in raw.items():          # two passes so file order doesn't matter
        if "mirror_of" not in play:
            resolved[pid] = play
    for pid, play in raw.items():
        if "mirror_of" in play:
            src = resolved.get(play["mirror_of"])
            if src is None:
                raise SystemExit(f"{pid}: mirror_of '{play['mirror_of']}' not found")
            resolved[pid] = build_mirror(play, src)

    plays = list(resolved.values())
    for p in plays:
        p["_formation"] = form
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
# they are the same only by accident: I Z Right 16 Boot is the quarterback at the 6 hole,
# while `ball_carrier` is the flanker he throws to.

CALL_DIGITS = re.compile(r"\b(\d)(\d)\b")


def play_alignment(form: dict, play: dict) -> dict:
    """Where the eleven actually line up for this play.

    A formation has one alignment, but a formation is not always one picture. The
    Power I's wingback has two legal spots in the same eleven-man look: tight to the
    end where he is a blocker on the edge, or offset in the backfield where he is a
    lead back. A play may say which, and the call says it out loud —
    `Power I Offset Right 34 Power` — the same way the I's call names the flanker's
    side.

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


def validate_call(play: dict, form: dict) -> list[str]:
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

    spec = play.get("assignments", {}).get(pos, {})
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
        phase = practice.get("phase")
        if phase and phase not in schedule.get("phases", {}):
            errors.append(f"install practice {n}: unknown phase '{phase}'")

    # Everything in the book has to be taught at some point, or the schedule quietly
    # drops a play and nobody notices until a Saturday.
    for pid in sorted(plays - set(installed_at)):
        errors.append(f"install: play '{pid}' is never installed")
    for fid in sorted(fronts - set(installed_at)):
        errors.append(f"install: defensive front '{fid}' is never installed")

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
            if play.get("defense") and play["defense"] not in defenses:
                errors.append(f"{pid}: unknown defense '{play['defense']}'")
            missing = set(form.get("alignment", {})) - set(play.get("assignments", {}))
            if missing:
                errors.append(f"{pid}: no assignment for {', '.join(sorted(missing))}")
            extra = set(play.get("assignments", {})) - set(form.get("alignment", {}))
            if extra:
                errors.append(f"{pid}: assignment for unknown position {', '.join(sorted(extra))}")
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
                errors.extend(validate_call(play, form))
    return errors


# ------------------------------------------------------------------ drawing --


def polyline(points, color, width=2.6, dashed=False):
    d = " ".join(
        ("M" if i == 0 else "L") + f"{fx(p[0]):.1f},{fy(p[1]):.1f}"
        for i, p in enumerate(points)
    )
    dash = ' stroke-dasharray="7 5"' if dashed else ""
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
    out = [
        f'<rect x="{x0:.0f}" y="0" width="{width:.0f}" height="{TITLE_H}" '
        f'fill="{COLORS["band"]}"/>',
        f'<text x="{x0 + PAD:.0f}" y="26" font-size="19" font-weight="700" '
        f'fill="#ffffff">{esc(name)}</text>',
        f'<text x="{x0 + PAD:.0f}" y="45" font-size="11.5" '
        f'fill="#a9b4c7">{esc(meta)}</text>',
    ]
    if call:
        bw = 9.2 * len(call) + 22
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
    r = 0.42 * SCALE
    for label, (x, y) in defense["alignment"].items():
        cx, cy = fx(x), fy(y)
        a = r * 0.62
        out.append(
            f'<line x1="{cx-a:.1f}" y1="{cy-a:.1f}" x2="{cx+a:.1f}" y2="{cy+a:.1f}" '
            f'stroke="{COLORS["defense"]}" stroke-width="3"/>'
            f'<line x1="{cx+a:.1f}" y1="{cy-a:.1f}" x2="{cx-a:.1f}" y2="{cy+a:.1f}" '
            f'stroke="{COLORS["defense"]}" stroke-width="3"/>'
        )
        out.append(
            f'<text x="{cx:.1f}" y="{cy - r - 4:.1f}" text-anchor="middle" font-size="10" '
            f'fill="{COLORS["defense"]}" font-weight="600">{esc(label.strip())}</text>'
        )
    return "\n".join(out)


def draw_paths(play: dict, alignment: dict) -> str:
    out = []
    carrier = play.get("ball_carrier")
    for pos, spec in play["assignments"].items():
        path = spec.get("path")
        if not path:
            continue
        ax, ay = alignment[pos]
        pts = [[ax, ay]] + [[ax + p[0], ay + p[1]] for p in path]
        kind = spec.get("type", "block")
        is_carrier = pos == carrier
        color = COLORS["carrier"] if is_carrier else COLORS["offense"]
        dashed = kind in ("motion", "pass", "fake")
        width = 3.2 if is_carrier else 2.4
        out.append(polyline(pts, color, width=width, dashed=dashed))
        if kind == "block":
            out.append(block_cap(pts[-2], pts[-1], color, width=width))
        else:
            out.append(arrow_head(pts[-2], pts[-1], color))
    return "\n".join(out)


def draw_offense(play: dict, alignment: dict) -> str:
    out = []
    carrier = play.get("ball_carrier")
    for pos, (x, y) in alignment.items():
        cx, cy = fx(x), fy(y)
        fill = COLORS["carrier"] if pos == carrier else COLORS["offense"]
        if pos in LINEMEN:
            s = 0.44 * SCALE
            out.append(
                f'<rect x="{cx-s:.1f}" y="{cy-s:.1f}" width="{2*s:.1f}" height="{2*s:.1f}" '
                f'rx="3" fill="#ffffff" stroke="{fill}" stroke-width="2.4"/>'
            )
        else:
            out.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{0.46*SCALE:.1f}" '
                f'fill="#ffffff" stroke="{fill}" stroke-width="2.4"/>'
            )
        out.append(
            f'<text x="{cx:.1f}" y="{cy+4:.1f}" text-anchor="middle" font-size="11.5" '
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


def render_card(play: dict, defenses: dict, frame: tuple[float, float, float]) -> str:
    form = play["_formation"]
    alignment = play_alignment(form, play)
    defense = defenses.get(play.get("defense", ""))

    # Same frame as the web diagrams, so a card and a diagram of the same play are
    # drawn at the same scale with the formation in the same place.
    fr_half, fr_top, fr_bot = frame
    card_w = (2 * fr_half) * SCALE
    field_h = (fr_top - fr_bot) * SCALE
    off_x, off_y = -fx(-fr_half), -fy(fr_top)

    # Column text width follows the card width instead of assuming the old canvas.
    chars = max(24, int(((card_w - 2 * PAD) / 2 - 34) / 6.5))

    ordered = ordered_positions(play)
    entries = [(pos, wrap(play["assignments"][pos]["rule"], chars)) for pos in ordered]
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
    if defense:
        svg.append(draw_defense(defense))
    svg.append(draw_paths(play, alignment))
    svg.append(draw_offense(play, alignment))
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

DEF_LINEMEN = {"LE", "LT", "LG", "NG", "RG", "RT", "RE"}


def draw_ghost_offense() -> str:
    """The opposition, drawn faintly — on a defensive card they are scenery."""
    out = []
    for pos, (x, y) in GENERIC_OFFENSE.items():
        cx, cy = fx(x), fy(y)
        if pos in LINEMEN:
            s = 0.42 * SCALE
            out.append(
                f'<rect x="{cx-s:.1f}" y="{cy-s:.1f}" width="{2*s:.1f}" height="{2*s:.1f}" '
                f'rx="3" fill="#ffffff" stroke="{COLORS["ghost"]}" stroke-width="2"/>'
            )
        else:
            out.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{0.44*SCALE:.1f}" '
                f'fill="#ffffff" stroke="{COLORS["ghost"]}" stroke-width="2"/>'
            )
    return "\n".join(out)


def draw_defenders(front: dict) -> str:
    """Our defenders: the subject of the card, so they are drawn solid and labelled."""
    out = []
    r = 0.44 * SCALE
    for pos, (x, y) in front["alignment"].items():
        cx, cy = fx(x), fy(y)
        a = r * 0.66
        color = COLORS["offense"]
        out.append(
            f'<line x1="{cx-a:.1f}" y1="{cy-a:.1f}" x2="{cx+a:.1f}" y2="{cy+a:.1f}" '
            f'stroke="{color}" stroke-width="3.4" stroke-linecap="round"/>'
            f'<line x1="{cx+a:.1f}" y1="{cy-a:.1f}" x2="{cx-a:.1f}" y2="{cy+a:.1f}" '
            f'stroke="{color}" stroke-width="3.4" stroke-linecap="round"/>'
        )
        out.append(
            f'<text x="{cx:.1f}" y="{cy - r - 5:.1f}" text-anchor="middle" font-size="11.5" '
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
            defense = defenses.get(play.get("defense", ""))
            if defense:
                xs += [x for x, _ in defense["alignment"].values()]
                ys += [y for _, y in defense["alignment"].values()]
            spots = play_alignment(form, play)
            xs += [x for x, _ in spots.values()]
            ys += [y for _, y in spots.values()]
            for pos, spec in play["assignments"].items():
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


def render_diagram(play: dict, defenses: dict, frame: tuple[float, float, float]) -> str:
    """Diagram only — no assignment text baked in.

    The web page pairs this with real HTML so the words reflow on a phone instead of
    shrinking into an unreadable block. Drawn in the shared frame from
    diagram_frame() so every play in the book lines up with every other one.
    """
    form = play["_formation"]
    defense = defenses.get(play.get("defense", ""))

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
        f'<title>{esc(play["name"])} — {esc(play.get("call", ""))}</title>',
        draw_field(),
    ]
    if defense:
        svg.append(draw_defense(defense))
    alignment = play_alignment(form, play)
    svg.append(draw_paths(play, alignment))
    svg.append(draw_offense(play, alignment))
    svg.append("</svg>")
    return "\n".join(svg)


# ------------------------------------------------------------------ outputs --



def play_section(play: dict, card_rel: str) -> list[str]:
    title = play["name"]
    out = ["---", "", f"## {title}", ""]
    if play.get("call"):
        out += [f"**Call it:** `{play['call']}`", ""]
    out += [f"![{title}]({card_rel})", ""]
    if play.get("purpose"):
        out += [play["purpose"], ""]
    out += ["| Position | Assignment |", "|---|---|"]
    ordered = [x for x in CARD_ORDER if x in play["assignments"]]
    for pos in ordered:
        carrier = " **(ball)**" if pos == play.get("ball_carrier") else ""
        out.append(f"| **{pos}**{carrier} | {play['assignments'][pos]['rule']} |")
    out.append("")
    if play.get("coaching_points"):
        out += ["**Coaching points**", ""]
        out += [f"- {c}" for c in play["coaching_points"]]
        out.append("")
    return out


def write_formation_readme(form: dict) -> str:
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
        out += play_section(p, f"cards/{p['id']}.svg")
    return "\n".join(out) + "\n"


def write_playbook(formations: list[dict]) -> str:
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
            out += play_section(p, f"playbook/{form['id']}/cards/{p['id']}.svg")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Render Sayville 8U play cards from JSON.")
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    args = ap.parse_args()

    defenses = load_defenses()
    formations = load_formations()

    schedule = load_install()
    errors = (validate_defenses(defenses) + validate(formations, defenses)
              + validate_install(schedule, formations, defenses))
    if errors:
        for e in errors:
            print(f"ERROR  {e}", file=sys.stderr)
        return 1

    total = sum(len(f["_plays"]) for f in formations)
    print(f"{total} plays across {len(formations)} formation(s) validated.")
    if args.check:
        return 0

    # One frame for the whole book, so no two diagrams are drawn at different scales.
    frame = diagram_frame(formations, defenses)
    print(f"Diagram frame: {frame[0]*2:.1f} yards wide, {frame[2]:.1f} to {frame[1]:.1f} deep")

    for form in formations:
        cards_dir = form["_dir"] / "cards"
        cards_dir.mkdir(exist_ok=True)
        for p in form["_plays"]:
            (cards_dir / f"{p['id']}.svg").write_text(render_card(p, defenses, frame), encoding="utf-8")
            (cards_dir / f"{p['id']}-field.svg").write_text(
                render_diagram(p, defenses, frame), encoding="utf-8"
            )
        (form["_dir"] / "README.md").write_text(write_formation_readme(form), encoding="utf-8")

    cards = DEFENSE_DIR / "cards"
    cards.mkdir(exist_ok=True)
    for fid, front in defenses.items():
        (cards / f"{fid}-field.svg").write_text(
            render_defense_diagram(front, frame), encoding="utf-8"
        )

    (ROOT / "PLAYBOOK.md").write_text(write_playbook(formations), encoding="utf-8")

    # The site is flat files at the repo root so Pages can serve from "/" and every page
    # can reference the cards in place, with no second copy of any SVG.
    pages = site_build.write_all(formations, defenses, ROOT)

    print(
        f"Wrote {total} cards (+{total} diagrams), {len(defenses)} defensive fronts, "
        f"{len(formations)} formation README(s), PLAYBOOK.md and {pages} site pages"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
