"""Builds the multi-page playbook website.

Structure — flat files at the repo root so every page can use the same relative paths
to the card SVGs, and so GitHub Pages can serve from "/" with no build step:

    index.html          home: formations, install plan, the calling language
    calls.html          the call sheet — every play, searchable, the fastest way in
    f-<formation>.html  one formation: its notes and its plays
    p-<play>.html       one play, deep-linkable, prints to a single landscape sheet
    rules.html          the league rulebook, verbatim, from rulebook/*.txt
    print.html          the whole playbook, one play diagram per landscape sheet
    assets/site.css     one stylesheet for all of it
    assets/site.js      play switcher, arrow-key paging, call sheet filtering

On every page the diagram is the main attraction: full width of its card, with the
assignments read underneath it rather than squeezed into a column beside it.
"""

from __future__ import annotations

import calendar
import hashlib
import json
import re

import blocking
from datetime import date as _date
from pathlib import Path

from common import (CARD_ORDER, call_prefix, esc, form_label,
                    ordered_positions, position_name)

SITE_TITLE = "Sayville 8U Tackle Football"

# The attribute that marks the current page in a nav strip. Kept as a constant so the
# f-strings that build those strips need no escaped quotes inside the {…} — Python only
# allowed backslashes there from 3.12, and this generator should run on 3.11 too.
ACTIVE_ATTR = ' class="active"'

# Same Print control on every page a coach might take off a screen. Hidden by the
# print stylesheet, so it never lands on the paper.
PRINT_BTN = (
    '<div class="play-actions">'
    '<button type="button" class="btn solid" onclick="window.print()">Print</button>'
    "</div>"
)


def page_head(title: str) -> str:
    """Page title with a Print button on the right."""
    return f'<div class="page-head"><h1 class="page">{esc(title)}</h1>{PRINT_BTN}</div>'

# The league's own document, and the verbatim text pulled out of it by
# generator/extract_rulebook.py. Both live in rulebook/.
RULEBOOK_DOCX = "2025-PAL-RULE-BOOK-updated-2025-10-05.docx"
RULEBOOK_TXT = "2025-PAL-RULE-BOOK.txt"

# --------------------------------------------------------------------------- css --

