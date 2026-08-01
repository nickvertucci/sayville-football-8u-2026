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


def ordered_positions(play: dict) -> list[str]:
    """Assignment keys in reading order, with anything unexpected kept at the end."""
    ordered = [p for p in CARD_ORDER if p in play["assignments"]]
    ordered += [p for p in play["assignments"] if p not in CARD_ORDER]
    return ordered
