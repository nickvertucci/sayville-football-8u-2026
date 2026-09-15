"""Builds the multi-page playbook website.

Structure — flat files at the repo root so every page can use the same relative paths
to the card SVGs, and so GitHub Pages can serve from "/" with no build step:

    index.html          home: formations, install plan, the calling language
    calls.html          the call sheet — every play, searchable, the fastest way in
    f-<formation>.html  one formation: its notes and its plays
    p-<play>.html       one play, deep-linkable, prints to a single landscape sheet
    rules.html          the league rulebook, verbatim, from rulebook/*.txt
    print.html          the whole book, one play per landscape sheet
    assets/site.css     one stylesheet for all of it
    assets/site.js      play switcher, arrow-key paging, call sheet filtering

On every page the diagram is the main attraction: full width of its card, with the
assignments read underneath it rather than squeezed into a column beside it.
"""

from __future__ import annotations

import calendar
import hashlib
import re

import blocking
from datetime import date as _date
from pathlib import Path

from common import (CARD_ORDER, call_prefix, esc, form_label, ordered_positions,
                    position_name)

SITE_TITLE = "Sayville 8U Tackle Football"

# The attribute that marks the current page in a nav strip. Kept as a constant so the
# f-strings that build those strips need no escaped quotes inside the {…} — Python only
# allowed backslashes there from 3.12, and this generator should run on 3.11 too.
ACTIVE_ATTR = ' class="active"'

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

/* The board itself: positions down the left, the two rotations across the top, the
   shape of an NFL team's depth chart. A real <table> so it reads as a grid, not a
   stack of cards — collapsed to cards only below 620px, the one place a grid this
   wide stops working.

   Rows are deliberately tight. Every row here is one name, and a name needs a chip,
   not a cell with sixteen pixels of padding round it — the old spacing made eleven
   positions three thousand pixels tall and put the answer to "who backs up the left
   tackle" below the fold. */
/* A scroll pane on both axes, and it has to be both. Sideways is what a phone needs,
   because four columns of names do not fit one and squeezing them is worse than
   scrolling them. Vertical is what makes the header freeze: a sticky cell sticks to
   its scroll container, so if the pane does not scroll, nothing holds 1st/2nd/3rd on
   screen and a coach reading down to the tailback is looking at unlabelled columns
   again.

   The cap is a share of the screen rather than a number of rows. On a tall screen the
   whole board clears it and the pane never scrolls; on a short one it does, and the
   header and the position column freeze. Same rule, and it is the small screen — the
   one being complained about — that gets the frozen panes. */
.tablewrap.dc-board-wrap {
  margin: 10px 0 4px; overflow: auto; max-height: 65vh; overscroll-behavior: contain;
  background: var(--panel);
  border: 1px solid var(--line); border-radius: 12px; box-shadow: var(--shadow);
}
/* Fixed layout, because the bench row holds eleven names and auto layout lets one
   long cell drag its whole column wide — the board went from four even columns to a
   sideways scroll the moment that row appeared. Fixed also means the columns stay
   the same width as names move around, so the grid does not twitch on every drag. */
table.dc-board {
  width: 100%; border-collapse: collapse; table-layout: fixed; min-width: 900px;
}
table.dc-board th, table.dc-board td {
  border-bottom: 1px solid var(--line-soft); border-right: 1px solid var(--line-soft);
  padding: 5px 10px;
}
table.dc-board th:last-child, table.dc-board td:last-child { border-right: 0; }
table.dc-board tbody tr:last-child td { border-bottom: 0; }
/* The header stays put while you read down the board. Twelve rows is more than a
   phone shows at once, so scrolling to the tailback used to leave four unlabelled
   columns of names and no way to tell a starter from third string — which is the
   question this page exists to answer. */
table.dc-board thead th { position: sticky; top: 0; z-index: 3; }
/* And the position stays put while you scroll sideways. The board is wider than a
   phone, and the column that says which row you are on was the first thing to leave
   the screen. */
table.dc-board .dc-poscell { position: sticky; left: 0; z-index: 2; }
table.dc-board thead th:first-child {
  left: 0; z-index: 4; background: var(--accent-solid);
}
/* The frozen column casts a shadow, so the half a name sliding under it reads as
   something passing behind rather than as a name that has been cut in half. */
table.dc-board .dc-poscell { box-shadow: 3px 0 6px rgba(0, 0, 0, .18); }
table.dc-board thead th {
  background: var(--accent-solid); color: var(--on-accent); text-align: left;
  font-size: 11px; text-transform: uppercase; letter-spacing: 1.3px; font-weight: 800;
  padding: 9px 12px;
}
/* Every column header reads the same. The units used to wear colours here and the
   colour was doing the work of the label — which failed the moment the header
   scrolled away, and told you nothing about order even when it was on screen. A
   depth chart numbers its columns; a number says both which one it is and where it
   sits behind the one in front of it. */
table.dc-board .dc-poscell { background: var(--panel-2); white-space: nowrap; width: 160px; }
table.dc-board .dc-poscell .dc-abbr { font-size: 14px; }
table.dc-board .dc-poscell .dc-label { font-size: 11.5px; margin-left: 7px; }
table.dc-board tbody tr:nth-child(even) td.dc-poscell { background: var(--panel); }
/* A spot no formation on this board aligns — see side_board. Present only because
   somebody is standing on it, and marked so it does not read as a twelfth starter. */
table.dc-board tr.dc-alt td { opacity: .72; }
table.dc-board tr.dc-alt .dc-abbr::after {
  content: " ·"; color: var(--muted); font-weight: 500;
}
/* An empty spot. A button, not a label — see side_board: it is a drop target you
   can also tab to, and a <span> would have been reachable by pointer only. */
.dc-open {
  font: inherit; font-size: 13px; font-style: italic; font-weight: 600;
  color: var(--muted); background: none; border: 0; padding: 3px 4px; cursor: pointer;
  border-radius: 999px;
}
.dc-open:hover { color: var(--ink-2); }
.dc-open:focus-visible { outline: 2px solid var(--accent-solid); outline-offset: 2px; }
/* The drop target is the whole cell, not the chip inside it, so an empty spot is as
   easy to hit as a full one. Below 620px the table becomes cards and the cells stop
   being cells, so the padding rides on the cell rather than the row. */
table.dc-board td.dc-cell { min-width: 130px; }
/* ---------------------------------------------------------------------- chips -- */
/* A name you can pick up. It is a <button> because every drag has a tap-then-tap
   equivalent — see the pointer handler in site.js — and that is the path a phone,
   a keyboard and a screen reader all take. */
.dc-chip {
  display: inline-flex; align-items: center; gap: 6px; font: inherit;
  font-size: 13.5px; font-weight: 700; color: var(--ink); background: var(--panel-2);
  border: 1px solid var(--line); border-radius: 999px; padding: 3px 11px;
  cursor: grab; touch-action: manipulation; user-select: none; -webkit-user-select: none;
  text-align: left; max-width: 100%;
}
.dc-chip { overflow: hidden; text-overflow: ellipsis; }
.dc-chip:hover { border-color: var(--accent-solid); }
.dc-chip:focus-visible { outline: 2px solid var(--accent-solid); outline-offset: 2px; }
/* Picked up by tap. The next tap on any spot puts him there, so the whole board
   reads as targets until he lands. */
.dc-chip.picked {
  background: var(--accent-solid); color: var(--on-accent);
  border-color: var(--accent-solid); cursor: grabbing;
}
#dc-board.placing td.dc-cell, #dc-board.placing .dc-pool { cursor: copy; }
#dc-board.placing td.dc-cell { box-shadow: inset 0 0 0 1px var(--accent-solid); }
/* The chip under the finger while a drag is in flight. Positioned by script. */
.dc-chip.flying {
  position: fixed; z-index: 90; pointer-events: none; cursor: grabbing;
  box-shadow: 0 8px 20px rgba(0,0,0,.45); opacity: .95;
}
.dc-chip.ghost { opacity: .3; }
td.dc-cell.over, .dc-pool.over { background: var(--accent-soft) !important; }

/* ---------------------------------------------------------------------- squad -- */
/* The whole squad for this side of the ball, and a source rather than a container:
   dragging a name out leaves it here, so the same kid goes on the first, second and
   third string without anyone having to think about where the chip "is". The ones already
   on the board are dimmed, which leaves the bright ones — the kids nobody has given
   a job — as the thing your eye lands on. */
/* ------------------------------------------------------------------ packages --
   Five pairs per side, on one line above the squad. A package is who goes on and
   comes off together, so the two slots sit one above the other inside a box and the
   box is the unit your eye picks up — not ten loose slots in a row.

   Three to a row, so six offensive packages are two rows of three: each box is wide
   enough for its names and for the note under it saying who comes in and who goes
   out. On a phone they stack one to a row. */