SITE_CSS = """
/* Every color goes through a token so dark mode is one block of overrides rather
   than forty hardcoded values that quietly stay light. */
:root {
  --bg: #eceff4;
  --panel: #ffffff;
  --panel-2: #f4f6fa;
  --ink: #111318;
  --ink-2: #333b49;
  --muted: #5b6472;
  --line: #e2e6ee;
  --line-soft: #eef1f6;
  --accent: #14213d;
  --accent-ink: #14213d;
  --accent-solid: #14213d;
  --accent-soft: #dde5f5;
  --on-accent: #ffffff;
  --red: #b3001b;
  --bar: #14213d;
  --bar-2: #1d3059;
  --on-bar: #cdd8ea;
  --on-bar-soft: #9db0d0;
  --bar-line: rgba(255,255,255,.10);
  --shadow: 0 1px 3px rgba(16,20,30,.14);
  --shadow-lg: 0 10px 30px rgba(8,12,22,.20);
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0d1017;
    --panel: #171b24;
    --panel-2: #212734;
    --ink: #e9edf4;
    --ink-2: #c6cdd9;
    --muted: #949dae;
    --line: #2a3140;
    --line-soft: #232935;
    --accent: #9db6e8;
    --accent-ink: #b9cbf1;
    --accent-solid: #2f4372;
    --accent-soft: #26314a;
    --on-accent: #ffffff;
    --red: #ff7183;
    --bar: #10141d;
    --bar-2: #171c28;
    --on-bar: #c9d3e6;
    --on-bar-soft: #8e9bb5;
    --bar-line: #232936;
    --shadow: 0 1px 3px rgba(0,0,0,.5);
    --shadow-lg: 0 14px 38px rgba(0,0,0,.6);
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font: 16px/1.55 "Segoe UI", system-ui, -apple-system, Helvetica, Arial, sans-serif;
}
a { color: inherit; }
.wrap { max-width: 1040px; margin: 0 auto; padding: 0 16px; }

/* ---------------------------------------------------------------- navigation --
   One slim bar. Desktop gets inline links with a Plays dropdown; phones get a
   hamburger and a slide-in drawer. No stacked rows of pills. */
.skip {
  position: absolute; left: -9999px; top: 0; z-index: 100; background: var(--panel);
  color: var(--ink); padding: 10px 16px; border-radius: 0 0 8px 0;
}
.skip:focus { left: 0; }

header.site {
  position: sticky; top: 0; z-index: 50; background: var(--bar); color: #fff;
  border-bottom: 1px solid var(--bar-line);
}
header.site > .wrap {
  display: flex; align-items: center; gap: 16px; height: 58px;
}
.brand {
  font-size: 17px; font-weight: 700; letter-spacing: -.2px; color: #fff;
  text-decoration: none; white-space: nowrap; margin-right: auto;
}
.brand b { font-weight: 400; color: var(--on-bar-soft); }

nav.desk { display: none; align-items: center; gap: 2px; height: 100%; }
.lnk {
  display: inline-flex; align-items: center; height: 100%; padding: 0 14px;
  font: inherit; font-size: 14.5px; font-weight: 500; color: var(--on-bar);
  text-decoration: none; background: none; border: 0; cursor: pointer;
  border-bottom: 2px solid transparent;
}
.lnk:hover { color: #fff; }
.lnk.active { color: #fff; border-bottom-color: var(--on-accent); font-weight: 600; }
.lnk.drop::after {
  content: ""; margin-left: 7px; width: 5px; height: 5px; border-right: 1.6px solid;
  border-bottom: 1.6px solid; transform: rotate(45deg) translate(-2px, -2px);
  transition: transform .18s;
}
.lnk.drop[aria-expanded="true"]::after { transform: rotate(-135deg) translate(-1px, -1px); }

.burger {
  width: 42px; height: 42px; margin-right: -8px; padding: 0; border: 0; cursor: pointer;
  background: none; position: relative; border-radius: 8px;
}
.burger:hover { background: rgba(255,255,255,.1); }
.burger span, .burger span::before, .burger span::after {
  position: absolute; left: 11px; width: 20px; height: 2px; border-radius: 2px;
  background: #fff; transition: transform .2s, opacity .15s;
}
.burger span { top: 20px; }
.burger span::before { content: ""; top: -6px; left: 0; }
.burger span::after { content: ""; top: 6px; left: 0; }
.burger[aria-expanded="true"] span { background: transparent; }
.burger[aria-expanded="true"] span::before { transform: translateY(6px) rotate(45deg); }
.burger[aria-expanded="true"] span::after { transform: translateY(-6px) rotate(-45deg); }

@media (min-width: 1000px) {
  nav.desk { display: flex; }
  .burger { display: none; }
}

/* Desktop dropdown: a full-width panel under the bar, like a normal site menu. */
.ddpanel {
  position: absolute; left: 0; right: 0; top: 100%; background: var(--panel);
  border-bottom: 1px solid var(--line); box-shadow: var(--shadow-lg);
}
.ddpanel[hidden] { display: none; }
.ddinner {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 26px; padding: 22px 0 26px;
}
.ddinner.one { grid-template-columns: minmax(0, 460px); }

/* Mobile drawer */
.scrim {
  position: fixed; inset: 0; z-index: 60; background: rgba(6,9,15,.55);
  backdrop-filter: blur(2px);
}
.scrim[hidden] { display: none; }
.drawer {
  position: fixed; top: 0; right: 0; bottom: 0; z-index: 70;
  width: min(360px, 88vw); background: var(--panel); color: var(--ink);
  border-left: 1px solid var(--line); box-shadow: var(--shadow-lg);
  overflow-y: auto; -webkit-overflow-scrolling: touch;
  transform: translateX(100%); transition: transform .22s ease;
}
.drawer[hidden] { display: block; }
.drawer.open { transform: translateX(0); }
@media (prefers-reduced-motion: reduce) { .drawer { transition: none; } }
.dtop {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 18px 12px; border-bottom: 1px solid var(--line);
  font-size: 11.5px; font-weight: 700; letter-spacing: 1.4px;
  text-transform: uppercase; color: var(--muted);
}
.dclose {
  border: 0; background: none; color: var(--ink); font-size: 26px; line-height: 1;
  cursor: pointer; padding: 0 4px; border-radius: 6px;
}
.dclose:hover { background: var(--panel-2); }
.dnav { padding: 8px 10px 34px; }
.dsec {
  margin: 18px 12px 2px; font-size: 11px; font-weight: 700; letter-spacing: 1.4px;
  text-transform: uppercase; color: var(--accent-ink);
}
.dlnk {
  display: block; padding: 12px 12px; font-size: 16px; font-weight: 600;
  color: var(--ink); text-decoration: none; border-radius: 9px;
}
.dlnk:hover { background: var(--panel-2); }
.dlnk.active { color: var(--accent-ink); background: var(--panel-2); }

/* Formation + play groups, shared by the dropdown and the drawer */
.mgrp { margin-top: 14px; }
.dnav .mgrp { padding: 0 2px; }
.mgh {
  display: flex; align-items: baseline; gap: 10px; text-decoration: none;
  padding: 8px 10px; margin-bottom: 2px; border-radius: 8px;
  font-size: 12px; font-weight: 700; letter-spacing: 1.3px; text-transform: uppercase;
  color: var(--muted); border-bottom: 1px solid var(--line);
}
.mgh:hover { color: var(--accent-ink); }
.mgh.active { color: var(--accent-ink); }
.mgn {
  margin-left: auto; font-size: 11px; font-weight: 600; letter-spacing: 0;
  text-transform: none; color: var(--muted);
}
.mplays { display: flex; flex-direction: column; }
.mplay {
  display: flex; align-items: center; gap: 10px; text-decoration: none;
  padding: 9px 10px; border-radius: 8px; color: var(--ink);
}
.mplay:hover { background: var(--panel-2); }
.mplay span { flex: 1 1 auto; font-size: 15px; font-weight: 500; }
.mplay em {
  font-style: normal; font-size: 11px; font-weight: 700; color: var(--muted);
  background: var(--panel-2); border-radius: 4px; padding: 2px 7px; white-space: nowrap;
}
.mplay.here { background: var(--accent-solid); }
.mplay.here span { color: var(--on-accent); font-weight: 600; }
.mplay.here em { background: rgba(255,255,255,.2); color: #fff; }

body.locked { overflow: hidden; }

/* -------------------------------------------------- play page navigation -- */
.crumbs {
  display: flex; gap: 7px; flex-wrap: wrap; align-items: baseline;
  font-size: 13px; color: var(--muted); margin: 16px 0 10px;
}
.crumbs a { color: var(--muted); text-decoration: none; }
.crumbs a:hover { color: var(--ink); text-decoration: underline; }
.crumbs b { color: var(--ink); font-weight: 600; }
.crumbs span { opacity: .5; }

.playbar {
  display: flex; gap: 6px; overflow-x: auto; -webkit-overflow-scrolling: touch;
  white-space: nowrap; padding-bottom: 10px; margin-bottom: 4px;
}
.playbar a {
  font-size: 13px; font-weight: 600; text-decoration: none; color: var(--ink-2);
  background: var(--panel); border: 1px solid var(--line); border-radius: 999px;
  padding: 6px 13px;
}
.playbar a:hover { border-color: var(--accent); color: var(--accent-ink); }
.playbar a.active {
  background: var(--accent-solid); border-color: var(--accent-solid); color: var(--on-accent);
}

main { padding-bottom: 56px; }
h1.page { font-size: clamp(23px, 5vw, 33px); letter-spacing: -.5px; margin: 22px 0 6px; }
.page-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; flex-wrap: wrap; margin: 22px 0 6px;
}
.page-head h1.page { margin: 0; }
.rb-hero .page-head { margin: 0 0 10px; }
.lede { color: var(--ink-2); max-width: 68ch; margin: 0 0 8px; }
.sub { color: var(--muted); font-size: 14px; margin: 0 0 20px; }
.section-head {
  font-size: 11.5px; text-transform: uppercase; letter-spacing: 1.4px; color: var(--muted);
  margin: 30px 0 12px; padding-bottom: 7px; border-bottom: 1px solid var(--line);
}
.hero-head {
  display: inline-block; font-size: clamp(22px, 4.6vw, 32px); font-weight: 800;
  letter-spacing: -.4px; color: var(--on-accent); background: var(--accent-solid);
  padding: 9px 22px; border-radius: 10px; margin: 34px 0 16px;
}

/* -------------------------------------------------------------------- pieces -- */
.callout {
  background: var(--panel); border: 1px solid var(--line); border-left: 4px solid var(--red);
  border-radius: 10px; padding: 14px 16px; margin: 18px 0; color: var(--ink-2);
  box-shadow: var(--shadow);
}
.callout strong { color: var(--ink); }
.callout p { margin: 0 0 8px; }
.callout p:last-child { margin: 0; }
.callout a { color: var(--accent-ink); }

.cards { display: grid; gap: 12px; grid-template-columns: 1fr; }
@media (min-width: 680px) { .cards { grid-template-columns: repeat(2, minmax(0,1fr)); } }
.fcard {
  display: block; text-decoration: none; color: var(--ink); background: var(--panel);
  border: 1px solid var(--line); border-radius: 12px; padding: 16px 17px;
  box-shadow: var(--shadow); transition: box-shadow .15s, transform .15s, border-color .15s;
}
.fcard:hover {
  box-shadow: var(--shadow-lg); transform: translateY(-2px); border-color: var(--accent);
}
.ftop { display: flex; align-items: baseline; gap: 10px; }
.fcard h3 { margin: 0; font-size: 20px; color: var(--accent-ink); flex: 1 1 auto; }
.fcard .n {
  font-size: 11.5px; font-weight: 700; letter-spacing: .5px; color: var(--muted);
  background: var(--panel-2); border-radius: 999px; padding: 3px 10px; white-space: nowrap;
}
.fcard p { margin: 9px 0 0; font-size: 14.5px; color: var(--ink-2); }
.fcard .fcall {
  display: inline-block; margin-top: 11px; font-size: 12.5px; color: var(--muted);
}
.fcard .fcall code {
  font-weight: 700; color: var(--on-accent); background: var(--accent-solid);
  border-radius: 4px; padding: 2px 7px; font-family: inherit;
}

/* Formation and defense cards on the home page carry an image, so the padding
   moves off the anchor and onto .body — plain .fcard (no thumb, e.g. defense.html)
   is untouched. */
.fcard.imgcard { padding: 0; overflow: hidden; }
.fcard.imgcard .thumb {
  display: flex; align-items: center; justify-content: center; height: 130px;
  background: #fff; border-bottom: 1px solid var(--line); padding: 10px 14px;
}
.fcard.imgcard .thumb img {
  display: block; width: auto; height: auto; max-width: 100%; max-height: 100%;
}
.fcard.imgcard .body { padding: 14px 17px 16px; }

.icon { width: 20px; height: 20px; flex: none; }
.quicklinks { display: flex; gap: 10px; margin: 4px 0 8px; }
.qlink {
  display: flex; align-items: center; justify-content: center; gap: 8px; flex: 1 1 0;
  text-decoration: none; color: var(--ink);
  background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
  padding: 12px 16px; font-size: 15px; font-weight: 600; box-shadow: var(--shadow);
  transition: box-shadow .15s, transform .15s, border-color .15s;
}
.qlink:hover {
  border-color: var(--accent); transform: translateY(-1px); box-shadow: var(--shadow-lg);
}
.qlink .icon { color: var(--accent-ink); }

.numgrid { display: grid; gap: 16px; grid-template-columns: 1fr; margin-bottom: 8px; }
@media (min-width: 680px) { .numgrid { grid-template-columns: repeat(2, minmax(0,1fr)); } }
.numcap {
  margin: 0 0 8px; font-size: 12.5px; font-weight: 700; color: var(--muted);
  text-transform: uppercase; letter-spacing: .4px;
}

/* Depth chart: positions down the left, numbered depth across the top — the shape
   of an NFL team's published chart. A real <table> so it reads as a grid. Names are
   hard values from roster.json; there is nothing to pick up. */
/* The board is the formation. Each band is a row of the field and each card is a
   spot, so the left guard is between the centre and the left tackle on the page the
   way he is on the grass. Bands are flex rather than a grid because the rows are
   different widths on purpose -- seven across the line, three in the backfield --
   and a shared grid would either stretch the backfield or squeeze the line. */
.dc-field { margin: 10px 0 4px; display: flex; flex-direction: column; gap: 8px; }
.dc-band {
  display: grid; grid-template-columns: repeat(var(--dc-cols, 7), minmax(0, 1fr));
  align-items: start; gap: 6px;
}
/* The leftover rows are a list, not a place on the field, so they go back to being
   a row of cards rather than being dropped into columns that mean nothing to them. */
.dc-band-alt {
  display: flex; flex-wrap: wrap; justify-content: center;
  margin-top: 4px; padding-top: 8px; border-top: 1px dashed var(--line);
}
.dc-band-h {
  flex: 1 0 100%; margin: 0 0 2px; text-align: center;
  font-size: 10px; font-weight: 800; letter-spacing: 1px;
  text-transform: uppercase; color: var(--muted);
}
.dc-pos {
  min-width: 0;
  background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
  box-shadow: var(--shadow); overflow: hidden;
}
.dc-band-alt .dc-pos { flex: 0 1 132px; }
/* A card straddling two columns is still one card wide -- it is centred on the seam
   between them rather than stretched across both. Half the pair less half the gap is
   exactly one column. */
.dc-pos.dc-straddle { justify-self: center; width: calc(50% - 3px); }
/* The spot on a black bar, the way it is on a real chart: it is the thing you scan
   for, and on a page of names it has to not be another name. Black rather than the
   site navy, and literal rather than a variable, because the bar wants maximum
   contrast against the names under it in both themes -- the navy is close enough to
   the dark theme's own panel that the bars stopped reading as bars. */
.dc-pos-h {
  margin: 0; padding: 3px 6px; text-align: center;
  background: #000; color: #fff;
}
/* `color: inherit` is doing real work on both of these, not tidying up. There are
   plain `.dc-abbr` and `.dc-label` rules further down the sheet that colour them for
   the defensive front pages, and a direct declaration beats an inherited one however
   specific the parent is -- so the white set on the bar never reached the text and
   the spot came out navy-on-black. Inheriting is what makes the bar's colour the
   text's colour here and in print, where the bar is forced white on black. */
.dc-pos-h .dc-abbr {
  display: block; color: inherit;
  font-size: 14px; font-weight: 900; letter-spacing: .8px;
}
.dc-pos-h .dc-label {
  display: block; color: inherit;
  font-size: 8.5px; font-weight: 700; letter-spacing: .3px;
  text-transform: uppercase; opacity: .78; line-height: 1.25;
}
.dc-names { margin: 0; padding: 2px 0; list-style: none; }
.dc-names li {
  display: flex; align-items: baseline; gap: 3px;
  padding: 1px 6px; font-size: 12px; font-weight: 600; color: var(--ink-2);
}
/* The rank has to be printed now that depth runs down the card instead of across a
   row of numbered columns -- otherwise the third string is just the third line. */
.dc-names li b {
  flex: 0 0 11px; font-size: 9px; font-weight: 800; color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.dc-names li.starter { font-size: 13.5px; font-weight: 800; color: var(--ink); }
.dc-names li.starter b { color: var(--accent-solid); }
.dc-names li:nth-child(even) { background: var(--panel-2); }
.dc-gap { color: var(--muted); }
.dc-open {
  margin: 0; padding: 4px 6px; font-size: 11px; font-style: italic; color: var(--muted);
}

.dc-pkgs { margin: 14px 0 0; }
.dc-pkgrow {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px; padding-bottom: 2px;
}
@media (max-width: 620px) { .dc-pkgrow { grid-template-columns: 1fr; } }
/* The rotations: position cards in a row, left to right in the order the file
   lists them, each no wider than a card on the board above. */
.dc-rotrow {
  display: grid; gap: 8px; justify-content: start;
  grid-template-columns: repeat(auto-fill, minmax(150px, 190px));
}
/* A rule across the sheet parts the rotations from the board above, and the cards
   are set a size up from a position card: five of them under a board that stops
   well short of the foot of the page had the room to spend. */
.dc-rots { border-top: 2px solid var(--ink); padding-top: 4px; }
.dc-rot .dc-pos-h .dc-abbr { font-size: 20px; }
.dc-rot .dc-names li { font-size: 20px; padding: 3px 8px; gap: 6px; }
.dc-rot .dc-names li b { flex-basis: 16px; font-size: 14px; }
.dc-rot .dc-names li.starter { font-size: 22px; }
.dc-pkg {
  display: flex; gap: 8px; align-items: flex-start;
  background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
  padding: 6px 8px; box-shadow: var(--shadow); min-width: 0;
}
.dc-pkg-body { flex: 1 1 auto; min-width: 0; }
/* The package name gets the same black bar as a position, for the same reason: it
   is the thing you scan a page of packages for, and grey small caps made it the
   quietest thing in its own box. Full width of the body so it reads as the box's
   heading and not as a first row. */
.dc-pkg-h {
  margin: -6px -8px 5px; padding: 3px 8px;
  font-size: 13.5px; font-weight: 800; letter-spacing: 1.1px;
  text-transform: uppercase; background: #000; color: #fff;
}
/* min-width stays at 168: it is what the offense's three-across cards can spare, and
   raising it for the defence's longer labels squeezed the offense body until "Brogan
   A." wrapped. The defence gets its room from being two across instead, so 54% of a
   wider card clears the cap rather than the floor. */
.dc-subcard {
  flex: 0 0 56%; min-width: 168px; max-width: 272px;
  border: 1px solid var(--line); border-radius: 8px; padding: 5px 7px;
  background: var(--panel-2); align-self: start;
}
.dc-subcard-h {
  margin: 0 0 4px; font-size: 12.5px; font-weight: 800; letter-spacing: 1.1px;
  text-transform: uppercase; color: var(--muted);
}
.dc-sub-empty {
  margin: 0; font-size: 12px; font-weight: 700; color: var(--ink-2);
}
table.dc-sub {
  width: 100%; border-collapse: collapse;
  font-size: 13px; line-height: 1.3;
}
/* Four points of gutter, not seven. The cells are nowrap, so a row too wide for the
   card does not wrap or shrink -- it runs out under the card's edge, which is what
   "Thomas D. (TB)" has been doing in Maverick and "Liam M. (TB)" in Bigshow. Three
   points either side of the rule is the cheapest fourteen the card can give back. */
/* The cell wraps, the pieces in it do not. A row is a name, or a name and the spot
   it plays, and the longest of them -- "Brogan A." against "Brooks A. (RILB)" -- is
   wider than the card whatever the card is given: the slot list beside it is already
   at its natural 99 points of a 245-point card, so there are only ever about 132
   left, against the 176 that row wants. It used to run off the edge and lose the end
   of a name.

   So the cell breaks between the name and the spot, and never inside either. That
   costs a line on the two or three rows that need it and nothing on the rest, and
   the card has the height to spend: it sits beside eleven slots and is shorter than
   they are. Making it wider instead meant stacking it under them, which measured
   four sheets where the chart gets two. */
table.dc-sub th, table.dc-sub td {
  padding: 1px 4px 1px 0; text-align: left; vertical-align: top;
  font-weight: 700; color: var(--ink); white-space: normal;
}
table.dc-sub .dc-sub-man, table.dc-sub .dc-sub-pos,
table.dc-sub .mv-a, table.dc-sub .mv-b { white-space: nowrap; }
table.dc-sub th:last-child, table.dc-sub td:last-child {
  border-left: 1px solid var(--line); padding-left: 4px;
}
table.dc-sub thead th {
  font-size: 10.5px; font-weight: 800; letter-spacing: .4px;
  text-transform: uppercase; color: var(--muted);
}
/* SUBS and MOVES name the two blocks outright, in a tinted band the width of the
   card. The rule between them said there were two kinds of change here; it did not
   say which kind you were looking at, so the reader worked it out from the column
   headings -- and "Moved / Spot" is only obviously a different subject from
   "Out / In" once you have already read both. A coach reading this on a sideline is
   answering one of two questions: who is running on and off, or who is already out
   there and standing somewhere new. The band answers it before he reads a name. */
table.dc-sub > caption {
  caption-side: top; text-align: left;
  margin: 0 0 2px; padding: 1px 5px; border-radius: 3px;
  background: var(--line); color: var(--ink-2);
  font-size: 9.5px; font-weight: 800; letter-spacing: .9px;
  text-transform: uppercase;
}
/* The Moved block is a second table under the first, and the rule between them does
   the work a third pair of columns would have done badly: Out is a man leaving and In
   is a man arriving, while a move is one man twice and fits neither. A solid rule
   rather than the hairline the cells use -- it is a change of subject, not a row.

   The arrow is drawn from borders, not typed. U+2192 came out of a printer as a tofu
   box the first time this book wanted an arrow; a border always prints. */
table.dc-sub.dc-moved {
  margin-top: 5px; padding-top: 4px; border-top: 1.5px solid var(--line);
}
.dc-mv .mv-a { color: var(--muted); font-weight: 800; }
.dc-mv .mv-b { font-weight: 800; }
.dc-mv .mv-b::before {
  content: ""; display: inline-block; vertical-align: middle;
  width: 0; height: 0; margin: 0 4px 1px 4px;
  border: 3px solid transparent; border-left-color: var(--muted); border-right: 0;
}
/* The spot after an incoming name is an annotation, not the name, and it was set only
   two points below it. Smaller is both truer and the cheapest width on the card --
   which the defence needs, where the spot is LOLB rather than C. */
.dc-sub-pos {
  font-size: 9.5px; font-weight: 800; letter-spacing: .2px;
  text-transform: uppercase; color: var(--muted);
}
.dc-pkg-slot {
  min-height: 18px; display: flex; align-items: center; gap: 6px;
  padding: 1px 0; min-width: 0; font-size: 13px; font-weight: 700; color: var(--ink);
}
.dc-pkg-slot[data-spot]::before {
  content: attr(data-spot);
  flex: 0 0 38px; font-size: 9px; font-weight: 800; letter-spacing: 0;
  color: var(--muted); text-transform: uppercase; white-space: nowrap;
}
/* The four backs carry the position and the number together -- QB (10), FB (20) -- not
   the number alone. The position is what the kid knows he is and the number is what a
   call says, and a card that prints only the number makes the reader hold the mapping
   in his head. The numbers are the ones on the nomenclature card: the back digit with
   the hole digit 0 behind it, 10 20 30 40, which is what the diagram labels those
   four with. One label column width for every slot, so the names line up under each
   other whether the label is three characters or seven. */
.dc-pkg-slot[data-n]::before {
  content: attr(data-spot) " (" attr(data-n) ")";
}
/* The defence's two halves both carry longer strings than the offense's -- LOLB where
   it has C, and that same label again after each incoming name on the sub card. So it
   gets four more points of card and eight fewer of label column. Offense is left
   exactly as it was; it has neither problem. */
.dc-side[data-side="defense"] .dc-subcard { flex-basis: 58%; }
.dc-side[data-side="defense"] .dc-pkg-slot[data-spot]::before { flex-basis: 30px; }
/* And the table itself a size down. The widest row the defence prints is Rampage's
   "Brayden S." against "Brooks A. (RILB)" -- two full names and a four-letter spot in
   one row, which the offense never has to fit. */
.dc-side[data-side="defense"] table.dc-sub { font-size: 11.5px; }

.dc-pkg-slot + .dc-pkg-slot { margin-top: 1px; }
/* A rule where the unit changes, so an eleven reads as its groups rather than as a
   list of eleven names. Offense breaks before the tight ends and before the line;
   defense before the linebackers and before the secondary. The two sides can share
   one rule because no key means something different across them -- which is what the
   defensive line's D bought: LT is ours, LDG is theirs. */
.dc-pkg-slot[data-spot="X"],
.dc-pkg-slot[data-spot="LT"],
.dc-pkg-slot[data-spot="LOLB"],
.dc-pkg-slot[data-spot="LC"] {
  margin-top: 5px; padding-top: 5px; border-top: 1px dashed var(--line);
}

.dc-bar {
  display: flex; align-items: center; justify-content: flex-end; gap: 14px;
  flex-wrap: wrap; margin: 14px 0 6px;
}
.dc-tools { display: flex; gap: 8px; flex-wrap: wrap; }

.dc-abbr { font-weight: 800; color: var(--accent-ink); font-size: 15px; }
.dc-label { color: var(--muted); font-size: 12.5px; }

.dc-side { margin: 26px 0 0; }
.dc-side .hero-head { margin: 0 0 2px; }
.rot-sub {
  display: inline-block; margin-left: 10px; font-size: 13px; font-weight: 700;
  letter-spacing: .6px; text-transform: uppercase; opacity: .82;
}
.rot-h {
  display: flex; align-items: baseline; gap: 8px;
  margin: 10px 0 6px; font-size: 12px; font-weight: 800; letter-spacing: 1.4px;
  text-transform: uppercase; color: var(--muted);
}


/* --------------------------------------------------------------- call sheet --
   A spreadsheet, on purpose: ruled cells with no gaps, empty ones drawn too, so the
   lineup keeps the formation's shape and the plays read straight down a column. One
   sheet per package, side by side, stacking on a phone. */
/* The formation blocks and the script column side by side. The script is a fixed
   width because it is ruled space to write in, not content that wants to breathe --
   giving it a share of the page would make its boxes wider as the window grows, which
   is the opposite of useful. */
.xl-top {
  display: grid; gap: 14px; align-items: start;
  grid-template-columns: minmax(0, 1fr) 330px;
}
@media (max-width: 860px) { .xl-top { grid-template-columns: 1fr; } }
.xl-sheets {
  display: grid; gap: 14px; margin: 10px 0 24px;
  grid-template-columns: repeat(auto-fit, minmax(min(460px, 100%), 1fr));
}
.script { margin: 10px 0 24px; }
.script-t { border: 2px solid var(--ink); }
/* Qualified with table.xl on purpose. `table.xl td` further down this file sets
   vertical-align: top and it has the same specificity as a bare `.script-t td`, so the
   later rule was winning and the numbers sat at the top of their cells however many
   times the rule below said middle. Two classes beats one, whatever the order. */
table.xl.script-t td { height: 26px; padding: 2px 5px; vertical-align: middle;
                       text-align: center; white-space: nowrap; }
table.xl.script-t td.sn {
  width: 26px; text-align: center; font-weight: 800; color: var(--muted);
}
/* The left/right split above the numbered rows: a header, so it is set off from the
   calls by the same heavy rule the column's border uses. */
table.xl.script-t td.split {
  font-size: 11px; font-weight: 800; border-bottom: 2px solid var(--ink);
}
.script-t .split-sep { margin: 0 8px; color: var(--muted); }
/* The split row spans both columns, and a spanning first row leaves the browser to
   guess the column widths -- it split them evenly and clipped every call. The col pins
   the number column to the width its cells ask for. */
.script-t col.sn-c { width: 26px; }
/* A script row is a play link, so it reads like one: the same size, weight and
   absence of underline as a package row, not the browser's blue-and-underlined
   default. It was the only list of plays on this page still wearing that. */
.script-t td a {
  display: block; color: var(--ink); font-weight: 700; text-decoration: none;
  font-size: 10px;
}
.script-t td a:hover { text-decoration: underline; }
/* Stacked on a phone the column is the full width and a name has room to wrap, so
   nowrap would only push it off the side of the screen. */
@media (max-width: 860px) {
  table.xl.script-t td { white-space: normal; }
}
.xl-sheet { min-width: 0; }
.xl-title {
  margin: 0; padding: 7px 8px; font-size: 15px; font-weight: 800;
  text-transform: uppercase; letter-spacing: .5px;
  color: var(--on-accent); background: var(--accent-solid);
}
table.xl {
  width: 100%; border-collapse: collapse; table-layout: fixed;
  background: var(--panel); font-size: 11.5px;
}
table.xl td, table.xl th {
  border: 1px solid var(--line); padding: 3px 3px; vertical-align: top;
  line-height: 1.25;
}
table.xl th {
  background: var(--panel-2); font-size: 11px; text-transform: uppercase;
  letter-spacing: .6px; color: var(--muted);
}
/* The scheme names run down the left edge as row headings, so a cell is read by the
   row it is in and the column it is under, not by anything repeated inside it. */
.xl-scheme {
  text-align: left !important; font-size: 10.5px; font-weight: 800;
  text-transform: uppercase; letter-spacing: .5px; color: var(--accent-ink);
  background: var(--panel-2); vertical-align: middle !important; white-space: nowrap;
}
/* LEFT / MIDDLE / RIGHT is a solid black band across the top of every formation
   block. The sheet is five blocks of near-identical small type, and the bar is what
   breaks them apart -- you find the block you want by the rule, then read down from
   the column heading, instead of counting rows. The empty corner cell is in the band
   too: a white notch at the left end would read as a missing cell. */
table.xl.xl-plays thead th {
  background: #000; color: #fff; border-color: #000; font-weight: 800;
}
col.xl-c0 { width: 4.6em; }
/* The halves of the sheet, split down the middle. With a Middle column between them
   the two sides were obviously separate; without one they run together, so the seam
   is drawn -- 2px, the same weight the script's border and the field's sidelines use,
   because it is the same kind of line. Third child is the Right column: the scheme
   label, then Left, then Right. */
table.xl.xl-plays th:nth-child(3),
table.xl.xl-plays td:nth-child(3) { border-left: 2px solid var(--ink); }
/* Specific enough to beat `table.xl td`, whose top alignment would otherwise win. */
table.xl.xl-plays td {
  height: 22px; text-align: center; vertical-align: middle; padding: 4px 5px;
}
/* A cell can hold four calls — Split Backs has four Sweeps to a side — so they stack
   as their own lines rather than wrapping into each other. */
.xl-plays td a {
  display: block; color: var(--ink); font-weight: 700; text-decoration: none;
  padding: 1px 0; font-size: 10.5px;
}
.xl-plays td a + a { border-top: 1px dotted var(--line); }
.xl-plays td a:hover { text-decoration: underline; }
/* The number is how the card, the book, the install chips and the boys' wristbands
   name the play, so it leads the cell in black rather than sitting behind the words
   as a grey footnote. It was a quiet "I-7" when the words of the call were the only
   way in; a boy looking for 7 needs to find 7.

   "#7 |" rather than a bare 7: a plain number running straight into the words of the
   call blended into them -- "7 Z Right - 32 Handoff" reads as one string, and the sheet
   is nothing but strings like it. The hash says this is a play number and the bar
   says where it stops, which is the same shape the install chips have always used. */
.xl-code {
  display: inline-block; margin-right: 6px; font-size: 11px; font-weight: 900;
  color: var(--ink); letter-spacing: 0;
  /* Its own line box, so type bigger than the call's does not make every row taller.
     Without this the sheet grew forty points and went to a second page. */
  line-height: 1;
}
.xl-none { color: var(--line); }
.xl-n {
  float: right; font-weight: 700; opacity: .75;
}

/* The packages along the bottom: three to a row, each a name over the two calls it
   comes on to run. Narrow cards on purpose — this is a strip under the sheet, not a
   second sheet. */
.pk-head { margin-top: 20px; }
.pk-sub {
  font-weight: 500; text-transform: none; letter-spacing: 0; color: var(--muted);
  font-size: 12.5px; margin-left: 8px;
}
/* ------------------------------------------------------- call sheet tabs --
   Two radios and two labels. No script, so the tabs survive JavaScript being off,
   and the checked radio drives which pane shows through a sibling selector. */
.sheet-tabs > input { position: absolute; opacity: 0; pointer-events: none; }
.tabrow {
  display: flex; gap: 6px; margin: 10px 0 14px;
  border-bottom: 2px solid var(--line);
}
.tab {
  padding: 7px 18px; font-weight: 800; font-size: 13px; letter-spacing: 1.1px;
  text-transform: uppercase; color: var(--muted); cursor: pointer;
  border: 2px solid transparent; border-bottom: 0; border-radius: 8px 8px 0 0;
  margin-bottom: -2px;
}
.tab:hover { color: var(--ink); }
#tab-off:checked ~ .tabrow .tab[for="tab-off"],
#tab-def:checked ~ .tabrow .tab[for="tab-def"] {
  color: var(--ink); border-color: var(--line); background: var(--panel);
  border-bottom: 2px solid var(--panel);
}
#tab-off:focus-visible ~ .tabrow .tab[for="tab-off"],
#tab-def:focus-visible ~ .tabrow .tab[for="tab-def"] { outline: 2px solid var(--accent-solid); }
.tabpane { display: none; }
#tab-off:checked ~ .pane-off, #tab-def:checked ~ .pane-def { display: block; }

/* ------------------------------------------------------------ wristbands --
   A pouch is landscape -- it wraps a forearm -- so a panel is wider than it is tall,
   and that shape decides the page. Eight rows fit down a landscape panel where sixteen
   do not, so a formation goes in two columns and the type gets to be sixteen point.
   Three panels stacked is one band; two bands across is the sheet. */
.band-sheet { margin: 16px 0 24px; }
/* Exactly a pouch, in inches, because that is what it has to be when it comes off the
   printer. Three of them is a wristband and a sheet. */
.band-set { display: grid; grid-template-rows: repeat(3, 2.75in); gap: 7px; width: 3.5in; }
.band {
  border: 1px dashed var(--line); border-radius: 4px; padding: 0 0 4px;
  background: var(--panel); overflow: hidden;
}
/* The bar is the pouch: a boy knows which window a number is in before he opens it.
   So the formation is the biggest thing on the band after the numbers themselves,
   and it is centred, because a name pushed into the left corner of a five-inch
   window is a name you have to go looking for. The number span keeps its corner and
   comes out of the flow to do it -- centring the name between two flex items would
   centre it in the space the span leaves, which is not the middle of the pouch. */
.band-form {
  display: grid; grid-auto-flow: column; grid-auto-columns: 1fr;
  margin: 0 0 2px; font-size: 15px; font-weight: 900;
  text-transform: uppercase; letter-spacing: .5px; line-height: 1.1;
  color: var(--on-accent); background: var(--accent-solid);
}
/* One segment per column. The divider is a white rule inside the black bar rather
   than a gap, because a gap between two black blocks reads as two bars and the
   pouch is one thing. */
.band-seg {
  position: relative;
  display: flex; align-items: center; justify-content: center;
  padding: 5px 8px; min-width: 0;
}
.band-seg + .band-seg { border-left: 2px solid var(--on-accent); }
.band-span {
  position: absolute; right: 6px; bottom: 4px;
  font-size: 10px; font-weight: 800; opacity: .8;
}
.band-body { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 4px; }
/* The formation label inside a pouch that holds two of them. Black on white, the
   same family as the bar above it, so the eye reads bar -> list -> bar -> list. */
.band-sub {
  margin: 2px 0 0; padding: 0 5px;
  font-size: 9.5px; font-weight: 900; letter-spacing: .7px;
  text-transform: uppercase; color: var(--ink);
  border-bottom: 1px solid var(--ink);
}
.band ol { margin: 0; padding: 0; list-style: none; }
/* The call at 10px, the NUMBER at 13, and the rows spread down the pouch.
   All three are measured against the youth window, 3.5in by 2.75in, two columns.

   The call is width-capped: the longest one the sheet carries is "Z Tight Right -
   18 Fake Sweep", and at 10px it cleared its column by two points with the rule
   two points off the call. Two points is not a gap, it is a collision -- the rule
   and the Z of "Z Tight" read as one mark. The gap is worth more than the type
   size, so the gap took two spaces and the call gave up the half point that pays
   for them; 9.5px leaves four points spare at the end of the longest row. The
   words are not shortened to buy more, because the call sheet spells them out too
   and a sheet that prints a different call from the one on the boy's wrist has to
   be translated under a play clock.

   The number is bigger than the call, which it was not before. He is not reading the
   band, he is being shouted a number and hunting for it; the call is what he reads
   once he has found the row. A 9px number under a 9.5px call had that backwards.

   The leading is what spends the height. Matching the sheet dropped the passes and
   the Shotgun, so a column is seven rows instead of nine and there was an inch and a
   quarter of empty pouch under them. Spread out, each row is a target a finger can
   hold on a moving arm. */
.band li {
  display: flex; align-items: baseline; gap: 7px;
  padding: 0 1px; font-size: 9.5px; font-weight: 700; line-height: 2.5;
  color: var(--ink); white-space: nowrap;
}
/* Zebra rather than a rule between rows. A rule is a thing to read past; a band of
   tone is the row itself, and a finger tracking one does not slip off it. */
.band li:nth-child(even) { background: var(--panel-2); }
/* The rule is the number's own edge, not a fence between two equals: it stays two
   points off the digits and seven off the call. Even padding either side would make
   it a third column of its own. */
.band li b {
  flex: 0 0 16px; font-size: 13px; text-align: right; font-weight: 900;
  font-variant-numeric: tabular-nums;
  padding-right: 2px; border-right: 1px solid var(--line);
}
.band li span { flex: 1 1 auto; min-width: 0; }
/* A phone is narrower than a pouch. Let the panels shrink rather than run off the
   side: the screen is a preview, the printed inches are the thing. */
@media (max-width: 560px) {
  .band-set { width: 100%; grid-template-rows: none; }
  .band li { font-size: 9.5px; line-height: 2.5; }
}

/* ------------------------------------------------- defensive call sheet --
   One table per front, positions down the side and packages across, so a cell is
   the boy who plays that spot in that package. The offensive sheet's title bar and
   table furniture are reused rather than reinvented: both are call sheets. */
.df-fronts { display: grid; gap: 16px; margin: 10px 0 20px; }
/* The front as a picture, above its table. Discs made of border, positioned by the
   alignment's own yards -- see _front_picture for why not an SVG. */
.front-pic {
  --fd-scale: 11.5px; --fd-pad: 11px;
  position: relative; width: 340px; max-width: 100%;
  height: calc(var(--fd-deep) * var(--fd-scale) + 2 * var(--fd-pad));
  margin: 8px auto 6px; border: 1px solid var(--line); border-radius: 4px;
  background: var(--panel-2);
}
.front-pic .los {
  position: absolute; left: 4%; right: 4%; top: var(--fd-pad);
  border-top: 1px dashed var(--ink-2);
}
.front-pic .fd {
  position: absolute; width: 0; height: 0; border: 6px solid var(--ink);
  border-radius: 50%; transform: translate(-50%, -50%);
}
/* The blank row between the line, the backers and the secondary. A row rather than a
   rule on the next one: the gap is the thing being asked for, and a row can carry it
   without the cell borders either side having to agree about it. */
table.xl.df-grid tr.df-gap td {
  height: 13px; padding: 0; border-left: 0; border-right: 0;
  background: var(--panel-2);
}
table.xl.df-grid { table-layout: auto; }
table.xl.df-grid td, table.xl.df-grid th { text-align: center; }
table.xl.df-grid .df-pos {
  width: 58px; text-align: left; font-weight: 800; font-size: 11px;
  letter-spacing: .4px; color: var(--muted); background: var(--panel-2);
}
table.xl.df-grid tbody td { font-weight: 700; }

.pk-grid {
  display: grid; gap: 10px; margin: 8px 0 24px; align-items: start;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
@media (max-width: 560px) { .pk-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.sit-grid { margin-top: 18px; }
/* The base eleven, once, across the full width: eleven little cells in the order they
   stand on the field. Printing all eleven names on all six package cards was six
   lists a coach had to diff in his head; this is the one he diffs them against. */
.bl-strip { margin-top: 18px; }
.bl-row {
  display: grid; grid-template-columns: repeat(11, minmax(0, 1fr)); gap: 0 1px;
  background: var(--line); border-top: 1px solid var(--line);
}
.bl-man {
  display: block; padding: 3px 4px 4px; min-width: 0; text-align: center;
  background: var(--panel); font-size: 11px; font-weight: 700; color: var(--ink);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.bl-man b {
  display: block; font-size: 9px; font-weight: 900; letter-spacing: .4px;
  text-transform: uppercase; color: var(--muted);
}
/* Out, then in. The arrow between them is drawn out of borders rather than set as a
   glyph: a border prints on anything, and U+2192 is a box on a machine whose font
   stack does not happen to carry it -- which is most of the ones this gets printed
   from. Same reason the discs on the blank line are borders. */
table.xl.pk-subs td {
  height: auto; padding: 2px 4px; vertical-align: middle; font-size: 10.5px;
  font-weight: 700; white-space: nowrap;
}
table.xl.pk-subs .sub-pos {
  width: 2.6em; text-align: left; font-size: 9.5px; font-weight: 900;
  letter-spacing: .3px; color: var(--muted); background: var(--panel-2);
}
/* The man coming off is dark grey and the man coming on is black. It was a
   strike-through, which is the right idea and the wrong mark: at seven and a half
   points a line through a name is a line through the letters, and the name a coach
   has to read to know who he is pulling gets harder to read the more certainly it
   says he is pulling him. Colour and weight say the same thing and leave the name
   alone. */
table.xl.pk-subs .sub-out { text-align: right; color: var(--ink-2); font-weight: 600; }
table.xl.pk-subs .sub-in { text-align: left; font-weight: 800; }
table.xl.pk-subs .sub-in::before {
  content: ""; display: inline-block; vertical-align: middle;
  width: 0; height: 0; margin: 0 5px 1px 0;
  border: 3px solid transparent; border-left-color: var(--muted); border-right: 0;
}
/* The spot an incoming man plays, after his name. It used to be a column of its own
   on the left, which read as the spot being SUBSTITUTED rather than the spot being
   filled -- and it had no honest answer at all for a boy who moved, because he fills
   one spot and leaves another. */
table.xl.pk-subs .sub-pos {
  font-size: 8.5px; font-weight: 800; letter-spacing: .2px;
  text-transform: uppercase; color: var(--muted); background: none;
  width: auto; padding: 0;
}
/* Moved: the boy in both elevens doing a different job. Under its own header row,
   because it is a change of subject from the two columns above it and not another
   row of them -- nobody comes off for him and nobody goes on. The arrow between his
   two spots is drawn from borders like every other arrow in this book: a typed one
   came out of a printer as a tofu box. */
/* The two group headers. A tinted full-width band rather than a rule, because the
   cells either side of it are already a two-column grid of names and one more
   horizontal line reads as another row of that grid. MOVES also keeps the rule
   above it: the band says what is coming, the rule says the list before it ended. */
table.xl.pk-subs tr.pk-grp th {
  padding: 1px 4px; text-align: left;
  background: var(--line); color: var(--ink-2);
  font-size: 8.5px; font-weight: 800; letter-spacing: .9px; text-transform: uppercase;
}
table.xl.pk-subs tr.pk-grp-mv th {
  border-top: 1.2px solid var(--ink-2);
}
table.xl.pk-subs .mv-name { font-weight: 800; color: var(--ink); }
table.xl.pk-subs .sub-mv { text-align: left; font-weight: 800; }
table.xl.pk-subs .sub-mv .mv-a { color: var(--muted); }
table.xl.pk-subs .sub-mv .mv-b::before {
  content: ""; display: inline-block; vertical-align: middle;
  width: 0; height: 0; margin: 0 3px 1px 3px;
  border: 3px solid transparent; border-left-color: var(--muted); border-right: 0;
}
/* Six across, not three. A substitution card is one short column of two names, where
   a package card is five whole calls, so six of these fit the width that three of
   those need -- and one row of six is half the height of two rows of three, which is
   the difference between this strip fitting under the field and the field paying for
   it twice over. */
.sub-grid { margin-top: 10px; grid-template-columns: repeat(6, minmax(0, 1fr)); }
@media (max-width: 860px) { .sub-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 560px) {
  .bl-row { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .sub-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.pk { min-width: 0; }
.pk-name {
  margin: 0; padding: 5px 8px; font-size: 12.5px; font-weight: 800;
  text-transform: uppercase; letter-spacing: .5px; text-align: center;
  position: relative;
  color: var(--on-accent); background: var(--accent-solid);
}
/* The package number is pinned to the right edge rather than floated, because a float
   sits inside the line box and would push the centred name off centre by its own
   width. Out of flow, the name centres on the card. */
.pk-n { position: absolute; right: 8px; top: 5px; font-weight: 700; opacity: .75; }
table.xl.pk-plays td {
  height: 22px; text-align: center; vertical-align: middle; padding: 3px 5px;
}
/* A package row carries the formation as well as the call, so it is a size down
   from a sheet cell and left-aligned -- these read as a list, not a grid. */
.pk-plays td a {
  display: block; color: var(--ink); font-weight: 700; text-decoration: none;
  font-size: 10px;
}
.pk-any { color: var(--muted); font-style: italic; font-size: 11px; }
/* The blank line at the bottom of the sheet. Seven circles and a ball, nothing else:
   the sheet is laminated and drawn on with a marker, so what belongs here is the part
   that never changes -- the centre, three men either side, and the ball in front of
   him. Everything that makes it a play gets drawn in on the sideline and wiped off
   after. */
/* Borders, not an SVG. An inline SVG here rendered perfectly on screen and was simply
   absent from the printed sheet at every size tried -- the same lesson the title bars
   taught earlier in this file: what always prints is a border. Fifteen columns, so the
   hole numbers sit over the gaps they name and 0 sits over the centre. */
/* The field the line stands on: a rule across the top to part it from the packages,
   and a sideline down each edge with hash marks on it, so the blank space reads as a
   piece of field rather than as the bottom of the page. All borders, which is the only
   thing that prints reliably. */
/* The padding above the line is the strip's own drop: the line of scrimmage sits that
   far below the rule that starts the field, which leaves somewhere to draw a defender
   or a motion arrow in front of the ball rather than the line being flush with the top
   edge of the box. */
.pk-field {
  position: relative; margin: 10px 0 0; padding: 37px 0 0;
  border-top: 1px solid var(--ink);
  border-left: 2px solid var(--ink); border-right: 2px solid var(--ink);
  break-inside: avoid;
}
.pk-field .hash {
  position: absolute; left: 0; width: 13px; border-top: 2px solid var(--ink);
}
.pk-field .hash.r { left: auto; right: 0; }
.pk-draw {
  display: grid; grid-template-rows: auto auto;
  align-items: center; justify-items: center; justify-content: center;
  margin: 0; row-gap: 2px;
  /* Fifteen columns, alternating a man and the gap beside him, so the numbers land
     over the holes they name. The widths are a line, not a spread: a man is 34, a
     split is 22, and the two outside columns are wide because 8 and 9 are outside the
     end rather than in a gap. Centred, so the sheet keeps its side margins. */
  grid-template-columns: 84px 34px 22px 34px 22px 34px 22px 34px
                         22px 34px 22px 34px 22px 34px 84px;
}
/* The numbers sit in the gaps, on the same line as the men, because that is where the
   hole is -- a row of digits above the line is a key, this is the thing itself. */
.pk-draw .hn { font-size: 11px; font-weight: 800; color: var(--muted); }
/* Solid discs, the centre included. Made entirely of border rather than given a
   background: a background needs print-color-adjust and the browser's cooperation,
   while a border prints whatever the print dialog is set to -- which is the rule this
   whole strip already had to learn the hard way. Zero box, thick border, round. */
.pk-draw .o {
  width: 0; height: 0; border: 11.5px solid var(--ink); border-radius: 50%;
}
/* The ball in front of the centre: an oval with a seam across it. */
.pk-draw .ball {
  width: 22px; height: 13px; border: 2px solid var(--ink); border-radius: 50%;
  position: relative;
}
.pk-draw .ball::after {
  content: ""; position: absolute; left: 4px; right: 4px; top: 50%;
  border-top: 2px solid var(--ink);
}
/* The room to draw in: the backfield, below the line. */
/* The field below the line: as deep as the sheet has room for, which is whatever the
   rest of it leaves. 62 points of drawing space to start, then 200 and 260 as
   formations came off the sheet, 120 when the down-and-distance board went in, 155
   once the board went to two calls, 185 when a package card went to five rows, and
   196 once the last of the bottom margin went into it too. It was 187 when the line
   of scrimmage dropped another nine points and the box had nowhere left to grow --
   the field the same height, the line just lower in it -- and it is 172 now because
   the board came off and the base eleven and the substitution cards went on in its
   place, which cost fifteen more points than the board did. Every one of those numbers was measured against the page, not chosen --
   and this one sits
   about four points under the two-page cliff rather than the twenty-odd the
   others kept, which is deliberate and is the thing to undo first if a printer
   ever spills this sheet onto a second sheet. */
.pk-draw .pad { grid-column: 1 / -1; height: 222px; }
.pk-plays td a:hover { text-decoration: underline; }
@media print {
  /* One formation to a row, full width. Two across put a formation in half a page,
     which is where the long calls wrapped -- "Trips Right - Y Slant Pass Right" over two lines
     in a cell an inch wide. The full width is the fix: the same rows, the same type
     size, but each cell three inches instead of one and a half, so nothing wraps and
     the block is *shorter* than it was at half width. Five of them still fit the one
     sheet because of it, not in spite of it. */
  /* Four blocks down the left, the script down the right. 230 points is what the
     longest call in the script needs to sit on one line -- "Split Backs - Z Right -
     X Sweep Right" -- and it is affordable because the blocks do not wrap at what is
     left: their widest, "Z Right - 18 Fake Sweep", has room to spare. Both are at the
     point size below rather than the width above: when the sides were spelled out the
     sheet had no spare width anywhere, so the four characters came out of the type.
     Checked at 200, where the script clipped, and at 230, where neither side does. */
  .xl-top { display: grid; grid-template-columns: 1fr 272px; gap: 0 6px;
            align-items: start; }
  .xl-sheets { grid-template-columns: 1fr; gap: 0; margin: 2px 0 0; }
  .script { margin: 2px 0 0; break-inside: avoid; }
  /* A block border round the whole column, 2px like the field's sidelines, so it reads
     as one object rather than twenty loose boxes. The cells keep the hairline the rest
     of the sheet's tables use. */
  .script-t { border: 2px solid #000; }
  /* The anchor carries its own font-size from the screen block, so sizing the cell
     does nothing to the call -- this column printed at 10px for a long time while the
     rule below claimed 9. Size the anchor, and the code span inside it, or nothing
     moves. 8.5px is what "Split Backs - Z Right - X Sweep Right" needs to sit on one
     line in 230 points now that the sides are spelled out; measured, not picked. */
  .script-t td a { letter-spacing: -.3px; font-size: 8.5px; }
  .script-t .xl-code { font-size: 9px; margin-right: 3px; }
  .script-t td a { color: #000; text-decoration: none; }
  /* 20.4 points a row is the height of the four formation blocks divided by twenty --
     measured against the page, not picked, and tuned until the foot of this column and
     the foot of the Power I block land on the same line. */
  /* Both columns centred: the number in its own box and the play in the rest of the
     row, which is how a call reads everywhere else on this sheet. The number column is
     17 points rather than 15 so the centring is visible in it -- at 15 a digit sat a
     hair off the left border and read as left-aligned whatever the rule said. It was
     20 until the letter calls grew a direction word; the three points went next door,
     where "Split Backs - Z Right - X Sweep Right" needed them, and two digits at 7px
     still do not fill 17. */
  /* Qualified with table.xl for the same reason as the screen rule: the print block's
     own `table.xl td` comes after this and would otherwise take back the padding, and
     the base rule's vertical-align: top would take back the centring. */
  /* nowrap is load-bearing, not cosmetic. A name that wraps makes its row two lines
     tall, and twenty rows growing a line each is most of an inch -- it took the sheet
     to two pages the first time the script was filled in. The column is sized so
     nothing needs to wrap; this makes a name that somehow did overflow visibly rather
     than silently push the field and the board off the page. */
  /* 19.4 rather than 20.4 since the split row joined the column: twenty-one rows now
     share the height twenty did, so the foot still lands on the Power I block's. */
  table.xl.script-t td { height: 19.4px; padding: 0 1px; line-height: 1.15;
                         font-size: 8.5px; font-weight: 700; white-space: nowrap;
                         vertical-align: middle; text-align: center; }
  table.xl.script-t td.sn { width: 17px; text-align: center; font-size: 7px;
                            font-weight: 800; color: #000; }
  table.xl.script-t td.split { font-size: 8.5px; border-bottom: 2px solid #000; }
  .script-t .split-sep { margin: 0 5px; color: #000; }
  .script-t col.sn-c { width: 17px; }
  /* No rule between blocks any more: the formation's own black bar below is the
     separator, and a 3px rule under the block as well was two fences for one fence's
     job. Dropping five of them also pays for the bar's padding, which is the only
     reason the sheet is still one sheet -- it was within a third of an inch of
     spilling before either change. */
  .xl-sheet { padding: 2px 0 3px; break-inside: avoid; }
  table.xl { font-size: 9px; }
  table.xl td, table.xl th { padding: 0 2px; }
  table.xl th { font-size: 8px; }
  /* The scheme column is a label, not a share of the page: at full width an even
     quarter each would leave three inches of white beside the word "Sweep". */
  col.xl-c0 { width: 50px; }
  /* The formation name is a full-width black bar with white type, the same treatment
     as the LEFT/MIDDLE/RIGHT row below it, so a block reads as one thing with a
     header on it rather than six similar tables in a column. It used to print as
     plain black text because the screen's white-on-navy bar came out pale grey
     whenever the browser left background graphics off; `print-color-adjust: exact`
     is what fixed that, so the bar can be a bar on paper now. */
  .xl-title {
    padding: 1px 4px; font-size: 10px; font-weight: 900; line-height: 1.3;
    color: #fff !important; background: #000 !important;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }
  /* The black band prints. `print-color-adjust: exact` is the whole reason it can:
     it tells the browser this fill is content, not decoration, so it survives the
     print dialog's background-graphics setting being off -- which is exactly what
     turned the old navy title bars into pale grey (see .xl-title above). Without it
     the white type would print white on white and the headings would vanish.
     Scoped to the head row, so .xl-scheme's own print rule below still strips the
     background off the scheme labels down the side. */
  table.xl.xl-plays thead th {
    background: #000 !important; color: #fff !important; border-color: #000 !important;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }
  /* Tighter rows on paper than on screen. The 4px of padding above and below
     every cell was 50 points of the one sheet -- a row of it for each block --
     and the sheet ran out of room the day Regular I got a Toss. */
  table.xl.xl-plays td { height: auto; vertical-align: middle; padding: 2px 2px; }
  /* A call is one line on paper: small enough to fit its cell, and never wrapping
     into a second line that makes the row taller. */
  .xl-plays td a { font-size: 8.5px; white-space: nowrap; letter-spacing: -.25px;
                   padding: 0; line-height: 1.2; }
  /* Four calls stacked in one cell ran together on paper: the rule between them is
     var(--line), which is a hairline grey a screen can show and a printer cannot.
     It is the same fence the sheet already meant to have, drawn dark enough to be
     one. */
  .xl-plays td a + a { border-top: 1px dotted #999; }
  table.xl.xl-plays td { line-height: 1.2; }
  .xl-scheme { line-height: 1.2; }
  /* The number is the play now -- it is what goes on a wristband and what a boy
     is looking for -- so it reads as black type rather than the grey footnote a
     letter-and-dash code was. Losing the letter paid for the size. */
  .xl-code { font-size: 10px; margin-right: 4px; color: #000; font-weight: 900; }
  tbody .xl-scheme { font-size: 8.5px; background: none !important; color: #000 !important; }
  thead .xl-scheme { font-size: 8.5px; }
  .xl-none { color: #ccc; }
  .xl-n { display: none; }
  /* The strip stays on the sheet with the blocks: three across, never split over a
     page break. CSS columns were tried here to pack the cards by height and came out
     18px WORSE than the grid -- balancing put Total Recall's four and Maverick's six
     in the same column and the other two ran short, so the ragged bottom cost more
     than the grid's even rows. Measure before believing that one. */
  /* Laminated and called from, not read. The page title and the word "Packages" are
     both things you know by the time you are holding it, and between them they were
     most of an inch of the one sheet. The rule under the heading stays -- it is what
     separates the packages from the formation blocks -- so it moves onto the grid. */
  /* Tabs are a screen affordance; on paper both panes print, a sheet each. The row
     itself has to go as well as being redundant -- its margins alone were enough to
     push the offensive sheet onto a second page. */
  .tabrow { display: none; }
  .tabpane { display: block !important; }
  .pane-def { page-break-before: always; break-before: page; }
  /* The wristband sheet is the one page whose whole job is the print, and the one
     page measured in inches rather than in what fits: a panel is 5 by 3 because a
     pouch is. Three of them is nine inches of a 10.4-inch page and one whole band, so
     a sheet is one boy and you print a copy each. The dashes are cut lines, so they
     have to print: a border always does, which is why a panel is bordered rather than
     shaded. */
  .band-page .page-head { display: none; }
  .band-sheet { margin: 0; }
  .band-set { width: 3.5in; grid-template-rows: repeat(3, 2.75in); gap: 0.07in;
              margin: 0 auto; break-inside: avoid; }
  .band { border-color: #000; background: none; break-inside: avoid; }
  /* This is the one that matters: the printed pouch is what goes on a wrist. The
     formation is set as big as the pouch allows and centred, so it reads through a
     plastic window at arm's length, outdoors, on a boy looking for it in a hurry.
     21px is what the width takes: the longest bar is SHOTGUN · POWER I, and at this
     size it is about half of the five inches, leaving the number range its corner.
     The height is free -- eight rows and the bar come to roughly two and three
     quarter inches of the three, and test_print_pages.py holds the sheet to one
     page if that ever stops being true. */
  .band-form { font-size: 15px; margin-bottom: 1px;
               letter-spacing: .5px; line-height: 1.1;
               color: #fff !important; background: #000 !important;
               -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .band-seg { padding: 4px 6px; }
  /* The divider has to be a drawn rule, not a gap in the fill: a printer that drops
     the black background would leave nothing at all between the two names. */
  .band-seg + .band-seg { border-left: 1.5pt solid #fff !important;
                          -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .band-span { font-size: 9px; opacity: 1; right: 5px; bottom: 3px; }
  .band-sub { font-size: 6.5pt; color: #000; border-bottom-color: #000;
              margin: 1px 0 0; padding: 0 3px; }
  /* Width sets the type here, not height: "Z Tight Right - 18 Fake Sweep" is the
     longest row there is and it has half of three and a half inches to fit in. The
     rows then have three inches to live in, which is why the leading is what it is --
     the space was going spare, and a row a boy can keep his eye on is what to spend
     it on. The leading is safe from the half point the call gave back to the gap:
     the row is as tall as the 13px number, not as tall as the call. */
  .band li { font-size: 9.5px; line-height: 2.5; padding: 0 1px; gap: 7px; }
  .band li:nth-child(even) { background: #eee !important;
                             -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .band li b { flex-basis: 16px; font-size: 13px; padding-right: 2px;
                border-right-color: #000; }

  /* The defensive sheet: three fronts, eleven rows and six packages each, then the
     blank front under them. Small enough that the whole thing is one sheet, the way
     the offensive side is. */
  .df-fronts { gap: 5px; margin: 0; }
  .front-pic { --fd-scale: 7.5px; --fd-pad: 8px;
               width: 250px; margin: 3px auto 3px;
               border-color: #999; background: none; }
  .front-pic .fd { border-width: 4.5px; border-color: #000; }
  .front-pic .los { border-top-color: #000; }
  /* The formation's own number stays on paper on this sheet -- "BASE" and "GOAL
     LINE" are what you call, and 4-4 and 6-3 are what they are, and the bar has
     room for both. The offensive sheet's .xl-n is a play count, which is why it
     is hidden up there and shown here. */
  .df-front .xl-n { display: inline; float: right; opacity: 1; font-weight: 900; }
  table.xl.df-grid tr.df-gap td { height: 9px; background: none; }
  .df-front { break-inside: avoid; }
  table.xl.df-grid { font-size: 8px; }
  table.xl.df-grid td, table.xl.df-grid th { padding: 0 2px; height: auto;
                                             line-height: 1.25; }
  table.xl.df-grid thead th { font-size: 7px; }
  table.xl.df-grid .df-pos { width: 30px; font-size: 7px; background: none; }
  .calls-page .page-head { display: none; }
  .pk-head { display: none; }
  .pk-sub { display: none; }
  .pk-grid { gap: 0 8px; margin: 0; padding-top: 4px; break-inside: avoid;
             border-top: 1px solid #000; }
  /* Under the blank field, the top rule of whatever comes next is also what closes
     the field off at the bottom -- the field has sidelines and a top, and this is its
     goal line. So no gap above it: a margin would leave the field hanging open with a
     stray rule below it. */
  /* The base strip closes the field off at the bottom the way the board used to: its
     own top rule is the field's goal line, so no margin above it. */
  .bl-strip { margin-top: 0; padding-top: 4px; border-top: 1px solid #000;
              break-inside: avoid; }
  .bl-row { gap: 0; background: none; border-top: 0; }
  .bl-man { padding: 0 2px 1px; font-size: 8px; line-height: 1.2;
            border-left: 1px solid #bbb; }
  .bl-man:first-child { border-left: 0; }
  .bl-man b { font-size: 6.5px; letter-spacing: .2px; color: #000; }
  .bl-card .pk-name { margin-bottom: 1px; }
  .pk-grid.sub-grid { border-top: 0; padding-top: 3px; margin-top: 0;
                      grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 0 5px; }
  /* The three-column hairline rules above count in threes; this grid is six across,
     one row, so every card but the first takes a left rule and none takes a top one. */
  .sub-grid .pk:not(:nth-child(3n + 1)) { border-left: 1px solid #bbb; }
  .sub-grid .pk:nth-child(n + 4) { border-top: 0; padding-top: 0; }
  .sub-grid .pk:nth-child(-n + 3) { padding-bottom: 0; }
  .sub-grid .pk { padding: 0 4px; }
  .sub-grid .pk:first-child { border-left: 0; }
  /* 1.1 rather than 1.25, and it is the SUBS/MOVES header rows that bought it. Eight
     extra rows across the package grid tipped the offensive sheet onto a second page;
     a seventh of a line off each data row pays for them and leaves the sheet at one.
     The type is unchanged -- 7.5px names with 1.1 leading are still a comfortable
     read at arm's length, and test_print_pages.py is what holds the page count. */
  table.xl.pk-subs td { font-size: 7.5px; padding: 0 2px; line-height: 1.0;
                        letter-spacing: -.2px; }
  table.xl.pk-subs .sub-pos { font-size: 6.5px; width: 2.4em; background: none;
                              color: #000; }
  table.xl.pk-subs .sub-out { color: #444; font-weight: 600; }
  table.xl.pk-subs .sub-in { font-weight: 800; }
  table.xl.pk-subs .sub-pos { font-size: 6.5pt; }
  /* The call sheet is the one page a coach prints most, and it prints on whatever is
     in the office. A tint is the first thing a mono laser throws away, so the band
     becomes black type instead.
     It also has to cost almost nothing in height: the offensive sheet is one page and
     eight header rows across the package grid are what tipped it to two. So the print
     header is set solid -- 5.5pt, line-height 1, no padding and no rule of its own --
     which is about a third of a data row. The rule above MOVES stays, because that
     one was already being paid for. */
  table.xl.pk-subs tr.pk-grp th {
    font-size: 5.5pt; letter-spacing: .4px; padding: 0 2px; line-height: 1;
    background: none; color: #000; border-bottom: 0;
  }
  table.xl.pk-subs tr.pk-grp-mv th { border-top: 0.5pt solid #000; padding-top: 0.5px; }
  table.xl.pk-subs .sub-mv .mv-b::before { margin: 0 2px 1px 2px; border-width: 2.5px;
                                           border-right: 0; border-left-color: #000; }
  table.xl.pk-subs .sub-in::before { margin: 0 3px 1px 0; border-width: 2.5px;
                                     border-left-color: #000; border-right: 0; }
  /* 22px of clear space above the line of scrimmage rather than 31. The offensive
     sheet finished 0.04in past the bottom of its page once the Y swap put another
     substitution row on three of the packages, and this is the one block on the
     sheet that is deliberately empty -- it is there to be drawn on in marker, and
     it keeps two and a third inches of room to be drawn in. Taking it out of a
     package or a play list would cost information; taking it from here costs nine
     points of blank paper. */
  .pk-field { margin: 5px 0 0; padding-top: 22px; border-top-color: #000;
              border-left-color: #000; border-right-color: #000; }
  .pk-field .hash { width: 11px; border-top-color: #000; }
  .pk-draw { margin: 0; row-gap: 1px;
             grid-template-columns: 72px 30px 19px 30px 19px 30px 19px 30px
                                    19px 30px 19px 30px 19px 30px 72px; }
  .pk-draw .hn { font-size: 8px; color: #000; }
  .pk-draw .o { border-width: 10px; border-color: #000; }
  .pk-draw .ball { width: 19px; height: 11px; border-color: #000; }
  .pk-draw .ball::after { border-top-color: #000; }
  .pk-draw .pad { height: 172px; }
  /* Hairlines between the cards. These went in when the name bars printed as plain
     black text and six lists of calls ran together into one block of small type. The
     bars are bars on paper now (see .pk-name below), so they do most of that work
     themselves -- but the rules are what separates the SECOND row of cards from the
     first, which a heading at the top of a card cannot do, and they cost nothing. The
     3n counts the three columns .pk-grid sets above: a left rule on every card that is
     not starting a row, a top rule on every card past the first row. */
  .pk { break-inside: avoid; padding: 0 5px; }
  .pk:not(:nth-child(3n + 1)) { border-left: 1px solid #bbb; }
  .pk:nth-child(n + 4) { border-top: 1px solid #bbb; padding-top: 4px; }
  .pk:nth-child(-n + 3) { padding-bottom: 4px; }
  /* A black bar with white type, centred -- the same treatment as .xl-title and the
     LEFT/MIDDLE/RIGHT row, so a package card and a formation block read as the same
     kind of object. It used to print as plain black text on white; `print-color-adjust:
     exact` is what lets the fill survive the print dialog's background-graphics setting,
     and without it the white type would print white on white and the heading would
     vanish. Same lesson as .xl-title, applied to the same problem. */
  .pk-name {
    padding: 1px 3px; font-size: 9px; font-weight: 900; line-height: 1.2;
    text-align: center;
    color: #fff !important; background: #000 !important;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }
  .pk-n { display: none; }
  table.xl.pk-plays td { height: auto; vertical-align: middle; line-height: 1.15; }
  .pk-plays td a { font-size: 7.5px; white-space: nowrap; letter-spacing: -.2px;
                   line-height: 1.15; padding: 0; }
  .pk-any { font-size: 7.5px; line-height: 1.15; }
  /* The heading is a title on paper, not a banner: a 29px h1 and its margin is most of
     half an inch of the one sheet, spent before the first call. The sub-line under it
     is gone entirely now (see write_calls), which is the rest of that half inch.
     Scoped to this page so the rest of the book keeps its headings. */
  .calls-page h1 { font-size: 15px; line-height: 1.2; margin-bottom: 2px; }
}

.plist { display: grid; gap: 12px; grid-template-columns: 1fr; }
@media (min-width: 620px) { .plist { grid-template-columns: repeat(2, minmax(0,1fr)); } }
@media (min-width: 900px) { .plist { grid-template-columns: repeat(3, minmax(0,1fr)); } }
.pcard {
  display: block; text-decoration: none; color: var(--ink); background: var(--panel);
  border: 1px solid var(--line); border-radius: 12px; overflow: hidden;
  box-shadow: var(--shadow); transition: box-shadow .15s, transform .15s, border-color .15s;
}
.pcard:hover {
  box-shadow: var(--shadow-lg); transform: translateY(-2px); border-color: var(--accent);
}
/* The diagrams are ink-on-paper SVGs, so they keep a paper surface in both themes. */
.pcard .thumb { background: #fff; border-bottom: 1px solid var(--line); }
.pcard .thumb img { display: block; width: 100%; height: auto; }
.pcard .body { padding: 11px 13px 13px; }
.pcard h4 { margin: 0 0 7px; font-size: 16px; color: var(--accent-ink); }

.favgrid { display: grid; gap: 12px; grid-template-columns: repeat(2, minmax(0,1fr)); margin-bottom: 6px; }
@media (min-width: 560px) { .favgrid { grid-template-columns: repeat(3, minmax(0,1fr)); } }
/* A short list is not a row with gaps in it. One or two favorites get their own columns
   rather than a third of the row each — capped, so the diagram on a lone card stays a
   card and does not become a poster, and gets the full width of a phone instead of half. */
.favgrid[data-count="1"] { grid-template-columns: minmax(0, 340px); }
.favgrid[data-count="2"] { grid-template-columns: repeat(2, minmax(0, 340px)); }
/* Four in a three-wide grid is three and a straggler. Two rows of two instead. */
.favgrid[data-count="4"] { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.favcard {
  background: var(--panel); border: 1px solid var(--line); border-radius: 12px;
  overflow: hidden; box-shadow: var(--shadow);
}
.favcard .thumb { display: block; background: #fff; border-bottom: 1px solid var(--line); }
.favcard .thumb img { display: block; width: 100%; height: auto; }
.favcard .body { padding: 11px 12px 12px; }
.favcard h4 { margin: 0 0 3px; font-size: 15px; line-height: 1.25; }
.favcard h4 a { text-decoration: none; color: var(--accent-ink); }
.favcard h4 a:hover { text-decoration: underline; }
.favcard .fmeta { display: block; font-size: 11.5px; color: var(--muted); margin-bottom: 10px; }
.favcard .sides { display: flex; gap: 8px; }
.favcard .side {
  flex: 1 1 0; text-align: center; text-decoration: none; font-size: 12.5px;
  font-weight: 700; color: var(--on-accent); background: var(--accent-solid);
  border-radius: 6px; padding: 7px 0;
}
.favcard .side:hover { filter: brightness(1.15); }

.call {
  display: inline-block; font-size: 12.5px; font-weight: 700; letter-spacing: .4px;
  color: var(--on-accent); background: var(--accent-solid); border-radius: 4px;
  padding: 3px 9px;
}
.tag {
  display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: .6px;
  color: var(--muted); background: var(--panel-2); border-radius: 4px; padding: 3px 7px;
}
.tags { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }

/* ---------------------------------------------------------------- the play -- */
article.play {
  background: var(--panel); color: var(--ink); border: 1px solid var(--line);
  border-radius: 14px; padding: 15px; box-shadow: var(--shadow); margin: 0 0 18px;
}
@media (min-width: 700px) { article.play { padding: 20px 22px; } }
article.play > header {
  display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap;
  border-bottom: 2px solid var(--accent-solid); padding-bottom: 10px; margin-bottom: 14px;
}
article.play h2 { margin: 0; font-size: clamp(20px, 4.2vw, 26px); color: var(--accent-ink); }

/* The picture is the main attraction: full width, nothing beside it, and edge to
   edge on a phone where the card padding is worth more as diagram. */
figure.diagram {
  margin: 0 -15px 14px; background: #fff; border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line); overflow: hidden;
}
figure.diagram img { display: block; width: 100%; height: auto; }
@media (min-width: 700px) {
  figure.diagram { margin: 0 0 16px; border: 1px solid var(--line); border-radius: 10px; }
}

.purpose { margin: 0 0 4px; color: var(--ink-2); font-size: 15.5px; max-width: 78ch; }

/* ---------------------------------------------------------- the front toggle --

   The same play, blocked three ways. The tabs sit directly above the diagram because
   the diagram is what changes — putting them anywhere else makes you hunt for what
   moved. All three panels are in the page and the toggle swaps which one is shown, so
   changing front is instant on a sideline with no signal. */
.fronts {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  margin: 14px 0 10px; padding-top: 12px; border-top: 1px solid var(--line);
}
.fronts-label {
  font-size: 11px; font-weight: 700; letter-spacing: 1.3px; text-transform: uppercase;
  color: var(--muted); margin-right: 4px;
}
.dtab {
  cursor: pointer; font: inherit; font-size: 13.5px; font-weight: 700;
  color: var(--accent-ink); background: var(--panel);
  border: 1px solid var(--line); border-radius: 999px; padding: 6px 15px;
  min-height: 36px;          /* a thumb on a phone, not a mouse on a desk */
}
.dtab:hover { border-color: var(--accent-solid); }
.dtab.on {
  background: var(--accent-solid); border-color: var(--accent-solid);
  color: var(--on-accent);
}
.dpanel { display: none; }
.dpanel.on { display: block; }
.block-title .vs { float: right; font-weight: 600; letter-spacing: 0.4px; }
.block-title {
  font-size: 11px; font-weight: 700; letter-spacing: 1.3px; text-transform: uppercase;
  color: var(--muted); margin: 18px 0 2px; padding-top: 12px;
  border-top: 1px solid var(--line);
}
dl.assign { margin: 0; }
@media (min-width: 720px) { dl.assign { columns: 2; column-gap: 30px; } }
dl.assign .row {
  break-inside: avoid; page-break-inside: avoid;
  display: grid; grid-template-columns: 42px minmax(0,1fr); gap: 10px;
  padding: 7px 0; border-bottom: 1px solid var(--line-soft);
}
dl.assign dt { font-weight: 700; color: var(--ink); }
dl.assign dd { margin: 0; color: var(--ink-2); font-size: 15px; }
dl.assign .row.ball dt, dl.assign .row.ball dd { color: var(--red); font-weight: 600; }
dl.assign.holes {
  background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
  padding: 4px 16px; box-shadow: var(--shadow); columns: 1; max-width: 520px;
}
dl.assign.holes dt { color: var(--accent-ink); }
p.legal {
  margin: 6px 0 0; font-size: 14px; color: var(--muted); max-width: 78ch;
  border-left: 3px solid var(--line); padding-left: 12px;
}
ul.coach { margin: 6px 0 0; padding-left: 20px; }
ul.coach li {
  margin-bottom: 6px; color: var(--ink-2); font-size: 15px;
  break-inside: avoid; page-break-inside: avoid;
}

.btn {
  display: inline-block; cursor: pointer; font: inherit; font-size: 13.5px;
  font-weight: 600; color: var(--accent-ink); background: var(--panel);
  border: 1px solid var(--line); border-radius: 999px; padding: 7px 16px;
  text-decoration: none; white-space: nowrap;
}
.btn:hover { background: var(--accent-solid); border-color: var(--accent-solid); color: #fff; }
/* display:inline-block above outranks the browser's own [hidden] rule, so a button
   with the attribute set stays on screen. Same fix as .ddpanel and .scrim. */
.btn[hidden] { display: none; }
.btn.solid {
  background: var(--accent-solid); border-color: var(--accent-solid); color: var(--on-accent);
}
.btn.solid:hover { filter: brightness(1.15); }
.play-actions { margin-left: auto; display: flex; gap: 8px; }

.pager { display: flex; gap: 10px; align-items: stretch; margin: 4px 0 30px; }
.pager > span { flex: 1 1 0; }
.pager a {
  flex: 1 1 0; font-size: 14px; font-weight: 600; color: var(--accent-ink);
  text-decoration: none; background: var(--panel); border: 1px solid var(--line);
  border-radius: 10px; padding: 10px 14px; box-shadow: var(--shadow);
}
.pager a:hover { box-shadow: var(--shadow-lg); border-color: var(--accent); }
.pager a.mid { text-align: center; }
.pager a.nxt { text-align: right; }
.pager .dir {
  display: block; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
  color: var(--muted);
}
@media (max-width: 620px) { .pager a.mid { display: none; } }

/* ------------------------------------------------------------- call sheet -- */
.searchbar {
  display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin: 4px 0 12px;
}
#q {
  flex: 1 1 260px; font: inherit; font-size: 16px; padding: 11px 15px;
  border: 1px solid var(--line); border-radius: 999px; background: var(--panel);
  color: var(--ink); min-width: 0;
}
#q::placeholder { color: var(--muted); }
#q:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
.chips { display: flex; gap: 6px; flex-wrap: wrap; }
.chip {
  cursor: pointer; font: inherit; font-size: 13px; font-weight: 600; color: var(--ink-2);
  background: var(--panel); border: 1px solid var(--line); border-radius: 999px;
  padding: 7px 14px;
}
.chip:hover { border-color: var(--accent); }
.chip[aria-pressed="true"] {
  background: var(--accent-solid); border-color: var(--accent-solid); color: var(--on-accent);
}
/* Filters are grouped and labelled: within a group the choices widen the list, across
   groups they narrow it, and a label on each group is what makes that legible. */
.fgroup { display: flex; align-items: baseline; gap: 10px; margin: 0 0 8px; flex-wrap: wrap; }
.flabel {
  font-size: 11px; text-transform: uppercase; letter-spacing: 1.1px; color: var(--muted);
  min-width: 96px; flex-shrink: 0;
}
@media (max-width: 620px) { .flabel { min-width: 0; width: 100%; } }

.morebtn {
  display: inline-flex; align-items: center; gap: 7px; cursor: pointer; font: inherit;
  font-size: 13px; font-weight: 600; color: var(--accent-ink); background: none;
  border: 0; padding: 6px 0; margin: 2px 0 0;
}
.morebtn::after { content: "▾"; font-size: 11px; }
.morebtn[aria-expanded="true"]::after { content: "▴"; }
.morebtn .badge {
  background: var(--accent-solid); color: var(--on-accent); border-radius: 999px;
  font-size: 11px; padding: 1px 7px; line-height: 1.6;
}
#morefilters { margin-top: 10px; padding-top: 12px; border-top: 1px solid var(--line-soft); }

/* What is applied right now, spelled out. Multi-select accumulates quietly otherwise. */
.activefilters { display: flex; gap: 6px; flex-wrap: wrap; margin: 12px 0 0; }
.pill {
  cursor: pointer; font: inherit; font-size: 12.5px; font-weight: 600;
  color: var(--on-accent); background: var(--accent-solid);
  border: 1px solid var(--accent-solid); border-radius: 999px; padding: 5px 8px 5px 10px;
  display: inline-flex; align-items: center; gap: 6px;
}
.pill .pg { font-weight: 500; opacity: .7; font-size: 11px; text-transform: uppercase;
  letter-spacing: .8px; }
.pill .px { font-size: 15px; line-height: 1; opacity: .8; }
.pill:hover .px { opacity: 1; }

.countline { display: flex; align-items: center; gap: 12px; margin: 12px 0 10px; }
.clearbtn {
  cursor: pointer; font: inherit; font-size: 13px; font-weight: 600;
  color: var(--accent-ink); background: none; border: 0; padding: 0;
  text-decoration: underline;
}
#count { color: var(--muted); font-size: 14px; }
.tablewrap {
  overflow-x: auto; background: var(--panel); border: 1px solid var(--line);
  border-radius: 12px; box-shadow: var(--shadow);
}
table.calls { width: 100%; border-collapse: collapse; min-width: 540px; }
table.calls th, table.calls td {
  text-align: left; padding: 11px 14px; border-bottom: 1px solid var(--line-soft);
  font-size: 14.5px; color: var(--ink);
}
/* On a phone the five-column table needed 540px and scrolled sideways — on the one page
   you actually hold on a sideline. Below 620px each row becomes a card instead: the call
   big at the top, the play name under it, then a labelled meta line. Nothing scrolls. */
@media (max-width: 620px) {
  .tablewrap { overflow-x: visible; }
  table.calls { min-width: 0; }
  table.calls thead { display: none; }
  table.calls, table.calls tbody, table.calls tr, table.calls td { display: block; width: 100%; }
  table.calls tr {
    padding: 12px 14px; border-bottom: 1px solid var(--line);
  }
  table.calls tr:last-child { border-bottom: 0; }
  table.calls td { border: 0; padding: 0; text-align: left; }
  table.calls td[data-label="Call"] { margin-bottom: 2px; }
  table.calls td[data-label="Call"] .call { font-size: 16px; }
  table.calls td[data-label="Play"] { font-size: 15px; margin-bottom: 6px; }
  /* Formation, type and ball read as one line, each behind its own small label. */
  table.calls td[data-label="Formation"],
  table.calls td[data-label="Type"],
  table.calls td[data-label="Ball"] {
    display: inline-block; width: auto; font-size: 13px; color: var(--muted);
    margin-right: 14px;
  }
  table.calls td[data-label="Formation"]::before,
  table.calls td[data-label="Type"]::before,
  table.calls td[data-label="Ball"]::before {
    content: attr(data-label) " "; font-size: 10px; text-transform: uppercase;
    letter-spacing: 1px; color: var(--muted); opacity: .75;
  }
}

table.calls th {
  font-size: 11px; text-transform: uppercase; letter-spacing: 1.1px; color: var(--muted);
  background: var(--panel-2); position: sticky; top: 0;
}
table.calls tbody tr:hover { background: var(--panel-2); }
table.calls a { color: var(--accent-ink); font-weight: 600; text-decoration: none; }
table.calls a:hover { text-decoration: underline; }
table.calls td.c { white-space: nowrap; }
.empty { padding: 26px 16px; color: var(--muted); }

/* ------------------------------------------------------------------- prose -- */
/* ------------------------------------------------------------------- install -- */
/* A practice schedule is read standing up with a whistle in your mouth, so the number
   is the thing you find first and everything else hangs off it. */
/* Full width, like every other page. This was capped at 82ch, which is a measure for
   prose and this page is not prose — it is a stack of practice cards with drill lists
   and play chips in them, and the cap left it a fifth narrower than the call sheet or
   the depth chart sitting one nav item away. The paragraphs inside the cards keep
   their own measure below; that is where the reading actually happens. */
.ins-wrap { max-width: none; }
.ph { margin: 34px 0 14px; padding-bottom: 10px; border-bottom: 2px solid var(--accent-solid); }
.ph:first-child { margin-top: 20px; }
.ph h2 {
  font-size: clamp(17px, 3vw, 21px); color: var(--ink); margin: 0 0 6px; letter-spacing: -.2px;
}

/* ---- the month grid ---- */
/* "What are we doing Tuesday?" is a question about a month, not about a scroll. The
   grid answers it at a glance and every event on it is a link to that practice's own
   page, which is where the plan actually lives. */
.cal-wrap { margin: 20px 0 8px; }
table.cal {
  width: 100%; border-collapse: separate; border-spacing: 0; table-layout: fixed;
  background: var(--panel); border: 1px solid var(--line); border-radius: 12px;
  box-shadow: var(--shadow); overflow: hidden; margin: 0 0 16px;
}
table.cal caption {
  caption-side: top; text-align: left; padding: 12px 14px 10px;
  font-size: clamp(15px, 2.6vw, 18px); font-weight: 700; color: var(--ink);
  letter-spacing: -.2px; background: var(--panel-2);
  border-bottom: 1px solid var(--line);
}
table.cal th {
  padding: 7px 4px; font-size: 10.5px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1px; color: var(--muted); background: var(--panel-2);
  border-bottom: 1px solid var(--line);
}
table.cal th abbr { text-decoration: none; border: 0; }
.cal-cell {
  vertical-align: top; height: 92px; padding: 4px 5px 6px; width: 14.28%;
  border-right: 1px solid var(--line); border-bottom: 1px solid var(--line);
}
table.cal tr > .cal-cell:last-child { border-right: 0; }
table.cal tbody tr:last-child .cal-cell { border-bottom: 0; }
.cal-cell.out { background: var(--panel-2); }
.cal-d {
  display: block; font-size: 11.5px; font-weight: 600; color: var(--muted);
  font-variant-numeric: tabular-nums; margin-bottom: 3px;
}
/* Marked in the browser, not at build time — a "today" baked into a generated page is
   wrong the morning after it is generated. */
.cal-cell.is-past { background: var(--line-soft); }
.cal-cell.is-past .cal-ev { opacity: .62; }
.cal-cell.is-today { background: var(--accent-soft); }
.cal-cell.is-today .cal-d {
  color: var(--on-accent); background: var(--accent-solid); border-radius: 999px;
  min-width: 20px; height: 20px; padding: 0 6px; display: inline-flex;
  align-items: center; justify-content: center; font-size: 11px;
}
.cal-ev {
  display: block; text-decoration: none; border-radius: 7px; padding: 4px 6px;
  background: var(--panel-2); border-left: 3px solid var(--accent-solid);
  margin-bottom: 3px; min-width: 0;
}
.cal-ev[data-phase="season"] { border-left-color: var(--red); }
.cal-ev:hover { background: var(--panel); outline: 1px solid var(--accent); }
.cal-ev-n {
  display: block; font-size: 11.5px; font-weight: 800; color: var(--accent-ink);
  line-height: 1.25; overflow: hidden;
}
.cal-ev-t {
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden; font-size: 11px; line-height: 1.3; color: var(--ink-2);
}
/* On a phone the month is still worth having — you can see the shape of the week —
   but the words do not fit. The cells shrink to the practice number and the list
   underneath carries the reading. */
@media (max-width: 640px) {
  .cal-cell { height: 56px; padding: 3px 2px 4px; }
  .cal-ev { padding: 2px 3px; text-align: center; }
  .cal-ev-t { display: none; }
  .cal-ev-n { font-size: 10.5px; }
}
@media (max-width: 480px) {
  .cal-ev { border-left-width: 2px; }
  .cal-ev-w { display: none; }
  .cal-ev-n { font-size: 12px; }
}
.cal-legend {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px 14px;
  margin: 0 0 6px; font-size: 12px; color: var(--muted);
}
.cal-key {
  width: 11px; height: 11px; border-radius: 3px; display: inline-block;
  margin-right: -6px; background: var(--accent-solid);
}
.cal-key.season { background: var(--red); }
.cal-key.today { background: var(--accent-solid); border-radius: 999px; }
/* Filled in by the browser once it knows what day it is. No display: block here — a
   div is one already, and setting it would outrank the browser's own [hidden] rule
   and leave an empty box on a page built after the last practice. */
.cal-next {
  margin: 16px 0 0; padding: 11px 14px; border-radius: 10px;
  background: var(--panel); border: 1px solid var(--accent); box-shadow: var(--shadow);
  font-size: 13.5px; color: var(--ink-2); text-decoration: none;
}
.cal-next b { color: var(--ink); }
.cal-next span { color: var(--muted); }

/* ---- the practice list under the calendar ---- */
/* One row per practice, in teaching order, with the phase notes still over the top of
   each run. It is the whole schedule as text: it survives a phone, a printer and a
   screen reader, none of which love a month grid. */
.ins-row {
  display: grid; grid-template-columns: 62px minmax(0, 1fr) 20px; gap: 14px;
  align-items: center; text-decoration: none;
  background: var(--panel); border: 1px solid var(--line); border-radius: 12px;
  padding: 11px 14px; margin: 0 0 8px; box-shadow: var(--shadow);
}
.ins-row:hover { border-color: var(--accent); }
.ins-row-n {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: var(--accent-solid); color: var(--on-accent); border-radius: 10px;
  padding: 6px 4px;
}
.ins-row-n small { font-size: 9px; text-transform: uppercase; letter-spacing: 1.1px; opacity: .75; }
.ins-row-n b { font-size: 22px; line-height: 1.1; font-variant-numeric: tabular-nums; }
.ins-row-body { min-width: 0; }
.ins-row-body time { display: block; font-size: 11.5px; font-weight: 700; color: var(--accent-ink); }
.ins-row-body strong { display: block; font-size: 15px; color: var(--ink); margin: 1px 0 3px; }
.ins-row-go { color: var(--muted); font-size: 17px; text-align: right; }
.ins-row:hover .ins-row-go { color: var(--accent-ink); }
@media (max-width: 560px) {
  .ins-row { grid-template-columns: 48px minmax(0, 1fr); gap: 10px; }
  .ins-row-go { display: none; }
  .ins-row-n { flex-direction: row; gap: 6px; padding: 4px 8px; }
  .ins-row-n b { font-size: 16px; }
}

/* ---- one practice, on its own page ---- */
.ins-day { margin-bottom: 26px; }
.ins-day h1.page { margin: 2px 0 6px; }
.ins-day-when { margin: 0; font-size: 14.5px; font-weight: 600; color: var(--accent-ink); }
.ins-day-when.undated { color: var(--muted); font-weight: 500; font-style: italic; }
.ins-day-h {
  display: flex; align-items: center; gap: 12px; margin: 24px 0 10px;
  padding-bottom: 8px; border-bottom: 2px solid var(--accent-solid);
}
.ins-day-h h2 { margin: 0; font-size: 16px; color: var(--ink); letter-spacing: -.2px; }
.ins-day-plan .ins-blk { background: var(--panel); border: 1px solid var(--line); }
.ins-day-plan .ins-huddle {
  margin: 0; padding: 11px 13px; border: 1px solid var(--line); border-radius: 10px;
  background: var(--panel); font-size: 13.5px;
}
.ins-day-plan .ins-blk .ins-play { background: var(--panel-2); }
/* The strip of practice numbers at the top of a day page — the playbar the play pages
   use, with numbers instead of names, so it stays one line for a whole season. */
.playbar.nums a {
  min-width: 34px; text-align: center; font-variant-numeric: tabular-nums;
  font-weight: 700;
}

.ins-blk {
  padding: 11px 13px; background: var(--panel-2); border-radius: 10px; margin: 0 0 10px;
}
.ins-blk:last-child { margin-bottom: 0; }
.ins-blk-h {
  display: flex; align-items: baseline; gap: 8px; margin: 0 0 8px; font-size: 13.5px;
  font-weight: 700; color: var(--ink);
}
.ins-blk-tag {
  background: var(--accent-solid); color: var(--on-accent); font-size: 10px;
  font-weight: 800; text-transform: uppercase; letter-spacing: .6px; border-radius: 999px;
  padding: 2px 9px; white-space: nowrap;
}
.ins-blk-time {
  margin-left: auto; font-size: 12px; font-weight: 600; color: var(--muted);
  font-variant-numeric: tabular-nums; white-space: nowrap;
}
.ins-drills { margin: 0; padding-left: 18px; font-size: 13.5px; color: var(--ink-2); line-height: 1.6; }
.ins-drills li { margin-bottom: 2px; }
/* A progression inside a drill. Tighter and quieter than its parent, because it is
   part of that drill rather than three more things to get through. */
.ins-drills .ins-drills {
  margin: 2px 0 4px; padding-left: 16px; font-size: 12.5px; color: var(--muted);
}
.ins-blk .ins-em:first-of-type { margin-top: 0; }
/* Two position groups running side by side in one block — offense splitting off
   from defense, or linemen from backs — need their own small heading or the drill
   lists below them read as one group's list running twice as long as it is. */
.ins-grp { margin: 0 0 10px; }
.ins-grp:last-child { margin-bottom: 0; }
.ins-grp-h { margin: 0 0 4px; font-size: 13.5px; font-weight: 700; color: var(--ink); }
/* The rotation card: a row a snap, a column a spot. A practice whose point is that
   everybody plays somewhere new is the one practice a coach cannot run out of his
   head -- with thirteen boys and six spots, the thing he loses track of is who has
   not had a turn yet. So the lineup is written out per snap and he reads down it.

   The depth number beside each name is what makes it a plan instead of a list: a row
   of 1s is the first team, and a row with a 6 in it is where tonight's teaching is.
   Depth 1 keeps the ink colour and anything deeper goes grey, so the eye finds the
   boys who are somewhere new without reading a single name. */
.rot-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.rot { border-collapse: collapse; width: 100%; font-size: 13px; }
.rot th, .rot td {
  border: 1px solid var(--line); padding: 4px 7px; text-align: left; white-space: nowrap;
}
.rot thead th {
  background: var(--accent-solid); color: var(--on-accent);
  font-size: 11px; font-weight: 900; letter-spacing: .6px; text-transform: uppercase;
}
.rot tbody tr:nth-child(even) { background: var(--panel-2); }
.rot-n { font-weight: 900; font-variant-numeric: tabular-nums; color: var(--muted); }
.rot-play a {
  font-weight: 800; font-variant-numeric: tabular-nums;
  color: var(--accent-ink); text-decoration: none;
}
.rot-play a:hover { text-decoration: underline; }
/* The number rides after the name rather than above it: a coach reads the name and
   the number answers "is this his spot?" without costing the row a second line. */
.rot-d {
  margin-left: 4px; font-size: 10.5px; font-weight: 800;
  font-variant-numeric: tabular-nums; color: var(--muted);
}
.rot-man.own { font-weight: 700; }
.rot-man.deep { color: var(--ink-2); }
.ins-list { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 9px; }
.ins-play {
  display: inline-flex; flex-direction: column; gap: 1px; text-decoration: none;
  background: var(--panel-2); border: 1px solid var(--line); border-radius: 8px;
  padding: 5px 10px; min-width: 0;
}
.ins-play:hover { border-color: var(--accent); background: var(--panel); }
.ins-play.def { border-left: 3px solid var(--red); }
/* A play being run again rather than taught. Quieter than an install, because the
   block is answering "what is new today" first and this is the honest answer to
   "what else are we running". */
.ins-play.again { border-left: 3px solid var(--line); }
.ins-play.again .ins-call { color: var(--muted); }
/* The water break between blocks. Deliberately quiet — it is punctuation in the run
   of practice, not a coaching block, and it appears after every one of them. */
.ins-water {
  display: flex; align-items: center; gap: 8px; margin: 6px 0 6px 2px;
  font-size: 12.5px; font-weight: 600; color: var(--muted);
  letter-spacing: 0.2px; text-transform: uppercase;
}
.ins-water::before {
  content: ""; width: 3px; height: 14px; border-radius: 2px; background: var(--line);
}
.ins-water-t { font-weight: 500; text-transform: none; letter-spacing: 0; }
.ins-play.form { border-left: 3px solid var(--accent-solid); }
/* A whole formation being gone back through rather than installed. It is a formation
   chip, so it links to the formation, but it is a review, so it reads like one --
   `.again` is written above `.form` and would otherwise lose the border to it. */
.ins-play.again.form { border-left: 3px solid var(--line); }
.ins-n time { display: block; font-size: 11px; line-height: 1.2; margin-top: 3px;
  font-style: normal; opacity: .85; }
.ins-call {
  font-size: 12.5px; font-weight: 700; color: var(--accent-ink);
  font-variant-numeric: tabular-nums;
}
.ins-name { font-size: 11.5px; color: var(--muted); }
.ins-none { font-size: 13px; color: var(--muted); font-style: italic; }
/* The one long-form sentence per block. It is the reason the whole page used to be
   capped; capping the paragraph instead lets the drills and the chips have the room
   and still stops the coaching note running to a hundred characters a line. */
.ins-em { margin: 0; font-size: 14px; color: var(--ink-2); line-height: 1.55; max-width: 84ch; }
.ins-req {
  margin: 7px 0 0; font-size: 12.5px; color: var(--muted);
  padding-left: 11px; border-left: 2px solid var(--line);
}
.ins-huddle {
  margin: 10px 0 0; padding-top: 10px; border-top: 1px dashed var(--line);
  font-size: 13px; color: var(--muted);
}
.ins-huddle-time {
  float: right; font-weight: 600; font-variant-numeric: tabular-nums;
}

/* What is in the book but not yet on the schedule. Deliberately quieter than the
   practices above it — it is a backlog, not a plan. */

/* ------------------------------------------------------------------ rulebook -- */
/* The league's document, reproduced. Their line breaks, indents and runs of spaces are
   meaningful on a page people read out loud at a game, so the text keeps its own
   whitespace (pre-wrap) and still wraps on a phone. Everything below is markup around
   that text — none of it changes a character. */

.rb-hero { margin: 0 0 4px; }
.rb-eyebrow {
  font-size: 11.5px; text-transform: uppercase; letter-spacing: 1.6px;
  color: var(--muted); margin: 0 0 6px; font-weight: 600;
}
.rb-hero h1.page { margin-bottom: 10px; }
.rb-facts {
  display: flex; flex-wrap: wrap; gap: 10px; margin: 16px 0 0; padding: 0;
}
.rb-facts > div {
  background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
  padding: 8px 14px; box-shadow: var(--shadow);
}
.rb-facts dt {
  font-size: 10.5px; text-transform: uppercase; letter-spacing: 1.2px;
  color: var(--muted); font-weight: 600;
}
.rb-facts dd { margin: 2px 0 0; font-size: 14.5px; font-weight: 700; color: var(--ink); }

.rb-toc {
  margin: 20px 0 30px; background: var(--panel); border: 1px solid var(--line);
  border-radius: 12px; padding: 14px 16px 12px; box-shadow: var(--shadow);
}
.rb-toc-h {
  font-size: 11px; text-transform: uppercase; letter-spacing: 1.3px; color: var(--muted);
  margin: 0 0 10px; font-weight: 700;
}
.rb-toc-grid { display: grid; gap: 1px 14px; grid-template-columns: 1fr; }
@media (min-width: 620px) { .rb-toc-grid { grid-template-columns: repeat(2, minmax(0,1fr)); } }
@media (min-width: 980px) { .rb-toc-grid { grid-template-columns: repeat(3, minmax(0,1fr)); } }
.rb-toc a {
  display: flex; gap: 10px; align-items: baseline; text-decoration: none;
  color: var(--ink-2); font-size: 13.5px; padding: 5px 7px; border-radius: 7px;
}
.rb-toc a:hover { background: var(--panel-2); color: var(--accent-ink); }
.rb-toc b {
  color: var(--on-accent); background: var(--accent-solid); font-size: 10.5px;
  min-width: 20px; height: 20px; border-radius: 5px; display: inline-flex;
  align-items: center; justify-content: center; flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}
.rb-toc span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.rulebook { max-width: 82ch; }

/* Section heading: the number as an eyebrow, the title as the headline. Both are the
   document's own words — only the styling separates them. */
.rulebook .rb-h {
  margin: 46px 0 14px; padding: 0 0 10px; border-bottom: 2px solid var(--accent-solid);
  scroll-margin-top: 74px; position: relative;
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 0;
  font-size: clamp(17px, 3vw, 21px); letter-spacing: -.2px; color: var(--ink);
}
.rulebook .rb-h:first-child { margin-top: 0; }
.rb-sn {
  font-size: 11px; letter-spacing: 1.5px; color: var(--accent-ink); font-weight: 800;
  text-transform: uppercase; width: 100%; margin-bottom: 4px;
}
.rb-st { font-weight: 700; }
.rb-top {
  margin-left: auto; align-self: center; text-decoration: none; font-size: 13px;
  color: var(--muted); border: 1px solid var(--line); border-radius: 6px;
  padding: 1px 7px; line-height: 1.5;
}
.rb-top:hover { color: var(--accent-ink); border-color: var(--accent); }

/* Body text. Every line is one paragraph, whitespace preserved. */
.rulebook p {
  margin: 0 0 8px; color: var(--ink-2); font-size: 15px; line-height: 1.6;
  white-space: pre-wrap; tab-size: 4; overflow-wrap: break-word;
}
/* Whole paragraphs are typed in capitals. Same words, but a wall of caps is read
   letter by letter, so give it a little tracking and stop it shouting. */
.rulebook .caps { letter-spacing: .3px; color: var(--ink); }

/* A numbered rule. The number is a chip you can scan down the page and link to. */
.rulebook .rb-rule { margin-top: 14px; padding-left: 0; }
.rb-num {
  display: inline-block; font-weight: 800; color: var(--accent-ink);
  font-variant-numeric: tabular-nums; letter-spacing: 0;
  background: var(--panel-2); border-radius: 5px; padding: 0 6px; margin-right: 2px;
}
.rb-sep2 { color: var(--muted); }

/* List items keep their marker and hang the wrapped lines under the text, not the mark. */
/* The marker sits at the column edge and the wrapped lines hang under the text, not
   under the mark. The literal tab after the marker is kept in the text but given no
   width, or it stacks with the indent and opens a canyon. */
.rulebook .rb-li {
  margin: 0 0 5px 22px; padding-left: 24px; text-indent: -24px; tab-size: 0;
}
.rb-mark {
  display: inline-block; min-width: 20px; font-weight: 700; color: var(--accent-ink);
}

footer.site {
  color: var(--muted); font-size: 13.5px; border-top: 1px solid var(--line);
  margin-top: 36px; padding: 18px 0 40px;
}
footer.site code { background: var(--panel-2); padding: 1px 5px; border-radius: 3px; }
footer.site a { color: var(--accent-ink); }

/* -------------------------------------------------------------------- print -- */
@media print {
  header.site, .drawer, .scrim, .skip, footer.site, .pager, .play-actions, .searchbar,
  .chips, .fgroup, .morebtn, #morefilters, .countline, #count, .clearbtn, .activefilters,
  .btn, .print-intro, .cal-next, .cal-legend, .quicklinks, .ins-row-go, .rb-top,
  .crumbs, .playbar, .fronts { display: none !important; }
  /* Print the front that is on screen, and only that one. A play page printed while
     you are looking at the 4-4 gives you the 4-4 sheet, which is the whole reason
     somebody flipped to it.

     The panel has to *become* the card's flexible column, not merely be visible
     inside it. The one-card-one-sheet layout below works by making the card a flex
     column whose diagram takes whatever height the words leave; wrapping the diagram
     in a plain block put an unflexing box between the two and the diagram stopped
     shrinking — every play page printed on two sheets while the book itself, which
     renders a single panel, still printed on one. */
  .dpanel { display: none !important; }
  .dpanel.on {
    display: flex !important; flex-direction: column;
    flex: 1 1 auto; min-height: 0;
  }
  :root {
    --ink: #111318; --ink-2: #333b49; --muted: #5b6472;
    --line: #dde1e8; --line-soft: #eef1f6; --panel: #fff; --accent-solid: #14213d;
    --accent-ink: #14213d; --red: #b3001b;
  }
  body { background: #fff; color: #000; font-size: 10pt; }
  .wrap { max-width: none; padding: 0; }
  main { padding: 0; }
  /* One card, one sheet — by construction rather than by tuning.

     This used to pin the diagram to a fixed height and trust that whatever came
     underneath would fit. It did, for the book that existed when the number was
     measured. Nineteen plays later, eighteen of forty-one cards were spilling onto a
     second sheet — the ones with five coaching points instead of four.

     So the card is now exactly one page box tall and lays itself out as a column: the
     header, assignments and coaching points take the room they need, and the diagram
     takes everything that is left. A simple play gets a bigger picture than a wordy
     one, which is the right way round, and no card can push past the page because the
     only flexible thing on it is the part that can afford to shrink. */
  article.play {
    box-shadow: none; border: 0; border-radius: 0; padding: 0; margin: 0;
    page-break-after: always; break-after: page;
    height: 100vh;
    display: flex; flex-direction: column;
  }
  article.play:last-of-type { page-break-after: auto; break-after: auto; }
  article.play > header { padding-bottom: 5px; margin-bottom: 8px; }
  article.play h2 { font-size: 16pt; }
  .call, .tag { font-size: 8.5pt; padding: 2px 6px; }
  /* Picture leads. The figure is pinned to a fixed height with the diagram centerd
     inside it, so pagination is identical for a wide play and a deep one and every
     card lands on exactly one sheet. The height below is the largest that still
     leaves room for eleven assignments and the coaching points — measured, not
     guessed, by rendering the book to PDF and counting pages. */
  figure.diagram {
    border: 0; margin: 0 0 4px;
    flex: 1 1 auto; min-height: 0;
    display: flex; align-items: center; justify-content: center;
  }
  figure.diagram img { width: auto; height: auto; max-width: 100%; max-height: 100%; }
  /* A defensive front's notes paragraph is for planning, not for holding the card on a
     sideline, and dropping it is what buys the diagram its height. */
  .purpose, .legalblock { display: none; }
  /* Defensive rules run longer than offensive ones. Nothing to special-case any
     more: their assignments simply claim more of the column and the diagram keeps
     the rest. */
  .block-title { font-size: 8pt; margin: 5px 0 0; padding-top: 4px; }
  dl.assign { columns: 3; column-gap: 16px; }
  dl.assign .row {
    padding: 1px 0; grid-template-columns: 28px minmax(0,1fr); gap: 5px; border: 0;
  }
  dl.assign dd, dl.assign dt { font-size: 8pt; line-height: 1.32; }
  article.play ul.coach { columns: 3; column-gap: 18px; margin-top: 3px; }
  ul.coach li { font-size: 8pt; line-height: 1.32; margin-bottom: 2px; }
  a[href]::after { content: ""; }
  /* A play printed from its own page — or from the print book, which prints every play
     the same way — is the graphic and nothing else. The diagram carries the play's name
     and code in its corners, so the page's header, the assignments and the coaching
     points all go, and the diagram takes the sheet. */
  main.play-page article.play > header, main.play-page .block-title,
  main.play-page dl.assign, main.play-page ul.coach { display: none !important; }
  /* And the graphic fills the sheet. The rule above only lets a diagram shrink to fit,
     never grow, so on its own it printed at screen size in the middle of the paper.
     Sized to the page box instead, contained so it keeps its shape. */
  main.play-page figure.diagram { margin: 0; }
  main.play-page figure.diagram img {
    width: 100%; height: 97vh; max-height: none; object-fit: contain;
  }

  /* A practice plan is one sheet, held on the field.

     This is the same argument the play cards make, and it reaches the same answer: a
     coach standing on a field is holding one piece of paper, and anything that spills
     onto a second sheet is something he is not going to see. Practices 1-4 fitted by
     luck — they are the short ones. The three that carry position groups, an install
     block and a scrimmage did not, and nothing was checking. */

  .ins-day, .ins-day-plan { padding-right: 10px; }
  .ins-day { margin-bottom: 10px; }
  .ins-day h1.page { font-size: 16pt; margin: 0 0 2px; }
  .rb-eyebrow { font-size: 8.5pt; margin: 0 0 1px; }
  .ins-day-when { font-size: 9.5pt; }
  .ins-day-h { margin: 10px 0 6px; padding-bottom: 3px; border-bottom-width: 1.5px; }
  .ins-day-h h2 { font-size: 12pt; }

  /* Blocks lose their panel fill — a background is a print-settings gamble, and the
     tag and the time already say where one block ends and the next begins. */
  .ins-day-plan .ins-blk, .ins-blk {
    background: none; border: 0; border-top: 1px solid var(--line);
    border-radius: 0; padding: 6px 0 4px; margin: 0;
    break-inside: avoid; page-break-inside: avoid;
  }
  .ins-blk-h { margin: 0 0 3px; font-size: 10.5pt; }
  .ins-blk-tag { font-size: 8pt; padding: 0 5px; }
  .ins-blk-time { font-size: 9.5pt; }
  .ins-em { font-size: 9.5pt; line-height: 1.4; }
  .ins-drills { font-size: 9.5pt; line-height: 1.45; padding-left: 15px; }
  .ins-drills li { margin-bottom: 0; }
  .ins-drills .ins-drills { font-size: 8.5pt; padding-left: 13px; margin: 0 0 1px; }
  .ins-req { font-size: 8.5pt; margin-top: 4px; }

  /* Position groups run side by side. They are two independent lists that happen on
     the field at the same time, so stacking them was only ever a phone compromise. */
  .ins-grp { margin: 0; break-inside: avoid; page-break-inside: avoid; }
  .ins-grp-h { font-size: 9.5pt; margin: 0 0 2px; }
  .ins-grps {
    display: grid; grid-auto-flow: column; grid-auto-columns: 1fr; gap: 10px;
  }

  /* The rotation card is the one thing on this page a coach holds while boys are
     moving, so it prints with a rule on every cell -- his thumb is the only thing
     keeping his place, and a tint alone is not enough to find the row again after he
     has looked up at the field. Nothing to scroll on paper either: the table simply
     is as wide as the sheet. */
  .rot-wrap { overflow: visible; }
  .rot { font-size: 8.5pt; width: 100%; }
  .rot th, .rot td { border: 0.5pt solid #000; padding: 1.5pt 3pt; }
  .rot thead th {
    background: #000 !important; color: #fff !important; font-size: 7pt;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }
  .rot tbody tr:nth-child(even) { background: #eee !important;
    -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .rot-play a { color: #000; }
  .rot-d { font-size: 6.5pt; color: #444; }
  .rot-man.deep { color: #000; }

  .ins-list { gap: 3px 6px; margin-bottom: 4px; }
  .ins-play { padding: 0 5px; background: none; }
  .ins-call { font-size: 9pt; }
  /* The teaching name under the call is what a coach already knows by the time he is
     holding the sheet — the call is the thing he reads out. On paper it goes, and the
     chips fit a line instead of two. */
  .ins-name { display: none; }

  /* The water break is punctuation. On screen it is a quiet line between blocks; on
     paper it is a run of five identical lines competing with the coaching, so it
     shrinks to a mark the eye skips until it wants it. */
  .ins-water { margin: 3px 0 0 1px; font-size: 8pt; gap: 6px; }
  .ins-water::before { height: 9px; }

  .ins-huddle { margin: 7px 0 0; padding-top: 6px; font-size: 9.5pt; }

  /* Depth chart: one rotation per sheet, offense and defense side by side on it.
     Hand the starters' sheet to the group that is on the field and the second's to
     the group that is coming on, and neither is holding the other's paper.

     Break *before* each rotation after the first rather than after every one. A
     trailing break-after emits a blank final sheet, and :last-of-type does not
     save you from it: the sections are not the only element type under main, so
     the selector misses and you print three pages for two rotations. Measured
     with test_print_pages.py, which is why this is a + selector and not a comment
     apologising for the extra page. */
  .dc-side + .dc-side { page-break-before: always; break-before: page; }
  /* A board split down the middle of a row is unreadable on a clipboard. */
  .dc-band, .dc-pos { break-inside: avoid; page-break-inside: avoid; }
  /* No break-inside:avoid on .dc-side itself. A side already starts at the top of a
     fresh sheet, so keeping it whole can never move it anywhere useful — and on a
     sheet too small to hold it, the browser honours the rule by emitting a blank
     page first. Measured: it turned a two-page overflow into a three. */
  .dc-side { margin: 0; }
  /* Background fills are a print-settings gamble; the heading is already spelled
     out, so print it as plain text with a rule under it. Home, defense and the
     depth chart all use .hero-head, and white-on-navy vanished whenever the
     browser left background graphics off. */
  .hero-head {
    background: none; color: #000; padding: 0 0 2px; margin: 8px 0 6px;
    border-bottom: 2px solid #000; border-radius: 0; display: block; font-size: 14pt;
    break-after: avoid; page-break-after: avoid;
  }
  .dc-side .hero-head { margin: 0 0 4px; }
  .rot-sub { font-size: 8pt; opacity: 1; }
  .rot-h { font-size: 7pt; margin: 4px 0 2px; }
  /* The offensive sheet finished 0.05in past the bottom of the page -- four bands,
     a heading and six packages, and it was the gaps between them rather than the
     content. These four rules buy about 0.16in back. Measured, not estimated: the
     board is 7.84in tall against a 7.79in page, so there is no room to be casual
     about spacing here and anything added later has to find its own. */
  .dc-field { gap: 3px; margin: 0 0 2px; }
  .dc-band { gap: 4px; }
  .dc-side .hero-head { margin: 0 0 2px; }
  .dc-pkgs { margin-top: 6px; }
  /* The offense's rotations, on paper: the rule black, and the type well up from the
     board's 8pt -- the offensive sheet ends two inches short of its page now that
     the six package cards are gone, and this spends some of it. */
  .dc-rots { margin-top: 10px; border-top: 2pt solid #000; padding-top: 3px; }
  .dc-rots .rot-h { font-size: 9pt; color: #000; }
  .dc-rot .dc-pos-h .dc-abbr { font-size: 16pt; line-height: 1.35; }
  .dc-rot .dc-names li { font-size: 18pt; line-height: 1.3; padding: 2px 6px; gap: 5px; }
  .dc-rot .dc-names li b { flex-basis: 16px; font-size: 12pt; }
  .dc-rot .dc-names li.starter { font-size: 20pt; line-height: 1.3; }
  /* The defensive sheet has room the offensive one does not -- eleven spots in three
     bands instead of four, and two fewer packages. Rather than leave that as white
     space under the board, the packages go to the foot of the page and the three
     bands spread into what is left, so the front is drawn at the size the paper can
     afford. The offense is untouched: it finishes 0.05in inside its page and has
     nothing to give.

     min-height rather than height, and 7.4in of a 7.79in page, so the sheet can
     still grow if a name is added without the whole thing tipping onto a third. */
  .dc-side[data-side="defense"] {
    display: flex; flex-direction: column; min-height: 7.4in;
  }
  .dc-side[data-side="defense"] .dc-field {
    flex: 1 1 auto; justify-content: space-evenly;
  }
  .dc-side[data-side="defense"] .dc-pkgs { margin-top: auto; }
  .dc-pos { box-shadow: none; border-color: #000; border-radius: 0; }
  /* The bar prints filled, the same as it looks on screen, with print-color-adjust
     forcing it through -- the same thing the wristband pouches already do.
     Be clear about the risk rather than pretending it away: this is white type on a
     black fill, so a browser told to skip background graphics prints nothing at all
     where the position should be. There is no CSS fallback for that -- the rule
     underneath still draws, but the name of the spot goes with the fill. Printing
     this page needs "Background graphics" left on, which is the same thing the
     wristbands need. The alternative is black type on white, which always prints and
     is what this was before. */
  .dc-pos-h {
    background: #000 !important; color: #fff !important;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
    border-bottom: 1.5pt solid #000; padding: 0 3px;
  }
  .dc-pos-h .dc-abbr { font-size: 8.5pt; line-height: 1.3; }
  /* The long name goes. It is "Right outside linebacker (Rhino)" under a four-letter
     bar, it wraps to three lines in a column this narrow, and it is the difference
     between each side fitting its sheet and not. The abbreviation is what a coach
     reads anyway, and the full names are on the defensive front pages. */
  .dc-pos-h .dc-label { display: none; }
  /* Set solid. A card is up to six names tall and there are four bands down the
     offensive sheet, so a point of leading on a name row is paid for twenty-four
     times and it was the difference between this board fitting its sheet and
     spilling onto a third. Measured with the same script that counts the pages. */
  .dc-names { padding: 0; }
  .dc-names li { padding: 0 3px; font-size: 8pt; line-height: 1.16; font-weight: 700;
                 color: #000; gap: 3px; }
  .dc-names li b { flex-basis: 9px; font-size: 6.5pt; color: #000; }
  .dc-names li.starter { font-size: 8.5pt; line-height: 1.2; font-weight: 800; }
  .dc-names li.starter b { color: #000; }
  .dc-names li:nth-child(even) { background: none; }
  .dc-open { font-size: 7.5pt; padding: 1px 3px; }
  .dc-band-h { font-size: 6.5pt; color: #000; }
  .dc-band-alt { border-top-color: #000; }
  /* Packages on paper: two rows of three, packed tight enough that each side of the
     ball still fits its one sheet after the tight ends joined the box. */
  /* Six cards packed three points apart, each outlined in the same hairline grey the
     tables use, read as one grey field of small names. A black rule and a real gap
     make each package a block you can find with a thumb. Both are afforded: turning
     the sheet left the tighter of the two sides about 78 points spare, and this
     spends roughly 30 of them. Border, not background: a fill here is a print-dialog
     setting, a rule is not. */
  .dc-pkgrow { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 7px 9px; }
  .dc-pkg { gap: 4px; padding: 3px 5px; box-shadow: none; border-radius: 0;
            border: 1.5pt solid #000; }
  /* Filled on paper too, same bargain as the position bars: it needs background
     graphics left on, and without them the package name goes white on white. */
  .dc-pkg-h {
    margin: -2px -4px 3px; padding: 1px 4px; font-size: 8pt;
    background: #000 !important; color: #fff !important;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }
  .dc-pkg-slot { min-height: 0; padding: 0; font-size: 7pt; line-height: 1.15; }
  .dc-pkg-slot[data-spot]::before { flex-basis: 36px; font-size: 6.5pt; letter-spacing: 0; }
  .dc-pkg-slot + .dc-pkg-slot { margin-top: 0; }
  .dc-pkg-slot[data-spot="X"],
  .dc-pkg-slot[data-spot="LT"],
  .dc-pkg-slot[data-spot="LOLB"],
  .dc-pkg-slot[data-spot="LC"] { margin-top: 1px; padding-top: 1px; }
  .dc-subcard { flex-basis: 56%; min-width: 120px; max-width: none; padding: 2px 2px; border-radius: 0; }
  .dc-subcard-h { font-size: 8pt; margin: 0 0 1px; }
  .dc-sub-empty { font-size: 8pt; }
  table.dc-sub { font-size: 8pt; }
  table.dc-sub th, table.dc-sub td { padding: 0 2px 0 0; }
  table.dc-sub th:last-child, table.dc-sub td:last-child { padding-left: 2px; }
  /* The defence carries a four-letter spot where the offense carries one or two, so
     its rows are the widest on the sheet even after they learned to wrap. Half a
     point of type is what clears them; the offense needs none and keeps its own. */
  .dc-side[data-side="defense"] table.dc-sub { font-size: 7.5pt; }
  table.dc-sub thead th { font-size: 6pt; }
  /* A tint that survives a mono laser: printers drop a light background and the band
     would come out as nothing but a gap. Black type on a hairline-boxed strip reads
     at 6pt either way. */
  table.dc-sub > caption {
    font-size: 6pt; letter-spacing: .6px; padding: 0 2px; margin: 0 0 1px;
    background: transparent; color: #000; border: 0; border-bottom: 0.75pt solid #000;
    border-radius: 0;
  }
  .dc-sub-pos { font-size: 7pt; }
  table.dc-sub.dc-moved { margin-top: 3px; padding-top: 2px; border-top-color: #000; }
  .dc-mv .mv-b::before { margin: 0 3px 1px 3px; border-width: 2.5px;
                         border-right: 0; border-left-color: #000; }
  .dc-tools { display: none; }
  .dc-bar { margin: 0 0 3px; display: block; }
  /* The title block is the price of the first sheet and it is paid in rows. */
  h1.page { font-size: 14pt; margin: 0 0 2px; }
  .page-head { display: block; margin: 0 0 4px; }

  /* Listing pages: cards and schedule rows as ink, not panels, and never split
     down the middle of a card. The same background-graphics gamble as the depth
     chart headings — white-on-navy chips become black type. */
  .pcard, .fcard, .ins-row, .callout, .rb-facts > div, .rb-toc {
    box-shadow: none; break-inside: avoid; page-break-inside: avoid;
  }
  .pcard, .fcard, .ins-row { border-radius: 0; }
  .ins-row-n {
    background: none !important; color: #000;
    border: 1px solid #000; border-radius: 0;
  }
  .fcard .fcall code, .rb-toc b, .rb-num, .call, .tag, .ins-blk-tag {
    background: none; color: #000; padding: 0 4px; border: 1px solid #000;
  }
  .pcard .call { display: none; }
  .section-head, .ph {
    color: #000; border-bottom-color: #000; margin: 12px 0 8px;
    break-after: avoid; page-break-after: avoid;
  }
  table.cal caption { background: none; color: #000; }
  .cal-cell { height: auto; min-height: 28px; }
}
"""

