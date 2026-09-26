"""Bits shared by the diagram renderer and the site builder.

Kept in one place so the two cannot drift — in particular CARD_ORDER, which decides
the order assignments are read in on a printed card and on the website.
"""

from __future__ import annotations

import re

# Order assignments are listed: line first, then receivers, then backs.
#
# X, Y and Z are the ends and the slot: the left end is the X, the right end is the
# Y, the split man is the Z. One letter a boy answers to, rather than LTE, RTE and SL
# -- three abbreviations of three different things that all had to be decoded first.
# The X key used to mean a split end nothing in this book has ever had; it means the
# left end now.
CARD_ORDER = [
    "X", "LT", "LG", "C", "RG", "RT", "Y", "TE",
    "LW", "RW", "WB", "W", "Z",
    "QB", "BB", "FB", "TB", "HB", "LH", "RH",
]

# What a position key is called in prose. Only used for headings and the calling-
# language table — assignment text never names a position, see playbook/CLAUDE.md.
POSITION_NAMES = {
    "TE": "Tight end", "Z": "Slot",
    "X": "Left tight end", "Y": "Right tight end",
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

    `family` is the heading a human reads ("I Formation", "Split Formation"); `name` is the
    handle. They are the same string on every formation we carry today, and the split
    is kept because a one-word `name` is what a call would ever shorten to if the
    heading grew longer than a huddle call should be.
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