.dc-pkgs { margin: 14px 0 0; }
.dc-pkgrow {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px; padding-bottom: 2px;
}
@media (max-width: 620px) { .dc-pkgrow { grid-template-columns: 1fr; } }
/* In and out against package 1, under the names, so the swap is read in one place. */
.dc-pkg-note {
  margin: 6px 0 0; padding-top: 5px; border-top: 1px solid var(--line);
  font-size: 12px; line-height: 1.4; color: var(--ink-2);
}
.dc-pkg-note:empty { display: none; }
.dc-pkg-note span { display: block; }
.dc-pkg-note b { color: var(--ink); }
.dc-pkg {
  background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
  padding: 6px; box-shadow: var(--shadow); min-width: 0;
}
.dc-pkg-h {
  margin: 0 0 4px; font-size: 10.5px; font-weight: 800; letter-spacing: 1.1px;
  text-transform: uppercase; color: var(--muted);
}
/* Same drop target as a board cell, and it has to look like one or nothing says it
   can be dropped into. */
.dc-pkg-slot {
  min-height: 26px; display: flex; align-items: center; gap: 4px;
  border-radius: 7px; padding: 1px; min-width: 0;
}
/* Which spot this slot is, where the side has a fixed answer. Drawn from the
   attribute rather than sitting in the slot as an element, because the slot's
   contents are rewritten every time it empties or fills — an element would be gone
   the first time a name came out. It also means an empty package still says which
   three spots it is short of, instead of three identical Opens. */
.dc-pkg-slot[data-spot]::before {
  content: attr(data-spot);
  flex: 0 0 20px; font-size: 9.5px; font-weight: 800; letter-spacing: .3px;
  color: var(--muted); text-transform: uppercase;
}
.dc-pkg-slot + .dc-pkg-slot { margin-top: 2px; }
/* The offense's line starts under its backs, and a rule says where. */
.dc-pkg-slot[data-spot="LT"] {
  margin-top: 5px; padding-top: 5px; border-top: 1px dashed var(--line);
}
.dc-pkg-slot .dc-chip {
  max-width: 100%; min-width: 0; overflow: hidden; text-overflow: ellipsis;
}

.dc-bench { margin: 14px 0 6px; }
.dc-pool {
  display: flex; flex-wrap: wrap; gap: 6px; min-height: 38px; padding: 8px 10px;
  border: 1px dashed var(--line); border-radius: 10px; background: var(--panel);
}
.dc-pool .dc-chip.placed { opacity: .45; font-weight: 600; }
.dc-pool .dc-chip.placed:hover, .dc-pool .dc-chip.picked { opacity: 1; }
/* How many rotations he is in, past the ordinary one. Written by site.js. */
.dc-pool .dc-chip[data-count]:not([data-count=""])::after {
  content: attr(data-count) "\\00d7"; margin-left: 1px; font-size: 10px;
  font-weight: 800; color: var(--accent-ink); opacity: .9;
}

/* ------------------------------------------------------------------ dc chrome -- */
.dc-bar {
  display: flex; align-items: center; justify-content: space-between; gap: 14px;
  flex-wrap: wrap; margin: 14px 0 6px;
}
.dc-tools { display: flex; gap: 8px; flex-wrap: wrap; }
.dc-edited {
  margin: 0 0 14px; padding: 8px 12px; border-radius: 8px; font-size: 13px;
  font-weight: 700; color: var(--ink); background: var(--accent-soft);
  border-left: 3px solid var(--accent-solid);
}
/* Where the copied JSON goes when the clipboard is not available — an http:// page
   on a phone, mostly, where navigator.clipboard is simply absent. */
.dc-out {
  display: block; width: 100%; margin: 0 0 14px; padding: 10px 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px;
  color: var(--ink); background: var(--panel); border: 1px solid var(--line);
  border-radius: 8px;
}

.dc-abbr { font-weight: 800; color: var(--accent-ink); font-size: 15px; }
.dc-label { color: var(--muted); font-size: 12.5px; }

/* ----------------------------------------------------------------- both sides -- */
/* Offense and defense are the top split, and the rotations are columns inside
   each. It was the other way round, which meant the answer to "who replaces the
   left tackle" lived on a different sheet from the question. A coordinator only
   ever wants one of these two sections, so each is a section and each is a sheet. */
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
/* The squad count under each board's heading. Written by site.js, because after the
   first drag the number the page shipped with is a lie.

   The column headers used to carry one of these too — a filled-of-eleven tally per
   column. It went because it was answering a question the columns past the third do
   not have: a depth chart is not eleven-deep at every spot and is not supposed to be,
   so "0/11" over column five was reporting a shortfall that is not one. */
.rot-count { font-weight: 800; letter-spacing: 0; opacity: .85; }
.rot-count.warn { color: var(--red); opacity: 1; }
/* The heading is uppercase; the squad count under it is a sentence and reading
   "2 WITH NO SPOT" is being shouted at. */
.rot-h .rot-count { text-transform: none; font-weight: 700; }


/* --------------------------------------------------------------- call sheet --
   A spreadsheet, on purpose: ruled cells with no gaps, empty ones drawn too, so the
   lineup keeps the formation's shape and the plays read straight down a column. One
   sheet per package, side by side, stacking on a phone. */