SITE_JS = """
/* The defensive-front toggle on a play page.

   Every front's diagram and assignments are already in the page, so this only moves a
   class. Two things make it worth its twenty lines: the choice is remembered, because
   a coach who has scouted the team they are playing wants every play in the book in
   that front and not to press a button fifty-six times; and it works on the print
   page too, where several plays are on one document at once. */
(function () {
  var KEY = 'sayville.front.v2';
  var groups = [].slice.call(document.querySelectorAll('.play'));
  if (!groups.length) return;

  function apply(play, front) {
    var hit = false;
    [].forEach.call(play.querySelectorAll('.dpanel'), function (p) {
      var on = p.dataset.front === front;
      p.classList.toggle('on', on);
      hit = hit || on;
    });
    [].forEach.call(play.querySelectorAll('.dtab'), function (t) {
      var on = t.dataset.front === front;
      t.classList.toggle('on', on);
      t.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    return hit;
  }

  function show(front) {
    groups.forEach(function (play) { apply(play, front); });
    try { localStorage.setItem(KEY, front); } catch (e) { /* private window */ }
  }

  groups.forEach(function (play) {
    [].forEach.call(play.querySelectorAll('.dtab'), function (tab) {
      tab.addEventListener('click', function () { show(tab.dataset.front); });
    });
  });

  /* A remembered front that this build no longer has would blank the diagram, so it
     is only applied if a panel actually answers to it. */
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) { saved = null; }
  if (saved && groups[0].querySelector('.dpanel[data-front="' + saved + '"]')) {
    show(saved);
  }
}());

/* Site navigation: hamburger drawer on a phone, dropdown on a desktop. */
(function () {
  var burger = document.getElementById('burger');
  var drawer = document.getElementById('drawer');
  var scrim = document.getElementById('scrim');
  var close = document.getElementById('dclose');
  var drops = [
    [document.getElementById('ddbtn'), document.getElementById('ddpanel')],
    [document.getElementById('dfbtn'), document.getElementById('dfpanel')]
  ].filter(function (d) { return d[0] && d[1]; });

  function openDrawer(on) {
    if (!drawer) return;
    if (on) drawer.hidden = false;
    // Let the element paint before transitioning in, or it jumps instead of sliding.
    requestAnimationFrame(function () { drawer.classList.toggle('open', on); });
    scrim.hidden = !on;
    burger.setAttribute('aria-expanded', on ? 'true' : 'false');
    document.body.classList.toggle('locked', on);
    if (!on) setTimeout(function () {
      if (!drawer.classList.contains('open')) drawer.hidden = true;
    }, 250);
  }

  function openDrop(which, on) {
    drops.forEach(function (d) {
      var show = on && d === which;
      d[1].hidden = !show;
      d[0].setAttribute('aria-expanded', show ? 'true' : 'false');
    });
  }

  function anyDropOpen() {
    return drops.some(function (d) { return !d[1].hidden; });
  }

  if (burger) burger.addEventListener('click', function () {
    openDrawer(burger.getAttribute('aria-expanded') !== 'true');
  });
  if (close) close.addEventListener('click', function () { openDrawer(false); burger.focus(); });
  if (scrim) scrim.addEventListener('click', function () { openDrawer(false); });

  drops.forEach(function (d) {
    d[0].addEventListener('click', function (e) {
      e.stopPropagation();
      openDrop(d, d[1].hidden);
    });
  });
  document.addEventListener('click', function (e) {
    if (!anyDropOpen()) return;
    var inside = drops.some(function (d) {
      return d[1].contains(e.target) || e.target === d[0];
    });
    if (!inside) openDrop(null, false);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (anyDropOpen()) openDrop(null, false);
    if (drawer && drawer.classList.contains('open')) { openDrawer(false); burger.focus(); }
  });
  // Crossing the breakpoint with the drawer open would leave the page scroll locked.
  window.addEventListener('resize', function () {
    if (window.innerWidth >= 1000 && drawer && drawer.classList.contains('open')) {
      openDrawer(false);
    }
    if (window.innerWidth < 1000) openDrop(null, false);
  });

  // Bring the current play into view in whichever menu is open.
  [document.getElementById('ddpanel'), document.getElementById('dfpanel'),
   drawer].forEach(function (root) {
    if (!root) return;
    var here = root.querySelector('.mplay.here');
    if (here) here.scrollIntoView({ block: 'nearest' });
  });
})();

/* The install calendar: which square is today, which practice is next.
   Both are done here rather than in the generator on purpose — a "today" baked into a
   static page is wrong the morning after the page was built, and this site is rebuilt
   whenever a play changes, not every night. */
(function () {
  var cells = document.querySelectorAll('.cal-cell[data-date]');
  if (!cells.length) return;
  var now = new Date();
  var today = now.getFullYear() + '-' +
    String(now.getMonth() + 1).padStart(2, '0') + '-' +
    String(now.getDate()).padStart(2, '0');

  var next = null;
  cells.forEach(function (cell) {
    var d = cell.dataset.date;
    if (d === today) cell.classList.add('is-today');
    else if (d < today) cell.classList.add('is-past');
    var ev = cell.querySelector('.cal-ev');
    if (ev && !next && d >= today) next = { cell: cell, ev: ev, date: d };
  });

  var box = document.getElementById('calnext');
  if (!box || !next) return;
  var when = next.date === today ? 'Today' : new Date(next.date + 'T12:00:00')
    .toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
  var name = next.ev.querySelector('.cal-ev-n');
  var focus = next.ev.querySelector('.cal-ev-t');
  box.innerHTML = '<b>Next up &mdash; ' + when + '.</b> ' +
    '<a href="' + next.ev.getAttribute('href') + '">' +
    (name ? name.textContent : 'Next practice') + '</a> ' +
    '<span>' + (focus ? focus.textContent : '') + '</span>';
  box.hidden = false;
  next.ev.classList.add('is-next');
})();

/* Arrow keys walk through the plays in a formation. */
(function () {
  var main = document.querySelector('main');
  if (!main) return;
  var prev = main.dataset.prev, next = main.dataset.next;
  if (!prev && !next) return;
  document.addEventListener('keydown', function (e) {
    var t = e.target.tagName;
    if (t === 'INPUT' || t === 'TEXTAREA' || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === 'ArrowLeft' && prev) location.href = prev;
    if (e.key === 'ArrowRight' && next) location.href = next;
  });
})();

/* Call sheet filtering.

   Every chip belongs to a group (formation, type, zone, direction, carrier). Picking
   two chips in the SAME group widens the list — Regular I or Split Backs. Picking
   chips in DIFFERENT groups narrows it — Split Backs AND runs. The old single-string
   filter could not express that at all: formation and type shared one exclusive group,
   so "Split Backs runs" quietly turned into "all runs". */
(function () {
  var q = document.getElementById('q');
  if (!q) return;
  var rows = Array.prototype.slice.call(document.querySelectorAll('#calls tbody tr'));
  var chips = Array.prototype.slice.call(document.querySelectorAll('.chip'));
  var count = document.getElementById('count');
  var empty = document.getElementById('empty');
  var clear = document.getElementById('clear');
  var moreBtn = document.getElementById('morebtn');
  var more = document.getElementById('morefilters');
  var badge = document.getElementById('morebadge');
  var summary = document.getElementById('activefilters');
  var total = rows.length;
  var active = {};

  // Groups whose chips live in the collapsed panel, so an active filter there can be
  // reported on the toggle instead of being hidden.
  var HIDDEN_GROUPS = ['zone', 'dir', 'carrier'];

  function chosen(group) { return active[group] || []; }

  function activeTotal() {
    var n = 0;
    for (var g in active) n += active[g].length;
    return n;
  }

  function apply() {
    var term = q.value.trim().toLowerCase();
    var n = 0;
    rows.forEach(function (r) {
      var show = true;
      for (var g in active) {
        var picked = active[g];
        // An empty group is not a filter — it means "any".
        if (picked.length && picked.indexOf(r.dataset[g]) === -1) { show = false; break; }
      }
      if (show && term && r.dataset.search.indexOf(term) === -1) show = false;
      r.hidden = !show;
      if (show) n++;
    });

    var filtered = activeTotal() > 0 || term;
    count.textContent = filtered
      ? n + ' of ' + total + (total === 1 ? ' play' : ' plays')
      : total + (total === 1 ? ' play' : ' plays');
    empty.hidden = n !== 0;
    clear.hidden = !filtered;

    var hiddenCount = 0;
    HIDDEN_GROUPS.forEach(function (g) { hiddenCount += chosen(g).length; });
    badge.hidden = hiddenCount === 0;
    badge.textContent = hiddenCount;

    drawSummary();
  }

  /* Every filter currently applied, spelled out and individually removable.

     Multi-select means a second click on a different formation ADDS it rather than
     switching to it — pick Regular I then Split Backs and you are looking at every
     plays, not five. That is correct behaviour and it is also the easiest thing in
     the world to do by accident, so what is applied has to be readable in one glance
     rather than inferred from which chips look dark. */
  function drawSummary() {
    summary.innerHTML = '';
    var any = false;
    chips.forEach(function (c) {
      if (chosen(c.dataset.group).indexOf(c.dataset.value) === -1) return;
      any = true;
      var pill = document.createElement('button');
      pill.type = 'button';
      pill.className = 'pill';
      pill.innerHTML = '<span class="pg">' + c.dataset.glabel + '</span> '
        + c.dataset.label + '<span class="px">\\u00d7</span>';
      pill.setAttribute('aria-label', 'Remove filter ' + c.dataset.glabel + ' '
        + c.dataset.label);
      pill.addEventListener('click', function () { c.click(); });
      summary.appendChild(pill);
    });
    summary.hidden = !any;
  }

  q.addEventListener('input', apply);

  chips.forEach(function (c) {
    c.addEventListener('click', function () {
      var g = c.dataset.group, v = c.dataset.value;
      var picked = active[g] || (active[g] = []);
      var at = picked.indexOf(v);
      if (at === -1) picked.push(v); else picked.splice(at, 1);
      c.setAttribute('aria-pressed', at === -1 ? 'true' : 'false');
      apply();
    });
  });

  clear.addEventListener('click', function () {
    active = {};
    chips.forEach(function (c) { c.setAttribute('aria-pressed', 'false'); });
    q.value = '';
    apply();
    q.focus();
  });

  if (moreBtn && more) moreBtn.addEventListener('click', function () {
    var open = moreBtn.getAttribute('aria-expanded') === 'true';
    moreBtn.setAttribute('aria-expanded', open ? 'false' : 'true');
    more.hidden = open;
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement !== q) { e.preventDefault(); q.focus(); }
    if (e.key === 'Escape' && document.activeElement === q) { q.value = ''; apply(); }
  });
  apply();
})();

"""

