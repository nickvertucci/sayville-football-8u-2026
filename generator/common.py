"""Bits shared by the diagram renderer and the site builder.

Kept in one place so the two cannot drift — in particular CARD_ORDER, which decides
the order assignments are read in on a printed card and on the website.
"""

from __future__ import annotations

# Order assignments are listed: line first, then receivers, then backs.
CARD_ORDER = [
    "X", "LE", "LT", "LG", "C", "RG", "RT", "RE", "TE",
    "LW", "RW", "WB", "W", "Z",
    "QB", "BB", "FB", "TB", "HB", "LH", "RH",
]

# What a position key is called in prose. Only used for headings and the calling-
# language table — assignment text never names a position, see playbook/CLAUDE.md.
POSITION_NAMES = {
    "X": "Split end", "TE": "Tight end", "Z": "Flanker",
    "LE": "Left end", "RE": "Right end",
    "LT": "Left tackle", "RT": "Right tackle",
    "LG": "Left guard", "RG": "Right guard", "C": "Center",
    "LW": "Left wing", "RW": "Right wing", "WB": "Wingback", "W": "Wingback",
    "QB": "Quarterback", "BB": "Blocking back", "FB": "Fullback",
    "TB": "Tailback", "HB": "Halfback",
    "LH": "Left halfback", "RH": "Right halfback",
}


def position_name(key: str) -> str:
    return POSITION_NAMES.get(key, key)


def esc(text) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def slug(text) -> str:
    return "".join(c for c in str(text).lower().replace(" ", "-") if c.isalnum() or c == "-")


def form_label(form: dict) -> str:
    """What a formation is called in the UI.

    `name` is the short internal handle and is a poor heading on its own — the
    I-formation's is the single letter "I", which renders as a stray tick. The family
    ("I-Formation", "Wishbone") is what a human should read.
    """
    return form.get("family") or form["name"]


def call_prefix(form: dict) -> str:
    """The first word of this formation's calls, e.g. "I" or "Bone"."""
    for play in form.get("_plays", []):
        call = play.get("call", "")
        if call:
            return call.split()[0]
    return form["name"]


def ordered_positions(play: dict) -> list[str]:
    """Assignment keys in reading order, with anything unexpected kept at the end."""
    ordered = [p for p in CARD_ORDER if p in play["assignments"]]
    ordered += [p for p in play["assignments"] if p not in CARD_ORDER]
    return ordered
