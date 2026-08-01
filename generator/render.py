#!/usr/bin/env python3
"""Sayville 8U play-card generator.

Reads the JSON play files under `playbook/<formation>/plays/` and writes:

    playbook/<formation>/cards/<play-id>.svg   one printable card per play
    playbook/<formation>/README.md             formation index
    playbook/index.html                        every card, print-to-PDF ready
    PLAYBOOK.md                                the whole book, in install order

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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAYBOOK_DIR = ROOT / "playbook"
DEFENSES_DIR = ROOT / "generator" / "defenses"

# ---------------------------------------------------------------- geometry --

SCALE = 27.0            # px per yard
X_MIN, X_MAX = -13.0, 13.0
Y_MIN, Y_MAX = -7.0, 9.5

FIELD_W = (X_MAX - X_MIN) * SCALE
FIELD_H = (Y_MAX - Y_MIN) * SCALE

TITLE_H = 58
PAD = 18
LINE_H = 17

# Which alignment keys are linemen (drawn as squares) vs backs and receivers (circles).
LINEMEN = {"LE", "LT", "LG", "C", "RG", "RT", "RE", "TE"}

# Only used by plays that declare `mirror_of`. A position with no counterpart maps to
# itself, which is only correct when it aligns on the middle of the formation — so
# formations with a one-sided back or receiver author both directions by hand instead.
MIRROR = {
    "LE": "RE", "RE": "LE",
    "LT": "RT", "RT": "LT",
    "LG": "RG", "RG": "LG",
    "LW": "RW", "RW": "LW",
    "LH": "RH", "RH": "LH",
    "C": "C", "QB": "QB", "FB": "FB", "TB": "TB",
}

# Order assignments are listed on the card: line first, then receivers, then backs.
CARD_ORDER = [
    "X", "LE", "LT", "LG", "C", "RG", "RT", "RE", "TE",
    "LW", "RW", "WB", "W", "Z",
    "QB", "BB", "FB", "TB", "HB", "LH", "RH",
]

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
    plays.sort(key=lambda p: (p.get("install_week", 99), p.get("name", ""), p.get("id", "")))
    return plays


def validate(formations: list[dict], defenses: dict) -> list[str]:
    errors = []
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
    return errors


# ------------------------------------------------------------------ drawing --


def esc(text) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


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


def render_card(play: dict, defenses: dict) -> str:
    form = play["_formation"]
    alignment = form["alignment"]
    defense = defenses.get(play.get("defense", ""))

    ordered = [p for p in CARD_ORDER if p in play["assignments"]]
    ordered += [p for p in play["assignments"] if p not in CARD_ORDER]

    entries = [(pos, wrap(play["assignments"][pos]["rule"], 46)) for pos in ordered]
    half = math.ceil(len(entries) / 2)
    columns = [entries[:half], entries[half:]]
    col_lines = max((sum(len(e[1]) for e in col) for col in columns), default=0)

    coach_lines = []
    for c in play.get("coaching_points", []):
        coach_lines.extend(wrap(c, 100))

    assign_h = col_lines * LINE_H + 34
    coach_h = (len(coach_lines) * LINE_H + 40) if coach_lines else 0
    total_h = TITLE_H + FIELD_H + assign_h + coach_h + PAD

    form_label = f"{form['name']} ({form['family']})" if form.get("family") else form["name"]
    meta_bits = [play.get("type", "").upper(), form_label]
    if defense:
        meta_bits.append(f"vs {defense['name']}")
    if play.get("install_week"):
        meta_bits.append(f"Install wk {play['install_week']}")
    meta = "  •  ".join(b for b in meta_bits if b)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{FIELD_W:.0f}" height="{total_h:.0f}" '
        f'viewBox="0 0 {FIELD_W:.0f} {total_h:.0f}" '
        f'font-family="Segoe UI, Helvetica, Arial, sans-serif">',
        f'<rect width="100%" height="100%" fill="{COLORS["card"]}"/>',
        title_band(0, FIELD_W, play["name"], meta, play.get("call", "")),
        f'<g transform="translate(0,{TITLE_H})">',
        draw_field(),
    ]
    if defense:
        svg.append(draw_defense(defense))
    svg.append(draw_paths(play, alignment))
    svg.append(draw_offense(play, alignment))
    svg.append("</g>")

    y0 = TITLE_H + FIELD_H
    svg.append(
        f'<line x1="{PAD}" y1="{y0+10:.0f}" x2="{FIELD_W-PAD:.0f}" y2="{y0+10:.0f}" '
        f'stroke="{COLORS["line"]}" stroke-width="1"/>'
    )
    svg.append(
        f'<text x="{PAD}" y="{y0+30:.0f}" font-size="11" font-weight="700" '
        f'fill="{COLORS["muted"]}" letter-spacing="1">ASSIGNMENTS</text>'
    )

    for ci, col in enumerate(columns):
        x = PAD + ci * (FIELD_W - 2 * PAD) / 2
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
            f'<line x1="{PAD}" y1="{cy-14:.0f}" x2="{FIELD_W-PAD:.0f}" y2="{cy-14:.0f}" '
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


def render_diagram(play: dict, defenses: dict) -> str:
    """Diagram only — no assignment text baked in.

    The web page pairs this with real HTML so the words reflow on a phone instead of
    shrinking into an unreadable block. Cropped tighter than the printable card since
    nothing ever aligns wider than the corners.
    """
    form = play["_formation"]
    defense = defenses.get(play.get("defense", ""))

    # Crop to what this play actually uses. A front with no deep safety would otherwise
    # leave six yards of blank grass at the top, which on a phone is six yards of nothing.
    ys = [y for _, y in form["alignment"].values()]
    if defense:
        ys += [y for _, y in defense["alignment"].values()]
    for pos, spec in play["assignments"].items():
        ay = form["alignment"][pos][1]
        ys += [ay + p[1] for p in spec.get("path", [])]

    y_top = min(Y_MAX, max(ys) + 1.3)
    y_bot = max(Y_MIN, min(ys) - 1.0)

    crop = 1.5 * SCALE
    vb_w = FIELD_W - 2 * crop
    vb_y = fy(y_top)
    vb_h = fy(y_bot) - vb_y

    # No title band here: the page always renders the name and call as real HTML above
    # the diagram, and repeating them inside the image just wastes phone screen.
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{vb_w:.0f}" height="{vb_h:.0f}" '
        f'viewBox="{crop:.0f} {vb_y:.0f} {vb_w:.0f} {vb_h:.0f}" '
        f'font-family="Segoe UI, Helvetica, Arial, sans-serif" role="img">',
        f'<title>{esc(play["name"])} — {esc(play.get("call", ""))}</title>',
        draw_field(),
    ]
    if defense:
        svg.append(draw_defense(defense))
    svg.append(draw_paths(play, form["alignment"]))
    svg.append(draw_offense(play, form["alignment"]))
    svg.append("</svg>")
    return "\n".join(svg)


# ------------------------------------------------------------------ outputs --


def slug(text) -> str:
    return "".join(c for c in str(text).lower().replace(" ", "-") if c.isalnum() or c == "-")


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
    heading = f"{form['name']} — {form['family']}" if form.get("family") else form["name"]
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
    out += ["## Plays", "", "| Play | Call | Type | Ball | Install |", "|---|---|---|---|---|"]
    for p in form["_plays"]:
        title = p["name"]
        out.append(
            f"| [{title}](#{slug(title)}) | `{p.get('call', '')}` | {p.get('type', '')} "
            f"| {p.get('ball_carrier', '—')} | Week {p.get('install_week', '-')} |"
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
        "| # | Play | Call | Type | Formation | Ball | Install |",
        "|---|---|---|---|---|---|---|",
    ]
    n = 0
    for form in formations:
        for p in form["_plays"]:
            n += 1
            title = p["name"]
            out.append(
                f"| {n} | [{title}](#{slug(title)}) | `{p.get('call', '')}` "
                f"| {p.get('type', '')} | {form['name']} "
                f"| {p.get('ball_carrier', '—')} | Week {p.get('install_week', '-')} |"
            )
    out.append("")
    for form in formations:
        label = f"{form['name']} ({form['family']})" if form.get("family") else form["name"]
        out += [f"# {label}", ""]
        for p in form["_plays"]:
            out += play_section(p, f"playbook/{form['id']}/cards/{p['id']}.svg")
    return "\n".join(out) + "\n"


def write_site(formations: list[dict]) -> str:
    """The GitHub Pages site: every play, grouped by formation then install week.

    Pairs the diagram-only SVG with real HTML text so it reflows on a phone, and
    prints landscape with the diagram beside the assignments.
    """
    total = sum(len(f["_plays"]) for f in formations)

    nav = "\n".join(
        f'<a href="#form-{esc(f["id"])}">{esc(f["name"])}</a>' for f in formations
    )

    sections = []
    for form in formations:
        label = f"{form['name']} — {form['family']}" if form.get("family") else form["name"]
        sections.append(
            f'<h2 class="formation" id="form-{esc(form["id"])}">{esc(label)}</h2>'
        )
        if form.get("notes"):
            sections.append(f'<p class="formation-note">{esc(form["notes"])}</p>')

        weeks: dict[int, list] = {}
        for p in form["_plays"]:
            weeks.setdefault(p.get("install_week", 99), []).append(p)

        for w in sorted(weeks):
            sections.append(
                f'<h3 class="week">{esc(f"Week {w}" if w != 99 else "Unscheduled")}</h3>'
            )
            for p in weeks[w]:
                title = p["name"]
                ordered = [x for x in CARD_ORDER if x in p["assignments"]]
                ordered += [x for x in p["assignments"] if x not in CARD_ORDER]
                rows = "\n".join(
                    f'<tr{" class=ball" if pos == p.get("ball_carrier") else ""}>'
                    f"<th>{esc(pos)}</th><td>{esc(p['assignments'][pos]['rule'])}</td></tr>"
                    for pos in ordered
                )
                coaching = ""
                if p.get("coaching_points"):
                    items = "\n".join(f"<li>{esc(c)}</li>" for c in p["coaching_points"])
                    coaching = (
                        f'<div class="coach"><h4>Coaching points</h4><ul>{items}</ul></div>'
                    )
                purpose = (
                    f'<p class="purpose">{esc(p["purpose"])}</p>' if p.get("purpose") else ""
                )
                tags = " ".join(
                    f'<span class="tag">{esc(t)}</span>'
                    for t in (
                        p.get("type", "").upper(),
                        p.get("ball_carrier", ""),
                        f"vs {p['defense']}" if p.get("defense") else "",
                    )
                    if t
                )
                if p.get("call"):
                    tags = f'<span class="call">{esc(p["call"])}</span>' + tags
                sections.append(
                    f'<article id="{esc(p["id"])}">'
                    f"<header><h4>{esc(title)}</h4>"
                    f'<div class="tags">{tags}</div>'
                    f'<button type="button" class="printone" '
                    f"onclick=\"printPlay('{esc(p['id'])}')\" "
                    f'title="Print just this play">Print this play</button>'
                    f"</header>"
                    f'<div class="grid">'
                    f'<div class="diagram"><img loading="lazy" '
                    f'src="playbook/{form["id"]}/cards/{p["id"]}-field.svg" '
                    f'alt="{esc(title)} diagram"></div>'
                    f'<div class="detail">{purpose}'
                    f'<table class="assign"><caption>Assignments</caption><tbody>{rows}'
                    f"</tbody></table></div>"
                    f"</div>{coaching}"
                    "</article>"
                )

    body = "\n".join(sections)
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sayville 8U Tackle Football — 2026 Playbook</title>
<meta name="description" content="Tight double wing playbook for 8U tackle football: {total} plays with diagrams, assignments and coaching points.">
<style>
  :root {{
    --ink: #111318; --muted: #5b6472; --line: #dde1e8;
    --navy: #14213d; --red: #b3001b; --bg: #eef1f5; --panel: #fff;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --ink: #e8ecf3; --muted: #98a2b3; --line: #2a3040; --bg: #10131a; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--ink);
    font: 16px/1.55 "Segoe UI", Helvetica, Arial, sans-serif;
  }}
  .wrap {{ max-width: 940px; margin: 0 auto; padding: 0 20px 64px; }}
  .hero {{ background: var(--navy); color: #fff; padding: 40px 0 30px; margin-bottom: 8px; }}
  .hero .wrap {{ padding-bottom: 0; }}
  .hero h1 {{ margin: 0 0 6px; font-size: clamp(26px, 5vw, 38px); letter-spacing: -.4px; }}
  .hero p {{ margin: 0; color: #a9b4c7; max-width: 62ch; }}
  nav {{
    position: sticky; top: 0; z-index: 5; background: var(--navy);
    border-top: 1px solid rgba(255,255,255,.12); padding: 10px 0;
  }}
  nav .wrap {{ display: flex; gap: 8px; flex-wrap: wrap; padding-bottom: 0; }}
  nav a {{
    color: #cdd6e6; text-decoration: none; font-size: 14px; font-weight: 600;
    padding: 5px 12px; border-radius: 999px; background: rgba(255,255,255,.09);
  }}
  nav a:hover {{ background: rgba(255,255,255,.2); color: #fff; }}
  nav .print {{
    margin-left: auto; cursor: pointer; font: inherit; font-size: 14px;
    font-weight: 600; color: var(--navy); background: #fff; border: 0;
    padding: 5px 14px; border-radius: 999px;
  }}
  nav .print:hover {{ background: #dfe6f2; }}
  h2.formation {{
    font-size: clamp(20px, 4vw, 26px); color: var(--ink);
    margin: 40px 0 4px; letter-spacing: -.3px;
  }}
  .formation-note {{ margin: 0 0 8px; color: var(--muted); max-width: 68ch; }}
  h3.week {{
    font-size: 13px; text-transform: uppercase; letter-spacing: 1.4px;
    color: var(--muted); margin: 28px 0 12px; padding-bottom: 8px;
    border-bottom: 1px solid var(--line);
  }}
  article {{
    background: var(--panel); color: #111318; border-radius: 10px;
    box-shadow: 0 1px 3px rgba(16,20,30,.16); margin: 0 0 18px; padding: 16px;
    /* Clears the sticky nav, which wraps to two rows on a phone. */
    scroll-margin-top: 112px;
  }}
  article header {{
    display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap;
    border-bottom: 2px solid var(--navy); padding-bottom: 9px; margin-bottom: 12px;
  }}
  article h4 {{ margin: 0; font-size: clamp(18px, 3.6vw, 21px); color: var(--navy); }}
  .tags {{ display: flex; gap: 6px; flex-wrap: wrap; }}
  .tag {{
    font-size: 11px; font-weight: 700; letter-spacing: .6px; color: #5b6472;
    background: #eef1f5; border-radius: 4px; padding: 3px 7px;
  }}
  .call {{
    font-size: 12.5px; font-weight: 700; letter-spacing: .5px; color: #fff;
    background: var(--navy); border-radius: 4px; padding: 3px 9px;
  }}
  .printone {{
    margin-left: auto; cursor: pointer; font: inherit; font-size: 12.5px;
    font-weight: 600; color: #5b6472; background: #eef1f5; border: 1px solid #dde1e8;
    border-radius: 999px; padding: 4px 12px; white-space: nowrap;
  }}
  .printone:hover {{ background: var(--navy); border-color: var(--navy); color: #fff; }}
  .grid {{ display: grid; gap: 4px 24px; }}
  .diagram {{ min-width: 0; }}
  .purpose {{ margin: 0 0 12px; color: #3d4553; }}
  article img {{ display: block; width: 100%; height: auto; }}
  table.assign {{ width: 100%; border-collapse: collapse; }}
  table.assign caption, .coach h4 {{
    text-align: left; font-size: 11px; font-weight: 700; letter-spacing: 1.2px;
    text-transform: uppercase; color: #5b6472; padding: 12px 0 4px; margin: 0;
  }}
  table.assign th, table.assign td {{
    text-align: left; vertical-align: top; padding: 7px 8px 7px 0;
    border-top: 1px solid #eceff4; font-size: 15px; color: #111318;
  }}
  table.assign th {{ width: 42px; font-weight: 700; }}
  tr.ball th, tr.ball td {{ color: var(--red); font-weight: 600; }}
  .coach h4 {{ padding-top: 14px; }}
  .coach ul {{ margin: 0; padding-left: 20px; }}
  .coach li {{ margin-bottom: 5px; color: #3d4553; }}
  footer {{ color: var(--muted); font-size: 14px; margin-top: 48px; }}
  footer code {{ background: rgba(127,127,127,.15); padding: 1px 5px; border-radius: 3px; }}

  /* Phone first — the diagram sits above the words. Side by side once there is room. */
  @media (min-width: 760px) {{
    article {{ padding: 20px; scroll-margin-top: 70px; }}
    .grid {{ grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr); }}
  }}

  /* One play per landscape sheet. Everything below is sized so a card with the longest
     assignment list and five coaching points still fits on a single page. */
  @page {{ size: landscape; margin: 9mm; }}
  @media print {{
    :root {{ --ink: #111318; --muted: #5b6472; --line: #dde1e8; }}
    body {{ background: #fff; font-size: 10pt; }}
    .hero, nav, footer, h2.formation, h3.week, .formation-note,
    .printone {{ display: none; }}
    /* "Print this play" sets .print-one on <html> and marks one card, so the same
       stylesheet prints either the whole book or a single sheet. */
    html.print-one article {{ display: none; }}
    html.print-one article.print-target {{
      display: block; page-break-after: auto; break-after: auto;
    }}
    .wrap {{ max-width: none; padding: 0; }}
    article {{
      box-shadow: none; border-radius: 0; padding: 0; margin: 0;
      page-break-after: always; break-after: page; page-break-inside: avoid;
    }}
    article:last-child {{ page-break-after: auto; break-after: auto; }}
    article header {{ padding-bottom: 5px; margin-bottom: 8px; }}
    article h4 {{ font-size: 16pt; }}
    .tag, .call {{ font-size: 8.5pt; padding: 2px 6px; }}
    /* Diagram on the left, everything a coach reads on the right. */
    .grid {{ grid-template-columns: 1.02fr 1fr; gap: 0 14px; }}
    .diagram {{ align-self: start; }}
    article img {{ max-height: 96mm; width: auto; max-width: 100%; }}
    .purpose {{ font-size: 8.5pt; margin-bottom: 6px; }}
    table.assign caption, .coach h4 {{ font-size: 8pt; padding: 4px 0 2px; }}
    table.assign th, table.assign td {{ font-size: 8.5pt; padding: 1.5px 6px 1.5px 0; }}
    .coach {{ grid-column: 1 / -1; }}
    .coach ul {{ column-count: 2; column-gap: 16px; }}
    .coach li {{ font-size: 8pt; margin-bottom: 1px; break-inside: avoid; }}
    a[href]::after {{ content: ""; }}
  }}
</style>
<div class="hero"><div class="wrap">
  <h1>Sayville 8U Tackle Football</h1>
  <p>2026 season playbook — {total} plays, in the order we install them. Every diagram
     is generated from the play files in this repo, so what is on this page is exactly
     what is in the binder.</p>
</div></div>
<nav><div class="wrap">{nav}
  <button type="button" class="print" onclick="window.print()">Print playbook</button>
</div></nav>
<div class="wrap">
{body}
<footer>
  <p>Generated by <code>generator/render.py</code>. <strong>Print playbook</strong> gives
  you the whole book in landscape, one play per sheet; <strong>Print this play</strong> on
  any card gives you just that sheet.</p>
</footer>
</div>
<script>
function printPlay(id) {{
  var el = document.getElementById(id);
  if (!el) return;
  document.documentElement.classList.add('print-one');
  el.classList.add('print-target');
  window.print();
}}
function clearPrintOne() {{
  document.documentElement.classList.remove('print-one');
  var t = document.querySelector('.print-target');
  if (t) t.classList.remove('print-target');
}}
// afterprint is not reliable everywhere, so undo on the media change too.
window.addEventListener('afterprint', clearPrintOne);
if (window.matchMedia) {{
  var mq = window.matchMedia('print');
  var onChange = function (e) {{ if (!e.matches) clearPrintOne(); }};
  if (mq.addEventListener) mq.addEventListener('change', onChange);
  else if (mq.addListener) mq.addListener(onChange);
}}
</script>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Render Sayville 8U play cards from JSON.")
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    args = ap.parse_args()

    defenses = {p.stem: load_json(p) for p in sorted(DEFENSES_DIR.glob("*.json"))}
    formations = load_formations()

    errors = validate(formations, defenses)
    if errors:
        for e in errors:
            print(f"ERROR  {e}", file=sys.stderr)
        return 1

    total = sum(len(f["_plays"]) for f in formations)
    print(f"{total} plays across {len(formations)} formation(s) validated.")
    if args.check:
        return 0

    for form in formations:
        cards_dir = form["_dir"] / "cards"
        cards_dir.mkdir(exist_ok=True)
        for p in form["_plays"]:
            (cards_dir / f"{p['id']}.svg").write_text(render_card(p, defenses), encoding="utf-8")
            (cards_dir / f"{p['id']}-field.svg").write_text(
                render_diagram(p, defenses), encoding="utf-8"
            )
        (form["_dir"] / "README.md").write_text(write_formation_readme(form), encoding="utf-8")

    # index.html lives at the repo root so GitHub Pages can serve from "/" and reference
    # the cards in place instead of keeping a second copy of every SVG.
    (ROOT / "index.html").write_text(write_site(formations), encoding="utf-8")
    (ROOT / "PLAYBOOK.md").write_text(write_playbook(formations), encoding="utf-8")

    print(
        f"Wrote {total} cards (+{total} diagrams), {len(formations)} formation "
        "README(s), index.html and PLAYBOOK.md"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