# ------------------------------------------------------------------- helpers --

# GitHub Pages serves the stylesheet and the script with `cache-control: max-age=600`
# and no fingerprint in the URL. For ten minutes after a deploy a returning visitor can
# therefore hold a cached OLD site.js while fetching a NEW page — and the two halves are
# not independent. When the call sheet's chips changed from `data-filter` to
# `data-group`/`data-value`, that pairing stopped filtering entirely: the old script
# looked for an attribute the new markup no longer had.
#
# Stamping the content hash into the URL makes a changed asset a different URL, so the
# browser cannot pair new markup with a stale script. The old file stays cached and
# simply stops being asked for.


def asset_url(name: str, content: str) -> str:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:10]
    return f"assets/{name}?v={digest}"


def versioned(path: str) -> str:
    """A generated card's URL, stamped with its content hash for the same reason.

    The cards had no fingerprint, and a browser kept them while the page around them
    changed: after the Z became the Z, a coach printed a play page titled Z with a
    card that still said Z. A changed card is now a different URL.
    """
    file = Path(__file__).resolve().parent.parent / path
    if not file.is_file():
        return path
    return f"{path}?v={hashlib.sha256(file.read_bytes()).hexdigest()[:10]}"


def css_url() -> str:
    return asset_url("site.css", SITE_CSS.strip() + "\n")