.xl-sheets {
  display: grid; gap: 14px; margin: 10px 0 24px;
  grid-template-columns: repeat(auto-fit, minmax(min(460px, 100%), 1fr));
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
.xl-lineup { border-bottom: 2px solid var(--ink); }
.xl-lineup td { height: 38px; text-align: center; }
.xl-empty { background: var(--panel-2); }
.xl-pos { display: block; font-size: 10px; font-weight: 800; color: var(--accent-ink); }
.xl-name { display: block; font-size: 10.5px; }
.xl-open { color: var(--muted); font-style: italic; }
/* Specific enough to beat `table.xl td`, whose top alignment would otherwise win. */
table.xl.xl-plays td {
  height: 22px; text-align: center; vertical-align: middle; padding: 4px 6px;
}
.xl-plays td a { color: var(--ink); font-weight: 700; text-decoration: none; }
.xl-plays td a:hover { text-decoration: underline; }
@media print {
  /* Two across, so each strong-left sheet prints beside its strong-right one. */
  .xl-sheets { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0; margin: 2px 0 0; }
  /* Quadrants, drawn with borders rather than a background so they print whatever the
     browser's background-graphics setting is: a thick black rule down the middle and
     one across, with room inside each so no table touches a rule. */
  .xl-sheet { padding: 6px 8px; }
  .xl-sheet:nth-child(odd) { border-right: 10px solid #000; }
  .xl-sheet:nth-last-child(n+3) { border-bottom: 10px solid #000; }
  /* Two rows of two fill the landscape sheet, so everything is sized up to use it:
     taller cells to write in and names a coach can read at arm's length. */
  table.xl { font-size: 9px; }
  table.xl td, table.xl th { padding: 1px 1px; }
  table.xl th { font-size: 9px; }
  /* Black text on no background. The screen's white-on-navy title printed as pale grey
     on paper whenever the browser left background graphics off. */
  .xl-title {
    padding: 0 0 3px; font-size: 14px; font-weight: 900;
    color: #000 !important; background: none !important;
  }
  /* A name is one line on paper: small enough to fit its cell, and never wrapping
     into a second line that makes the row taller. */
  .xl-lineup td { height: 30px; padding: 1px 0; vertical-align: middle; }
  /* On paper the formation reads as players, not a spreadsheet: the grid behind them
     is barely there, and an empty square has no fill, so only the named spots show. */
  table.xl.xl-lineup td { border-color: #f9fafb; }
  .xl-lineup .xl-empty { background: none !important; }
  .xl-pos { font-size: 7.5px; }
  .xl-name { font-size: 8px; white-space: nowrap; letter-spacing: -.2px; }
  table.xl.xl-plays td { height: 32px; vertical-align: middle; }
  .xl-plays td a { font-size: 9.5px; }
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
  .section-head, .btn, .print-intro, .cal-next, .cal-legend,
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
  ul.coach { columns: 3; column-gap: 18px; margin-top: 3px; }
  ul.coach li { font-size: 8pt; line-height: 1.32; margin-bottom: 2px; }
  a[href]::after { content: ""; }
  /* A play printed from its own page is the graphic and nothing else. The card already
     carries the play's name and call in its header strip, so the page's header, the
     assignments and the coaching points all go, and the diagram takes the sheet. The
     printed book keeps them. */
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
  table.dc-board tr { break-inside: avoid; page-break-inside: avoid; }
  /* No break-inside:avoid on .dc-side itself. A side already starts at the top of a
     fresh sheet, so keeping it whole can never move it anywhere useful — and on a
     sheet too small to hold it, the browser honours the rule by emitting a blank
     page first. Measured: it turned a two-page overflow into a three. */
  .dc-side { margin: 0; }
  /* Background fills are a print-settings gamble; the heading is already spelled
     out, so print it as plain text with a rule under it. */
  .dc-side .hero-head {
    background: none; color: #000; padding: 0 0 3px; margin: 0 0 6px;
    border-bottom: 2px solid #000; border-radius: 0; display: block; font-size: 17pt;
  }
  .rot-sub { font-size: 9pt; opacity: 1; }
  .rot-h { font-size: 8pt; margin: 6px 0 3px; }
  /* Screen scrolls the wide board sideways; paper has nowhere to scroll to, and
     a clipped overflow box silently drops the last string. */
  .tablewrap.dc-board-wrap {
    overflow: visible; max-height: none; box-shadow: none; border-radius: 0; margin: 0;
  }
  table.dc-board thead th, table.dc-board .dc-poscell {
    position: static; box-shadow: none;
  }
  table.dc-board { min-width: 0; }
  table.dc-board .dc-poscell { width: 33mm; white-space: normal; }
  table.dc-board .dc-poscell .dc-label { display: block; margin-left: 0; }
  table.dc-board th, table.dc-board td { padding: 3px 8px; }
  table.dc-board .dc-poscell .dc-abbr { font-size: 10pt; }
  table.dc-board .dc-poscell .dc-label { font-size: 7.5pt; }
table.dc-board thead th { padding: 5px 8px; font-size: 8pt; }
  /* The rotation names survive as printed words. A header fill is the one place colour
     would have carried meaning nothing else does, and a printer set to skip
     backgrounds drops it silently — leaving white text on white paper — so the whole
     header row goes to plain text on a rule, which reads the same out of any tray.

     Both selectors are needed. The screen rules that colour these headers carry an
     attribute and a second class, so a plain `thead th` here loses to them on
     specificity no matter that it comes later in the file, and the fills print. */
table.dc-board thead th { background: none; color: #000; border-bottom: 2px solid #000; }
  table.dc-board thead th.rot-th[data-rot] { background: none; color: #000; }
  /* On paper a chip is just a name — the pill, the border and the drag affordance
     all cost ink and say nothing a coach holding the sheet can act on. */
  .dc-chip {
    background: none; border: 0; padding: 0; font-size: 10pt; font-weight: 800;
    color: #000; border-radius: 0;
  }
  /* The squad list is for building the board on screen. On paper it is a second copy
     of names already in the columns and packages, so it goes and the space is the
     packages'. */
  .dc-bench { display: none; }
  /* Packages on paper: two rows of three, as on screen, with the in/out notes, packed
     tight enough that each side of the ball still fits its one sheet. */
  .dc-pkgrow { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 4px; }
  .dc-pkg { padding: 2px 5px; box-shadow: none; border-radius: 0; }
  .dc-pkg-h { margin: 0; font-size: 7pt; }
  .dc-pkg-slot { min-height: 0; padding: 0; }
  .dc-pkg-slot + .dc-pkg-slot { margin-top: 0; }
  .dc-pkg-slot[data-spot="LT"] { margin-top: 1px; padding-top: 1px; }
  .dc-pkg .dc-chip { font-size: 8pt; }
  .dc-pkg-note { margin: 2px 0 0; padding-top: 2px; font-size: 7pt; line-height: 1.25; }
  /* Buttons and the local-edits banner are screen furniture. */
  .dc-tools, .dc-edited { display: none; }
  .dc-bar { margin: 0 0 6px; display: block; }
  /* The title block is the price of the first sheet and it is paid in rows. */
  h1.page { font-size: 18pt; margin: 0 0 3px; }
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
  var KEY = 'sayville.front';
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

/* The depth chart board.

   Drag a name to another spot, or tap a name and then tap where it goes. Both run
   the same move(): a drag is tap-then-tap with the finger held down in between, and
   implementing it twice is how the two quietly come to disagree.

   The DOM is the state. Every cell carries its side, position and rotation, so "what
   does the chart say" is a query and there is no second copy to keep honest.
   localStorage holds placements only — the roster the page shipped with stays both
   the reset point and the baseline the Copy button edits, which is what keeps a
   local rearrangement from ever being mistaken for the roster in the repo. */
(function () {
  var board = document.getElementById('dc-board');
  var blob = document.getElementById('dc-data');
  if (!board || !blob) return;
  var data = JSON.parse(blob.textContent);
  var KEY = 'sayville-depth-chart-v1';
  var LEGACY_ROT = { purple: 'd1', gold: 'd2', white: 'd3' };
  // The slot was the Z until the book renamed him SL.
  var LEGACY_POS = { Z: 'SL' };
  var edited = document.getElementById('dc-edited');
  var resetBtn = document.getElementById('dc-reset');
  var copyBtn = document.getElementById('dc-copy');
  // Every drop target on the page. A package slot is one of these too: it takes a
  // name the same way a board cell does, so it goes in the selector rather than into
  // a second set of handlers that would have to be kept in step with this one.
  var SLOT = 'td.dc-cell, .dc-pkg-slot, .dc-pool';
  var HOLDER = 'td.dc-cell, .dc-pkg-slot';

  function all(sel, ctx) {
    return Array.prototype.slice.call((ctx || board).querySelectorAll(sel));
  }
  function sideOf(el) {
    var side = el.closest('.dc-side');
    return side ? side.dataset.side : '';
  }
  function chipIn(slot) { return slot.querySelector('.dc-chip'); }

  /* A cell with nobody in it says Open, and says it as a button so that the spot can
     be tabbed to and chosen from a keyboard exactly like a name can. The squad rail
     needs no such marker — it is never empty. */
  function fill(slot) {
    if (!slot.matches(HOLDER)) return;
    var has = chipIn(slot), open = slot.querySelector('.dc-open');
    if (has && open) open.remove();
    if (!has && !open) {
      slot.innerHTML = '<button type="button" class="dc-open">Open</button>';
    }
  }

  function isPool(el) { return el.classList.contains('dc-pool'); }

  /* Three rules, and every gesture on this page is one of them.

       squad rail -> spot   assign. The rail is a source, not a container, so the kid
                            stays in it and the board gets a copy. This is the whole
                            reason a kid can be on all three units at once.
       spot -> spot         move, swapping with whoever is there.
       spot -> squad rail   take him out of that spot.

     The one thing none of them may produce is the same kid twice in one rotation. He
     cannot be at left tackle and centre on the unit that is on the field, so an
     assignment that would do it takes him off the first spot instead — which turns
     out to read as a move, which is what a coach expected anyway. */
  function move(chip, target) {
    var from = chip.parentNode;
    if (!target || from === target) return;
    // Offense chips stay on offense. The two sides are separate problems and a kid
    // is on both of them; dragging across would merge two answers into one.
    if (sideOf(target) !== sideOf(chip)) return;

    if (isPool(target)) {
      // Off the board. A rail chip dropped back on the rail is a no-op, caught above.
      if (isPool(from)) return;
      chip.remove();
      fill(from);
      refresh();
      return;
    }

    // From the rail the chip is a template: clone it and leave the original in place.
    var moving = isPool(from) ? chip.cloneNode(true) : chip;
    if (moving !== chip) moving.classList.remove('picked', 'ghost', 'placed');

    var held = chipIn(target);
    if (held) {
      // A swap when he came off the board, a bump to nowhere when he came off the
      // rail — there is no spot to send the incumbent back to in that case.
      if (moving === chip) from.appendChild(held); else held.remove();
    }
    var open = target.querySelector('.dc-open');
    if (open) open.remove();
    target.appendChild(moving);

    // A kid may appear as many times in a column as the coach wants. This used to
    // clear him out of every other spot in the same column on the grounds that he
    // cannot be in two places at once — which is true of a unit that takes the field
    // together and false of a depth chart. Column 2 is not the second eleven; it is
    // "second in line here", and the same backup can be second at left tackle and
    // second at right tackle without ever playing both at once.

    fill(from);
    fill(target);
    refresh();
  }

  /* Every placement on the board — the cells only. The squad rail is the roster and
     never changes, so saving it would be saving the input. A record names its spot
     rather than pointing at it, so one whose spot has since gone from roster.json is
     skipped instead of taking the whole save down with it. */
  function snapshot() {
    var out = [];
    all(HOLDER).forEach(function (td) {
      var c = chipIn(td);
      if (!c) return;
      // A package slot has no rot/pos, so it names itself: "pkg" and its number, then
      // which of the two it is. Same four-part shape as a board record, so restore()
      // needs no second branch and an old save stays readable.
      out.push(td.dataset.pkg
        ? [sideOf(td), 'pkg', td.dataset.pkg + ':' + td.dataset.at, c.dataset.name]
        : [sideOf(td), td.dataset.rot, td.dataset.pos, c.dataset.name]);
    });
    return out;
  }

  var pristine = JSON.stringify(snapshot());

  // Who comes in and who goes out for each package, against package 1 — the
  // starters. Worked out from the boxes every time the board changes, so a note can
  // never disagree with the names above it.
  function packageNotes() {
    all('.dc-side').forEach(function (sec) {
      var boxes = all('.dc-pkg', sec);
      function group(box) {
        return all('.dc-pkg-slot', box).map(function (sl) {
          var c = chipIn(sl);
          return c ? { name: c.dataset.name, spot: sl.dataset.spot || '' } : null;
        }).filter(Boolean);
      }
      var starters = boxes.length
        ? group(boxes[0]).map(function (p) { return p.name; }) : [];
      boxes.forEach(function (box, i) {
        var note = box.querySelector('.dc-pkg-note');
        if (!note) return;
        var here = group(box);
        note.textContent = '';
        if (!here.length) return;
        if (i === 0) { note.textContent = 'Starters'; return; }
        var names = here.map(function (p) { return p.name; });
        var ins = here.filter(function (p) { return starters.indexOf(p.name) < 0; })
          .map(function (p) { return p.spot ? p.name + ' (' + p.spot + ')' : p.name; });
        var outs = starters.filter(function (n) { return names.indexOf(n) < 0; });
        if (!ins.length && !outs.length) {
          var first = boxes[0].querySelector('.dc-pkg-h');
          note.textContent = 'Same players as ' + (first ? first.textContent : 'package 1');
          return;
        }
        [['In', ins], ['Out', outs]].forEach(function (row) {
          if (!row[1].length) return;
          var line = document.createElement('span');
          var label = document.createElement('b');
          label.textContent = row[0] + ': ';
          line.appendChild(label);
          line.appendChild(document.createTextNode(row[1].join(', ')));
          note.appendChild(line);
        });
      });
    });
  }

  function persist() {
    var now = JSON.stringify(snapshot());
    var dirty = now !== pristine;
    try {
      if (dirty) localStorage.setItem(KEY, now);
      // Dragging the last kid back where he started is a reset. Clearing the key
      // rather than storing a board identical to the shipped one means there is only
      // one way to be unedited, and the banner cannot get stuck on.
      else localStorage.removeItem(KEY);
    } catch (e) { /* private mode: the board still works, it just will not keep */ }
    if (edited) edited.hidden = !dirty;
    if (resetBtn) resetBtn.hidden = !dirty;
    packageNotes();
  }

  function restore() {
    var raw = null, at;
    try { raw = localStorage.getItem(KEY); } catch (e) { return; }
    if (!raw) return;
    try { at = JSON.parse(raw); } catch (e) { return; }
    if (!Array.isArray(at)) return;

    var byKey = {}, template = {};
    all(HOLDER).forEach(function (td) {
      byKey[td.dataset.pkg
        ? sideOf(td) + '/pkg/' + td.dataset.pkg + ':' + td.dataset.at
        : sideOf(td) + '/' + td.dataset.rot + '/' + td.dataset.pos] = td;
    });
    all('.dc-pool .dc-chip').forEach(function (c) {
      template[sideOf(c) + '/' + c.dataset.name] = c;
    });
    // Clear the board and set it out again from the save. Every chip on it is a copy
    // of a rail chip, so there is nothing here to preserve — only to rebuild.
    all(HOLDER).forEach(function (td) { td.innerHTML = ''; fill(td); });

    at.forEach(function (rec) {
      // A board saved while the columns were still called Purple, Gold and White.
      // Without this every record misses its cell, and the coach who rearranged his
      // line at halftime opens the page to the shipped roster and no explanation.
      var rot = LEGACY_ROT[rec[1]] || rec[1];
      var td = byKey[rec[0] + '/' + rot + '/' + (LEGACY_POS[rec[2]] || rec[2])];
      var src = template[rec[0] + '/' + rec[3]];
      // A spot or a kid that has left roster.json since this was saved. Dropping the
      // one record keeps the rest of the board, which is the point of naming spots.
      if (!td || !src || chipIn(td)) return;
      var chip = src.cloneNode(true);
      chip.classList.remove('picked', 'ghost', 'placed');
      var open = td.querySelector('.dc-open');
      if (open) open.remove();
      td.appendChild(chip);
    });
  }

  function refresh() {
    /* The rail carries the whole squad now, so it needs to say who in it is actually
       doing something. A kid already on the board is dimmed and wears the number of
       spots he holds; the ones left bright are the ones nobody has given a job. That
       is the question the rail is scanned for.

       Spots, not rotations: two of them can be in the same column now, because a
       backup can be second in line at two different positions. */
    ['offense', 'defense'].forEach(function (side) {
      var sec = board.querySelector('.dc-side[data-side="' + side + '"]');
      if (!sec) return;
      var spots = {};
      all('td.dc-cell .dc-chip, .dc-pkg-slot .dc-chip', sec).forEach(function (c) {
        spots[c.dataset.name] = (spots[c.dataset.name] || 0) + 1;
      });
      var idle = 0, squad = [];
      all('.dc-pool .dc-chip', sec).forEach(function (c) {
        var n = spots[c.dataset.name] || 0;
        squad.push(c.dataset.name);
        c.classList.toggle('placed', n > 0);
        // The badge earns its space only past one. A kid in a single spot is the
        // ordinary case and does not need a number to say so.
        c.dataset.count = n > 1 ? String(n) : '';
        c.title = n
          ? c.dataset.name + ' is in ' + n + (n === 1 ? ' spot' : ' spots')
          : c.dataset.name + ' has no spot yet';
        if (!n) idle++;
      });

      var el = board.querySelector('[data-count="' + side + '-idle"]');
      if (el) {
        el.textContent = idle ? idle + ' with no spot' : 'everybody is in';
        el.classList.toggle('warn', idle > 0);
      }
    });

    persist();
  }

  /* ------------------------------------------------------------ tap to place -- */
  var picked = null, suppress = false;

  function clearPick() {
    if (picked) picked.classList.remove('picked');
    picked = null;
    board.classList.remove('placing');
  }
  function pick(chip) {
    var same = picked === chip;
    clearPick();
    if (same) return;
    picked = chip;
    chip.classList.add('picked');
    board.classList.add('placing');
  }

  board.addEventListener('click', function (e) {
    if (suppress) return;           // the drag that just ended already decided this
    var chip = e.target.closest('.dc-chip');
    var slot = e.target.closest(SLOT);
    if (picked && chip && isPool(slot) && isPool(picked.parentNode)) {
      pick(chip);
      return;
    }
    if (picked && slot && chip !== picked) {
      var held = picked;
      // A name tapped in the squad rail stays picked after it lands. Putting the same
      // left tackle on all three units is one tap and then three, instead of
      // six — and it is the reason the rail is a source in the first place, so the
      // interface should not make you re-say it every time. A name picked up off the
      // board has been moved, and moving is finished when it lands.
      if (!isPool(held.parentNode)) clearPick();
      move(held, slot);
      return;
    }
    if (chip) { pick(chip); return; }
    clearPick();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') clearPick();
  });

  /* --------------------------------------------------------------- drag it -- */
  /* One handler for mouse and finger both. The native HTML5 drag events never fire
     on touch, and a coach uses this on a phone on a sideline, so native drag was
     never an option here.

     A finger has to hold still for a moment before the drag takes. Without that,
     every attempt to scroll the page would pick a kid up instead — and because the
     hold elapses before the first move, the touchmove that follows can be cancelled
     and the scroll never starts. Moving first is a scroll, and lets go of the chip. */
  var HOLD = 180, SLOP = 5;
  var down = null, dragged = null, fly = null, over = null;

  function cleanup() {
    if (down && down.timer) clearTimeout(down.timer);
    if (fly) fly.remove();
    if (dragged) dragged.classList.remove('ghost');
    if (over) over.classList.remove('over');
    down = null; dragged = null; fly = null; over = null;
  }

  function begin(e) {
    dragged = down.chip;
    var r = dragged.getBoundingClientRect();
    fly = dragged.cloneNode(true);
    fly.classList.add('flying');
    fly.classList.remove('picked');
    fly.style.width = r.width + 'px';
    down.dx = e.clientX - r.left;
    down.dy = e.clientY - r.top;
    document.body.appendChild(fly);
    dragged.classList.add('ghost');
    clearPick();
  }

  function hover(e) {
    var el = document.elementFromPoint(e.clientX, e.clientY);
    var slot = el && el.closest ? el.closest(SLOT) : null;
    if (slot && sideOf(slot) !== sideOf(dragged)) slot = null;
    if (slot === over) return;
    if (over) over.classList.remove('over');
    over = slot;
    if (over) over.classList.add('over');
  }

  board.addEventListener('pointerdown', function (e) {
    if (e.button) return;
    var chip = e.target.closest('.dc-chip');
    if (!chip) return;
    cleanup();
    down = { chip: chip, x: e.clientX, y: e.clientY, id: e.pointerId, ready: false };
    // A mouse means it — the button went down on a chip and nothing else was going
    // to happen. A finger might be starting a scroll, so it waits out the hold.
    if (e.pointerType === 'mouse') down.ready = true;
    else down.timer = setTimeout(function () { if (down) down.ready = true; }, HOLD);
  });

  window.addEventListener('pointermove', function (e) {
    if (!down || e.pointerId !== down.id) return;
    if (!dragged) {
      if (Math.abs(e.clientX - down.x) < SLOP && Math.abs(e.clientY - down.y) < SLOP) return;
      if (!down.ready) { cleanup(); return; }   // moved before the hold: a scroll
      begin(e);
    }
    e.preventDefault();
    fly.style.left = (e.clientX - down.dx) + 'px';
    fly.style.top = (e.clientY - down.dy) + 'px';
    hover(e);
  }, { passive: false });

  // Belt and braces for iOS, where a scroll the compositor has already taken over
  // cannot be called back by preventing a pointermove.
  window.addEventListener('touchmove', function (e) {
    if (dragged) e.preventDefault();
  }, { passive: false });

  function finish(e) {
    if (!down || (e && e.pointerId !== down.id)) return;
    var chip = dragged, target = over;
    cleanup();
    if (!chip) return;
    if (target) move(chip, target);
    // The click that follows a drag must not also pick the chip back up.
    suppress = true;
    setTimeout(function () { suppress = false; }, 0);
  }
  window.addEventListener('pointerup', finish);
  window.addEventListener('pointercancel', finish);

  /* ------------------------------------------------------------ back to JSON -- */
  /* roster.json as this board would write it. Built by editing the file the page
     shipped with rather than emitting a fresh one, so the note, the packages and
     anything else a coach put in that file survive the round trip. */
  function exported() {
    var out = JSON.parse(JSON.stringify(data.roster));
    /* Packages go back into the file too. The button says it hands you the whole
       roster, and a coach who sets his packages, hits Copy and pastes the result into
       the repo should not find them missing — the one thing worse than not saving is
       looking like you did. Trailing empty packages are dropped so an untouched board
       writes nothing rather than ten empty pairs. */
    var packs = out.packages || (out.packages = {});
    ['offense', 'defense'].forEach(function (side) {
      var sec = board.querySelector('.dc-side[data-side="' + side + '"]');
      if (!sec) return;
      var rows = [];
      all('.dc-pkg', sec).forEach(function (box) {
        var row = all('.dc-pkg-slot', box).map(function (sl) {
          var c = chipIn(sl);
          return c ? c.dataset.name : '';
        });
        // Empty slots at the end are dropped too, so a package with only its backs
        // set writes three names rather than three and four blanks.
        while (row.length && !row[row.length - 1]) row.pop();
        rows.push(row);
      });
      while (rows.length && !rows[rows.length - 1].join('')) rows.pop();
      if (rows.length) packs[side] = rows; else delete packs[side];
    });
    if (!Object.keys(packs).length) delete out.packages;
    ['offense', 'defense'].forEach(function (side) {
      var lists = out[side] || (out[side] = {});
      Object.keys(lists).forEach(function (pos) { lists[pos] = []; });
      var sec = board.querySelector('.dc-side[data-side="' + side + '"]');
      if (!sec) return;
      // The columns, in depth order. Both sides run the same six.
      var cols = data.rotations[side] || [];
      var playing = {};
      all('td.dc-cell', sec).forEach(function (td) {
        var at = cols.indexOf(td.dataset.rot);
        if (at < 0) return;
        var list = lists[td.dataset.pos] || (lists[td.dataset.pos] = []);
        while (list.length < at) list.push('');
        // An empty 1st spot above a filled 2nd one has to keep 2nd at index 1, so the
        // hole is written as a blank rather than closed up. A kid in more than one
        // spot is simply written more than once, which is exactly how the file is read
        // back — depth is the index, so the same name at index 0 and index 1 says he
        // is the starter and his own backup, and the same name at index 1 of two
        // different positions says he is second in line at both.
        var chip = chipIn(td);
        list[at] = chip ? chip.dataset.name : '';
        if (chip) playing[chip.dataset.name] = true;
      });
      // Behind every rotation go the kids in none of them. The rail holds the whole
      // squad now, so it is the ones NOT on the board that belong here — appending
      // all of them would write every name back twice.
      all('.dc-pool .dc-chip', sec).forEach(function (chip) {
        if (playing[chip.dataset.name]) return;
        var list = lists[chip.dataset.home] || (lists[chip.dataset.home] = []);
        while (list.length < cols.length) list.push('');
        list.push(chip.dataset.name);
      });
      // Trailing blanks say nothing, and a list of nothing but blanks is a spot with
      // nobody on it — which is what an empty list already means.
      Object.keys(lists).forEach(function (pos) {
        while (lists[pos].length && !lists[pos][lists[pos].length - 1]) lists[pos].pop();
      });
    });
    return JSON.stringify(out, null, 2) + '\\n';
  }

  function fallback(text) {
    var ta = document.getElementById('dc-out');
    if (!ta) {
      ta = document.createElement('textarea');
      ta.id = 'dc-out';
      ta.className = 'dc-out';
      ta.rows = 12;
      ta.readOnly = true;
      var bar = document.getElementById('dc-bar');
      if (bar) bar.insertAdjacentElement('afterend', ta);
    }
    ta.value = text;
    ta.hidden = false;
    ta.focus();
    ta.select();
  }

  function flash(btn, label) {
    if (btn._was) return;
    btn._was = btn.textContent;
    btn.textContent = label;
    setTimeout(function () { btn.textContent = btn._was; btn._was = null; }, 1500);
  }

  if (copyBtn) copyBtn.addEventListener('click', function () {
    var text = exported();
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () { flash(copyBtn, 'Copied'); },
        function () { fallback(text); });
    } else fallback(text);
  });

  // Two taps to throw the board away. A single misplaced tap on a phone should not
  // cost a coach the rearrangement he just spent halftime on.
  var armed = 0;
  if (resetBtn) resetBtn.addEventListener('click', function () {
    if (!armed) {
      armed = setTimeout(function () { armed = 0; resetBtn.textContent = 'Reset'; }, 4000);
      resetBtn.textContent = 'Reset — tap again';
      return;
    }
    try { localStorage.removeItem(KEY); } catch (e) {}
    // Reloading restores the roster the page ships with, which means there is no
    // second copy of the default here to fall out of step with the real one.
    location.reload();
  });

  restore();
  refresh();
  packageNotes();
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
    changed: after the Z became the SL, a coach printed a play page titled SL with a
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
        # The 5-3 is the tab that starts on, not whichever front sorts first. It is
        # what an 8U team actually lines up in against us, so it is the answer to the
        # question the page is usually being opened to ask.
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

    coach = ""
    if play.get("coaching_points"):
        items = "\n    ".join(f"<li>{esc(c)}</li>" for c in play["coaching_points"])
        coach = (
            '<p class="block-title">Coaching points</p>\n'
            f'  <ul class="coach">\n    {items}\n  </ul>'
        )
    return f"""<article class="play" id="{esc(play['id'])}">
  <header>
    <{heading}>{esc(play['name'])}</{heading}>
    <div class="tags">{''.join(tags)}</div>
    {actions}
  </header>
  {front_panels(form, play, defenses, single)}
  {coach}
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
  <h1 class="page">The rulebook</h1>
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
            # elsewhere — 3 is the tailback in both I looks and the right halfback in the
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

HOLES = [
    ("0 / 1", "Between the center and the guard"),
    ("2 / 3", "Between the guard and the tackle"),
    ("4 / 5", "Between the tackle and the end"),
    ("6 / 7", "Outside the tight end"),
    ("8 / 9", "Wider still — all the way outside"),
]


def write_home(formations: list[dict], defenses: dict) -> str:
    total = sum(len(f["_plays"]) for f in formations)
    cards = []
    for f in formations:
        blurb = first_sentence(f.get("summary") or f.get("notes", ""))
        cards.append(
            f'<a class="fcard imgcard" href="{f_href(f)}">'
            f'<div class="thumb"><img loading="lazy" src="{formation_icon_src(f)}" '
            f'alt="{esc(form_label(f))} alignment"></div>'
            f'<div class="body"><div class="ftop"><h3>{esc(form_label(f))}</h3>'
            f'<span class="n">{len(f["_plays"])} plays</span></div>'
            f"<p>{esc(blurb)}</p>"
            f'<span class="fcall"><code>{esc(call_prefix(f))}</code></span></div></a>'
        )
    defcards = "".join(
        f'<a class="fcard imgcard" href="{d_href(f)}">'
        f'<div class="thumb"><img loading="lazy" src="{def_src(f)}" '
        f'alt="{esc(f["name"])} front"></div>'
        f'<div class="body"><div class="ftop"><h3>{esc(f["call"])}</h3>'
        f'<span class="n">{esc(f["name"])}</span></div>'
        f'<p>{esc(first_sentence(f.get("summary", "")))}</p></div></a>'
        for f in our_fronts(defenses).values()
    )
    body = f"""<h1 class="page">The 2026 Playbook</h1>
<p class="lede">{_count(len(formations)).capitalize()} formations &middot; {total} plays
&middot; {_count(len(our_fronts(defenses)))} fronts.</p>

<div class="quicklinks">
  <a class="qlink" href="calls.html">{icon('search')}<span>Call sheet</span></a>
  <a class="qlink" href="install.html">{icon('calendar')}<span>Install</span></a>
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
    <p class="numcap">Where it goes &mdash; even right, odd left</p>
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


# Where a play hits, in the same five bands the calling language uses. The zone comes
# out of the hole digit, which render.py has already checked against the play's own
# diagram — so filtering by "off-tackle" cannot disagree with the card.
HOLE_ZONES = [
    ("inside", "Inside 0/1"),
    ("guard-tackle", "Guard–tackle 2/3"),
    ("off-tackle", "Off-tackle 4/5"),
    ("outside", "Outside 6/7"),
    ("wide", "Wide 8/9"),
]
ZONE_KEYS = [key for key, _ in HOLE_ZONES]


def call_digits(call: str) -> tuple[str, str]:
    """(zone, direction) for a call, or ("", "") if it has no two-digit number."""
    m = re.search(r"\b(\d)(\d)\b", call or "")
    if not m:
        return "", ""
    hole = int(m.group(2))
    return ZONE_KEYS[hole // 2], ("right" if hole % 2 == 0 else "left")


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
    should not claim to be just the right (or just the left) — "Slant", not "Slant
    Right".

    The SL's alignment goes the same way. A reverse starts him on the side its own
    direction comes back from, so the two halves of that pair disagree about where he
    lines up and one card cannot claim either — "Split SL Reverse", not "Split SL Left
    SL Reverse". Both sides are a click away on the card itself, named in full.
    """
    name = re.sub(r"\bZ (?:Right|Left)\s+", "", name)
    return re.sub(r"\s+(Right|Left)$", "", name)


def write_calls(formations: list[dict], defenses: dict, root: Path) -> str:
    """The call sheet: the offense laid out where it stands, not a list of plays.

    This used to be Favorite Plays over a searchable table of all forty. The table
    answered "which plays exist", which is a question the formation pages and the
    printed book already answer, and it answered it in a shape you cannot hold on a
    sideline. What a coach actually does with a call sheet is swap plays in and out of
    a lineup, so the sheet is now the lineup.

    One sheet per offensive package, side by side like a spreadsheet. The top table is
    the lineup: eight columns, seven for the line and an eighth on the right because
    the slot stands out there rather than on anybody's shoulder. The line and the
    quarterback are column one of the depth chart; the fullback, tailback and slot
    are the package. Every sheet is package 1's personnel: the Split formation, strong
    left and then strong right, each the mirror of the other, and then the I formation,
    strong left and strong right, mirrored the same way.

    Under it, blank Left, Middle and Right columns to write the plays into.
    """
    roster = {}
    path = root / "roster.json"
    if path.is_file():
        import json as _json
        roster = _json.loads(path.read_text(encoding="utf-8"))
    offense = roster.get("offense") or {}
    packages = [p for p in (roster.get("packages") or {}).get("offense") or [] if any(p)]

    def starter(pos: str) -> str:
        names = offense.get(pos) or []
        return names[0] if names else ""

    line = ("LTE", "LT", "LG", "C", "RG", "RT", "RTE")

    def lineup_table(package: list[str], layout: str) -> str:
        """`layout` is "i-", "split-" or "sg-" (Shotgun), then "right" or "left"."""
        backs = dict(zip(PACKAGE_SPOTS["offense"], package))
        # The line across and the quarterback under the center, with the SL just off the
        # line past one end: the right, unless the formation is strong left, when he is
        # past the left end and the line moves over a column to make room. In the I the
        # fullback and tailback stack behind the quarterback; in the Split formation they
        # sit side by side a row deeper. Either way, strong left mirrors strong right.
        left = layout.endswith("-left")
        first = 1 if left else 0
        center = first + 3
        grid = [[None] * 8 for _ in range(4)]
        # A package that sets a lineman plays him; otherwise it is the starter.
        for col, pos in enumerate(line, start=first):
            grid[0][col] = (pos, backs.get(pos) or starter(pos))
        grid[1][center] = ("QB", starter("QB"))
        grid[1][0 if left else 7] = ("SL", backs.get("SL", ""))
        if layout.startswith("sg-"):
            # The Shotgun: the quarterback five yards deep in the last row, a halfback
            # either side of him — the fullback always on his left and the tailback on
            # his right, whichever side the SL is on.
            grid[1][center] = None
            grid[3][center] = ("QB", starter("QB"))
            grid[3][center - 1] = ("LH", backs.get("FB", ""))
            grid[3][center + 1] = ("RH", backs.get("TB", ""))
        elif layout.startswith("i-"):
            grid[2][center] = ("FB", backs.get("FB", ""))
            grid[3][center] = ("TB", backs.get("TB", ""))
        else:
            # The fullback always lines up left of center and the tailback right of
            # it, whichever side the SL is on.
            grid[3][center - 1] = ("FB", backs.get("FB", ""))
            grid[3][center + 1] = ("TB", backs.get("TB", ""))
        rows = []
        for row in grid:
            tds = []
            for spot in row:
                if spot is None:
                    tds.append('<td class="xl-empty"></td>')
                    continue
                pos, name = spot
                who = esc(name) if name else '<span class="xl-open">Open</span>'
                tds.append(f'<td class="xl-spot"><span class="xl-pos">{esc(pos)}</span>'
                           f'<span class="xl-name">{who}</span></td>')
            rows.append(f'<tr>{"".join(tds)}</tr>')
        return f'<table class="xl xl-lineup">{"".join(rows)}</table>'

    plays_by_id = {p["id"]: p for f in formations for p in f["_plays"]}
    sides = ("Left", "Middle", "Right")

    def plays_table(title: str, placed: dict) -> str:
        """Left, Middle and Right, three rows, with any play placed on this sheet at the
        top of its side and the rest blank to be written in. A play is named without
        the formation the sheet's heading already says, and links to its page."""
        cols = []
        for side in sides:
            cells = []
            for pid in placed.get(side, []):
                if pid not in plays_by_id:
                    raise SystemExit(f"call sheet '{title}': no such play '{pid}'")
                play = plays_by_id[pid]
                name = play["name"]
                if name.lower().startswith(title.lower() + " - "):
                    name = name[len(title) + 3:]
                cells.append(f'<a href="{p_href(play)}">{esc(name)}</a>')
            cols.append(cells)
        depth = max([3] + [len(c) for c in cols])
        rows = "".join(
            "<tr>" + "".join(f"<td>{c[i] if i < len(c) else ''}</td>" for c in cols) + "</tr>"
            for i in range(depth)
        )
        return ('<table class="xl xl-plays"><thead><tr>'
                + "".join(f"<th>{side}</th>" for side in sides)
                + f'</tr></thead><tbody>{rows}</tbody></table>')

    # Every sheet is the same personnel, package 1's: the Split formation and then the I,
    # each with strong left on the left of the page and strong right on the right, so a
    # sheet sits on the side it runs to. The other packages stay on the depth chart.
    # The last item of each is the plays placed on it, by the side of the table.
    order = []
    if packages:
        p = packages[0]
        order += [("Split formation - Strong left", p, "split-left", {"Left": ["sb-pitch-l", "sb-qb-sweep-l", "sb-fake-sweep-l"]}),
                  ("Split formation - Strong right", p, "split-right", {"Right": ["sb-pitch-r", "sb-qb-sweep-r", "sb-fake-sweep-r"]}),
                  ("I formation - Strong left", p, "i-left", {"Left": ["i-power-l", "i-te-jet-l"], "Right": ["i-sl-jet-r"]}),
                  ("I formation - Strong right", p, "i-right", {"Left": ["i-sl-jet-l"], "Right": ["i-power-r", "i-te-jet-r"]}),
                  ("Shotgun - Strong left", p, "sg-left", {"Left": ["sg-te-out-l", "sg-qb-sweep-l", "sg-rb-sweep-l"]}),
                  ("Shotgun - Strong right", p, "sg-right", {"Right": ["sg-te-out-r", "sg-qb-sweep-r", "sg-rb-sweep-r"]})]
    sheets = "".join(
        f'<section class="xl-sheet"><p class="xl-title">{esc(title)}</p>'
        f'{lineup_table(package, layout)}{plays_table(title, placed)}</section>'
        for title, package, layout, placed in order
    ) or '<p class="lede">No offensive packages in roster.json yet.</p>'

    body = f"""<h1 class="page">Call sheet</h1>
<div class="xl-sheets">{sheets}</div>"""
    return page(
        f"Call sheet — {SITE_TITLE}",
        body,
        formations,
        defenses=defenses,
        active_nav="calls",
        description="Each offensive package with its lineup, and the plays by side.",
        # Portrait: two sheets across and three rows down, so all six formations fit
        # one page with each strength beside its mirror.
        page_rule="size: letter portrait; margin: 0.3in;",
    )


def write_formation_page(form: dict, formations: list[dict], defenses: dict) -> str:
    cards = []
    for p in form["_plays"]:
        cards.append(
            f'<a class="pcard" href="{p_href(p)}">'
            f'<div class="thumb"><img loading="lazy" src="{card_src(form, p)}" '
            f'alt="{esc(p["name"])} diagram"></div>'
            f'<div class="body"><h4>{esc(p["name"])}</h4>'
            f'<span class="call">{esc(p.get("call", ""))}</span></div></a>'
        )
    blocks = ['<p class="section-head">The plays</p>'
              f'<div class="plist">{"".join(cards)}</div>']

    notes = ""
    if form.get("coaching_notes"):
        items = "\n    ".join(f"<li>{esc(c)}</li>" for c in form["coaching_notes"])
        notes = (
            '<p class="section-head">Coaching notes</p>\n'
            f'<ul class="coach">\n    {items}\n  </ul>'
        )

    body = f"""<h1 class="page">{esc(form_label(form))}</h1>
<p class="sub">{len(form['_plays'])} plays
&nbsp;·&nbsp; {esc(form.get('personnel', ''))}</p>
<p class="lede">{esc(form.get('notes', ''))}</p>
{notes}
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
    actions = (
        '<div class="play-actions">'
        '<button type="button" class="btn solid" onclick="window.print()">Print</button>'
        "</div>"
    )

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


def install_items(pr: dict, plays: dict, forms_by_id: dict, defenses: dict) -> list[str]:
    """The play, front and formation chips a practice installs."""
    items = []
    for pid in pr.get("plays", []):
        play, _form = plays[pid]
        items.append(
            f'<a class="ins-play" href="{p_href(play)}">'
            f'<span class="ins-call">{esc(play.get("call", ""))}</span>'
            f'<span class="ins-name">{esc(play["name"])}</span></a>'
        )
    # A play this practice runs again rather than teaches. Marked, because the block
    # answers "what is new today" first and this is the honest answer to "what else
    # are we running".
    for pid in pr.get("review", []):
        play, _form = plays[pid]
        items.append(
            f'<a class="ins-play again" href="{p_href(play)}">'
            f'<span class="ins-call">{esc(play.get("call", ""))}</span>'
            f'<span class="ins-name">{esc(play["name"])} &middot; review</span></a>'
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


def practice_blocks_html(pr: dict, items: list[str], needs: str) -> str:
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
        water = pr.get("water_break")
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
        elif kind == "install":
            emphasis = pr.get("emphasis", "")
            emphasis_html = f'<p class="ins-em">{esc(emphasis)}</p>' if emphasis else ""
            extra = "".join(f"<li>{esc(n)}</li>" for n in blk.get("notes", []))
            extra_html = f'<ul class="ins-drills">{extra}</ul>' if extra else ""
            body = (f'<div class="ins-list">{"".join(items)}</div>'
                    f'{emphasis_html}{extra_html}{needs}')
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
    body = f"""<h1 class="page">Install schedule</h1>
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
    phases: dict, formations: list[dict], defenses: dict,
) -> str:
    """One practice, on its own page: what we install, and the run of practice.

    Everything a coach carries onto the field for that session and nothing from any
    other one — the long scroll made you scan past four practices to find tonight's.
    """
    plays = {p["id"]: (p, f) for f in formations for p in f["_plays"]}
    forms_by_id = {f["id"]: f for f in formations}

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
    <div class="play-actions">
      <button type="button" class="btn solid" onclick="window.print()">Print</button>
    </div>
  </div>
  <div class="ins-day-plan">{practice_blocks_html(pr, items, needs)}</div>
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
DEFENSE_POSITION_NAMES = {
    "LE": "Left end", "LT": "Left tackle", "NT": "Nose tackle", "RT": "Right tackle",
    "RE": "Right end", "W": "Weak linebacker", "M": "Middle linebacker",
    "S": "Strong linebacker", "R": "Rover", "LC": "Left corner", "RC": "Right corner",
    "FS": "Free safety",
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
ROTATIONS = [str(n) for n in range(1, 7)]

# Packages, above the squad. A fixed group rather than a list because the group is the
# thing being named — the kids who go on and come off together. Count and size are per
# side and here and nowhere else: the markup, the roster round-trip and the print sheet
# all take their shape from them. Offense is six across, seven deep: the backfield and
# then the four interior linemen, because a package can change the line too. Defense
# is five of three.
PACKAGE_COUNT = {"offense": 6, "defense": 5}
PACKAGE_SIZE = {"offense": 7, "defense": 3}

# What each side calls its packages. The offense heading names the three spots the
# group is made of, in the order the slots sit in — the line does not change between
# packages, so the package IS the backfield, and saying which three it is turns a box
# of names into something a coach can check at a glance.
PACKAGE_TITLE = {
    "offense": "Offensive FB-TB-SL Packages",
    "defense": "Packages",
}

# What each slot in a package is, where the side has a fixed answer. Offense does: the
# fullback, the tailback and the slot, then the left tackle, left guard, right guard
# and right tackle, in that order. Defense does not, and labelling its slots would be
# inventing a structure it has not got.
#
# The label is drawn from this attribute in CSS rather than put in the slot as an
# element, because the slot's contents are rewritten whenever it empties or fills —
# a child element would be wiped the first time somebody took a name out of it.
PACKAGE_SPOTS = {"offense": ("FB", "TB", "SL", "LT", "LG", "RG", "RT")}


def rotations_for(side: str) -> list[tuple[str, str, str]]:
    """The columns, in depth order. Both sides run the same six."""
    return [(n, "d" + n, "") for n in ROTATIONS]


def dc_chip(name: str, home: str) -> str:
    """One kid, one draggable name.

    A <button> rather than a <span> because everything a chip can do by drag it can
    also do by tap-then-tap, and a button is focusable, keyboard-operable and
    announced as interactive without a line of ARIA. draggable="false" is deliberate:
    the native HTML5 drag never fires on touch, and a coach uses this on a phone on a
    sideline — the pointer-event handler in site.js covers mouse and finger both, and
    the native one would only fight it.

    data-home is the position this name sits at in roster.json. A kid left out of every
    rotation still has to be written back somewhere, and this is where.
    """
    return (f'<button type="button" class="dc-chip" draggable="false" '
            f'data-name="{esc(name)}" data-home="{esc(home)}">{esc(name)}</button>')


def side_squad(order: list[str], names_by_pos: dict) -> list[tuple[str, str]]:
    """Every kid on this side of the ball, once each, with the spot he is listed at.

    Read in position order rather than alphabetically, because that is the order the
    coach entered them and it keeps the linemen together. The spot travels with the
    name so that a kid left out of every rotation can still be written back to the
    file at the position he belongs to.
    """
    out, seen = [], set()
    for pos in order:
        for name in (names_by_pos.get(pos) or []):
            if name and name not in seen:
                seen.add(name)
                out.append((name, pos))
    return out


def side_board(side: str, order: list[str], alt_order: list[str],
               names_by_pos: dict, label_fn, packages: list | None = None,
               package_names: list | None = None) -> str:
    """One side of the ball, every rotation, as columns of one grid.

    Rotation belongs on the X axis. The question this page exists to answer is "the
    left tackle just came off — who goes in", and with a table per rotation that
    answer was eight hundred pixels down the page and had to be found by counting
    rows. Side by side it is the next cell over.
    """
    rows = []
    for pos in order + alt_order:
        names = names_by_pos.get(pos) or []
        # A spot no formation on this board aligns, carried only because somebody is
        # standing on it. Off the count, so it cannot make a full unit read as twelve.
        alt = ' class="dc-alt"' if pos in alt_order else ""
        cells = ""
        for idx, (rot_name, rot_key, _hint) in enumerate(rotations_for(side)):
            name = names[idx] if idx < len(names) else ""
            # Open is a button so an empty spot can be tabbed to and chosen from a
            # keyboard exactly like a name can — the whole board is reachable without
            # a pointer, which a drag-only interface never is.
            inner = (dc_chip(name, pos) if name
                     else '<button type="button" class="dc-open">Open</button>')
            cells += (f'<td class="dc-cell" data-label="{esc(rot_name)}" '
                      f'data-side="{side}" data-pos="{esc(pos)}" data-rot="{rot_key}">'
                      f'{inner}</td>')
        rows.append(
            f'<tr{alt} data-pos="{esc(pos)}">'
            f'<td class="dc-poscell"><span class="dc-abbr">{esc(pos)}</span>'
            f'<span class="dc-label">{esc(label_fn(pos))}</span></td>{cells}</tr>'
        )

    head = "".join(
        f'<th class="rot-th" data-rot="{rot_key}">{esc(rot_name)}</th>'
        for rot_name, rot_key, hint in rotations_for(side)
    )
    # The whole squad, not just whoever is left over. This rail used to be the bench —
    # the kids in no rotation — and a chip lived in exactly one place, so putting a kid
    # on Purple took him off Gold. Three rotations make that wrong: the same left
    # tackle plays on all three, and a coach should say so by dragging, not by editing
    # JSON. So the rail is a source rather than a container. Everybody stays in it, the
    # board holds copies, and a kid can be in as many rotations as he can stand.
    pool = "".join(dc_chip(name, home)
                   for name, home in side_squad(order, names_by_pos))
    # The packages, above the squad. A package is the group who go on and come off
    # together, so it is fixed slots rather than a list: the board answers "who plays
    # left guard", and this answers "who am I sending in next".
    packs = packages or []

    spots = PACKAGE_SPOTS.get(side, ())

    def spot_attr(at: int) -> str:
        return f' data-spot="{esc(spots[at])}"' if at < len(spots) else ""

    def in_slot(n: int, at: int) -> str:
        pair = packs[n - 1] if n - 1 < len(packs) else []
        name = pair[at] if isinstance(pair, list) and at < len(pair) else ""
        return (dc_chip(name, "") if name
                else '<button type="button" class="dc-open">Open</button>')

    pkgs = "".join(
        # A package the coach has named is called by its name; the rest by number.
        f'<div class="dc-pkg"><p class="dc-pkg-h">'
        f'{esc((package_names or [])[n - 1] if n - 1 < len(package_names or []) else f"Package {n}")}</p>'
        + "".join(
            f'<div class="dc-pkg-slot" data-side="{side}" data-pkg="{n}" '
            f'data-at="{at}"{spot_attr(at)}>{in_slot(n, at)}</div>'
            for at in range(PACKAGE_SIZE[side]))
        # Who is in and out against package 1, filled in by the board script so it
        # follows every name a coach drags.
        + '<p class="dc-pkg-note" aria-live="polite"></p></div>'
        for n in range(1, PACKAGE_COUNT[side] + 1)
    )
    return (
        f'<div class="tablewrap dc-board-wrap"><table class="dc-board">'
        f'<thead><tr><th>Position</th>{head}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
        f'<div class="dc-pkgs"><p class="rot-h">'
        f'{esc(PACKAGE_TITLE.get(side, "Packages"))}</p>'
        f'<div class="dc-pkgwrap"><div class="dc-pkgrow">{pkgs}</div></div></div>'
        f'<div class="dc-bench"><p class="rot-h">Squad'
        f'<span class="rot-count" data-count="{side}-idle"></span></p>'
        f'<div class="dc-pool" data-side="{side}" data-rot="squad">{pool}</div></div>'
    )


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
    # The board is the base formation's eleven — SL, FB and TB in the backfield. It
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
    def_label = lambda p: def_names.get(p, p)  # noqa: E731

    # One section per side of the ball, each carrying both rotations as columns. The
    # split used to be Purple sheet / Gold sheet with offense and defense side by
    # side inside; it is now offense sheet / defense sheet with the rotations side by
    # side. Same two sheets either way, and this way the coordinator who only ever
    # looks at one side of the ball is handed exactly his page.
    sides = (
        ("offense", "Offense", off_order, alt_order, position_name,
         "The base formation's eleven."),
        ("defense", "Defense", def_order, def_alt_order, def_label,
         f"The {front['name'].replace('-', '–')}, our everyday front."
         if front else "Our everyday front."),
    )
    sections = []
    for side, heading, order, alts, label, sub in sides:
        packs = (roster.get("packages") or {}).get(side)
        sections.append(
            f'<section class="dc-side" data-side="{side}">'
            f'<p class="hero-head">{esc(heading)}'
            f'<span class="rot-sub">{esc(sub)}</span></p>'
            f'{side_board(side, order, alts, roster.get(side, {}), label, packs, (roster.get("package_names") or {}).get(side))}'
            f'</section>'
        )

    # What the script needs that the board does not already carry. The roster goes
    # along whole so Copy can hand back a file with the note still in it rather than a
    # board-shaped fragment of one.
    #
    # The columns go per side, not as one list. Offense has a fourth and defense does
    # not, and every depth index the script works out — which slot of the list a cell
    # writes to, how far to pad before the kids in no column — is counted against the
    # side it is on. One shared list would write defense names into a Jumbo slot that
    # does not exist.
    import json as _json
    # A literal "</script>" inside the blob would close the tag early. Every "<" in
    # JSON is inside a string, so escaping it is lossless and the parser never sees
    # the difference — cheaper than trusting that no kid is ever nicknamed "<3".
    data = _json.dumps(
        {"roster": roster,
         "rotations": {side: [k for _n, k, _h in rotations_for(side)]
                       for side in ("offense", "defense")}},
        ensure_ascii=False).replace("<", "\\u003c")

    # One side per sheet — see the .dc-side rules in the print stylesheet.
    body = f"""<h1 class="page">Depth Chart</h1>
<script type="application/json" id="dc-data">{data}</script>
<div class="dc-bar" id="dc-bar">
  <div class="dc-tools">
    <button type="button" class="btn" id="dc-reset" hidden>Reset</button>
    <button type="button" class="btn" id="dc-copy">Copy roster.json</button>
    <button type="button" class="btn solid" onclick="window.print()">Print</button>
  </div>
</div>
<div class="dc-edited" id="dc-edited" hidden>Showing your local edits, not the roster
in the repo.</div>

<div id="dc-board">
{"".join(sections)}
</div>"""
    return page(
        f"Depth Chart — {SITE_TITLE}",
        body,
        formations,
        defenses=defenses,
        active_nav="depth",
        description="First, second and third string — offense and defense, who plays where.",
        # Pin the margin so a side cannot be pushed onto a second sheet by a print
        # dialog set to wide margins. Same 9mm the play-card book uses. The paper size
        # is deliberately not pinned: whatever is in the tray, Letter or A4, both fit.
        page_rule="margin: 9mm;",
    )


def write_defense_index(formations: list[dict], defenses: dict) -> str:
    cards = []
    for fid, f in our_fronts(defenses).items():
        counts = {}
        for r in f.get("roles", {}).values():
            counts[r] = counts.get(r, 0) + 1
        cards.append(
            f'<a class="fcard imgcard" href="{d_href(f)}">'
            f'<div class="thumb"><img loading="lazy" src="{def_src(f)}" '
            f'alt="{esc(f["name"])} front"></div>'
            f'<div class="body"><div class="ftop"><h3>{esc(f["call"])}</h3>'
            f'<span class="n">{esc(f["name"])}</span></div>'
            f'<p>{esc(first_sentence(f.get("summary", "")))}</p>'
            f'<span class="fcall">{counts.get("DL", 0)} down &nbsp;&middot;&nbsp; '
            f'{counts.get("LB", 0)} linebackers &nbsp;&middot;&nbsp; '
            f'{counts.get("DB", 0)} defensive backs</span></div></a>'
        )
    body = f"""<h1 class="page">Defensive playbook</h1>
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

    actions = ('<div class="play-actions">'
               '<button type="button" class="btn solid" onclick="window.print()">Print</button>'
               "</div>")
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


def write_print_book(formations: list[dict], defenses: dict) -> str:
    total = sum(len(f["_plays"]) for f in formations) + len(our_fronts(defenses))
    arts = [play_article(f, p, defenses, single=blocking.DEFAULT_FRONT)
            for f in formations for p in f["_plays"]]
    arts += [defense_article(d) for d in our_fronts(defenses).values()]
    body = f"""<div class="print-intro">
  <h1 class="page">Print the whole book</h1>
  <p class="lede">{total} plays, one per landscape sheet, diagram first. Hit the button
  (or your browser's print command) and print to PDF for a binder. To print a single
  play instead, open that play and use the Print button there.</p>
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
        description=f"All {total} plays formatted one per landscape page.",
        landscape=True,
    )


# ---------------------------------------------------------------------- entry --


def write_all(formations: list[dict], defenses: dict, root: Path) -> int:
    # Sweep out pages this build no longer writes. The site is flat files at the repo
    # root, so a deleted play or a dropped formation leaves its page sitting there,
    # still linked from anyone's bookmark and still in the search engine's index. The
    # cards learned this lesson first — 112 of them outlived the plays they drew.
    keep = {"index.html", "calls.html", "print.html", "defense.html", "rules.html",
            "install.html", "depth-chart.html"}
    keep |= {f_href(f) for f in formations}
    keep |= {p_href(p) for f in formations for p in f["_plays"]}
    keep |= {d_href(d) for d in our_fronts(defenses).values()}
    keep |= {install_href(pr) for pr in load_schedule(root).get("practices", [])}
    for stale in root.glob("*.html"):
        if stale.name not in keep:
            stale.unlink()

    assets = root / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "site.css").write_text(SITE_CSS.strip() + "\n", encoding="utf-8")
    (assets / "site.js").write_text(SITE_JS.strip() + "\n", encoding="utf-8")

    written = 0
    (root / "index.html").write_text(write_home(formations, defenses), encoding="utf-8")
    (root / "calls.html").write_text(write_calls(formations, defenses, root), encoding="utf-8")
    (root / "print.html").write_text(
        write_print_book(formations, defenses), encoding="utf-8")
    (root / "defense.html").write_text(
        write_defense_index(formations, defenses), encoding="utf-8")
    (root / "rules.html").write_text(
        write_rulebook(formations, defenses, root), encoding="utf-8")
    (root / "install.html").write_text(
        write_install(formations, defenses, root), encoding="utf-8")
    (root / "depth-chart.html").write_text(
        write_depth_chart(formations, defenses, root), encoding="utf-8")
    written += 7

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
            write_install_day(pr, prev, nxt, practices, phases, formations, defenses),
            encoding="utf-8")
        written += 1

    for front in our_fronts(defenses).values():
        (root / d_href(front)).write_text(
            write_defense_page(front, formations, defenses), encoding="utf-8")
        written += 1

    for form in formations:
        (root / f_href(form)).write_text(
            write_formation_page(form, formations, defenses), encoding="utf-8"
        )
        written += 1
        plays = form["_plays"]
        for i, play in enumerate(plays):
            prev = plays[i - 1] if i else None
            nxt = plays[i + 1] if i + 1 < len(plays) else None
            (root / p_href(play)).write_text(
                write_play_page(form, play, prev, nxt, formations, defenses),
                encoding="utf-8",
            )
            written += 1
    return written