def js_url() -> str:
    return asset_url("site.js", SITE_JS.strip() + "\n")


# Small inline icons — no external asset, no network request, and they inherit
# `currentColor` so they follow the surrounding text through light and dark mode.
_ICON_PATHS = {
    "search": '<circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "calendar": ('<rect x="3" y="4" width="18" height="17" rx="2"/>'
                 '<line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/>'
                 '<line x1="3" y1="10" x2="21" y2="10"/>'),
    "shield": '<path d="M12 2 L20 6 V11 C20 16.5 16.5 20.5 12 22 C7.5 20.5 4 16.5 4 11 V6 Z"/>',
    "printer": ('<path d="M6 9V3h12v6"/><rect x="5" y="9" width="14" height="7" rx="1"/>'
                '<path d="M8 14h8v7H8z"/>'),
}


def icon(name: str, cls: str = "icon") -> str:
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true">{_ICON_PATHS[name]}</svg>')


def f_href(form: dict) -> str:
    return f"f-{form['id']}.html"


def p_href(play: dict) -> str:
    return f"p-{play['id']}.html"


def d_href(front: dict) -> str:
    return f"d-{front['id']}.html"


def def_src(front: dict) -> str:
    return versioned(f"defense/cards/{front['id']}-field.svg")


def card_src(form: dict, play: dict, front: str = blocking.DEFAULT_FRONT,
             full: bool = False) -> str:
    suffix = "" if full else "-field"
    return versioned(f"playbook/{form['id']}/cards/{play['id']}-{front}{suffix}.svg")


def resolved(play: dict, front: str) -> dict:
    """This play's assignments against one front, resolved by render.py before we ran."""
    return play["_resolved"][front]


def our_fronts(defenses: dict) -> dict:
    """The defensive playbook: the fronts we call, not the ones we expect to face.

    A scout front is in `defense/` because every offensive card is drawn against it,
    not because anybody is going to call it on a Saturday. Putting it in the defensive
    book would be telling nine-year-olds to learn a defence we do not play.
    """
    return {fid: f for fid, f in defenses.items() if not f.get("scout")}


def formation_icon_src(form: dict) -> str:
    return versioned(f"playbook/{form['id']}/cards/{form['id']}-icon.svg")


def defense_menu(defenses: dict, active_def: str) -> str:
    rows = "".join(
        f'<a class="mplay{" here" if fid == active_def else ""}" href="{d_href(f)}">'
        f'<span>{esc(f["call"])}</span><em>{esc(f["name"])}</em></a>'
        for fid, f in our_fronts(defenses).items()
    )
    return (
        f'<section class="mgrp">'
        f'<a class="mgh" href="defense.html">Fronts'
        f'<span class="mgn">{len(our_fronts(defenses))} legal</span></a>'
        f'<div class="mplays">{rows}</div></section>'
    )


def menu_groups(formations: list[dict], active_form: str, active_play: str) -> str:
    """The formations-and-plays part of the menu, shared by the desktop dropdown
    and the mobile drawer."""
    out = []
    for form in formations:
        plays = "".join(
            f'<a class="mplay{" here" if p["id"] == active_play else ""}" '
            f'href="{p_href(p)}"><span>{esc(p["name"])}</span>'
            f'<em>{esc(p.get("call", ""))}</em></a>'
            for p in form["_plays"]
        )
        out.append(
            f'<section class="mgrp">'
            f'<a class="mgh{" active" if form["id"] == active_form else ""}" '
            f'href="{f_href(form)}">{esc(form_label(form))}'
            f'<span class="mgn">{len(form["_plays"])} plays</span></a>'
            f'<div class="mplays">{plays}</div></section>'
        )
    return "".join(out)


NAV_LINKS = [("index.html", "Home", "home"),
             ("install.html", "Install", "install"),
             ("calls.html", "Call sheet", "calls"),
             ("wristbands.html", "Wristbands", "bands"),
             ("depth-chart.html", "Depth Chart", "depth")]


def page(
    title: str,
    body: str,
    formations: list[dict],
    active_nav: str = "",
    active_form: str = "",
    active_play: str = "",
    active_def: str = "",
    defenses: dict | None = None,
    description: str = "",
    landscape: bool = False,
    page_rule: str = "",
    main_attrs: str = "",
) -> str:
    def link(href, label, key, cls="lnk"):
        on = " active" if key == active_nav else ""
        return f'<a class="{cls}{on}" href="{href}">{esc(label)}</a>'

    groups = menu_groups(formations, active_form, active_play)
    dgroups = defense_menu(defenses or {}, active_def)
    off_open = " active" if active_form else ""
    def_open = " active" if active_def or active_nav == "defense" else ""

    desk = (
        link(*NAV_LINKS[0])
        + f'<button type="button" class="lnk drop{off_open}" id="ddbtn" '
        f'aria-expanded="false" aria-controls="ddpanel">Offensive Playbook</button>'
        + f'<button type="button" class="lnk drop{def_open}" id="dfbtn" '
        f'aria-expanded="false" aria-controls="dfpanel">Defensive Playbook</button>'
        + "".join(link(*nav) for nav in NAV_LINKS[1:])
    )
    drawer_links = "".join(link(h, la, k, "dlnk") for h, la, k in NAV_LINKS)

    page_style = (
        '\n<style>@page { size: landscape; margin: 9mm; }</style>' if landscape else
        f'\n<style>@page {{ {page_rule} }}</style>' if page_rule else ""
    )
    desc = (
        f'\n<meta name="description" content="{esc(description)}">' if description else ""
    )
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>{desc}
<link rel="stylesheet" href="{css_url()}">{page_style}
<a class="skip" href="#main">Skip to content</a>
<header class="site">
  <div class="wrap">
    <a class="brand" href="index.html">Sayville 8U <b>Playbook</b></a>
    <nav class="desk" aria-label="Main">{desk}</nav>
    <button type="button" class="burger" id="burger" aria-expanded="false"
            aria-controls="drawer" aria-label="Open menu"><span></span></button>
  </div>
  <div class="ddpanel" id="ddpanel" hidden>
    <div class="wrap"><div class="ddinner">{groups}</div></div>
  </div>
  <div class="ddpanel" id="dfpanel" hidden>
    <div class="wrap"><div class="ddinner one">{dgroups}</div></div>
  </div>
</header>
<div class="scrim" id="scrim" hidden></div>
<aside class="drawer" id="drawer" aria-label="Menu" hidden>
  <div class="dtop">
    <span>Menu</span>
    <button type="button" class="dclose" id="dclose" aria-label="Close menu">&times;</button>
  </div>
  <nav class="dnav">{drawer_links}<p class="dsec">Offensive Playbook</p>{groups}<p class="dsec">Defensive Playbook</p>{dgroups}</nav>
</aside>
<main id="main"{main_attrs}><div class="wrap">
{body}
</div></main>
<footer class="site"><div class="wrap">
  Generated by <code>generator/render.py</code> — edit the JSON under
  <code>playbook/</code>, never these pages.
  <a href="rules.html">Rules</a>
  <a href="print.html">Print book</a>
  <a href="https://github.com/nickvertucci/sayville-football-8u-2026">Source</a>
</div></footer>
<script src="{js_url()}"></script>
</html>
"""


def front_panels(form: dict, play: dict, defenses: dict,
                 single: str | None = None) -> str:
    """The same play drawn and blocked against each front, one panel per front.

    All three are in the page, and the toggle shows one. They are not fetched on
    demand because the reason this page exists is to be opened on a phone on a
    sideline, where the network is a field full of people and one of these is what you
    need in the next fifteen seconds.
    """
    tabs, panels = [], []
    fronts = [single] if single else list(blocking.SCOUT_FRONTS)
    for fid in fronts:
        front = defenses[fid]
        # The 4-4 is the tab that starts on, not whichever front sorts first. It is
        # our everyday front, so it is the answer to the question the page is usually
        # being opened to ask.
        first = " on" if fid == blocking.DEFAULT_FRONT or single else ""
        tabs.append(
            f'<button type="button" class="dtab{first}" data-front="{esc(fid)}" '
            f'aria-pressed="{"true" if first else "false"}">{esc(front["name"])}</button>'
        )
        rows = "\n      ".join(
            f'<div class="row{" ball" if pos == play.get("ball_carrier") else ""}">'
            f'<dt>{esc(pos)}</dt>'
            f'<dd>{esc(resolved(play, fid)[pos]["rule"])}</dd></div>'
            for pos in ordered_positions(play)
        )
        panels.append(
            f'<div class="dpanel{first}" data-front="{esc(fid)}">\n'
            f'  <figure class="diagram">\n'
            f'    <img src="{card_src(form, play, fid)}" loading="lazy" '
            f'alt="{esc(play["name"])} against the {esc(front["name"])}">\n'
            f'  </figure>\n'
            f'  <p class="block-title">Assignments <span class="vs">vs '
            f'{esc(front["name"])}</span></p>\n'
            f'  <dl class="assign">\n      {rows}\n  </dl>\n'
            f'</div>'
        )
    if single:
        return "\n".join(panels)
    return (
        '<div class="fronts" role="group" aria-label="Defensive front">\n'
        f'  <span class="fronts-label">Blocked against</span>\n  '
        + "\n  ".join(tabs) + "\n</div>\n" + "\n".join(panels)
    )


def play_article(form: dict, play: dict, defenses: dict, heading: str = "h2",
                 actions: str = "", single: str | None = None) -> str:
    """One play: diagram full width, assignments underneath, coaching points last."""
    tags = [f'<span class="call">{esc(play["call"])}</span>'] if play.get("call") else []
    for t in (play.get("type", "").upper(), play.get("ball_carrier", "")):
        if t:
            tags.append(f'<span class="tag">{esc(t)}</span>')

    # The coaching points are not on the page. They are written to the coach, not
    # to the man looking the play up, and the diagram plus the eleven assignments
    # is what somebody on a sideline came here for. They are still in the play's
    # JSON and still on the printed card.
    return f"""<article class="play" id="{esc(play['id'])}">
  <header>
    <{heading}>{esc(play['name'])}</{heading}>
    <div class="tags">{''.join(tags)}</div>
    {actions}
  </header>
  {front_panels(form, play, defenses, single)}
</article>"""


# ------------------------------------------------------------------ rulebook --

# A heading in the body reads "SECTION 9: PLAY OF THE GAME"; the same words in the
# table of contents are spaced out to the far side of the page. The gap is what
# tells them apart, so only the body ones become linkable headings.
SECTION_RE = re.compile(r"^SECTION\s*:?\s*(\d+)([\s:]*)(\S.*)$")


# A numbered rule opening a line: "9.02 – SPECIALIZED GAME MODIFICATIONS", "15.03 - Upon
# reaching". The number becomes its own anchor so a rule can be linked to directly.
RULE_RE = re.compile(r"^(\d{1,2}\.\d{2,3})(\s*[-–—:]?\s*)(.*)$")

# A list marker the league typed or Word drew, always followed by a tab.
MARKER_RE = re.compile(r"^([•▪➢✔]|\(?[a-z]\)|\(?[ivx]+\)|\d{1,2}\.)\t(.*)$", re.I)


def mostly_capitals(s: str) -> bool:
    """Whole paragraphs of this rulebook are typed in capitals. They are the same
    words either way, but a wall of caps is read letter by letter, so give those
    lines a little tracking instead of leaving them shouting."""
    letters = [c for c in s if c.isalpha()]
    if len(letters) < 12:
        return False
    return sum(c.islower() for c in letters) / len(letters) < 0.12


def rulebook_html(text: str) -> str:
    """Render the rulebook's own words, unaltered.

    Every character the league wrote survives — their spacing, their capitals, their
    typos. Everything done here is markup around that text, never a change to it:
    a section heading splits into its number and its title so the two can be styled
    apart, a rule number becomes a linkable chip, and a list marker gets a hanging
    indent. Extract the text content of this block and you get the file back.
    """
    out, seen, rules = [], set(), set()
    for raw in text.split("\n"):
        if not raw.strip():
            continue
        line = raw.strip()

        m = SECTION_RE.match(line)
        gap = m.group(2) if m else ""
        if m and "\t" not in gap and len(gap) <= 2:
            n = m.group(1)
            anchor = f"section-{n}" if n not in seen else f"section-{n}-{len(seen)}"
            seen.add(n)
            # "SECTION 9" / ": " / "PLAY OF THE GAME" — all three kept, styled apart.
            head = line[: m.start(2)] if m.start(2) > 0 else line
            out.append(
                f'<h2 id="{anchor}" class="rb-h">'
                f'<span class="rb-sn">{esc(head + m.group(2))}</span>'
                f'<span class="rb-st">{esc(m.group(3))}</span>'
                f'<a class="rb-top" href="#top" aria-label="Back to the top">&uarr;</a>'
                "</h2>"
            )
            continue

        r = RULE_RE.match(line)
        if r:
            num = r.group(1)
            anchor = ""
            if num not in rules:
                rules.add(num)
                anchor = f' id="rule-{num.replace(".", "-")}"'
            caps = " caps" if mostly_capitals(r.group(3)) else ""
            out.append(
                f'<p class="rb-rule{caps}"{anchor}>'
                f'<span class="rb-num">{esc(num)}</span>'
                f'<span class="rb-sep2">{esc(r.group(2))}</span>'
                f'{esc(r.group(3))}</p>'
            )
            continue

        mk = MARKER_RE.match(line)
        if mk:
            caps = " caps" if mostly_capitals(mk.group(2)) else ""
            out.append(
                f'<p class="rb-li{caps}">'
                f'<span class="rb-mark">{esc(mk.group(1))}</span>\t'
                f'{esc(mk.group(2))}</p>'
            )
            continue

        caps = " caps" if mostly_capitals(raw) else ""
        out.append(f'<p class="rb-l{caps}">{esc(raw)}</p>')
    return "\n".join(out)


def rulebook_toc(text: str) -> str:
    """Jump links to each section — ours, not the document's."""
    items, seen = [], set()
    for raw in text.split("\n"):
        m = SECTION_RE.match(raw.strip())
        if not m:
            continue
        gap = m.group(2)
        if "\t" in gap or len(gap) > 2 or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        items.append(
            f'<a href="#section-{m.group(1)}"><b>{esc(m.group(1))}</b>'
            f'<span>{esc(m.group(3).title())}</span></a>'
        )
    return (
        '<nav class="rb-toc" aria-label="Sections">'
        f'<p class="rb-toc-h">The {len(items)} sections</p>'
        f'<div class="rb-toc-grid">{"".join(items)}</div></nav>'
    )


def write_rulebook(formations: list[dict], defenses: dict, root: Path) -> str:
    src = root / "rulebook" / RULEBOOK_TXT
    text = src.read_text(encoding="utf-8")
    sections = len(re.findall(r'id="section-\d+"', rulebook_html(text)))
    body = f"""<header class="rb-hero" id="top">
  <p class="rb-eyebrow">Suffolk County P.A.L. &middot; Junior Football</p>
  {page_head("The rulebook")}
  <p class="lede">Reproduced word for word from the league's own document. Nothing is
  paraphrased and nothing is corrected &mdash; their spelling and their spacing stand as
  written, so anything on this page can be read aloud to an official.</p>
  <dl class="rb-facts">
    <div><dt>Sections</dt><dd>{sections}</dd></div>
    <div><dt>Revision</dt><dd>10 / 5 / 2025</dd></div>
    <div><dt>Status</dt><dd>Only version accepted</dd></div>
  </dl>
</header>
<div class="callout">
  <p><strong>Source:</strong> <code>{esc(RULEBOOK_DOCX)}</code>, the version the league
  marks <em>ONLY VERSION ACCEPTED</em>. Check the league's current release before relying
  on any of it.</p>
  <p><strong>One thing is not verbatim:</strong> the league's officers were listed on the
  cover page by name. Those names are removed here &mdash; their roles are kept, because
  the role is the part a coach needs. Everything else is exactly as written.</p>
</div>
{rulebook_toc(text)}
<div class="rulebook">
{rulebook_html(text)}
</div>"""
    return page(
        f"League rules — {SITE_TITLE}",
        body,
        formations,
        defenses=defenses,
        active_nav="rules",
        description="The Suffolk County PAL Junior Football rulebook, reproduced verbatim.",
    )


# --------------------------------------------------------------------- pages --

def _count(n: int) -> str:
    """Small counts read better as words, and they must not be written by hand —
    the home page claimed "three defensive fronts" for a while after the fourth
    one was added."""
    return {1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
            6: "six", 7: "seven", 8: "eight"}.get(n, str(n))


def first_sentence(text: str) -> str:
    """The homepage cards show one line, not the formation's full writeup — the rest
    is one tap away on the formation's own page."""
    m = re.search(r"(.+?[.!?])(\s|$)", text)
    return m.group(1) if m else text


def backs_table(formations: list[dict]) -> list[tuple[str, str]]:
    """The back digits, read out of the formations that define them.

    The mapping lives in each formation.json because the generator validates calls
    against it — so this table is the same data the build checks, not a second copy
    of it that can quietly disagree.
    """
    by_digit: dict[str, dict[str, list[str]]] = {}
    for form in formations:
        for digit, pos in (form.get("backs") or {}).items():
            by_digit.setdefault(digit, {}).setdefault(pos, []).append(form_label(form))

    rows = []
    for digit in sorted(by_digit):
        spots = by_digit[digit]
        covered = sum(len(v) for v in spots.values())
        if len(spots) == 1:
            pos, forms_with = next(iter(spots.items()))
            if covered == len(formations):
                where = "every formation" if len(formations) > 2 else "both formations"
            else:
                where = f"{forms_with[0]} only" if len(forms_with) == 1 \
                    else ", ".join(forms_with) + " only"
            rows.append((digit, f"{esc(position_name(pos))} &mdash; {esc(where)}"))
        else:
            # A digit can mean the same spot in several formations and a different one
            # elsewhere — 3 is the tailback in the Regular I and the left halfback in the
            # Split Backs. Name every formation, or the table quietly drops one.
            parts = []
            for pos, forms_with in spots.items():
                names = [esc(f) for f in forms_with]
                # "the A, the B and the C" — a chain of "and"s reads like a list nobody
                # proofread, and this row is three formations long the moment a digit
                # means two different things.
                where = names[0] if len(names) == 1 else \
                    " and the ".join([", the ".join(names[:-1]), names[-1]])
                parts.append(f"{esc(position_name(pos).lower())} in the {where}")
            text = " &nbsp;·&nbsp; ".join(parts)
            rows.append((digit, text[0].upper() + text[1:]))
    return rows

# Off the nomenclature card: 0 over the center, then outward, even right and odd left.
# There is no 1 — the middle is one hole. The word is what happens to the ball; the
# blocking family the hole names is in brackets after it, because that is the coach's
# half of the same line and it is still what the build holds a play to.
HOLES = [
    ("0", "Handoff — straight over the center (Smash)"),
    ("2 / 3", "Handoff — between the center and the guard (Smash)"),
    ("4 / 5", "Handoff — between the guard and the tackle (Dive)"),
    ("6 / 7", "Handoff — between the tackle and the end (Power)"),
    ("8 / 9", "Toss — outside the end. Sweep if the quarterback, the Z or an end is coming across to get there"),
]


def write_home(formations: list[dict], defenses: dict) -> str:
    total = sum(len(f["_plays"]) for f in formations)
    cards = []
    for f in formations:
        blurb = first_sentence(f.get("summary") or f.get("notes", ""))
        cards.append(
            f'<a class="fcard imgcard" href="{f_href(f)}">'
            f'<div class="thumb"><img src="{formation_icon_src(f)}" '
            f'alt="{esc(form_label(f))} alignment"></div>'
            f'<div class="body"><div class="ftop"><h3>{esc(form_label(f))}</h3>'
            f'<span class="n">{len(f["_plays"])} plays</span></div>'
            f"<p>{esc(blurb)}</p>"
            f'<span class="fcall"><code>{esc(call_prefix(f))}</code></span></div></a>'
        )
    defcards = "".join(
        f'<a class="fcard imgcard" href="{d_href(f)}">'
        f'<div class="thumb"><img src="{def_src(f)}" '
        f'alt="{esc(f["name"])} front"></div>'
        f'<div class="body"><div class="ftop"><h3>{esc(f["call"])}</h3>'
        f'<span class="n">{esc(f["name"])}</span></div>'
        f'<p>{esc(first_sentence(f.get("summary", "")))}</p></div></a>'
        for f in our_fronts(defenses).values()
    )
    body = f"""{page_head("The 2026 Playbook")}
<p class="lede">{_count(len(formations)).capitalize()} formations &middot; {total} plays
&middot; {_count(len(our_fronts(defenses)))} fronts.</p>

<div class="quicklinks">
  <a class="qlink" href="calls.html">{icon('search')}<span>Call sheet</span></a>
  <a class="qlink" href="install.html">{icon('calendar')}<span>Install</span></a>
  <a class="qlink" href="print.html">{icon('printer')}<span>Print playbook</span></a>
</div>

<p class="hero-head">Formations</p>
<div class="cards imgcards">
  {chr(10).join('  ' + c for c in cards).strip()}
</div>

<p class="hero-head">Defense</p>
<div class="cards imgcards">{defcards}</div>

<p class="section-head">How to call a play</p>
<div class="numgrid">
  <div>
    <p class="numcap">Who carries it</p>
    <dl class="assign holes">
      {chr(10).join(f'      <div class="row"><dt>{esc(n)}</dt><dd>{d}</dd></div>'
                    for n, d in backs_table(formations)).strip()}
    </dl>
  </div>
  <div>
    <p class="numcap">Where it goes &mdash; 0 is the middle, then even right, odd left</p>
    <dl class="assign holes">
      {chr(10).join(f'      <div class="row"><dt>{esc(n)}</dt><dd>{esc(d)}</dd></div>'
                    for n, d in HOLES).strip()}
    </dl>
  </div>
</div>

<div class="callout">
  <p><strong>Read the rules before you install anything.</strong> Minimum three
  linebackers, no blitzing &mdash; the 6-2 is illegal.
  <a href="rules.html">Full rulebook &rarr;</a></p>
</div>"""
    return page(
        f"{SITE_TITLE} — 2026 Playbook",
        body,
        formations,
        defenses=defenses,
        active_nav="home",
        description=f"{total} plays across {len(formations)} formations for 11-on-11 8U "
        "tackle football, with diagrams, assignments and coaching points.",
    )


def chip(group: str, value: str, label: str, glabel: str, title: str = "") -> str:
    """One filter chip. `glabel` rides along so the active-filter summary can say
    "Direction: Right" rather than a bare "Right" that could be three things."""
    t = f' title="{esc(title)}"' if title else ""
    return (f'<button class="chip" data-group="{esc(group)}" data-value="{esc(value)}" '
            f'data-label="{esc(label)}" data-glabel="{esc(glabel)}" '
            f'aria-pressed="false"{t}>{esc(label)}</button>')


def filter_group(label: str, chips: list[str]) -> str:
    return (f'<div class="fgroup"><span class="flabel">{esc(label)}</span>'
            f'<div class="chips">{"".join(chips)}</div></div>')


def strip_direction(name: str) -> str:
    """The favorites cards show one image for both sides of a play, so the caption
    should not claim to be just the right (or just the left) — "Power", not "Power
    Right".

    The Z's alignment goes the same way. A reverse starts him on the side its own
    direction comes back from, so the two halves of that pair disagree about where he
    lines up and one card cannot claim either — "Split Z Reverse", not "Split Z Left
    Z Reverse". Both sides are a click away on the card itself, named in full.
    """
    name = re.sub(r"\bZ (?:Right|Left)\s+", "", name)
    return re.sub(r"\s+(Right|Left)$", "", name)


# The middle of the line, and the A gap either side of the center. These used to have
# a column of their own, on the argument that a call going straight ahead has no side
# to pick. It stayed empty in every row but one and then in every row at all, so the
# sheet is two columns now and a middle-hole call takes the side it is run to -- 32
# Handoff is an A gap, but it is the RIGHT A gap and the back who carries it goes
# right. The holes are still named here because that is what decides the side when the
# digit itself does not.
MIDDLE_HOLES = (0, 2, 3)


def _call_column(play: dict) -> str:
    """Left or Right, from the hole the call names or else from direction.

    Everything outside the A gaps takes its side from the digit: even right, odd
    left. A middle-hole call, and a word call with no hole at all, takes its
    `direction` instead -- which every play in the book carries.
    """
    m = re.search(r"\b(\d)(\d)\b", play.get("call") or "")
    if m:
        hole = int(m.group(2))
        if hole not in MIDDLE_HOLES:
            return "Right" if hole % 2 == 0 else "Left"
    d = play.get("direction")
    if d in ("left", "right"):
        return d.capitalize()
    # Nothing to place it by. Better to stop than to drop it off a sheet whose whole
    # claim is that a play is on it the moment it is authored.
    raise SystemExit(
        f"{play.get('id')}: the call sheet has a Left column and a Right column, and "
        f"'{play.get('call')}' names neither a side digit nor a direction."
    )


# Inside out: the center and the A gap, the B gap, the C gap, outside the end, all
# the way outside. Same order the book installs them, and the order HOLE_SCHEME walks
# the gaps. Protect is not in it because the sheet is runs only now (see
# sheet_plays) -- a scheme that does get through anyway still prints, under its own
# name at the end of the block, which is how a leak would show itself.
SCHEME_ORDER = ("Smash", "Dive", "Power", "Sweep", "Toss")


def _sheet_name(play: dict, form: dict) -> str:
    """The play as you call it, minus only the formation the block already names.

    "Regular I Z Left 37 Handoff" in the Regular I block is "Z Left - 37 Handoff". The
    alignment stays: the column is where the ball goes, which is not where the Z
    stands, and the two come apart often enough to matter -- Regular I Z Right Z Sweep
    is a Z lined up right running into the Left column. Dropping the alignment made
    those two cells read identically.

    The side is spelled out, here as everywhere else. It was "Z R" and "Trips L" for a
    while, on the argument that this sheet is the one surface that is all coach -- but
    a coach reads it to yell it, and a sheet that prints a different call from the one
    on the boy's wrist is a sheet that has to be translated under a play clock. The
    four characters came out of the type size instead, which is measured.

    This reads off the call rather than the play name, because in Trips the strength
    word IS the formation name -- stripping the heading off "Trips - Right - X Sweep
    Right" left a bare "Right -". A formation with no strength word, like the Wishbone,
    keeps nothing.
    """
    call = play.get("call") or ""
    # The Z first, when the call has one. "Tight Right" was what a leftmost match of
    # the pattern below found, and it dropped the letter off the front of the one
    # thing the alignment is telling you -- which boy is where. The sheet has the room
    # now that the middle column is gone, and "Z Tight Right" is what gets yelled.
    m = re.search(r"\b(Z(?:\s+\w+)?\s+(?:Left|Right))\s+(.*)$", call)
    if m:
        return f"{m.group(1)} - {m.group(2)}"
    m = re.search(r"\b(\w+)\s+(Left|Right)\s+(.*)$", call)
    if m:
        return f"{m.group(1)} {m.group(2)} - {m.group(3)}"
    # No strength word at all (the Wishbone): drop the formation, keep the call.
    label = form_label(form)
    if call.lower().startswith(label.lower() + " "):
        return call[len(label) + 1:]
    return call


def _package_row(play: dict, form: dict) -> str:
    """A package card names the formation too, because a package crosses them.

    On the sheet proper the block heading says the formation, so a cell only has
    to say the alignment and the call. A package card has no such heading -- it
    is a list of calls from wherever -- so the formation goes back in front:
    "Split Backs - Z Right - X Sweep Right".

    Trips is the exception, because its strength word IS its name. Saying it
    twice reads as a stutter, so "Trips - Trips Right - 38 Quick Pass" comes out
    "Trips - Right - 38 Quick Pass".
    """
    label = form_label(form)
    tail = _sheet_name(play, form)
    if tail.startswith(label + " "):
        tail = tail[len(label) + 1:]
    return f"{label} - {tail}"


def _roster_and_plays(root: Path, formations: list[dict]) -> tuple[dict, dict]:
    """`roster.json`, and every play in the book keyed by its call.

    The two lists on this sheet that name plays -- the packages and the script -- name
    them the same way and check them the same way, so they read the file and build the
    index once here rather than twice each with its own idea of what counts as a play.

    The index is the whole book, not one formation's plays: any of the three may name a
    play from anywhere, including a formation whose block is not on the sheet.
    """
    path = root / "roster.json"
    if not path.is_file():
        return {}, {}
    roster = json.loads(path.read_text(encoding="utf-8"))
    plays = {p["call"]: (p, f) for f in formations for p in f["_plays"]}
    return roster, plays


# How many calls a package may carry. The packages sit directly above the blank field,
# so their height is what the field's height is measured against -- a taller card is
# field taken away. Five, not six: the sixth row across four of the six packages was
# most of a quarter inch of the sheet. Three since the script grew its left/right split
# row: the two rows a card gave up are room handed back to the sheet.
PACKAGE_PLAY_CAP = 3


def _package_strip(root: Path, formations: list[dict]) -> str:
    """The packages along the bottom, three to a row, with the plays each one runs.

    A package is eleven names that come on together, and the ones that are not the
    base eleven come on to do something in particular. That "something" was only
    ever in somebody's head: the sheet named the package and stopped.

    So each card names the package and lists what it is in the game to call --
    however many plays that is, from whichever formations. A package that runs the
    whole book says so instead: `["any"]` in the JSON, "Any play" on the card.

    The pairing lives in `roster.json` under `package_plays`, beside the packages
    themselves, because it is a coaching decision and not something the generator
    can work out. Each entry is a play's full call. A call that names no play stops
    the build rather than printing a play nobody can run.
    """
    roster, plays = _roster_and_plays(root, formations)
    names = (roster.get("package_names") or {}).get("offense") or []
    assigned = (roster.get("package_plays") or {}).get("offense") or []
    if not assigned:
        return ""

    cards = []
    for i, calls in enumerate(assigned):
        label = names[i] if i < len(names) else f"Package {i + 1}"
        # The cap is what makes the strip's height known, so the field below always has
        # the same room. A call past it would quietly eat that space, so the build stops
        # instead of printing a card nobody measured for.
        if list(calls) != ["any"] and len(calls) > PACKAGE_PLAY_CAP:
            raise SystemExit(
                f"roster.json package_plays, {label}: {len(calls)} plays, and a package "
                f"is capped at {PACKAGE_PLAY_CAP} — the call sheet's blank field is "
                "sized against the height of these cards. Drop a call, or re-measure "
                "the field."
            )
        if list(calls) == ["any"]:
            rows = '<tr><td class="pk-any">Any play</td></tr>'
        else:
            cells = []
            for call in calls:
                found = plays.get(call)
                if found is None:
                    raise SystemExit(
                        f"roster.json package_plays, {label}: '{call}' is not a play in "
                        f"the book. Use a play's full call, or \"any\" on its own."
                    )
                play, form = found
                cells.append(
                    f'<tr><td><a href="{p_href(play)}">'
                    f'<span class="xl-code">#{esc(play["code"])} |</span>'
                    f'{esc(_package_row(play, form))}</a></td></tr>'
                )
            rows = "".join(cells)
        cards.append(
            f'<section class="pk"><p class="pk-name">{esc(label)}'
            f'<span class="pk-n">{i + 1}</span></p>'
            f'<table class="xl pk-plays"><tbody>{rows}</tbody></table></section>'
        )

    return ('<p class="section-head pk-head">Packages '
            '<span class="pk-sub">what each one comes on to call</span></p>'
            f'<div class="pk-grid">{"".join(cards)}</div>'
            f'{_blank_line()}'
            f'{_subs_strip(roster)}')


# The lineup, in the order it stands on the field: the seven on the line from left to
# right, then the men behind it. Not PACKAGE_SPOTS order -- that one starts at the
# quarterback because a package card is read as a backfield -- because this strip is a
# picture of the formation and a coach reading it is looking left to right along his
# own line.
LINEUP_SPOTS = ("X", "LT", "LG", "C", "RG", "RT", "Y", "Z", "QB", "FB", "TB")


def _base_eleven(roster: dict) -> list[tuple[str, str]]:
    """The first man at each of the eleven spots, in lineup order."""
    side = roster.get("offense") or {}
    out = []
    for spot in LINEUP_SPOTS:
        names = side.get(spot) or []
        if not names:
            raise SystemExit(
                f"roster.json offense: nobody is listed at {spot}, and the call sheet's "
                "base eleven is the first name at each spot."
            )
        out.append((spot, names[0]))
    return out


# The five men up front are the same five in every package but one. A package is a
# thing you call to move the ball differently -- a back somewhere else, an end out
# wide -- and the boys blocking for it should not have to relearn who is beside them
# every time one gets called. So a package changes the backfield and the three
# outside the tackles, and leaves the line alone.
#
# Tiny is the exception and the only one. It exists to put a different five up front,
# which is the one thing no other package is allowed to do, and naming it here rather
# than letting it pass quietly is the point: an exception somebody chose reads
# differently from a rule nobody enforced.
LINE_SPOTS = ("LT", "LG", "C", "RG", "RT")
LINE_FREE_PACKAGES = frozenset({"Tiny"})


def check_package_lines(roster: dict) -> None:
    """Every offensive package but Tiny fields the base line, or the build stops.

    This is the invariant that kept coming undone by hand -- a package picked up a
    guard here and a tackle there until four of the six had their own line and the
    substitution cards were mostly linemen. A rule the build does not check is a
    rule until somebody edits the file.
    """
    packs = (roster.get("packages") or {}).get("offense") or []
    names = (roster.get("package_names") or {}).get("offense") or []
    if not packs:
        return
    spots = PACKAGE_SPOTS["offense"]
    base = dict(zip(spots, packs[0]))
    for i, pack in enumerate(packs[1:], start=1):
        label = names[i] if i < len(names) else f"Package {i + 1}"
        if label in LINE_FREE_PACKAGES:
            continue
        here = dict(zip(spots, pack))
        wrong = [(sp, base[sp], here[sp]) for sp in LINE_SPOTS
                 if here.get(sp) != base.get(sp)]
        if wrong:
            detail = "; ".join(f"{sp} is {got} and the base line's is {want}"
                               for sp, want, got in wrong)
            raise SystemExit(
                f"roster.json packages.offense, {label}: a package changes the "
                f"backfield and the ends, not the line -- {detail}. Put the base "
                f"line back, or add {label} to LINE_FREE_PACKAGES in site_build.py "
                "if it is meant to be an exception like Tiny."
            )


def _subs_strip(roster: dict) -> str:
    """The base eleven, then what changes for each package.

    A package card up the sheet says what a package comes on to CALL. This says who
    comes on, and only who: a package is eleven names in roster.json, but ten of them
    are usually the same ten as the last package, and printing all eleven six times is
    six lists a coach has to diff in his head while a play clock runs. So the base is
    printed once, in lineup order, and a package is the difference from it -- out, in,
    one line each.

    Out, in and moved, the same three the depth chart prints and worked out by the
    same function. It used to be one row per CHANGED SPOT -- "Z: Philip out, Ryan in"
    and "TB: Nico out, Philip in" -- which says two boys changed when it is one boy
    turning round and one coming on. A move is the substitution nobody is told to
    make, so it gets its own block under a rule rather than being spread across two
    rows that each half-say it.

    It also makes a package drifting off the depth chart visible instead of quiet.
    A package whose left guard is not the left guard shows a substitution at left
    guard; if that is not what the package is for, the card says so on paper.
    """
    packs = (roster.get("packages") or {}).get("offense") or []
    names = (roster.get("package_names") or {}).get("offense") or []
    if not packs:
        return ""
    check_package_lines(roster)
    base = _base_eleven(roster)
    spots = PACKAGE_SPOTS["offense"]

    cells = "".join(
        f'<span class="bl-man"><b>{esc(spot)}</b>{esc(man)}</span>'
        for spot, man in base
    )
    base_card = ('<section class="pk bl-card"><p class="pk-name">Base offense</p>'
                 f'<div class="bl-row">{cells}</div></section>')

    cards = []
    for i, pack in enumerate(packs):
        label = names[i] if i < len(names) else f"Package {i + 1}"
        if len(pack) != len(spots):
            raise SystemExit(
                f"roster.json packages.offense, {label}: {len(pack)} names for "
                f"{len(spots)} spots."
            )
        out, inn, moved = package_changes(packs, i + 1, spots)
        rows = []
        # A SUBS row and a MOVES row, because the two are different instructions and
        # the reader is one of them at a time. Running on and off is a thing somebody
        # is told to do; a move is a boy already on the field standing somewhere new,
        # and he is the one nobody shouts at. A rule between the blocks said only
        # that the subject had changed. The header says which subject.
        #
        # A package with no moves gets no MOVES row -- and then the SUBS row is the
        # only header on the card, which is still worth printing: it is what tells
        # the reader the card has no moves, rather than leaving him to wonder whether
        # this card just does not show them.
        if out or inn:
            rows.append('<tr class="pk-grp"><th colspan="2">Subs</th></tr>')
        for k in range(max(len(out), len(inn))):
            leaving = out[k] if k < len(out) else ""
            name, spot = inn[k] if k < len(inn) else ("", "")
            coming = (f'{esc(name)} <span class="sub-pos">{esc(spot)}</span>'
                      if name and spot else (esc(name) if name else "—"))
            rows.append(
                f'<tr><td class="sub-out">{esc(leaving) if leaving else "—"}</td>'
                f'<td class="sub-in">{coming}</td></tr>'
            )
        if moved:
            rows.append('<tr class="pk-grp pk-grp-mv"><th colspan="2">Moves</th></tr>')
        for name, a, b in moved:
            rows.append(
                f'<tr><td class="sub-out mv-name">{esc(name)}</td>'
                f'<td class="sub-mv"><span class="mv-a">{esc(a)}</span>'
                f'<span class="mv-b">{esc(b)}</span></td></tr>'
            )
        body = ("".join(rows) if rows else
                '<tr><td class="pk-any" colspan="2">Base eleven</td></tr>')
        cards.append(
            f'<section class="pk"><p class="pk-name">{esc(label)}'
            f'<span class="pk-n">{i + 1}</span></p>'
            f'<table class="xl pk-subs"><tbody>{body}</tbody></table></section>'
        )

    return ('<p class="section-head pk-head">Who comes on '
            '<span class="pk-sub">the base eleven, then what each package changes</span></p>'
            f'<div class="bl-strip">{base_card}</div>'
            f'<div class="pk-grid sub-grid">{"".join(cards)}</div>')


# The line, as fifteen grid columns: a number, a man, a number, a man ... so the hole
# numbers land over the gaps they name and 0 lands over the centre. Same numbering as
# the nomenclature card, which is what the coach and the kids already read.
#
#     9  |  7  |  5  |  3  | 0 |  2  |  4  |  6  |  8
#       X    LT    LG     C    RG    RT   Y
HOLE_COLUMNS = ((1, "9"), (3, "7"), (5, "5"), (7, "3"),
                (9, "2"), (11, "4"), (13, "6"), (15, "8"))
MAN_COLUMNS = (2, 4, 6, 8, 10, 12, 14)
BALL_COLUMN = 8

# Where the hash marks sit down each sideline, as a percentage of the field's height.
HASH_MARKS = (14, 32, 50, 68, 86)


def _blank_line() -> str:
    """A blank line of scrimmage to draw a play on, at the foot of the call sheet.

    The sheet is laminated, so the bottom of it is worth more as somewhere to invent a
    play than as more print. What is drawn is only the part that is the same on every
    snap: the hole numbers, the centre with three men either side, and the ball in
    front of him. The backs, the routes and the blocks are the coach's, in marker.

    Built from bordered elements rather than an inline SVG. The SVG version rendered
    on screen and was absent from the printed sheet at every size tried; a border
    always prints, which is the same rule the black title bars in this file follow.
    """
    holes = "".join(
        f'<span class="hn" style="grid-column:{col};grid-row:2">{esc(n)}</span>'
        for col, n in HOLE_COLUMNS
    )
    ball = f'<span class="ball" style="grid-column:{BALL_COLUMN};grid-row:1"></span>'
    men = "".join(
        f'<span class="o" style="grid-column:{col};grid-row:2"></span>'
        for col in MAN_COLUMNS
    )
    hashes = "".join(
        f'<span class="hash{side}" style="top:{pct}%"></span>'
        for pct in HASH_MARKS for side in ("", " r")
    )
    return (f'<div class="pk-field" role="img" aria-label="Blank line of scrimmage with '
            f'the hole numbers and sidelines, to draw a play on">{hashes}'
            f'<div class="pk-draw">{holes}{ball}{men}'
            f'<span class="pad" style="grid-row:3"></span></div></div>')


# The script is twenty plays, and the twenty share the whole height beside the four
# formation blocks rather than sitting small at the top of it. So the row height is not
# a constant here: it is that height divided by twenty, which is what `.script-t td`
# sets in the print CSS. Change this number and that height has to be re-measured with
# it, which is why the two carry each other's name.
SCRIPT_ROWS = 20


def _script_strip(root: Path, formations: list[dict]) -> str:
    """The numbered column down the right of the formation blocks.

    The plays in the order they are called, from roster.json under `script_plays`,
    beside package_plays and under the same rule: a full call that has to name a real
    play or the build stops.

    A play may appear more than once -- a script repeats on purpose, and this one calls
    22 Smash three times. Short of the twenty rows is fine and the rest print blank;
    past twenty stops the build, because the column's height is what the field and the
    board below it were measured against.

    No heading: twenty rows sharing the height is the point, and a heading would take a
    row's worth of it.
    """
    roster, plays = _roster_and_plays(root, formations)
    assigned = (roster.get("script_plays") or {}).get("offense") or []
    if len(assigned) > SCRIPT_ROWS:
        raise SystemExit(
            f"roster.json script_plays: {len(assigned)} plays, and the script column "
            f"holds {SCRIPT_ROWS} — the call sheet's field and board are sized against "
            "its height."
        )

    cells = []
    sides = {"left": 0, "right": 0}
    for call in assigned:
        found = plays.get(call)
        if found is None:
            raise SystemExit(
                f"roster.json script_plays: '{call}' is not a play in the book. "
                "Use a play's full call."
            )
        play, form = found
        if play.get("direction") in sides:
            sides[play["direction"]] += 1
        cells.append(f'<a href="{p_href(play)}">'
                     f'<span class="xl-code">#{esc(play["code"])} |</span>'
                     f'{esc(_package_row(play, form))}</a>')
    cells += [""] * (SCRIPT_ROWS - len(cells))

    rows = "".join(
        f'<tr><td class="sn">{i}</td><td>{cell}</td></tr>'
        for i, cell in enumerate(cells, 1)
    )
    # The split row: how much of the script goes each way, so a lean toward one side is
    # visible before the first snap rather than noticed by the defense in the second
    # quarter. Counted off each play's own `direction`; a play with neither is left out.
    both = sides["left"] + sides["right"]
    def pct(n: int) -> str:
        return f"{round(100 * n / both)}%" if both else "—"
    split = (f'<thead><tr><td class="split" colspan="2">'
             f'Left {pct(sides["left"])} ({sides["left"]})'
             f'<span class="split-sep">·</span>'
             f'Right {pct(sides["right"])} ({sides["right"]})</td></tr></thead>')
    return ('<section class="script" role="img" aria-label="The possession script, '
            f'{SCRIPT_ROWS} numbered rows of plays in the order they are called, '
            f'{pct(sides["left"])} left and {pct(sides["right"])} right">'
            f'<table class="xl script-t"><colgroup><col class="sn-c"><col></colgroup>'
            f'{split}<tbody>{rows}</tbody></table></section>')


# The fronts the defensive sheet carries, in the order a coach reaches for them: the
# everyday one, the heavy one, and the one for the two-yard line. The other two fronts
# in the book (the 5-3 and Prevent) are in the defensive playbook; this is a call sheet,
# not the book.
DEF_SHEET_FRONTS = ("4-4", "5-4-2", "6-3")


def _def_eleven(front_id: str, spots: list[str], slides: dict,
                pack: list[str], base_spots: tuple) -> list[str]:
    """One package's eleven, arranged in `front_id`'s spots.

    A package is stored against the base front, so every other front needs to know
    which base man takes which of its spots -- the guard who slides out to tackle, the
    safety who walks up to nose. That is a coaching decision, so it lives in
    roster.json under front_slides rather than being guessed from the coordinates here.
    """
    by_spot = dict(zip(base_spots, pack))
    if front_id == blocking.DEFAULT_FRONT:
        return [by_spot.get(sp, "") for sp in spots]
    slide = slides.get(front_id) or {}
    return [by_spot.get(slide.get(sp, ""), "") for sp in spots]


# The window every front picture is drawn in, in the same yards the alignment uses.
# One width for all three, not one each: a 6-3 really is tighter than a 4-4, and a
# picture that rescaled per front would hide the only thing these pictures are for.
# The dots are inset a little from the edges so the widest man -- a 4-4 corner, nine
# and a half yards out -- sits inside the frame instead of half on top of it.
FRONT_VIEW_X = 10.0
FRONT_PAD_X = 3.0
# Depth is the other way round: yards to the inch, fixed, and the card is as tall as
# its own deepest man needs. Sharing one depth for all three gave the goal line card
# six yards of white under its linebackers, because a 6-3 has nobody behind them.
# A fixed scale is what keeps the three comparable -- two yards of separation looks
# the same on every card -- so only the height moves.
FRONT_MIN_DEEP = 2.0


def _front_picture(front: dict) -> str:
    """The front as dots, over a dashed line of scrimmage.

    Absolutely positioned discs rather than an inline SVG. An SVG in this position on
    this page rendered on screen and printed nothing at all -- see _blank_line -- and
    a disc made of border prints whatever the print dialog is set to.

    The frame is narrow and centred rather than the full width of the sheet. Drawn
    edge to edge, twenty yards of field across seven inches of paper put the eleven
    dots so far apart that they read as specks rather than as a front; at a third of
    that width the same eleven dots look like the picture a coach recognises.

    Down the page the stylesheet owns the scale -- one --fd-scale per yard, screen and
    print -- and this only says how deep the front goes, so the card can be exactly
    that tall.
    """
    deep = max([y for _, y in front["alignment"].values()] + [FRONT_MIN_DEEP])
    dots = []
    for label, (x, y) in front["alignment"].items():
        left = FRONT_PAD_X + (x + FRONT_VIEW_X) / (2 * FRONT_VIEW_X) * (
            100 - 2 * FRONT_PAD_X)
        dots.append(
            f'<span class="fd" style="left:{left:.1f}%;'
            f'top:calc(var(--fd-pad) + {y:g} * var(--fd-scale))" '
            f'title="{esc(label)}"></span>'
        )
    return (f'<div class="front-pic" style="--fd-deep:{deep:g}" role="img" '
            f'aria-label="{esc(front["name"])} front, eleven defenders">'
            f'<span class="los"></span>{"".join(dots)}</div>')


def _defense_sheet(root: Path, defenses: dict) -> str:
    """The defensive call sheet: a table per front, a package per column.

    Rows are the front's own spots, columns are the six packages, and a cell is the
    boy who plays there. That is the question this sheet answers -- "Goal Line
    Wolfpack, who is on the field and where" -- which on the offensive side is a
    play's name and on this side is eleven names.
    """
    roster, _ = _roster_and_plays(root, [])
    packs = (roster.get("packages") or {}).get("defense") or []
    names = (roster.get("package_names") or {}).get("defense") or []
    slides = {k: v for k, v in (roster.get("front_slides") or {}).items()
              if isinstance(v, dict)}
    if not packs:
        return ""

    base_spots = PACKAGE_SPOTS["defense"]
    by_id = {f["id"]: f for f in defenses.values()} if defenses else {}
    tables = []
    for fid in DEF_SHEET_FRONTS:
        front = by_id.get(fid)
        if front is None:
            continue
        spots = list(front["alignment"])
        slide = slides.get(fid)
        if fid != blocking.DEFAULT_FRONT:
            if slide is None:
                raise SystemExit(
                    f"roster.json front_slides: no entry for '{fid}', which the "
                    "defensive call sheet needs to know where the base eleven goes."
                )
            if sorted(slide) != sorted(spots):
                raise SystemExit(
                    f"roster.json front_slides, {fid}: names {sorted(slide)} but the "
                    f"front's spots are {sorted(spots)}."
                )
            if sorted(slide.values()) != sorted(base_spots):
                raise SystemExit(
                    f"roster.json front_slides, {fid}: the base men it uses are "
                    f"{sorted(slide.values())}, which is not the base eleven. "
                    "Eleven on the field either way."
                )
        elevens = [_def_eleven(fid, spots, slides, pk, base_spots) for pk in packs]
        head = "".join(f"<th>{esc(n)}</th>"
                       for n in (names or [f"Package {i+1}" for i in range(len(packs))]))
        # A blank row where the unit changes, so the line, the backers and the
        # secondary read as three groups rather than eleven rows. The front's own
        # roles say where those changes are, so a front with two linebackers or six
        # linemen gets its rules in the right places without anything here knowing.
        roles = front.get("roles") or {}
        rows, last_role = [], None
        for i, sp in enumerate(spots):
            role = roles.get(sp)
            if last_role is not None and role != last_role:
                rows.append(f'<tr class="df-gap"><td colspan="{len(packs) + 1}"></td></tr>')
            last_role = role
            cells = "".join(f'<td>{esc(e[i])}</td>' for e in elevens)
            rows.append(f'<tr><td class="df-pos">{esc(sp)}</td>{cells}</tr>')
        label = front.get("call") or front["name"]
        tables.append(
            f'<section class="df-front"><p class="xl-title">{esc(label)}'
            f'<span class="xl-n">{esc(front["name"])}</span></p>'
            f'{_front_picture(front)}'
            f'<table class="xl df-grid"><thead><tr><th class="df-pos"></th>{head}'
            f'</tr></thead><tbody>{"".join(rows)}</tbody></table></section>'
        )
    return f'<div class="df-fronts">{"".join(tables)}</div>{_def_blank_line()}'


# Two down linemen either side of the ball, and the rest of the front is the coach's
# to draw. Columns 4, 6, 10 and 12 of the same fifteen-column line the offensive strip
# uses, which is how the two strips end up the same size with the same spacing: this
# one is that one with the outer men and the numbers taken off. The offensive strip
# names its holes because the calling language depends on them; this one names nothing,
# because what goes on it changes with every opponent.
DEF_MAN_COLUMNS = (4, 6, 10, 12)


def _def_blank_line() -> str:
    """The blank front: a ball, and two down linemen either side of it."""
    ball = f'<span class="ball" style="grid-column:{BALL_COLUMN};grid-row:1"></span>'
    men = "".join(
        f'<span class="o" style="grid-column:{col};grid-row:2"></span>'
        for col in DEF_MAN_COLUMNS
    )
    hashes = "".join(
        f'<span class="hash{side}" style="top:{pct}%"></span>'
        for pct in HASH_MARKS for side in ("", " r")
    )
    return ('<div class="pk-field" role="img" aria-label="Blank line of scrimmage with '
            f'the ball and four down linemen, to draw a front on">{hashes}'
            f'<div class="pk-draw">{ball}{men}'
            '<span class="pad" style="grid-row:3"></span></div></div>')


# The call sheet is the one page that lays the formations out two across instead of
# one after another, so its order is a seating chart rather than the teaching order the
# rest of the book runs on. Regular I keeps the top row, the Wishbone drops to the
# bottom next to Power I, and Trips comes up into the middle. Everything else -- the
# nav, the install, the formation pages -- still reads `order` out of formation.json,
# which is why this list lives here and not there.
CALL_SHEET_ORDER = (
    "i-form", "split-backs",
    "trips", "shotgun",
    "wishbone", "power-i",
)

# Formations that stay in the book but come off the call sheet. The Wishbone and
# Trips are teaching formations here -- each has its own page, its cards, its place
# in the printed book and in PLAYBOOK.md, and its plays are authored and checked
# like every other -- but neither is what anybody reaches for on a Sunday. The
# Shotgun came off later for the same reason: six plays a coach knows by heart do
# not need a block of his one sheet. Off the sheet, the blocks below them move up
# and the field below the line of scrimmage grows by their height, which is the
# point: that space gets drawn on with a marker. Same shape as sheet_plays dropping
# the passes -- a filter here, not a deletion anywhere, so a formation comes back by
# taking it out of this set.
#
# The Single Back joins them on the way in rather than on the way out. It is brand
# new, nobody has lined up in it yet, and a block on the sheet for a formation the
# boys cannot get into without being told is a block that costs a real one. Note that
# leaving it off is not free either -- a seventh block is what pushed the offensive
# sheet onto a second printed page, which test_print_pages.py caught. Take it out of
# this set when it has been installed, and expect to pay for the room.
SHEET_OMIT = frozenset({"wishbone", "trips", "shotgun", "single-back", "power-i"})

# The wristbands no longer have a list of their own: they carry exactly what the
# call sheet carries, through called_plays(). A second list was a second thing to
# keep in step, and it did not stay in step.


def _call_sheet_order(formations: list[dict]) -> list[dict]:
    """`formations` seated for the call sheet grid, teaching order for anything new.

    A formation this list has never heard of sorts to the end by its own `order`,
    so adding a playbook/<dir> puts it on the sheet without editing this file.
    """
    rank = {fid: i for i, fid in enumerate(CALL_SHEET_ORDER)}
    return sorted(
        formations,
        key=lambda f: (rank.get(f.get("id"), len(rank)), f.get("order", 99),
                       f.get("name", "")),
    )


# A pouch is 3.5 inches by 2.75, landscape, because that is the window on the YOUTH
# wristband these go in. It was five by three, which is the adult band, and an insert
# cut to five inches does not go in a three-and-a-half-inch window at all -- the whole
# sheet was unusable on the bands the boys actually wear.
#
# Three of them stacked is 8.25 inches of a ten-and-a-bit-inch page, so a sheet is
# still exactly one wristband and you still print a copy per boy. The shape is what
# decides the rest: eight rows fit down the panel where sixteen do not, so a formation
# goes in two columns, and the width is what sets the type -- and there is now a lot
# less of it, so the type is measured against the longest row rather than chosen.
BAND_POUCHES = 3
# Two columns, and the row chrome is what pays for them. In a 3.5in youth window a
# column is 147 points once the border, the gutter, the row padding and the number
# column are taken out -- and the longest call in the book, "Z Tight Right - Y Slant
# Pass Right", fits that at 9px. One column would buy half a point of type and cost
# eighteen rows of scrolling down a two-and-three-quarter-inch pouch, which is not a
# trade worth making.
#
# The chrome is tight on purpose: every point spent on padding or on the number
# column is a point off the type in a window this small.
BAND_PANEL_COLUMNS = 2


def band_call(play: dict, form: dict) -> str:
    """The play's name, minus the formation the panel heading already says.

    "Split Backs - Z Tight Right - 38 Toss" is "Z Tight Right - 38 Toss" in the
    Split Backs pouch. Nothing else comes off. "Right" is a word and about a point
    and a half of type, and it is worth both: the boy reading this is nine, he has
    been taught the word, and an abbreviation is one more thing to remember at the
    moment he has least room to remember anything. The call sheet shortens it to R;
    this does not.

    It reads off the NAME rather than the call, which is the same words with the
    dashes still in: "Z Tight Right - 36 Handoff" instead of a run of six words. The
    dash is where the boy's eye stops -- where he is standing on the left of it and
    what he does on the right -- and at a glance through a plastic window that break
    is worth more than the two points of type it costs.
    """
    text = play.get("name") or play.get("call") or ""
    label = form_label(form)
    for prefix in (label + " - ", label + " "):
        if text.startswith(prefix):
            return text[len(prefix):]
    return text


def called_plays(formations: list[dict]) -> list[tuple[dict, list[dict]]]:
    """What a coach can actually call on a Saturday: formation -> its plays.

    The one selection the call sheet and the wristbands both read, so the band a
    boy is wearing cannot hold a play the sheet does not call, and the sheet
    cannot call one that is not on his band. They used to have a rule each and
    they drifted: the band carried the passes and the whole Shotgun, fourteen
    plays the sheet never asks for, and the argument for it -- that the sheet's
    third-and-long square called two Shotgun sweeps -- had stopped being true.
    Nothing on the sheet references a Shotgun number now.

    In call sheet order, which is also number order: the numbers were handed out
    in this order precisely so a band reads down without jumping about.

    A play can take itself off both with `"sheet": false` in its own JSON. That is
    for a play that is still in the book and still taught -- it keeps its page, its
    diagram and its number -- but is not one a coach wants in front of him on a
    Saturday. Omitting a whole formation is SHEET_OMIT's job; this is the one play.
    """
    return [(f, sorted((p for p in f["_plays"]
                        if p.get("type") == "run" and p.get("sheet", True)),
                       key=lambda p: int(p.get("code") or 0)))
            for f in _call_sheet_order(formations)
            if f.get("id") not in SHEET_OMIT]


def band_plays(formations: list[dict]) -> list[tuple[dict, list[dict]]]:
    """The wristband's plays: exactly the call sheet's, and never anything else."""
    return [(f, ps) for f, ps in called_plays(formations) if ps]


def _deal(groups: list[tuple[dict, list[dict]]], parts: int) -> list[list]:
    """Formations dealt into `parts` piles, whole, as evenly as they go."""
    height = lambda g: 1 + len(g[1])
    target = sum(height(g) for g in groups) / parts
    piles, cur, used = [], [], 0
    for g in groups:
        if cur and used + height(g) / 2 > target and len(piles) < parts - 1:
            piles.append(cur)
            cur, used = [], 0
        cur.append(g)
        used += height(g)
    piles.append(cur)
    return piles + [[]] * (parts - len(piles))


def _band_pouches(groups: list[tuple[dict, list[dict]]]) -> list[list]:
    """The formations dealt into the three pouches.

    A formation is never split across two pouches: the panel heading is what lets a row
    say "Z Right 36 Handoff" instead of "Regular I Z Right 36 Handoff", and half a
    formation under a heading naming all of it is a lie a boy cannot check. Today that
    deals out as Regular I, Split Backs, and Shotgun with Power I behind it.
    """
    return _deal(groups, BAND_POUCHES)


def _band_panel(pouch: list[tuple[dict, list[dict]]]) -> str:
    """One pouch, landscape: a bar naming it, then its numbers in two columns.

    Inside the panel a formation *may* break across the two columns -- the bar above
    them already named it, so 1 to 8 down one and 9 to 16 down the other is one list
    read the way a page is. A pouch holding two formations splits on the formation
    instead and labels each column, because there the break means something.
    """
    if not pouch:
        return '<div class="band"></div>'
    plays = [(p, f) for f, ps in pouch for p in ps]

    def rows(items):
        return "".join(
            f'<li><b>{esc(p["code"])}</b><span>{esc(band_call(p, f))}</span></li>'
            for p, f in items
        )

    def seg(name, codes):
        """The bar: the name, and the number range only when it is a real range.

        "1-70" on a pouch holding 1 to 16 and 69 to 70 is a lie that reads as
        seventy plays. The split-Z plays took the next free numbers, the way every
        new play does, so a formation's numbers no longer run contiguously -- and a
        span written across a gap says nothing true. Print it when it is honest and
        leave it off when it is not; every row carries its own number regardless.
        """
        nums = sorted(int(c) for c in codes)
        span = ""
        if nums and nums[-1] - nums[0] == len(nums) - 1:
            span = (f'<span class="band-span">{nums[0]}\u2013{nums[-1]}</span>')
        return f'<span class="band-seg">{esc(name)}{span}</span>'

    # Two formations in one pouch get the bar split in two, each half naming the
    # column under it. One formation gets a single bar and its numbers run down one
    # column and on into the next.
    if len(pouch) == BAND_PANEL_COLUMNS:
        # One formation to a column, and half the black bar over each.
        cols = [f"<ol>{rows([(p, f) for p in ps])}</ol>" for f, ps in pouch]
        bar = "".join(seg(form_label(f), [p["code"] for p in ps]) for f, ps in pouch)
    else:
        # One formation: the bar names it once and the numbers run down one column
        # and on into the next, the way a page is read.
        label = " \u00b7 ".join(form_label(f) for f, _ in pouch)
        bar = seg(label, [p["code"] for p, _f in plays])
        half = -(-len(plays) // BAND_PANEL_COLUMNS)
        cols = [f"<ol>{rows(plays[i * half:(i + 1) * half])}</ol>"
                for i in range(BAND_PANEL_COLUMNS)]

    body = "".join(f"<div>{c}</div>" for c in cols)
    return ('<div class="band">'
            f'<p class="band-form">{bar}</p>'
            f'<div class="band-body">{body}</div></div>')


def _band_set(groups: list[tuple[dict, list[dict]]]) -> str:
    """One wristband: three panels, one per pouch, stacked in call sheet order."""
    return ('<div class="band-set">'
            + "".join(_band_panel(p) for p in _band_pouches(groups))
            + "</div>")


def write_wristbands(formations: list[dict], defenses: dict) -> str:
    groups = band_plays(formations)
    numbered = [p for _f, ps in groups for p in ps]
    lo = numbered[0]["code"] if numbered else "1"
    hi = numbered[-1]["code"] if numbered else "1"
    # No prose. The page is the inserts themselves and the Print button, and the
    # three paragraphs that used to sit above them said things the page already
    # shows or that belong in the README: how big a pouch is, what a row reads
    # like, that numbers are never reused. None of it is needed by somebody who
    # has come here to print a band, and all of it is off the top of the screen
    # before the first pouch is.
    body = f"""<div class="page-head">
  <h1>Wristbands</h1>
  <button class="btn" type="button" onclick="window.print()">Print</button>
</div>
<div class="band-sheet">{_band_set(groups)}</div>"""
    return page(
        f"Wristbands — {SITE_TITLE}",
        body,
        formations,
        defenses=defenses,
        active_nav="bands",
        main_attrs=' class="band-page"',
        description=f"Wristband inserts: every callable play, {lo} to {hi}, three pouches a band.",
        page_rule="size: letter portrait; margin: 0.3in;",
    )


def write_calls(formations: list[dict], defenses: dict, root: Path) -> str:
    """The call sheet: every formation's plays, by scheme and by side.

    This used to be one sheet per package, each an eight-column grid of player
    names above three mostly blank columns to write plays into. The lineup took
    half of every sheet to say what the Depth Chart page already says, it only
    ever reached three of the five formations — Trips and the Wishbone were
    nowhere on it — and it answered "who is in" on a page whose job is "what do
    we call".

    So the sheet is the book now, laid out the way a call sheet lays one out: a
    block per formation, the schemes down the side inside-out, and Left, Middle
    and Right across. Every play is in the cell its own call puts it in, so a
    play is on the sheet the moment it is authored — nothing here is a list
    anybody has to keep in step by hand.
    """
    sides = ("Left", "Right")
    none_cell = '<td><span class="xl-none">&mdash;</span></td>'

    # One selection, shared with the wristbands -- see called_plays(). The passes
    # stay in the book (their cards, their pages and the printed playbook are
    # untouched); they are just not what anybody reaches for this sheet to call.
    selection = dict((f["id"], ps) for f, ps in called_plays(formations))
    sheet_forms = [f for f in _call_sheet_order(formations) if f["id"] in selection]

    def sheet_plays(form: dict) -> list[dict]:
        return selection.get(form["id"], [])

    def plays_table(form: dict) -> str:
        placed: dict[tuple[str, str], list[dict]] = {}
        for play in sheet_plays(form):
            placed.setdefault((play["scheme"], _call_column(play)), []).append(play)

        schemes = [s for s in SCHEME_ORDER if any(k[0] == s for k in placed)]
        schemes += sorted({k[0] for k in placed} - set(SCHEME_ORDER))

        rows = []
        for scheme in schemes:
            tds = []
            for side in sides:
                cell = "".join(
                    f'<a href="{p_href(p)}"><span class="xl-code">#{esc(p["code"])} |</span>'
                    f'{esc(_sheet_name(p, form))}</a>'
                    for p in placed.get((scheme, side), [])
                )
                tds.append(f"<td>{cell}</td>" if cell else none_cell)
            rows.append(f'<tr><th scope="row" class="xl-scheme">{esc(scheme)}</th>'
                        f'{"".join(tds)}</tr>')

        return ('<table class="xl xl-plays">'
                '<colgroup><col class="xl-c0"><col><col></colgroup>'
                '<thead><tr><th class="xl-scheme"></th>'
                + "".join(f"<th>{side}</th>" for side in sides)
                + f'</tr></thead><tbody>{"".join(rows)}</tbody></table>')

    # The count and the block itself both come off the filtered list, not the
    # formation's own: a header reading 12 over a table of 10 is a sheet that lies,
    # and a formation whose plays are all passes would otherwise print an empty block.
    sheets = "".join(
        f'<section class="xl-sheet"><p class="xl-title">{esc(form_label(form))}'
        f'<span class="xl-n">{len(sheet_plays(form))}</span></p>{plays_table(form)}</section>'
        for form in sheet_forms if sheet_plays(form)
    ) or '<p class="lede">No plays in the book yet.</p>'

    packages = _package_strip(root, formations)
    script = _script_strip(root, formations)

    # No sub-line under the heading. "Every play in the book, by formation and scheme"
    # restates the title, and the holes rule is on the play cards and in the book where
    # somebody learning it will actually be looking. On paper the line cost a row of
    # calls; the page description below still carries the same words for search.
    # Two sheets on one page, behind a pair of tabs. The offensive sheet is the page
    # it always was; the defensive one answers a different question with the same
    # furniture. Radios rather than script, so the tabs work with
    # JavaScript off. On paper the tabs are not a choice at all: both panes print,
    # offense then defense, a sheet each, because a coach who hits Print wants the
    # whole call sheet and not whichever half he happened to be looking at.
    defense = _defense_sheet(root, defenses)
    body = f"""{page_head("Call sheet")}
<div class="sheet-tabs">
  <input type="radio" name="sheet" id="tab-off" checked>
  <input type="radio" name="sheet" id="tab-def">
  <nav class="tabrow" role="tablist">
    <label class="tab" for="tab-off">Offense</label>
    <label class="tab" for="tab-def">Defense</label>
  </nav>
  <section class="tabpane pane-off">
    <div class="xl-top"><div class="xl-sheets">{sheets}</div>{script}</div>
    {packages}
  </section>
  <section class="tabpane pane-def">{defense}</section>
</div>"""
    return page(
        f"Call sheet — {SITE_TITLE}",
        body,
        formations,
        defenses=defenses,
        active_nav="calls",
        main_attrs=' class="calls-page"',
        description="Every run in the book, by formation, scheme and side.",
        # Portrait, two blocks across: with no lineup grid a block is a handful of
        # rows, so all five formations fit one sheet of paper.
        page_rule="size: letter portrait; margin: 0.3in;",
    )


def write_formation_page(form: dict, formations: list[dict], defenses: dict) -> str:
    cards = []
    for p in form["_plays"]:
        cards.append(
            f'<a class="pcard" href="{p_href(p)}">'
            f'<div class="thumb"><img src="{card_src(form, p)}" '
            f'alt="{esc(p["name"])} diagram"></div>'
            f'<div class="body"><h4>{esc(p["name"])}</h4>'
            f'<span class="call">{esc(p.get("call", ""))}</span></div></a>'
        )
    blocks = ['<p class="section-head">The plays</p>'
              f'<div class="plist">{"".join(cards)}</div>']

    # Neither the alignment prose nor the coaching notes are on this page. A
    # formation page is how a coach gets to a play in two taps, and prose above
    # the plays is a screen he scrolls past every time to reach the thing he came
    # for. Both are still in formation.json: the notes are printed in the
    # formation's README.md, and the alignment line is still the page's meta
    # description, which is what a shared link shows. They are read once, not
    # every time the formation is opened.
    body = f"""{page_head(form_label(form))}
<p class="sub">{len(form['_plays'])} plays
&nbsp;·&nbsp; {esc(form.get('personnel', ''))}</p>
{chr(10).join(blocks)}"""
    return page(
        f"{form_label(form)} — {SITE_TITLE}",
        body,
        formations,
        defenses=defenses,
        active_form=form["id"],
        description=form.get("notes", "")[:160],
    )


def write_play_page(
    form: dict, play: dict, prev: dict | None, nxt: dict | None,
    formations: list[dict], defenses: dict,
) -> str:
    actions = PRINT_BTN

    # Every play in this formation, so moving between them is one tap and you can see
    # where the play you are looking at sits in the install.
    siblings = "\n    ".join(
        f'<a href="{p_href(p)}"{ACTIVE_ATTR if p["id"] == play["id"] else ""}>'
        f'{esc(p["name"])}</a>'
        for p in form["_plays"]
    )
    crumbs = (
        f'<nav class="crumbs"><a href="index.html">Home</a><span>/</span>'
        f'<a href="{f_href(form)}">{esc(form_label(form))}</a><span>/</span>'
        f'<b>{esc(play["name"])}</b></nav>'
    )
    playbar = f'<div class="playbar">\n    {siblings}\n  </div>'

    pager = ['<div class="pager">']
    if prev:
        pager.append(
            f'<a href="{p_href(prev)}"><span class="dir">← Previous</span>'
            f'{esc(prev["name"])}</a>'
        )
    else:
        pager.append("<span></span>")
    pager.append(
        f'<a class="mid" href="{f_href(form)}"><span class="dir">Formation</span>'
        f'All {esc(form_label(form))} plays</a>'
    )
    if nxt:
        pager.append(
            f'<a class="nxt" href="{p_href(nxt)}">'
            f'<span class="dir">Next →</span>{esc(nxt["name"])}</a>'
        )
    else:
        pager.append("<span></span>")
    pager.append("</div>")

    body = (
        crumbs + "\n" + playbar + "\n"
        + play_article(form, play, defenses, actions=actions)
        + "\n" + "\n".join(pager)
    )
    # Marks this as a play's own page, so its print is the picture alone. print.html
    # renders the same article without it and keeps the words.
    attrs = ' class="play-page"'
    if prev:
        attrs += f' data-prev="{p_href(prev)}"'
    if nxt:
        attrs += f' data-next="{p_href(nxt)}"'
    return page(
        f"{play['name']} ({play.get('call', '')}) — {SITE_TITLE}",
        body,
        formations,
        defenses=defenses,
        active_form=form["id"],
        active_play=play["id"],
        description=f"{play['name']} — {play.get('call', '')}"[:160],
        # The graphic alone on a letter sheet, turned to fit a diagram that is wider
        # than it is deep, with the margins as thin as a home printer allows.
        page_rule="size: letter landscape; margin: 0.25in;",
        main_attrs=attrs,
    )


def defense_article(front: dict, heading: str = "h2", actions: str = "") -> str:
    rows = "".join(
        f'<div class="row"><dt>{esc(pos)}</dt>'
        f'<dd>{esc(front["assignments"][pos]["rule"])}</dd></div>'
        for pos in front["alignment"]
        if pos in front.get("assignments", {})
    )
    coach = ""
    if front.get("coaching_points"):
        items = "".join(f"<li>{esc(c)}</li>" for c in front["coaching_points"])
        coach = f'<p class="block-title">Coaching points</p><ul class="coach">{items}</ul>'
    legal = ""
    if front.get("legal"):
        legal = (
            f'<div class="legalblock">'
            f'<p class="block-title">Why it is legal</p>'
            f'<p class="legal">{esc(front["legal"])}</p></div>'
        )
    counts = {}
    for r in front.get("roles", {}).values():
        counts[r] = counts.get(r, 0) + 1
    tags = "".join(
        f'<span class="tag">{counts.get(k, 0)} {label}</span>'
        for k, label in (("DL", "down"), ("LB", "LB"), ("DB", "DB"))
    )
    return f"""<article class="play def" id="{esc(front['id'])}">
  <header>
    <{heading}>{esc(front['name'])}</{heading}>
    <div class="tags"><span class="call">{esc(front['call'])}</span>{tags}</div>
    {actions}
  </header>
  <figure class="diagram">
    <img src="{def_src(front)}" alt="{esc(front['name'])} alignment">
  </figure>
  <p class="purpose">{esc(front.get('notes', ''))}</p>
  <p class="block-title">Assignments</p>
  <dl class="assign">{rows}</dl>
  {coach}
  {legal}
</article>"""


def install_href(pr: dict) -> str:
    return f"install-{pr['n']}.html"


def practice_date(pr: dict):
    """The day a practice lands on, or None if the schedule has not pinned one.

    Dates are stored ISO in install.json and the weekday is computed here, so a
    hand-typed "Mon" cannot disagree with the day it is printed next to. A practice
    with no date, or a date the schedule has not committed to yet, still gets its own
    page and its own row in the list — it just does not land on the calendar.
    """
    raw = str(pr.get("date", "")).strip()
    try:
        return _date.fromisoformat(raw)
    except ValueError:
        return None


def date_label(day, long: bool = False) -> str:
    """"Tue, Aug 11" for a chip, "Tuesday, August 11, 2026" for a page heading."""
    if long:
        return f"{day.strftime('%A, %B')} {day.day}, {day.year}"
    return f"{day.strftime('%a, %b')} {day.day}"


def practice_agenda(pr: dict) -> list[dict]:
    """Every practice, whichever shape it was written in, as one list of timed blocks.

    Two shapes live in install.json. The first four practices use the fixed
    agility/install/finisher trio they were authored in; a practice with more going on
    — position groups running side by side, a water break, a live scrimmage — names its
    own `blocks` instead. Normalising the two here rather than in the file means the
    calendar, the day page and the practice list read one shape instead of carrying
    three copies of the same branch, and no already-taught practice had to be rewritten
    to a schema the coach never asked for.
    """
    custom = pr.get("blocks")
    if custom:
        return [dict(b) for b in custom]

    out: list[dict] = []
    tags = iter("ABCDEFGHIJ")
    if pr.get("agility_drills"):
        out.append({"tag": next(tags), "kind": "drills", "title": "Agility training",
                    "time": pr.get("agility_time", ""),
                    "drills": pr["agility_drills"]})
    out.append({"tag": next(tags), "kind": "install", "title": "Install",
                "time": pr.get("install_time", "")})
    if pr.get("finisher"):
        out.append({"tag": next(tags), "kind": "note", "title": "Finisher",
                    "time": pr.get("finisher_time", ""), "note": pr["finisher"]})
    return out


def practice_window(pr: dict) -> str:
    """When to show up and when it is over — the first block's start to the last
    thing on the sheet, which is the huddle if there is one."""
    times = [b.get("time", "") for b in practice_agenda(pr)]
    times.append(pr.get("huddle_time", ""))
    times = [t for t in times if t]
    if not times:
        return ""
    start = times[0].split("–")[0].strip()
    end = times[-1].split("–")[-1].strip()
    return f"{start}–{end}" if end and end != start else start


def play_number(play: dict) -> str:
    """"#18 | " ahead of a play wherever a sheet lists it — the call sheet's cells and a
    practice's install chips — so paper uses the same number the diagram and the boys'
    wristbands do."""
    return f"#{play['code']} | " if play.get("code") else ""


def install_items(pr: dict, plays: dict, forms_by_id: dict, defenses: dict) -> list[str]:
    """The play, front and formation chips a practice installs."""
    items = []
    for pid in pr.get("plays", []):
        play, _form = plays[pid]
        items.append(
            f'<a class="ins-play" href="{p_href(play)}">'
            f'<span class="ins-call">{esc(play_number(play))}{esc(play.get("call", ""))}</span>'
            f'<span class="ins-name">{esc(play["name"])}</span></a>'
        )
    # A play this practice runs again rather than teaches. Marked, because the block
    # answers "what is new today" first and this is the honest answer to "what else
    # are we running".
    for pid in pr.get("review", []):
        play, _form = plays[pid]
        items.append(
            f'<a class="ins-play again" href="{p_href(play)}">'
            f'<span class="ins-call">{esc(play_number(play))}{esc(play.get("call", ""))}</span>'
            f'<span class="ins-name">{esc(play["name"])} &middot; review</span></a>'
        )
    # A practice that goes back through everything already installed out of a formation
    # rather than a named list of plays. Listing the plays individually would be a lie
    # about how the block runs -- the coach calls whatever he likes off the book, and
    # what the sheet owes him is which book, not which six plays.
    for fmid in pr.get("review_formations", []):
        form = forms_by_id[fmid]
        items.append(
            f'<a class="ins-play again form" href="{f_href(form)}">'
            f'<span class="ins-call">{esc(form_label(form))}</span>'
            f'<span class="ins-name">everything installed &middot; review</span></a>'
        )
    for fid in pr.get("fronts", []):
        front = defenses[fid]
        items.append(
            f'<a class="ins-play def" href="{d_href(front)}">'
            f'<span class="ins-call">{esc(front["call"])}</span>'
            f'<span class="ins-name">{esc(front["name"])} defence</span></a>'
        )
    for fmid in pr.get("formations", []):
        form = forms_by_id[fmid]
        items.append(
            f'<a class="ins-play form" href="{f_href(form)}">'
            f'<span class="ins-call">{esc(form_label(form))}</span>'
            f'<span class="ins-name">formation &mdash; alignment only</span></a>'
        )
    return items


def install_count(pr: dict) -> int:
    return (len(pr.get("plays", [])) + len(pr.get("fronts", []))
            + len(pr.get("formations", [])))


def requires_html(pr: dict, plays: dict, defenses: dict) -> str:
    need = pr.get("requires", [])
    if not need:
        return ""
    names = ", ".join(esc(plays[n][0]["name"]) if n in plays
                      else esc(defenses[n]["call"]) for n in need)
    return f'<p class="ins-req">Needs {names} working first</p>'


def drills_html(drills: list) -> str:
    """A drill list, where a drill may carry a progression under it.

    A drill is a string, or an object with a `then` — the steps you work through
    inside that drill, in order:

        {"drill": "Start with up-the-middle handoffs",
         "then": ["Move to slant handoffs", "Move to pitches"]}

    The nesting is the content, not decoration: "start here, then move to this" is one
    drill that grows, and flattening it into four bullets of equal weight loses the
    order and reads as four separate things to get through.
    """
    if not drills:
        return ""
    out = []
    for d in drills:
        if isinstance(d, dict):
            out.append(f'<li>{esc(d.get("drill", ""))}{drills_html(d.get("then"))}</li>')
        else:
            out.append(f"<li>{esc(d)}</li>")
    return f'<ul class="ins-drills">{"".join(out)}</ul>'


# The spots a rotation deals with when a block does not name its own. Six, because
# the line is a different problem: a tackle and a guard swap and nothing about the
# play changes, while a boy moving from Z to TB is being asked to do another job
# entirely. The line rotates in its own block ("groups"), not on a lineup card.
ROTATION_SPOTS = ("X", "Y", "Z", "QB", "FB", "TB")


def rotation_html(blk: dict, plays: dict, roster: dict) -> str:
    """One rotation block: the lineup for every snap, a row each.

    Nothing is checked here. validate_install() has already refused to build a card
    that puts a boy somewhere the depth chart never listed him, that puts one boy in
    two spots on the same snap, or that runs a play nobody has been taught yet. By the
    time this runs every cell is known good, so this only decides how it reads.
    """
    snaps = blk.get("snaps") or []
    if not snaps:
        return ""
    spots = list(blk.get("spots") or ROTATION_SPOTS)
    side = roster.get("offense") or {}
    depth = {sp: {n: i for i, n in enumerate(side.get(sp) or [], 1)} for sp in spots}
    # A rotation is about who is standing where, and the play is only on the card when
    # the card is what decides it. A practice where the coach calls whatever he likes
    # off the installed book leaves the play off every snap, and the column goes with
    # it rather than printing six dashes a coach has to look past on the field.
    with_plays = any(snap.get("play") for snap in snaps)

    head = "".join(f"<th>{esc(sp)}</th>" for sp in spots)
    rows = []
    for i, snap in enumerate(snaps, 1):
        cells = [f'<td class="rot-n">{i}</td>']
        if with_plays:
            pid = snap.get("play")
            found = plays.get(pid) if pid else None
            if found:
                play = found[0] if isinstance(found, tuple) else found
                cell = (f'<a href="{p_href(play)}" title="{esc(play["name"])}">'
                        f'#{esc(play["code"])}</a>')
            else:
                cell = '<span class="xl-none">&mdash;</span>'
            cells.append(f'<td class="rot-play">{cell}</td>')
        for sp, man in zip(spots, snap.get("men") or []):
            d = depth.get(sp, {}).get(man)
            klass = "own" if d == 1 else "deep"
            num = f'<span class="rot-d">{d}</span>' if d else ""
            cells.append(f'<td><span class="rot-man {klass}">{esc(man)}</span>{num}</td>')
        rows.append(f'<tr>{"".join(cells)}</tr>')

    play_head = "<th>Play</th>" if with_plays else ""
    return ('<div class="rot-wrap"><table class="rot">'
            f'<thead><tr><th>#</th>{play_head}{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def practice_blocks_html(pr: dict, items: list[str], needs: str,
                         plays: dict | None = None,
                         roster: dict | None = None) -> str:
    """The run of practice, block by block, in the order it happens."""
    if not items:
        items = ['<span class="ins-none">No new install &mdash; review</span>']
    rendered = []
    for blk in practice_agenda(pr):
        tag = blk.get("tag", "")
        t = blk.get("time", "")
        t_html = f'<span class="ins-blk-time">{esc(t)}</span>' if t else ""
        head = (f'<p class="ins-blk-h"><span class="ins-blk-tag">Block {esc(tag)}</span> '
                f'{esc(blk.get("title", ""))}{t_html}</p>')
        # A block can override the practice's break — `"water_break": 0` on the warm-up
        # runs it straight into the first block.
        water = blk.get("water_break", pr.get("water_break"))
        kind = blk.get("kind")
        if kind == "note":
            body = f'<p class="ins-em">{esc(blk.get("note", ""))}</p>'
        elif kind == "drills":
            body = drills_html(blk.get("drills", []))
        elif kind == "groups":
            body = ('<div class="ins-grps">' + "".join(
                f'<div class="ins-grp"><p class="ins-grp-h">{esc(g.get("name", ""))}</p>'
                f'{drills_html(g.get("drills", []))}</div>'
                for g in blk.get("groups", [])
            ) + '</div>')
        elif kind == "rotation":
            note = blk.get("note", "")
            note_html = f'<p class="ins-em">{esc(note)}</p>' if note else ""
            body = note_html + rotation_html(blk, plays or {}, roster or {})
        elif kind == "install":
            emphasis = pr.get("emphasis", "")
            emphasis_html = f'<p class="ins-em">{esc(emphasis)}</p>' if emphasis else ""
            extra = "".join(f"<li>{esc(n)}</li>" for n in blk.get("notes", []))
            extra_html = f'<ul class="ins-drills">{extra}</ul>' if extra else ""
            body = (f'<div class="ins-list">{"".join(items)}</div>'
                    f'{emphasis_html}{extra_html}{needs}'
                    f'{rotation_html(blk, plays or {}, roster or {})}')
        else:
            body = ""
        rendered.append(f'<div class="ins-blk">{head}{body}</div>')
        # A water break after every block, written once on the practice rather than
        # five times in its block list. Typed out it is five entries a coach has to
        # keep in step with the clock; as a property it cannot drift, and the run of
        # practice still reads as the coaching blocks instead of alternating between
        # work and water.
        if water:
            rendered.append(
                f'<p class="ins-water">Water break'
                f'<span class="ins-water-t">{esc(water)} min</span></p>')

    huddle = pr.get("huddle", "")
    if huddle:
        h_time = pr.get("huddle_time", "")
        h_time_html = (f'<span class="ins-huddle-time">{esc(h_time)}</span>'
                       if h_time else "")
        rendered.append(
            f'<p class="ins-huddle"><b>Team huddle.</b> {esc(huddle)}{h_time_html}</p>')
    return "".join(rendered)


def month_grid(year: int, month: int, days: dict) -> str:
    """One month, Sunday-first, with whatever practices fall in it.

    A real table rather than a grid of divs: a month is a table of dates, and a screen
    reader announcing "Tuesday, 11" off the column header is the whole reason to use
    one. Days outside the month keep their cell so the weeks stay seven wide.
    """
    weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(year, month)
    head = "".join(
        f'<th scope="col"><abbr title="{calendar.day_name[(i + 6) % 7]}">'
        f'{calendar.day_abbr[(i + 6) % 7][:3]}</abbr></th>' for i in range(7)
    )
    rows = []
    for week in weeks:
        cells = []
        for day in week:
            if day.month != month:
                cells.append('<td class="cal-cell out"></td>')
                continue
            evs = "".join(days.get(day, []))
            cls = " has" if evs else ""
            cells.append(
                f'<td class="cal-cell{cls}" data-date="{day.isoformat()}">'
                f'<span class="cal-d">{day.day}</span>{evs}</td>'
            )
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return (f'<table class="cal">'
            f'<caption>{calendar.month_name[month]} {year}</caption>'
            f'<thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


def months_between(first, last) -> list[tuple[int, int]]:
    out, y, m = [], first.year, first.month
    while (y, m) <= (last.year, last.month):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def load_schedule(root: Path) -> dict:
    import json as _json
    path = root / "install.json"
    if not path.is_file():
        return {"practices": []}
    return _json.loads(path.read_text(encoding="utf-8"))


def write_install(formations: list[dict], defenses: dict, root: Path) -> str:
    """The install schedule as a calendar.

    The schedule used to be one long scroll of practice cards, which is the wrong shape
    for both questions a coach actually asks it. "What are we doing Tuesday?" wants a
    month you can point at; "what is the plan for this practice?" wants one page with
    nothing else on it. So this page is the month grid and a list of the practices under
    it, and every practice links to its own page.

    Practices are still numbered, and the number is still what carries teaching order —
    a rained-out session moves the whole schedule down one rather than skipping
    something. The date is only where that number happens to land.
    """
    schedule = load_schedule(root)
    practices = schedule.get("practices", [])
    plays = {p["id"]: (p, f) for f in formations for p in f["_plays"]}
    forms_by_id = {f["id"]: f for f in formations}
    phases = schedule.get("phases", {})

    # ---- the calendar -------------------------------------------------------
    days: dict = {}
    dated = [(practice_date(pr), pr) for pr in practices]
    dated = [(d, pr) for d, pr in dated if d]
    for day, pr in dated:
        # A square on a phone is barely wider than the word "Practice", so the word is
        # dropped below 480px and only the number is left. The link keeps its whole
        # name in aria-label, so what is dropped is pixels, not meaning.
        label = f'Practice {pr["n"]}'
        if pr.get("focus"):
            label += f' — {pr["focus"]}'
        days.setdefault(day, []).append(
            f'<a class="cal-ev" href="{install_href(pr)}" '
            f'data-phase="{esc(pr.get("phase", ""))}" aria-label="{esc(label)}">'
            f'<span class="cal-ev-n"><span class="cal-ev-w">Practice </span>{pr["n"]}</span>'
            f'<span class="cal-ev-t">{esc(pr.get("focus", ""))}</span></a>'
        )

    cal_html = ""
    if dated:
        first, last = min(d for d, _ in dated), max(d for d, _ in dated)
        cal_html = (
            '<div class="cal-next" id="calnext" hidden></div>'
            '<div class="cal-wrap">'
            + "".join(month_grid(y, m, days) for y, m in months_between(first, last))
            + "</div>"
            + '<p class="cal-legend">'
            + "".join(
                f'<span class="cal-key {esc(ph)}"></span> '
                f'{esc(phases.get(ph, {}).get("label", ph))} '
                for ph in dict.fromkeys(pr.get("phase") for _d, pr in dated)
                if ph
            )
            + '<span class="cal-key today"></span> Today</p>'
        )

    # ---- the practices, in order, grouped by phase ---------------------------
    rows, seen_phase = [], None
    for pr in practices:
        phase = pr.get("phase")
        if phase != seen_phase:
            seen_phase = phase
            meta = phases.get(phase, {})
            rows.append(
                f'<div class="ph"><h2>{esc(meta.get("label", phase or ""))}</h2></div>'
            )
        day = practice_date(pr)
        when = date_label(day) if day else esc(str(pr.get("date", "")))
        rows.append(
            f'<a class="ins-row" href="{install_href(pr)}">'
            f'<span class="ins-row-n"><small>Practice</small><b>{pr["n"]}</b></span>'
            f'<span class="ins-row-body"><time>{when}</time>'
            f'<strong>{esc(pr.get("focus", ""))}</strong></span>'
            f'<span class="ins-row-go" aria-hidden="true">&rarr;</span></a>'
        )

    # The page is the calendar and the list of practices under it. The intro paragraph,
    # the counts strip, each phase's note, every practice's time / blocks / new-or-review
    # line, the +N and REV badges on the calendar and the "Not scheduled yet" list all
    # described the schedule rather than being it, so they are gone.
    body = f"""{page_head("Install schedule")}
{cal_html}
<div class="ins-wrap">
{chr(10).join(rows)}
</div>"""
    return page(
        f"Install schedule — {SITE_TITLE}",
        body,
        formations,
        defenses=defenses,
        active_nav="install",
        description="Practice-by-practice install schedule for the playbook.",
    )


def write_install_day(
    pr: dict, prev: dict | None, nxt: dict | None, all_practices: list[dict],
    phases: dict, formations: list[dict], defenses: dict, root: Path | None = None,
) -> str:
    """One practice, on its own page: what we install, and the run of practice.

    Everything a coach carries onto the field for that session and nothing from any
    other one — the long scroll made you scan past four practices to find tonight's.
    """
    plays = {p["id"]: (p, f) for f in formations for p in f["_plays"]}
    forms_by_id = {f["id"]: f for f in formations}
    # The depth chart, for the rotation card's numbers. Read here rather than in
    # the block renderer so a practice with two rotation blocks still reads the
    # file once.
    roster = _roster_and_plays(root, formations)[0] if root else {}

    items = install_items(pr, plays, forms_by_id, defenses)
    needs = requires_html(pr, plays, defenses)
    day = practice_date(pr)
    when = date_label(day, long=True) if day else str(pr.get("date", ""))
    phase = phases.get(pr.get("phase"), {})

    crumbs = ('<nav class="crumbs"><a href="index.html">Home</a><span>/</span>'
              f'<a href="install.html">Install schedule</a><span>/</span>'
              f'<b>Practice {pr["n"]}</b></nav>')

    # Every practice on the schedule, so you can step to any other one without going
    # back to the calendar first — the same bar the play pages carry.
    others = "\n    ".join(
        f'<a href="{install_href(p)}"'
        f'{ACTIVE_ATTR if p["n"] == pr["n"] else ""} '
        f'title="{esc(p.get("focus", ""))}">{p["n"]}</a>'
        for p in all_practices
    )
    bar = f'<div class="playbar nums">\n    {others}\n  </div>' if others else ""

    # A practice whose date is not settled yet says so rather than leaving a gap where
    # the date goes — the schedule is built out one practice at a time.
    when_html = (f'<p class="ins-day-when">{esc(when)}</p>' if when else
                 '<p class="ins-day-when undated">Date not set yet</p>')

    # The page is the practice: what it is, when, and the run of it. The facts strip,
    # the "Installing today" line, the phase note and the previous/next buttons each
    # repeated something the plan or the practice bar above already says, so they are
    # gone and the plan starts right under the date.
    body = f"""{crumbs}
{bar}
<div class="ins-day">
  <p class="rb-eyebrow">Practice {pr["n"]}{" &middot; " + esc(phase.get("label", "")) if phase.get("label") else ""}</p>
  <h1 class="page">{esc(pr.get("focus", ""))}</h1>
  {when_html}
  <div class="ins-day-h"><h2>The run of practice</h2>
    {PRINT_BTN}
  </div>
  <div class="ins-day-plan">{practice_blocks_html(pr, items, needs, plays, roster)}</div>
</div>"""

    attrs = ""
    if prev:
        attrs += f' data-prev="{install_href(prev)}"'
    if nxt:
        attrs += f' data-next="{install_href(nxt)}"'
    return page(
        f"Practice {pr['n']}: {pr.get('focus', '')} — {SITE_TITLE}",
        body,
        formations,
        defenses=defenses,
        active_nav="install",
        description=(f"Practice {pr['n']}"
                     + (f" — {when}" if when else "")
                     + f": {pr.get('focus', '')}")[:160],
        main_attrs=attrs,
    )



# The defense side has no shared position-name table the way offense does — those
# names are specific to the calling language (see common.POSITION_NAMES) and mixing
# defensive roles into that table would put "left end" in a place that answers a
# different question. Kept local to the depth chart, the only page that needs it.
#
# Every line key carries a D. It is not decoration: LG and LT are offensive line
# positions in this book, and a chart with both on it wants to say which one it
# means without the reader working it out from context.
DEFENSE_POSITION_NAMES = {
    "LDE": "Left defensive end", "LDT": "Left defensive tackle",
    "LDG": "Left defensive guard", "NT": "Nose tackle",
    "RDG": "Right defensive guard", "RDT": "Right defensive tackle",
    "RDE": "Right defensive end",
    "LOLB": "Left outside linebacker", "LILB": "Left inside linebacker",
    "MLB": "Middle linebacker",
    "RILB": "Right inside linebacker", "ROLB": "Right outside linebacker",
    "LLB": "Left linebacker", "RLB": "Right linebacker",
    "LC": "Left corner", "RC": "Right corner", "FS": "Free safety",
    "LS": "Left safety", "MS": "Middle safety", "RS": "Right safety",
}

# What the backers answer to on the field. A position key is for the book; this is the
# word yelled across a field at an eight-year-old, and it is the one he will remember.
# Depth-chart only -- it must not reach the cards, where "block the lion" would send a
# guard looking for an animal.
DEFENSE_NICKNAMES = {
    "LOLB": "Lion", "LILB": "Leo", "RILB": "Ray", "ROLB": "Rhino",
}


# The columns, in the order they take the field. Depth in roster.json *is* the column:
# the first name at a position is the starter, the second is second string, and so on.
# One ordered list per position stays the thing a coach edits, and nobody has to keep
# two copies of the same roster agreeing with each other.
#
# These were Purple, Gold and White once. A colour is a fine name for a practice jersey
# and a poor one for a column: it carries no order, so "who is behind him" needed a key
# nobody had, and once the header had scrolled away the board was a row of anonymous
# columns of names. A depth chart numbers its columns.
#
# The sixth used to be Jumbo, a short-yardage package rather than a depth, and it was
# the last thing on this page that needed explaining before it could be read. It is
# column six now. Both sides of the ball run the same six, so there is no longer a
# per-side column list and nothing has to ask which side it is building.
# Seven, not six. The squad outgrew it: the slot is seven deep and the seventh man
# there plays nowhere else on offense, so at six he was in roster.json and on no
# chart at all — the one failure mode a depth chart must not have, because the way
# you find out is a Saturday.
#
# It costs almost nothing to print. A position card is only as tall as its own last
# filled name, so the seventh row appears on the one card that has a seventh man and
# nowhere else; the offensive sheet had about four tenths of an inch spare and this
# spends a tenth of it. Raise it again the same way if the squad grows, and check
# test_print_pages.py rather than assuming.
ROTATIONS = [str(n) for n in range(1, 8)]

# Packages, above the squad. A fixed group rather than a list because the group is the
# thing being named — the kids who go on and come off together. Count and size are per
# side and here and nowhere else: the markup, the roster round-trip and the print sheet
# all take their shape from them.
#
# The two sides mean different things by "package", which is why they are sized so
# differently. An offensive package is a whole eleven: six of them, eleven deep, the
# quarterback and the backfield, the two tight ends, then the five interior linemen.
# A defensive package is an eleven too. It is easier to think of as "the base with
# three or four swapped", and that is what the sub card prints -- but what it holds is
# the whole unit, because a card that says who came off has to know who is on.
PACKAGE_COUNT = {"offense": 6, "defense": 6}
PACKAGE_SIZE = {"offense": 11, "defense": 11}

# What each side calls its packages. The offense heading names the backfield the
# group is made of, in the order those four sit in the box as #1 through #4.
PACKAGE_TITLE = {
    "offense": "Offensive Packages",
    "defense": "Packages",
}

# What each slot in a package is. Offense: the quarterback, the fullback and the
# tailback, then X, Y and Z, then the left tackle, left guard, center, right guard and
# right tackle. Defense: the base front's own eleven, line then backers then
# secondary, so a name on the card carries the spot he plays — Gavin P. (LDE).
# Three groups, in the order a coach says them: the backfield, the three outside
# the tackles, then the line. It is also the order the package arrays are stored
# in roster.json, because one order that both the file and the page use cannot
# drift out of step with itself. The dashed rules on the depth chart fall out of
# it -- the CSS breaks before X and before LT, which are exactly the two seams.
PACKAGE_SPOTS = {
    "offense": ("QB", "FB", "TB", "X", "Y", "Z", "LT", "LG", "C", "RG", "RT"),
    "defense": ("LDE", "LDG", "RDG", "RDE",
                "LOLB", "LILB", "RILB", "ROLB", "LC", "RC", "FS"),
}

# Only the backs are numbered on the package card. The number is the back's digit
# with the hole digit 0 behind it — 10, 20, 30 — the way the diagram labels the
# three, so the card and the diagram agree.
#
# X, Y and Z are not in here. They had 40, 50 and 60 for a while, back when the
# numbering had to point at them somehow, and the letters took those digits away:
# a letter IS the name, and "Z (40)" printed a number no call says any more. The
# line was never numbered and still is not.
PACKAGE_NUMBERED = ("QB", "FB", "TB")


def rotations_for(side: str) -> list[tuple[str, str, str]]:
    """The columns, in depth order. Both sides run the same six."""
    return [(n, "d" + n, "") for n in ROTATIONS]


def package_changes(packs: list, n: int, spots: tuple = ()):
    """What package `n` changes about the base eleven: (out, in, moved).

    Three kinds, and the third is the one a two-column card cannot say by itself.
    `out` is a boy who leaves the eleven, `in` is a boy who joins it and the spot he
    joins at, and `moved` is a boy in BOTH elevens playing a different job -- nobody
    ran on or off for him, so neither of the other two lists can name him.

    The depth chart and the call sheet both print this, in different shapes and at
    different sizes, and they work it out here so they cannot disagree about who is
    doing what. They did once: the call sheet listed a move as a substitution at each
    of the two spots, which read as two boys changing when it was one boy turning
    round.
    """
    first = [name for name in (packs[0] if packs else []) if name]
    here = packs[n - 1] if n - 1 < len(packs) else []
    first_set = set(first)
    here_set = {name for name in here if name}
    out = [name for name in first if name not in here_set]
    inn = []
    for i, name in enumerate(here):
        if name and name not in first_set:
            spot = spots[i] if i < len(spots) else ""
            inn.append((name, spot))

    # Where each man stands in the base, and where he stands here. A name in both with
    # two different spots is a move. Listed in base order, which is the order the
    # package card reads down.
    was = {name: spots[i] for i, name in enumerate(packs[0] if packs else [])
           if name and i < len(spots)}
    now = {name: spots[i] for i, name in enumerate(here) if name and i < len(spots)}
    moved = [(name, was[name], now[name]) for name in first
             if name in now and was.get(name) != now[name]]
    return out, inn, moved


def package_sub_card_html(packs: list, n: int, spots: tuple = ()) -> str:
    """Who comes off, who goes on, and who stays on at a different job.

    Out and In are the eleven changing: names that leave the base package and
    names that join it. Incoming names carry the spot they play here, so the
    card says Joseph P. (Y) rather than just Joseph P.

    Moved is the third thing, and it used to be nothing. A boy in both elevens
    is not a substitution, so the card dropped him -- and that quietly lost the
    fact that Philip is the Z in Shifty and the TAILBACK in Fortnite. Nobody
    came off for him and nobody went on, so neither column could say it, and a
    coach reading the card had two elevens that agreed on the name and
    disagreed on the job. It is the change most likely to put a boy in the
    wrong place, because he is the one man on the field who was not told to
    run on or off.

    Package 1 is the base on both sides — Shifty on offense, Base on defense —
    so it is what everything else is measured against and its own card says so.
    """
    out, inn, moved = package_changes(packs, n, spots)

    if n <= 1:
        body = '<p class="dc-sub-empty">Base</p>'
    elif not (out or inn or moved):
        body = '<p class="dc-sub-empty">Same as base</p>'
    else:
        body = ""
        width = max(len(out), len(inn))
        if width:
            rows = []
            for i in range(width):
                leaving = out[i] if i < len(out) else ""
                entering = inn[i] if i < len(inn) else ("", "")
                name, spot = entering
                coming = (
                    f'<span class="dc-sub-man">{esc(name)}</span> '
                    f'<span class="dc-sub-pos">({esc(spot)})</span>'
                    if name and spot else
                    (f'<span class="dc-sub-man">{esc(name)}</span>' if name else "—")
                )
                rows.append(
                    '<tr><td>'
                    + (f'<span class="dc-sub-man">{esc(leaving)}</span>'
                       if leaving else "—")
                    + f'</td><td>{coming}</td></tr>'
                )
            body += (
                '<table class="dc-sub"><caption>Subs</caption>'
                '<thead><tr><th>Out</th><th>In</th></tr>'
                '</thead><tbody>'
                + "".join(rows)
                + "</tbody></table>"
            )
        if moved:
            rows = "".join(
                f'<tr><td><span class="dc-sub-man">{esc(name)}</span></td>'
                f'<td class="dc-mv"><span class="mv-a">{esc(a)}</span>'
                f'<span class="mv-b">{esc(b)}</span></td></tr>'
                for name, a, b in moved
            )
            body += (
                '<table class="dc-sub dc-moved"><caption>Moves</caption>'
                '<thead><tr><th>Player</th><th>Spot</th></tr></thead><tbody>'
                + rows
                + "</tbody></table>"
            )
    return f'<aside class="dc-subcard"><p class="dc-subcard-h">Sub card</p>{body}</aside>'


def alignment_bands(alignment: dict, order: list[str], side: str) -> list[list[str]]:
    """`order` split into rows of the field, read off the alignment itself.

    The board is laid out like the formation rather than as an alphabetical list,
    so a coach looking for the left guard looks where the left guard stands. The
    rows are not typed out anywhere: they are the distinct depths in the
    formation's own coordinates, and the men in each are sorted left to right.
    That is what makes it work for the defense too, and for a front nobody has
    drawn yet — change `4-4.json` and the board rearranges itself.

    Depths inside three quarters of a yard of each other are one row. The gaps
    that matter are much bigger than that (the offense goes -0.5, -1.5, -3.3,
    -5.5) and the tolerance keeps a half-yard stagger from splitting a line in
    two.
    """
    spots = [p for p in order if p in alignment]
    if not spots:
        return []
    # Offense is drawn with the backfield at negative y, defense downfield at
    # positive, and both read from the line of scrimmage outward.
    depth = (lambda p: -alignment[p][1]) if side == "offense" else (lambda p: alignment[p][1])
    bands: list[list[str]] = []
    for pos in sorted(spots, key=depth):
        if bands and abs(depth(pos) - depth(bands[-1][0])) <= 0.75:
            bands[-1].append(pos)
        else:
            bands.append([pos])
    return [sorted(b, key=lambda p: alignment[p][0]) for b in bands]


def position_card(side: str, pos: str, names: list[str], label_fn,
                  style: str = "", cls: str = "") -> str:
    """One position: the spot on a dark bar, the starter, then the men behind him.

    Depth is down the card now rather than across a row. A name's rank is printed
    beside it because the column it used to be in is gone, and a gap stays a gap --
    an empty second string is a blank line, not everybody below moving up.
    """
    rots = rotations_for(side)
    last = max((i for i, n in enumerate(names[:len(rots)]) if n), default=-1)
    if last < 0:
        body = '<p class="dc-open">Open</p>'
    else:
        body = "<ol class=\"dc-names\">" + "".join(
            f'<li class="{"starter" if i == 0 else ""}">'
            f'<b>{i + 1}</b>'
            + (f'<span>{esc(names[i])}</span>' if i < len(names) and names[i]
               else '<span class="dc-gap">—</span>')
            + "</li>"
            for i in range(last + 1)
        ) + "</ol>"
    return (f'<div class="dc-pos{cls}" data-pos="{esc(pos)}"{style}>'
            f'<p class="dc-pos-h"><span class="dc-abbr">{esc(pos)}</span>'
            f'<span class="dc-label">{esc(label_fn(pos))}</span></p>'
            f'{body}</div>')


# Two board-only adjustments, and the only two places the layout is told something the
# alignment does not say. They are here rather than in the defensive JSON because the
# JSON is where the front is DRAWN -- moving a corner there moves him on every play card
# in the book, and a corner at 4.4 yards is where a corner actually stands.
#
# BOARD_DROP sends a spot to the bottom row of the board. The corners share the
# linebackers' depth on the field, which put six cards in that row and squeezed the four
# linebackers into the middle of it. Dropped, they read as what they are -- the
# secondary, across the back of the board with the free safety between them -- and the
# linebackers get the room.
#
# BOARD_NUDGE then slides a card sideways, in card widths. The outside linebacker stacks
# the end closely enough to land in his column, which drew him directly under the end
# and lost the one thing the picture is for: he plays OUTSIDE that man. Three quarters
# out leaves a quarter of overlap, so the stack still reads while the alignment does too.
#
# The inside pair is nudged a quarter each for spacing alone. Their columns are the
# guards', a column apart, while the outside backers now sit three quarters wider than
# the ends -- which left the row reading 1.75, 1.0, 1.75 and looking like two pairs
# rather than a front of four. A quarter out apiece spreads the four evenly at 1.5
# columns, and a quarter is small enough that each inside backer is still plainly on his
# guard.
BOARD_DROP = {"defense": ("LC", "RC")}
BOARD_NUDGE = {"defense": {"LOLB": -0.75, "LILB": -0.25,
                           "RILB": 0.25, "ROLB": 0.75}}


def side_board(side: str, order: list[str], alt_order: list[str],
               names_by_pos: dict, label_fn, packages: list | None = None,
               package_names: list | None = None,
               alignment: dict | None = None,
               rotations: list | None = None) -> str:
    """One side of the ball, laid out the way it lines up.

    This was six numbered columns of a grid, which answered "who is second at left
    tackle" by making you find the left tackle's row first -- eleven rows that read
    as a list and not as a football team. The board is now the formation: the line
    across the top in its own order, the backfield under it, the secondary behind
    that, each spot a card with the starter at the top and the men behind him under
    it. A coach looks where the player stands.

    Names are hard values from roster.json -- a printed depth chart, not a board you
    rearrange in the browser.
    """
    align = alignment or {}
    bands = alignment_bands(align, order, side)
    seen = {p for b in bands for p in b}

    # The dropped spots leave their own row and join the bottom one. Their columns are
    # still worked out from their real x below, so a corner lands out past the end he
    # lines up outside of — he is only a row lower than the field puts him.
    drop = [p for p in BOARD_DROP.get(side, ()) if p in seen]
    if drop and len(bands) > 1:
        bands = [[p for p in band if p not in drop] for band in bands]
        bands[-1] = sorted(bands[-1] + drop, key=lambda p: align[p][0])
        bands = [b for b in bands if b]

    # Every band shares one set of columns, and the columns are every distinct spot
    # on the side rather than just the widest band's. Taking them from the widest
    # band gave the board only as many columns as the line has men, so anybody
    # standing outside the last of them had to share his column: the Z landed
    # directly under the Y instead of outside him, and the free safety -- the only
    # man in his row -- sat a column left of centre because there was no column at
    # the middle for him to be in. With one column per spot the picture is the
    # alignment: the slot is outside the tight end, the four down linemen interleave
    # with the linebackers behind them, and anybody on the ball is in the middle
    # column because the middle column exists.
    # The columns are the front row's -- the offensive line, the defensive line --
    # and everybody behind stands in the column of the man he is behind. That is how
    # a depth chart is read: the inside linebacker belongs under the defensive guard
    # he plays off, not in a column of his own a half-yard to the side of him, which
    # is what one-column-per-spot produced. Eleven columns of stagger is an accurate
    # plot of the alignment and a bad board.
    #
    # A man who is not behind anybody gets his own column, placed in x order: the
    # corners out past the ends, the free safety in the middle, the slot outside the
    # tight end. 1.3 yards is the line between the two, and it sits in a real gap --
    # a linebacker is about a yard off the lineman he stacks (the 4-4's are 1.0 and
    # 1.1), and the nearest thing that must NOT snap is the slot at 1.4 outside the
    # tight end and the safety at 1.4 inside the guards.
    # 1.2 yards, and both sides of it are close. The linebackers that must snap onto
    # their linemen are 1.0 and 1.1 off them; the two men that must NOT snap -- the
    # slot outside the tight end, the safety inside the guards -- are both 1.4. So
    # there is a fifth of a yard of daylight either way, and moving anybody by a
    # foot in the JSON is enough to change this board. It is the kind of constant
    # that deserves the arithmetic written next to it.
    SNAP = 1.2
    ref = bands[0] if bands else []
    cols_x = sorted(round(align[p][0], 2) for p in ref)
    span_x = cols_x[0] if cols_x else 0.0, cols_x[-1] if cols_x else 0.0
    # A new column only for a man standing OUTSIDE the front row -- the corners, the
    # slot. Somebody who falls in a gap BETWEEN two of them does not get one, because
    # a column for him pushes the front row apart to make room and the four down
    # linemen stop being four down linemen. He straddles the gap instead, which is
    # also where he actually stands: the free safety is over the ball, between the
    # guards, not in a lane of his own that shoves them a card further apart.
    for band in bands[1:]:
        for pos in band:
            x = round(align[pos][0], 2)
            outside = x < span_x[0] - SNAP or x > span_x[1] + SNAP
            if outside and all(abs(x - c) > SNAP for c in cols_x):
                cols_x.append(x)
    cols_x = sorted(set(cols_x))

    def placement(pos: str) -> tuple[int, int]:
        """(first column, how many columns wide) for this spot."""
        if not cols_x or pos not in align:
            return (0, 1)
        x = align[pos][0]
        # Ties go to the inside man. The 4-4's inside linebacker sits exactly halfway
        # between the end and the guard (1.1 from each), and an inside linebacker
        # belongs under the guard.
        i = min(range(len(cols_x)),
                key=lambda i: (abs(cols_x[i] - x), abs(cols_x[i])))
        if abs(cols_x[i] - x) <= SNAP:
            return (i + 1, 1)
        left = [j for j, c in enumerate(cols_x) if c < x]
        right = [j for j, c in enumerate(cols_x) if c > x]
        if left and right:
            # Inclusive of both neighbours: the columns either side of him, so he
            # centres on the seam between them.
            return (left[-1] + 1, right[0] - left[-1] + 1)
        return (i + 1, 1)

    def place(band: list[str]) -> str:
        used: set[int] = set()
        out = []
        for pos in band:
            col, wide = placement(pos)
            while col in used:          # two men rounding to one column: step outward
                col += 1
            used.add(col)
            cls = " dc-straddle" if wide > 1 else ""
            bits = [f"grid-column:{col} / span {wide}"] if col else []
            nudge = BOARD_NUDGE.get(side, {}).get(pos)
            if nudge:
                bits.append(f"transform:translateX({nudge * 100:g}%)")
            style = f' style="{";".join(bits)}"' if bits else ""
            out.append(position_card(side, pos, names_by_pos.get(pos) or [], label_fn,
                                     style, cls))
        return "".join(out)
    # Anything the alignment does not place keeps its place on the board rather than
    # vanishing: a spot only a change-up front uses, or one the base formation has no
    # room for. Same rule as before, just a row of its own.
    leftover = [p for p in order if p not in seen]

    cols = max(len(cols_x), 1)
    field = "".join(f'<div class="dc-band">{place(band)}</div>' for band in bands)
    for extra, title in ((leftover, "Also on the board"),
                         (alt_order, "Other formations")):
        if extra:
            field += (f'<div class="dc-band dc-band-alt"><p class="dc-band-h">'
                      f'{esc(title)}</p>'
                      + "".join(position_card(side, p, names_by_pos.get(p) or [], label_fn)
                                for p in extra)
                      + "</div>")

    packs = packages or []
    pkg_names = package_names or []
    spots = PACKAGE_SPOTS.get(side, ())

    def slot_html(n: int, at: int) -> str:
        pair = packs[n - 1] if n - 1 < len(packs) else []
        name = pair[at] if isinstance(pair, list) and at < len(pair) else ""
        label = spots[at] if at < len(spots) else ""
        attr = ""
        if label in PACKAGE_NUMBERED:
            attr += f' data-n="{(PACKAGE_NUMBERED.index(label) + 1) * 10}"'
        if label:
            attr += f' data-spot="{esc(label)}"'
        who = esc(name) if name else ""
        return f'<div class="dc-pkg-slot"{attr}>{who}</div>'

    filled = [
        n for n in range(1, PACKAGE_COUNT[side] + 1)
        if any(packs[n - 1] if n - 1 < len(packs) else [])
    ]
    pkgs = "".join(
        f'<div class="dc-pkg"><div class="dc-pkg-body"><p class="dc-pkg-h">'
        f'{esc(pkg_names[n - 1] if n - 1 < len(pkg_names) else f"Package {n}")}</p>'
        + "".join(slot_html(n, at) for at in range(PACKAGE_SIZE[side]))
        + "</div>"
        + package_sub_card_html(packs, n, spots)
        + "</div>"
        for n in filled
    )
    pkg_block = (
        f'<div class="dc-pkgs"><p class="rot-h">'
        f'{esc(PACKAGE_TITLE.get(side, "Packages"))}</p>'
        f'<div class="dc-pkgwrap"><div class="dc-pkgrow">{pkgs}</div></div></div>'
        if pkgs else ""
    )
    # Rotations take the packages' place where a side has them: a spot and the boys
    # who take it in turn, drawn as the same black-barred card as a position above.
    if rotations:
        cards = "".join(
            f'<div class="dc-pos dc-rot"><p class="dc-pos-h">'
            f'<span class="dc-abbr">{esc(rot["name"])}</span></p>'
            '<ol class="dc-names">'
            + "".join(f'<li class="{"starter" if i == 0 else ""}"><b>{i + 1}</b>'
                      f'<span>{esc(name)}</span></li>'
                      for i, name in enumerate(rot["players"]))
            + '</ol></div>'
            for rot in rotations
        )
        pkg_block = (f'<div class="dc-pkgs dc-rots"><p class="rot-h">Rotations</p>'
                     f'<div class="dc-rotrow">{cards}</div></div>')
    return (f'<div class="dc-field" style="--dc-cols:{cols}">{field}</div>'
            f'{pkg_block}')


def write_depth_chart(formations: list[dict], defenses: dict, root: Path) -> str:
    roster = {}
    path = root / "roster.json"
    if path.is_file():
        import json as _json
        roster = _json.loads(path.read_text(encoding="utf-8"))

    # Whichever front is the base — the same "lowest order wins" rule the offense
    # board uses below, rather than a hardcoded id that keeps pointing at the old
    # front the day the base changes.
    front = next(iter(defenses.values()), None)
    # The board is the base formation's eleven — Z, FB and TB in the backfield. It
    # used to be every spot any formation aligns, which meant the Split Backs LH and
    # RH sat on both rotations reading Open and made a complete unit look two short
    # of a full sheet. A depth chart answers "who is on the field", and what is on
    # the field is the base offense.
    base = min(formations, key=lambda f: f.get("order", 99))
    off_order = [p for p in CARD_ORDER if p in base["alignment"]]
    # The spots the other formations use and this board does not. Nobody is on them
    # today, but a name put against one must not disappear just because the base
    # offense has no room for it — so they surface underneath, and only if used.
    # "Only if used" is the whole rule: the Split Backs LH and RH are empty, and a
    # pair of Open rows under a complete eleven says the unit is two short when it
    # is not.
    alt_order = [p for p in CARD_ORDER
                 if p not in base["alignment"]
                 and any(p in form["alignment"] for form in formations)
                 and any(roster.get("offense", {}).get(p) or [])]
    def_order = list(front["alignment"]) if front else []
    # The same courtesy the offense board pays the Split Backs' LH and RH: a spot only
    # a change-up front uses — the nose tackle, once the base stopped being the 5-3 —
    # surfaces underneath rather than taking the name on it out of the book silently.
    def_alt_order = [p for f in defenses.values() for p in f["alignment"]
                     if p not in def_order
                     and any(roster.get("defense", {}).get(p) or [])]
    def_alt_order = list(dict.fromkeys(def_alt_order))

    # A front may name its own spots — W and S are the weak and strong linebackers of
    # a three-linebacker front, and the two inside backers of a four-linebacker one.
    def_names = {**DEFENSE_POSITION_NAMES, **(front or {}).get("position_names", {})}

    def def_label(p: str) -> str:
        """The long name, with the nickname after it where the backers have one."""
        name = def_names.get(p, p)
        nick = DEFENSE_NICKNAMES.get(p)
        return f"{name} ({nick})" if nick else name

    # One section per side of the ball, each carrying both rotations as columns. The
    # split used to be Purple sheet / Gold sheet with offense and defense side by
    # side inside; it is now offense sheet / defense sheet with the rotations side by
    # side. Same two sheets either way, and this way the coordinator who only ever
    # looks at one side of the ball is handed exactly his page.
    sides = (
        ("offense", "Offense", off_order, alt_order, position_name,
         "The base formation's eleven.", base["alignment"]),
        ("defense", "Defense", def_order, def_alt_order, def_label,
         f"The {front['name'].replace('-', '–')}, our everyday front."
         if front else "Our everyday front.",
         (front or {}).get("alignment", {})),
    )
    # The offense prints its rotations instead of its packages. Every name on one has
    # to be a boy somewhere on the chart, the same guard package_plays has on a call.
    squad = {n for part in ("offense", "defense")
             for names in (roster.get(part) or {}).values() for n in names if n}
    rotations = {}
    for side in ("offense", "defense"):
        rots = (roster.get("rotations") or {}).get(side) or []
        for rot in rots:
            for name in rot.get("players") or []:
                if name not in squad:
                    raise SystemExit(
                        f"roster.json rotations.{side}, {rot.get('name')}: '{name}' is "
                        "not on the depth chart. Use the name as the chart spells it."
                    )
        rotations[side] = rots

    sections = []
    for side, heading, order, alts, label, sub, align in sides:
        packs = None if rotations[side] else (roster.get("packages") or {}).get(side)
        sections.append(
            f'<section class="dc-side" data-side="{side}">'
            f'<p class="hero-head">{esc(heading)}'
            f'<span class="rot-sub">{esc(sub)}</span></p>'
            f'{side_board(side, order, alts, roster.get(side, {}), label, packs, (roster.get("package_names") or {}).get(side), align, rotations[side])}'
            f'</section>'
        )

    # One side per sheet — see the .dc-side rules in the print stylesheet.
    body = f"""<h1 class="page">Depth Chart</h1>
<div class="dc-bar">
  <div class="dc-tools">
    {PRINT_BTN}
  </div>
</div>
<div id="dc-board">
{"".join(sections)}
</div>"""
    return page(
        f"Depth Chart — {SITE_TITLE}",
        body,
        formations,
        defenses=defenses,
        active_nav="depth",
        description="Offense and defense depth chart — who plays where.",
        # Pin the margin so a side cannot be pushed onto a second sheet by a print
        # dialog set to wide margins. Same 9mm the play-card book uses. The paper size
        # is deliberately not pinned: whatever is in the tray, Letter or A4, both fit.
        # Landscape. Seven columns of board and three package cards across are a
        # wide thing on a tall sheet; turned, each side of the ball has room
        # rather than having to be squeezed into it.
        page_rule="size: letter landscape; margin: 9mm;",
    )


def write_defense_index(formations: list[dict], defenses: dict) -> str:
    cards = []
    for fid, f in our_fronts(defenses).items():
        counts = {}
        for r in f.get("roles", {}).values():
            counts[r] = counts.get(r, 0) + 1
        cards.append(
            f'<a class="fcard imgcard" href="{d_href(f)}">'
            f'<div class="thumb"><img src="{def_src(f)}" '
            f'alt="{esc(f["name"])} front"></div>'
            f'<div class="body"><div class="ftop"><h3>{esc(f["call"])}</h3>'
            f'<span class="n">{esc(f["name"])}</span></div>'
            f'<p>{esc(first_sentence(f.get("summary", "")))}</p>'
            f'<span class="fcall">{counts.get("DL", 0)} down &nbsp;&middot;&nbsp; '
            f'{counts.get("LB", 0)} linebackers &nbsp;&middot;&nbsp; '
            f'{counts.get("DB", 0)} defensive backs</span></div></a>'
        )
    body = f"""{page_head("Defensive playbook")}
<p class="lede">{_count(len(our_fronts(defenses))).capitalize()} fronts, each checked against the
league rulebook by the generator &mdash; an illegal front fails the build.</p>

<div class="cards imgcards">{''.join(cards)}</div>

<div class="callout">
  <p><strong>Read the rules before you install a front.</strong> Cap six down linemen,
  minimum three linebackers at two yards, defensive backs at two yards or deeper &mdash;
  no blitzing, ever. <a href="rules.html#section-9">Rule 9.02</a> covers the penalty.</p>
</div>"""
    return page(
        f"Defensive playbook — {SITE_TITLE}",
        body,
        formations,
        defenses=defenses,
        active_nav="defense",
        description=f"{_count(len(our_fronts(defenses))).capitalize()} legal defensive fronts for "
        "8U tackle, with assignments.",
    )


def write_defense_page(front: dict, formations: list[dict], defenses: dict) -> str:
    ids = list(our_fronts(defenses))
    i = ids.index(front["id"])
    prev = defenses[ids[i - 1]] if i else None
    nxt = defenses[ids[i + 1]] if i + 1 < len(ids) else None

    actions = PRINT_BTN
    siblings = "".join(
        f'<a href="{d_href(f)}"{ACTIVE_ATTR if fid == front["id"] else ""}>{esc(f["call"])}</a>'
        for fid, f in our_fronts(defenses).items()
    )
    crumbs = (f'<nav class="crumbs"><a href="index.html">Home</a><span>/</span>'
              f'<a href="defense.html">Defense</a><span>/</span>'
              f'<b>{esc(front["call"])}</b></nav>')
    pager = ['<div class="pager">']
    pager.append(
        f'<a href="{d_href(prev)}"><span class="dir">&larr; Previous</span>'
        f'{esc(prev["call"])}</a>' if prev else "<span></span>")
    pager.append('<a class="mid" href="defense.html">'
                 '<span class="dir">Defense</span>All fronts</a>')
    pager.append(
        f'<a class="nxt" href="{d_href(nxt)}"><span class="dir">Next &rarr;</span>'
        f'{esc(nxt["call"])}</a>' if nxt else "<span></span>")
    pager.append("</div>")

    body = (crumbs + f'<div class="playbar">{siblings}</div>'
            + defense_article(front, actions=actions) + "".join(pager))
    attrs = ""
    if prev:
        attrs += f' data-prev="{d_href(prev)}"'
    if nxt:
        attrs += f' data-next="{d_href(nxt)}"'
    return page(
        f"{front['call']} ({front['name']}) — {SITE_TITLE}",
        body,
        formations,
        defenses=defenses,
        active_def=front["id"],
        description=front.get("summary", "")[:160],
        landscape=True,
        main_attrs=attrs,
    )


# The front the printed playbook is drawn against: the 4-4, the look the plays' blocking
# was written for.
PRINT_BOOK_FRONT = "4-4"


def write_print_book(formations: list[dict], defenses: dict) -> str:
    # The whole playbook the way a single play prints from its own page: each play's
    # diagram alone, filling a letter sheet turned landscape. Same `play-page` class, so
    # the same print rules hide the words, and a coach printing the book gets exactly
    # the sheets he would get printing every play one at a time.
    total = sum(len(f["_plays"]) for f in formations)
    # Every diagram loads up front. A lazy image only loads as it scrolls near the screen,
    # and a browser's print preview does not scroll: it printed the first four plays —
    # the ones close enough to have loaded — and blank space for the other fourteen.
    arts = [play_article(f, p, defenses, single=PRINT_BOOK_FRONT)
            .replace('loading="lazy"', 'loading="eager"')
            for f in formations for p in f["_plays"]]
    body = f"""<div class="print-intro">
  <h1 class="page">Print the playbook</h1>
  <p class="lede">All {total} plays against the 4-4, one per landscape sheet.</p>
  <p><button type="button" class="btn solid"
     onclick="window.print()">Print {total} plays</button></p>
</div>
{chr(10).join(arts)}"""
    return page(
        f"Print book — {SITE_TITLE}",
        body,
        formations,
        defenses=defenses,
        active_nav="print",
        description=f"All {total} plays, one per landscape page.",
        page_rule="size: letter landscape; margin: 0.25in;",
        main_attrs=' class="play-page"',
    )


# ---------------------------------------------------------------------- entry --


def write_all(formations: list[dict], defenses: dict, root: Path) -> int:
    # Sweep out pages this build no longer writes. The site is flat files at the repo
    # root, so a deleted play or a dropped formation leaves its page sitting there,
    # still linked from anyone's bookmark and still in the search engine's index. The
    # cards learned this lesson first — 112 of them outlived the plays they drew.
    keep = {"index.html", "calls.html", "print.html", "defense.html", "rules.html",
            "install.html", "depth-chart.html", "wristbands.html"}
    keep |= {f_href(f) for f in formations}
    keep |= {p_href(p) for f in formations for p in f["_plays"]}
    keep |= {d_href(d) for d in our_fronts(defenses).values()}
    keep |= {install_href(pr) for pr in load_schedule(root).get("practices", [])}
    for stale in root.glob("*.html"):
        if stale.name not in keep:
            stale.unlink()

    assets = root / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "site.css").write_text(SITE_CSS.strip() + "\n", encoding="utf-8", newline="\n")
    (assets / "site.js").write_text(SITE_JS.strip() + "\n", encoding="utf-8", newline="\n")

    written = 0
    (root / "index.html").write_text(write_home(formations, defenses), encoding="utf-8", newline="\n")
    (root / "calls.html").write_text(write_calls(formations, defenses, root), encoding="utf-8", newline="\n")
    (root / "print.html").write_text(
        write_print_book(formations, defenses), encoding="utf-8", newline="\n")
    (root / "defense.html").write_text(
        write_defense_index(formations, defenses), encoding="utf-8", newline="\n")
    (root / "rules.html").write_text(
        write_rulebook(formations, defenses, root), encoding="utf-8", newline="\n")
    (root / "install.html").write_text(
        write_install(formations, defenses, root), encoding="utf-8", newline="\n")
    (root / "depth-chart.html").write_text(
        write_depth_chart(formations, defenses, root), encoding="utf-8", newline="\n")
    (root / "wristbands.html").write_text(
        write_wristbands(formations, defenses), encoding="utf-8", newline="\n")
    written += 8

    # One page per practice. The schedule page is the calendar; this is what a coach
    # actually opens on the field, so it is a real page with a URL you can text to
    # somebody rather than an anchor a fifth of the way down a scroll.
    schedule = load_schedule(root)
    practices = schedule.get("practices", [])
    phases = schedule.get("phases", {})
    for i, pr in enumerate(practices):
        prev = practices[i - 1] if i else None
        nxt = practices[i + 1] if i + 1 < len(practices) else None
        (root / install_href(pr)).write_text(
            write_install_day(pr, prev, nxt, practices, phases, formations,
                              defenses, root),
            encoding="utf-8", newline="\n")
        written += 1

    for front in our_fronts(defenses).values():
        (root / d_href(front)).write_text(
            write_defense_page(front, formations, defenses), encoding="utf-8", newline="\n")
        written += 1

    for form in formations:
        (root / f_href(form)).write_text(
            write_formation_page(form, formations, defenses),
            encoding="utf-8", newline="\n")
        written += 1
        plays = form["_plays"]
        for i, play in enumerate(plays):
            prev = plays[i - 1] if i else None
            nxt = plays[i + 1] if i + 1 < len(plays) else None
            (root / p_href(play)).write_text(
                write_play_page(form, play, prev, nxt, formations, defenses),
                encoding="utf-8", newline="\n")
            written += 1
    return written
