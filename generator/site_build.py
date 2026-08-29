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

import hashlib
import re
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
.tablewrap.dc-board-wrap {
  margin: 10px 0 4px; overflow-x: auto; background: var(--panel);
  border: 1px solid var(--line); border-radius: 12px; box-shadow: var(--shadow);
}
table.dc-board { width: 100%; border-collapse: collapse; min-width: 460px; }
table.dc-board th, table.dc-board td {
  border-bottom: 1px solid var(--line-soft); border-right: 1px solid var(--line-soft);
  padding: 5px 10px;
}
table.dc-board th:last-child, table.dc-board td:last-child { border-right: 0; }
table.dc-board tbody tr:last-child td { border-bottom: 0; }
table.dc-board thead th {
  background: var(--accent-solid); color: var(--on-accent); text-align: left;
  font-size: 11px; text-transform: uppercase; letter-spacing: 1.3px; font-weight: 800;
  padding: 9px 12px;
}
/* Purple and Gold are the units, so the column headers wear them. A coach scanning
   for the Gold left tackle finds the column by colour before reading a word of it. */
table.dc-board thead th.rot-th[data-rot="purple"] { background: #5b2d8e; }
table.dc-board thead th.rot-th[data-rot="gold"] { background: #8a6508; }
table.dc-board .dc-poscell { background: var(--panel-2); white-space: nowrap; width: 1%; }
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
@media (max-width: 620px) {
  .tablewrap.dc-board-wrap { overflow-x: visible; }
  table.dc-board { min-width: 0; }
  table.dc-board thead { display: none; }
  table.dc-board, table.dc-board tbody, table.dc-board tr, table.dc-board td {
    display: block; width: 100%;
  }
  table.dc-board tr { padding: 8px 12px; border-bottom: 1px solid var(--line); }
  table.dc-board tr:last-child { border-bottom: 0; }
  table.dc-board td {
    border: 0; padding: 2px 0; background: none !important; min-width: 0;
  }
  table.dc-board .dc-poscell { padding: 0 0 5px; margin-bottom: 4px; border-bottom: 1px dashed var(--line); }
  table.dc-board td.dc-cell::before {
    content: attr(data-label); display: inline-block; min-width: 52px;
    font-size: 10px; text-transform: uppercase; letter-spacing: 1px; font-weight: 800;
  }
  table.dc-board td.dc-cell[data-rot="purple"]::before { color: #a882d8; }
  table.dc-board td.dc-cell[data-rot="gold"]::before { color: #d0a63a; }
  table.dc-board .dc-open { padding: 3px 0; }
}

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
/* A kid on both sides of the same rotation is playing every snap. That is the fact
   this page was hiding: nine of the eleven Purple starters never leave the field. */
.dc-chip.two-way::before {
  content: ""; width: 6px; height: 6px; border-radius: 999px; flex: 0 0 auto;
  background: var(--red);
}

/* ---------------------------------------------------------------------- bench -- */
/* The kids in neither rotation. It was a footnote at the bottom of the page; it is
   now the pile you drag out of, so it sits under the board it feeds. */
.dc-bench { margin: 0 0 6px; }
.dc-pool {
  display: flex; flex-wrap: wrap; gap: 6px; min-height: 38px; padding: 8px 10px;
  border: 1px dashed var(--line); border-radius: 10px; background: var(--panel);
}
.dc-pool:empty::before {
  content: "Everybody is in a rotation."; color: var(--muted); font-size: 13px;
  font-style: italic;
}

/* ------------------------------------------------------------------ dc chrome -- */
.dc-bar {
  display: flex; align-items: center; justify-content: space-between; gap: 14px;
  flex-wrap: wrap; margin: 14px 0 6px;
}
.dc-tally { margin: 0; font-size: 13px; color: var(--ink-2); }
.dc-tally b { color: var(--ink); }
.dc-tally .warn { color: var(--red); font-weight: 800; }
.dc-tools { display: flex; gap: 8px; flex-wrap: wrap; }
.dc-hint { margin: 0 0 10px; font-size: 13px; color: var(--muted); max-width: 62ch; }
.dc-hint b { color: var(--ink-2); }
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

.dc-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 8px; }
.dc-row {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  flex-wrap: wrap; background: var(--panel); border: 1px solid var(--line);
  border-radius: 10px; padding: 10px 14px; box-shadow: var(--shadow);
}
.dc-pos { display: flex; align-items: baseline; gap: 9px; min-width: 170px; }
.dc-abbr { font-weight: 800; color: var(--accent-ink); font-size: 15px; }
.dc-label { color: var(--muted); font-size: 12.5px; }
.dc-slots { display: flex; gap: 8px; flex-wrap: wrap; }
.dc-slot {
  display: flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 600;
  background: var(--panel-2); border-radius: 999px; padding: 5px 12px 5px 5px;
}
.dc-slot b {
  display: inline-flex; align-items: center; justify-content: center; width: 18px;
  height: 18px; border-radius: 999px; font-size: 10.5px; color: var(--on-accent);
  background: var(--accent-solid);
}
.dc-slot.dc-open { color: var(--muted); font-style: italic; font-weight: 500; }
.dc-slot.dc-open b { background: var(--line); color: var(--muted); }

/* ----------------------------------------------------------------- both sides -- */
/* Offense and defense are the top split, and Purple and Gold are columns inside
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
/* A unit short of eleven is a hole somebody has to fill, so say so in the column
   header instead of making the coach count Open rows. Written by site.js, because
   after the first drag the number the page shipped with is a lie. */
.rot-count { font-weight: 800; letter-spacing: 0; opacity: .85; }
.rot-count.warn { color: var(--red); opacity: 1; }
thead .rot-count { margin-left: 7px; font-size: 11px; }
/* The body red is nearly invisible on the gold header fill. A short unit is the one
   thing on this page that must not be missable, so on a coloured header it goes pale
   instead of dark — same alarm, read against the fill it actually sits on. */
thead .rot-count.warn { color: #ffd2d8; }

.pkg {
  margin: 14px 0 8px; padding: 14px 16px 4px; background: var(--panel);
  border: 1px solid var(--line); border-left: 4px solid var(--accent-solid);
  border-radius: 10px; box-shadow: var(--shadow);
}
.pkg-name {
  margin: 0 0 4px; font-weight: 800; font-size: 12.5px; letter-spacing: .4px;
  text-transform: uppercase; color: var(--accent-ink);
}
.pkg-note { margin: 0 0 12px; font-size: 13.5px; color: var(--ink-2); }
.pkg .dc-list { margin-bottom: 10px; }

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
.ins-wrap { max-width: 82ch; }
.ph { margin: 34px 0 14px; padding-bottom: 10px; border-bottom: 2px solid var(--accent-solid); }
.ph:first-child { margin-top: 20px; }
.ph h2 {
  font-size: clamp(17px, 3vw, 21px); color: var(--ink); margin: 0 0 6px; letter-spacing: -.2px;
}
.ph p { margin: 0; color: var(--muted); font-size: 14px; max-width: 68ch; }

.ins {
  display: grid; grid-template-columns: 78px minmax(0, 1fr); gap: 16px;
  background: var(--panel); border: 1px solid var(--line); border-radius: 12px;
  padding: 14px 16px; margin: 0 0 10px; box-shadow: var(--shadow);
}
@media (max-width: 560px) { .ins { grid-template-columns: 1fr; gap: 8px; } }
.ins-n {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: var(--accent-solid); color: var(--on-accent); border-radius: 10px;
  padding: 8px 4px; align-self: start;
}
@media (max-width: 560px) { .ins-n { flex-direction: row; gap: 8px; padding: 5px 10px; } }
.ins-n span { font-size: 9.5px; text-transform: uppercase; letter-spacing: 1.2px; opacity: .75; }
.ins-n b { font-size: 26px; line-height: 1.1; font-variant-numeric: tabular-nums; }
@media (max-width: 560px) { .ins-n b { font-size: 18px; } }

.ins-body h3 { margin: 0 0 9px; font-size: 16.5px; color: var(--ink); }
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
.ins-blk .ins-em:first-of-type { margin-top: 0; }
.ins-list { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 9px; }
.ins-play {
  display: inline-flex; flex-direction: column; gap: 1px; text-decoration: none;
  background: var(--panel-2); border: 1px solid var(--line); border-radius: 8px;
  padding: 5px 10px; min-width: 0;
}
.ins-play:hover { border-color: var(--accent); background: var(--panel); }
.ins-play.def { border-left: 3px solid var(--red); }
.ins-play.form { border-left: 3px solid var(--accent-solid); }
.ins-n time { display: block; font-size: 11px; line-height: 1.2; margin-top: 3px;
  font-style: normal; opacity: .85; }
.ins-call {
  font-size: 12.5px; font-weight: 700; color: var(--accent-ink);
  font-variant-numeric: tabular-nums;
}
.ins-name { font-size: 11.5px; color: var(--muted); }
.ins-none { font-size: 13px; color: var(--muted); font-style: italic; }
.ins-em { margin: 0; font-size: 14px; color: var(--ink-2); line-height: 1.55; }
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
.ins-todo {
  margin: 34px 0 0; padding: 18px 18px 14px; border: 1px dashed var(--line);
  border-radius: 12px; background: var(--panel-2);
}
.ins-todo summary {
  font-size: 17px; font-weight: 700; color: var(--ink); cursor: pointer;
}
.ins-todo summary::marker { color: var(--muted); }
.ins-todo[open] summary { margin-bottom: 6px; }
.ins-todo-count { margin-left: 8px; font-size: 12px; font-weight: 600; color: var(--muted); }
.ins-todo > p { margin: 10px 0 14px; font-size: 14px; color: var(--muted); max-width: 66ch; }
.ins-todo code { font-size: .92em; background: var(--panel); border-radius: 4px; padding: 1px 5px; }
.ins-todo-grp { margin-bottom: 12px; }
.ins-todo-grp h4 {
  margin: 0 0 6px; font-size: 11px; text-transform: uppercase; letter-spacing: 1.2px;
  color: var(--muted); display: flex; align-items: center; gap: 7px;
}
.ins-todo-grp h4 span {
  background: var(--line); color: var(--ink-2); border-radius: 999px;
  padding: 0 7px; font-size: 10.5px; letter-spacing: 0;
}
.ins-todo .ins-play { background: var(--panel); }

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
  .section-head, .btn, .print-intro,
  .crumbs, .playbar { display: none !important; }
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
  /* The purpose is why you'd call the play — useful when planning, not when holding
     the card on a sideline. Dropping it is what buys the diagram its height. */
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

  /* Depth chart: one rotation per sheet, offense and defense side by side on it.
     Hand the Purple sheet to the group that is on the field and the Gold sheet to
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
    overflow: visible; box-shadow: none; border-radius: 0; margin: 0;
  }
  table.dc-board { min-width: 0; }
  table.dc-board th, table.dc-board td { padding: 3px 8px; }
  table.dc-board .dc-poscell .dc-abbr { font-size: 10pt; }
  table.dc-board .dc-poscell .dc-label { font-size: 7.5pt; }
  table.dc-board thead th { padding: 5px 8px; font-size: 8pt; }
  /* Purple and Gold survive as printed words. A header fill is the one place colour
     would have carried meaning nothing else does, and a printer set to skip
     backgrounds drops it silently — so the whole header row goes to plain text on a
     rule, which reads the same out of any tray. */
  table.dc-board thead th { background: none; color: #000; border-bottom: 2px solid #000; }
  /* On paper a chip is just a name — the pill, the border and the drag affordance
     all cost ink and say nothing a coach holding the sheet can act on. */
  .dc-chip {
    background: none; border: 0; padding: 0; font-size: 10pt; font-weight: 800;
    color: #000; border-radius: 0;
  }
  .dc-chip.two-way::before {
    width: auto; height: auto; background: none; content: "\\2022 "; font-weight: 800;
  }
  .dc-pool {
    display: flex; flex-wrap: wrap; gap: 2px 12px; border: 0; padding: 0;
    min-height: 0; background: none;
  }
  .dc-bench { margin: 6px 0 0; }
  /* Buttons, hints and the local-edits banner are screen furniture. The tally is
     not: how many spots are open is the first thing a coach checks on the sheet. */
  .dc-tools, .dc-hint, .dc-edited { display: none; }
  .dc-bar { margin: 0 0 6px; display: block; }
  .dc-tally { font-size: 8.5pt; }
  /* The title block is the price of the first sheet and it is paid in rows: at
     web sizes the h1, the lede and the Jumbo cards together cost more vertical
     room than the four backfield spots underneath them, and the offense lands on
     a second sheet by a single row.

     The lede goes rather than the Jumbo package or the title. It is the note out
     of roster.json, which explains how the file is structured to whoever edits
     it — that is a reader sitting at a keyboard, not a coach holding the paper,
     and the paper is the thing with a page limit. */
  h1.page { font-size: 18pt; margin: 0 0 3px; }
  .dc-note { display: none; }
  .pkg { margin: 10px 0 0; padding: 8px 10px 2px; box-shadow: none; border-radius: 0; }
  .pkg-name { font-size: 9pt; margin: 0 0 2px; }
  .pkg-note { font-size: 7.5pt; margin: 0 0 5px; }
  /* The package is three spots, not a third unit. Stacked rows cost it the whole
     bottom of the Purple sheet and push the rotation onto a second page, so on
     paper it lays out across instead of down. */
  .pkg .dc-list, .dc-list {
    display: flex; flex-direction: row; flex-wrap: wrap;
    gap: 4px 10px; margin-bottom: 2px;
  }
  .dc-row {
    padding: 2px 6px; border-radius: 0; box-shadow: none; gap: 6px;
    flex: 0 0 auto; justify-content: flex-start;
  }
  .dc-row .dc-label { display: none; }
  .dc-row .dc-abbr { font-size: 8pt; }
  .dc-slot { font-size: 8pt; }
}
"""

SITE_JS = """
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
   two chips in the SAME group widens the list — Split Backs or Full House. Picking
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
     switching to it — pick Regular I then Power I and you are looking at eighteen
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
  var tally = document.getElementById('dc-tally');
  var edited = document.getElementById('dc-edited');
  var resetBtn = document.getElementById('dc-reset');
  var copyBtn = document.getElementById('dc-copy');
  var SLOT = 'td.dc-cell, .dc-pool';

  function all(sel, ctx) {
    return Array.prototype.slice.call((ctx || board).querySelectorAll(sel));
  }
  function sideOf(el) {
    var side = el.closest('.dc-side');
    return side ? side.dataset.side : '';
  }
  function chipIn(slot) { return slot.querySelector('.dc-chip'); }

  /* A cell with nobody in it says Open, and says it as a button so that the spot can
     be tabbed to and chosen from a keyboard exactly like a name can. The bench needs
     no such marker — its :empty rule speaks for it. */
  function fill(slot) {
    if (!slot.classList.contains('dc-cell')) return;
    var has = chipIn(slot), open = slot.querySelector('.dc-open');
    if (has && open) open.remove();
    if (!has && !open) {
      slot.innerHTML = '<button type="button" class="dc-open">Open</button>';
    }
  }

  function move(chip, target) {
    var from = chip.parentNode;
    if (!target || from === target) return;
    // Offense chips stay on offense. The two sides are separate problems and a kid
    // is on both of them; dragging across would merge two answers into one.
    if (sideOf(target) !== sideOf(chip)) return;
    var held = target.classList.contains('dc-cell') ? chipIn(target) : null;
    // A swap, not a shove: whoever is already there goes back where this one came
    // from. Dropping onto the bench is not a swap, because the bench holds any number.
    if (held) from.appendChild(held);
    var open = target.querySelector('.dc-open');
    if (open) open.remove();
    target.appendChild(chip);
    fill(from);
    fill(target);
    refresh();
  }

  /* Every placement on the board, in a shape that survives a roster.json edit: a
     record names the spot rather than pointing at it, so one whose spot has since
     gone is skipped instead of taking the whole save down with it. */
  function snapshot() {
    var out = [];
    all(SLOT).forEach(function (s) {
      all('.dc-chip', s).forEach(function (c) {
        out.push([sideOf(s), s.dataset.rot, s.dataset.pos || '',
                  c.dataset.name, c.dataset.home]);
      });
    });
    return out;
  }

  var pristine = JSON.stringify(snapshot());

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
  }

  function restore() {
    var raw = null, at;
    try { raw = localStorage.getItem(KEY); } catch (e) { return; }
    if (!raw) return;
    try { at = JSON.parse(raw); } catch (e) { return; }
    if (!Array.isArray(at)) return;

    var byKey = {};
    all(SLOT).forEach(function (s) {
      byKey[sideOf(s) + '/' + s.dataset.rot + '/' + (s.dataset.pos || '')] = s;
    });
    // Lift every chip off the board, then set them back down where the save says.
    // Two chips can share a name — the same kid is on both sides — so they come off
    // into a list per side and are matched out of it one at a time.
    var loose = { offense: [], defense: [] };
    all('.dc-chip').forEach(function (c) {
      var side = sideOf(c);
      if (loose[side]) loose[side].push(c);
      c.remove();
    });
    all(SLOT).forEach(function (s) { s.innerHTML = ''; fill(s); });

    function take(side, name) {
      var list = loose[side] || [];
      for (var i = 0; i < list.length; i++) {
        if (list[i].dataset.name === name) return list.splice(i, 1)[0];
      }
      return null;
    }

    at.forEach(function (rec) {
      var slot = byKey[rec[0] + '/' + rec[1] + '/' + (rec[2] || '')];
      if (!slot) return;
      if (slot.classList.contains('dc-cell') && chipIn(slot)) return;
      var chip = take(rec[0], rec[3]);
      if (!chip) return;
      var open = slot.querySelector('.dc-open');
      if (open) open.remove();
      slot.appendChild(chip);
    });
    // Anybody the save never mentions is somebody added to roster.json since it was
    // written. The bench is the honest place for him: unplaced, and visibly so.
    Object.keys(loose).forEach(function (side) {
      var bench = byKey[side + '/bench/'];
      loose[side].forEach(function (c) { if (bench) bench.appendChild(c); });
    });
    all(SLOT).forEach(fill);
  }

  function refresh() {
    var counts = {}, seen = {};
    // Alt rows are off the count. They are spots no formation on this board aligns,
    // carried only because somebody is standing on one, and counting them would make
    // a complete eleven read as twelve.
    all('tbody tr[data-pos]').forEach(function (tr) {
      if (tr.classList.contains('dc-alt')) return;
      all('td.dc-cell', tr).forEach(function (td) {
        var k = sideOf(td) + '-' + td.dataset.rot;
        var c = counts[k] || (counts[k] = { on: 0, of: 0 });
        c.of++;
        var chip = chipIn(td);
        if (!chip) return;
        c.on++;
        var rot = seen[td.dataset.rot] || (seen[td.dataset.rot] = {});
        rot[chip.dataset.name] = (rot[chip.dataset.name] || 0) + 1;
      });
    });

    // A name on both sides of one rotation is a kid who never leaves the field. It
    // is the most consequential thing this page knows and it used to say none of it.
    all('.dc-chip').forEach(function (c) {
      var rot = seen[c.parentNode.dataset.rot];
      var two = !!(rot && rot[c.dataset.name] > 1);
      c.classList.toggle('two-way', two);
      c.title = two ? c.dataset.name + ' plays both ways in this rotation' : '';
    });

    Object.keys(counts).forEach(function (k) {
      var el = board.querySelector('[data-count="' + k + '"]');
      if (!el) return;
      el.textContent = counts[k].on + '/' + counts[k].of;
      el.classList.toggle('warn', counts[k].on < counts[k].of);
    });
    ['offense', 'defense'].forEach(function (side) {
      var pool = board.querySelector('.dc-pool[data-side="' + side + '"]');
      var el = board.querySelector('[data-count="' + side + '-bench"]');
      if (pool && el) el.textContent = String(all('.dc-chip', pool).length);
    });

    if (tally) {
      var open = 0;
      Object.keys(counts).forEach(function (k) { open += counts[k].of - counts[k].on; });
      var both = data.rotations.map(function (r) {
        var n = 0, m = seen[r] || {};
        Object.keys(m).forEach(function (name) { if (m[name] > 1) n++; });
        return r.charAt(0).toUpperCase() + r.slice(1) + ' ' + n;
      }).join(', ');
      tally.innerHTML = '<b>' + data.squad.length + '</b> on the squad &middot; '
        + (open
            ? '<span class="warn">' + open + (open === 1 ? ' spot' : ' spots') + ' open</span>'
            : 'every spot filled')
        + ' &middot; playing both ways: ' + both;
    }
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
    if (picked && slot && chip !== picked) {
      var held = picked;
      clearPick();
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
    ['offense', 'defense'].forEach(function (side) {
      var lists = out[side] || (out[side] = {});
      Object.keys(lists).forEach(function (pos) { lists[pos] = []; });
      var sec = board.querySelector('.dc-side[data-side="' + side + '"]');
      if (!sec) return;
      all('td.dc-cell', sec).forEach(function (td) {
        var at = data.rotations.indexOf(td.dataset.rot);
        if (at < 0) return;
        var list = lists[td.dataset.pos] || (lists[td.dataset.pos] = []);
        while (list.length < at) list.push('');
        // An empty Purple spot above a filled Gold one has to keep Gold at index 1,
        // so the hole is written as a blank rather than closed up.
        var chip = chipIn(td);
        list[at] = chip ? chip.dataset.name : '';
      });
      all('.dc-pool[data-side="' + side + '"] .dc-chip', sec).forEach(function (chip) {
        var list = lists[chip.dataset.home] || (lists[chip.dataset.home] = []);
        while (list.length < data.rotations.length) list.push('');
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
    return f"defense/cards/{front['id']}-field.svg"


def card_src(form: dict, play: dict, full: bool = False) -> str:
    suffix = "" if full else "-field"
    return f"playbook/{form['id']}/cards/{play['id']}{suffix}.svg"


def formation_icon_src(form: dict) -> str:
    return f"playbook/{form['id']}/cards/{form['id']}-icon.svg"


def defense_menu(defenses: dict, active_def: str) -> str:
    rows = "".join(
        f'<a class="mplay{" here" if fid == active_def else ""}" href="{d_href(f)}">'
        f'<span>{esc(f["call"])}</span><em>{esc(f["name"])}</em></a>'
        for fid, f in defenses.items()
    )
    return (
        f'<section class="mgrp">'
        f'<a class="mgh" href="defense.html">Fronts'
        f'<span class="mgn">{len(defenses)} legal</span></a>'
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


def play_article(form: dict, play: dict, heading: str = "h2", actions: str = "") -> str:
    """One play: diagram full width, assignments underneath, coaching points last."""
    rows = []
    for pos in ordered_positions(play):
        ball = " ball" if pos == play.get("ball_carrier") else ""
        rows.append(
            f'<div class="row{ball}"><dt>{esc(pos)}</dt>'
            f'<dd>{esc(play["assignments"][pos]["rule"])}</dd></div>'
        )

    tags = [f'<span class="call">{esc(play["call"])}</span>'] if play.get("call") else []
    for t in (play.get("type", "").upper(), play.get("ball_carrier", "")):
        if t:
            tags.append(f'<span class="tag">{esc(t)}</span>')
    if play.get("defense"):
        tags.append(f'<span class="tag">vs {esc(play["defense"])}</span>')

    coach = ""
    if play.get("coaching_points"):
        items = "\n    ".join(f"<li>{esc(c)}</li>" for c in play["coaching_points"])
        coach = (
            '<p class="block-title">Coaching points</p>\n'
            f'  <ul class="coach">\n    {items}\n  </ul>'
        )
    purpose = f'<p class="purpose">{esc(play["purpose"])}</p>' if play.get("purpose") else ""

    return f"""<article class="play" id="{esc(play['id'])}">
  <header>
    <{heading}>{esc(play['name'])}</{heading}>
    <div class="tags">{''.join(tags)}</div>
    {actions}
  </header>
  <figure class="diagram">
    <img src="{card_src(form, play)}" alt="{esc(play['name'])} diagram">
  </figure>
  {purpose}
  <p class="block-title">Assignments</p>
  <dl class="assign">
    {chr(10).join('    ' + r for r in rows).strip()}
  </dl>
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
        for f in defenses.values()
    )
    body = f"""<h1 class="page">The 2026 Playbook</h1>
<p class="lede">{_count(len(formations)).capitalize()} formations &middot; {total} plays
&middot; {_count(len(defenses))} fronts.</p>

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

    The Z's alignment goes the same way. A reverse starts him on the side its own
    direction comes back from, so the two halves of that pair disagree about where he
    lines up and one card cannot claim either — "Split Z Reverse", not "Split Z Left
    Z Reverse". Both sides are a click away on the card itself, named in full.
    """
    name = re.sub(r"\bZ (?:Right|Left)\s+", "", name)
    return re.sub(r"\s+(Right|Left)$", "", name)


def write_calls(formations: list[dict], defenses: dict, root: Path) -> str:
    plays_by_id = {p["id"]: (p, f) for f in formations for p in f["_plays"]}
    favorites = {}
    fav_path = root / "favorites.json"
    if fav_path.is_file():
        import json as _json
        favorites = _json.loads(fav_path.read_text(encoding="utf-8"))

    fav_cards = []
    for entry in favorites.get("plays", []):
        rp, rf = plays_by_id[entry["right"]]
        lp, _lf = plays_by_id[entry["left"]]
        fav_cards.append(
            f'<div class="favcard">'
            f'<a class="thumb" href="{p_href(rp)}" tabindex="-1">'
            f'<img loading="lazy" src="{card_src(rf, rp)}" '
            f'alt="{esc(strip_direction(rp["name"]))} diagram"></a>'
            f'<div class="body">'
            f'<h4><a href="{p_href(rp)}">{esc(strip_direction(rp["name"]))}</a></h4>'
            f'<span class="fmeta">{esc(form_label(rf))}</span>'
            f'<div class="sides">'
            f'<a class="side" href="{p_href(rp)}">Right</a>'
            f'<a class="side" href="{p_href(lp)}">Left</a>'
            f'</div></div></div>'
        )
    fav_section = ""
    if fav_cards:
        intro = esc(favorites.get("intro", ""))
        fav_section = f"""<p class="hero-head">Favorite Plays</p>
<p class="lede">{intro}</p>
<div class="favgrid" data-count="{len(fav_cards)}">
  {chr(10).join('  ' + c for c in fav_cards).strip()}
</div>

"""

    rows, carriers = [], []
    for f in formations:
        for p in f["_plays"]:
            zone, direction = call_digits(p.get("call", ""))
            carrier = p.get("ball_carrier", "")
            if carrier and carrier not in carriers:
                carriers.append(carrier)
            search = " ".join(
                str(x).lower()
                for x in (p["name"], p.get("call", ""), f["name"], f.get("family", ""),
                          p.get("type", ""), carrier, position_name(carrier), zone,
                          direction)
            )
            rows.append(
                f'<tr data-form="{esc(f["id"])}" data-type="{esc(p.get("type", ""))}" '
                f'data-zone="{esc(zone)}" data-dir="{esc(direction)}" '
                f'data-carrier="{esc(carrier)}" data-search="{esc(search)}">'
                f'<td class="c" data-label="Call">'
                f'<span class="call">{esc(p.get("call", ""))}</span></td>'
                f'<td data-label="Play"><a href="{p_href(p)}">{esc(p["name"])}</a></td>'
                f'<td data-label="Formation">{esc(form_label(f))}</td>'
                f'<td class="c" data-label="Type">{esc(p.get("type", ""))}</td>'
                f'<td class="c" data-label="Ball" '
                f'title="{esc(position_name(carrier))}">{esc(carrier or "—")}</td></tr>'
            )

    primary = (
        filter_group("Formation",
                     [chip("form", f["id"], form_label(f), "Formation")
                      for f in formations])
        + filter_group("Type", [chip("type", t, t.capitalize(), "Type")
                                for t in ("run", "pass")])
    )
    more = (
        filter_group("Where it hits",
                     [chip("zone", key, label, "Where") for key, label in HOLE_ZONES])
        + filter_group("Direction",
                       [chip("dir", d, d.capitalize(), "Direction")
                        for d in ("right", "left")])
        + filter_group("Who touches it",
                       [chip("carrier", c, c, "Ball", position_name(c))
                        for c in sorted(carriers, key=lambda k: (
                            CARD_ORDER.index(k) if k in CARD_ORDER else 99, k))])
    )

    body = f"""<h1 class="page">Call sheet</h1>
{fav_section}<p class="hero-head">All Plays</p>
<p class="lede">Every play in the book. Pick as many filters as you like — choices inside a
group widen the list, choices across groups narrow it. Press <kbd>/</kbd> to jump to the
search box.</p>
<div class="searchbar">
  <input id="q" type="search" placeholder="Search plays, calls, formations…"
         autocomplete="off" aria-label="Search plays">
</div>
{primary}
<button type="button" class="morebtn" id="morebtn" aria-expanded="false"
        aria-controls="morefilters">More filters<span class="badge" id="morebadge"
        hidden></span></button>
<div id="morefilters" hidden>{more}</div>
<div class="activefilters" id="activefilters" hidden></div>
<p class="countline"><span id="count"></span>
  <button type="button" class="clearbtn" id="clear" hidden>Clear filters</button></p>
<div class="tablewrap">
  <table class="calls" id="calls">
    <thead><tr>
      <th>Call</th><th>Play</th><th>Formation</th><th>Type</th><th>Ball</th>
    </tr></thead>
    <tbody>
      {chr(10).join('      ' + r for r in rows).strip()}
    </tbody>
  </table>
  <p class="empty" id="empty" hidden>No plays match those filters.</p>
</div>"""
    return page(
        f"Call sheet — {SITE_TITLE}",
        body,
        formations,
        defenses=defenses,
        active_nav="calls",
        description="Searchable list of every play and its huddle call.",
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
        + play_article(form, play, actions=actions) + "\n" + "\n".join(pager)
    )
    attrs = ""
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
        description=play.get("purpose", "")[:160],
        landscape=True,
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


def write_install(formations: list[dict], defenses: dict, root: Path) -> str:
    """The practice-by-practice install schedule.

    Numbered practices rather than dates: a rained-out session moves everything down
    one instead of skipping something. Built from install.json, whose ordering the
    generator has already checked — nothing here is taught before the play it is
    built on.
    """
    import json as _json
    path = root / "install.json"
    if not path.is_file():
        schedule = {"practices": []}
    else:
        schedule = _json.loads(path.read_text(encoding="utf-8"))

    plays = {p["id"]: (p, f) for f in formations for p in f["_plays"]}
    forms_by_id = {f["id"]: f for f in formations}
    phases = schedule.get("phases", {})

    total_plays = sum(len(pr.get("plays", [])) for pr in schedule["practices"])
    total_fronts = sum(len(pr.get("fronts", [])) for pr in schedule["practices"])
    preseason = [pr for pr in schedule["practices"] if pr.get("phase") == "preseason"]

    blocks, seen_phase = [], None
    for pr in schedule["practices"]:
        phase = pr.get("phase")
        if phase != seen_phase:
            seen_phase = phase
            meta = phases.get(phase, {})
            blocks.append(
                f'<div class="ph"><h2>{esc(meta.get("label", phase or ""))}</h2>'
                f'<p>{esc(meta.get("note", ""))}</p></div>'
            )
        items = []
        for pid in pr.get("plays", []):
            play, form = plays[pid]
            items.append(
                f'<a class="ins-play" href="{p_href(play)}">'
                f'<span class="ins-call">{esc(play.get("call", ""))}</span>'
                f'<span class="ins-name">{esc(play["name"])}</span></a>'
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
        if not items:
            items.append('<span class="ins-none">No new install &mdash; review</span>')

        need = pr.get("requires", [])
        needs = ""
        if need:
            names = ", ".join(esc(plays[n][0]["name"]) if n in plays
                              else esc(defenses[n]["call"]) for n in need)
            needs = f'<p class="ins-req">Needs {names} working first</p>'

        date = pr.get("date", "")
        date_html = f"<time>{esc(date)}</time>" if date else ""

        drills = pr.get("agility_drills", [])
        block_a_html = ""
        if drills:
            a_time = pr.get("agility_time", "")
            a_time_html = f'<span class="ins-blk-time">{esc(a_time)}</span>' if a_time else ""
            drill_items = "".join(f"<li>{esc(d)}</li>" for d in drills)
            block_a_html = (
                '<div class="ins-blk"><p class="ins-blk-h">'
                f'<span class="ins-blk-tag">Block A</span> Agility training{a_time_html}</p>'
                f'<ul class="ins-drills">{drill_items}</ul></div>'
            )

        b_time = pr.get("install_time", "")
        b_time_html = f'<span class="ins-blk-time">{esc(b_time)}</span>' if b_time else ""
        block_b_html = (
            '<div class="ins-blk"><p class="ins-blk-h">'
            f'<span class="ins-blk-tag">Block B</span> Install{b_time_html}</p>'
            f'<div class="ins-list">{"".join(items)}</div>'
            f'<p class="ins-em">{esc(pr.get("emphasis", ""))}</p>'
            f'{needs}</div>'
        )

        fin = pr.get("finisher", "")
        block_c_html = ""
        if fin:
            c_time = pr.get("finisher_time", "")
            c_time_html = f'<span class="ins-blk-time">{esc(c_time)}</span>' if c_time else ""
            block_c_html = (
                '<div class="ins-blk"><p class="ins-blk-h">'
                f'<span class="ins-blk-tag">Block C</span> Finisher{c_time_html}</p>'
                f'<p class="ins-em">{esc(fin)}</p></div>'
            )

        huddle = pr.get("huddle", "")
        huddle_html = ""
        if huddle:
            h_time = pr.get("huddle_time", "")
            h_time_html = f'<span class="ins-huddle-time">{esc(h_time)}</span>' if h_time else ""
            huddle_html = (
                f'<p class="ins-huddle"><b>Team huddle.</b> {esc(huddle)}{h_time_html}</p>'
            )

        blocks.append(
            f'<article class="ins">'
            f'<div class="ins-n"><span>Practice</span><b>{pr["n"]}</b>{date_html}</div>'
            f'<div class="ins-body"><h3>{esc(pr.get("focus", ""))}</h3>'
            f'{block_a_html}{block_b_html}{block_c_html}{huddle_html}</div></article>'
        )

    # Anything not on the schedule yet, so a play cannot go missing quietly.
    scheduled = {pid for pr in schedule["practices"] for pid in pr.get("plays", [])}
    todo = []
    for form in formations:
        rest = [p for p in form["_plays"] if p["id"] not in scheduled]
        if rest:
            links = "".join(
                f'<a class="ins-play" href="{p_href(p)}">'
                f'<span class="ins-call">{esc(p.get("call", ""))}</span>'
                f'<span class="ins-name">{esc(p["name"])}</span></a>' for p in rest)
            todo.append(f'<div class="ins-todo-grp"><h4>{esc(form_label(form))} '
                        f'<span>{len(rest)}</span></h4>'
                        f'<div class="ins-list">{links}</div></div>')
    scheduled_fronts = {fid for pr in schedule["practices"] for fid in pr.get("fronts", [])}
    rest_fronts = [f for fid, f in defenses.items() if fid not in scheduled_fronts]
    if rest_fronts:
        links = "".join(
            f'<a class="ins-play def" href="{d_href(f)}">'
            f'<span class="ins-call">{esc(f["call"])}</span>'
            f'<span class="ins-name">{esc(f["name"])} defence</span></a>' for f in rest_fronts)
        todo.append(f'<div class="ins-todo-grp"><h4>Defence '
                    f'<span>{len(rest_fronts)}</span></h4>'
                    f'<div class="ins-list">{links}</div></div>')

    todo_block = ""
    if todo:
        left = sum(1 for f in formations for p in f["_plays"] if p["id"] not in scheduled)
        front_word = "front" if len(rest_fronts) == 1 else "fronts"
        todo_block = (
            '<details class="ins-todo"><summary>Not scheduled yet'
            f'<span class="ins-todo-count">{left} plays &middot; {len(rest_fronts)} '
            f"{front_word}</span></summary>"
            "<p>Add them to <code>install.json</code> as you go &mdash; the build "
            "catches bad ordering.</p>"
            f'{"".join(todo)}</details>'
        )

    body = f"""<h1 class="page">Install schedule</h1>
<p class="lede">{esc(schedule.get("intro", ""))}</p>
<dl class="rb-facts">
  <div><dt>Practices planned</dt><dd>{len(schedule["practices"])}</dd></div>
  <div><dt>Plays scheduled</dt><dd>{total_plays} of {sum(len(f["_plays"]) for f in formations)}</dd></div>
  <div><dt>Fronts scheduled</dt><dd>{total_fronts} of {len(defenses)}</dd></div>
</dl>
<div class="ins-wrap">
{chr(10).join(blocks)}
{todo_block}
</div>"""
    return page(
        f"Install schedule — {SITE_TITLE}",
        body,
        formations,
        defenses=defenses,
        active_nav="install",
        description="Practice-by-practice install schedule for the playbook.",
    )


# The defense side has no shared position-name table the way offense does — those
# names are specific to the calling language (see common.POSITION_NAMES) and mixing
# defensive roles into that table would put "left end" in a place that answers a
# different question. Kept local to the depth chart, the only page that needs it.
DEFENSE_POSITION_NAMES = {
    "LE": "Left end", "LT": "Left tackle", "NT": "Nose tackle", "RT": "Right tackle",
    "RE": "Right end", "W": "Weak linebacker", "M": "Middle linebacker",
    "S": "Strong linebacker", "LC": "Left corner", "RC": "Right corner",
    "FS": "Free safety",
}


def depth_rows(order: list[str], names_by_pos: dict, label_fn) -> str:
    """A flat position/name list. The package block, and nothing else.

    The rotations outgrew this shape — see side_board — but a package is three
    spots that ride on the starting unit, and giving it Purple and Gold columns
    would claim it is a unit of its own.
    """
    rows = []
    for pos in order:
        names = names_by_pos.get(pos) or []
        if names:
            slots = "".join(
                f'<span class="dc-slot"><b>{i + 1}</b>{esc(n)}</span>'
                for i, n in enumerate(names)
            )
        else:
            slots = '<span class="dc-slot dc-open"><b>&mdash;</b>Open</span>'
        rows.append(
            f'<div class="dc-row"><div class="dc-pos">'
            f'<span class="dc-abbr">{esc(pos)}</span>'
            f'<span class="dc-label">{esc(label_fn(pos))}</span></div>'
            f'<div class="dc-slots">{slots}</div></div>'
        )
    return "".join(rows)


# The two rotations, in the order they take the field. Depth in roster.json *is*
# the rotation: the first name at a position is Purple, the second is Gold. One
# ordered list per position stays the thing a coach edits, and nobody has to keep
# two copies of the same roster agreeing with each other.
ROTATIONS = [
    ("Purple", "starters", "purple"),
    ("Gold", "second", "gold"),
]


def dc_chip(name: str, home: str) -> str:
    """One kid, one draggable name.

    A <button> rather than a <span> because everything a chip can do by drag it can
    also do by tap-then-tap, and a button is focusable, keyboard-operable and
    announced as interactive without a line of ARIA. draggable="false" is deliberate:
    the native HTML5 drag never fires on touch, and a coach uses this on a phone on a
    sideline — the pointer-event handler in site.js covers mouse and finger both, and
    the native one would only fight it.

    data-home is the position this name sits at in roster.json. A chip dragged to the
    bench has to know where it came from or the copied-out JSON cannot put it back.
    """
    return (f'<button type="button" class="dc-chip" draggable="false" '
            f'data-name="{esc(name)}" data-home="{esc(home)}">{esc(name)}</button>')


def side_board(side: str, order: list[str], alt_order: list[str],
               names_by_pos: dict, label_fn) -> str:
    """One side of the ball, both rotations, as columns of one grid.

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
        for idx, (rot_name, _note, rot_key) in enumerate(ROTATIONS):
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
        f'<th class="rot-th" data-rot="{rot_key}">{esc(rot_name)}'
        f'<span class="rot-count" data-count="{side}-{rot_key}"></span></th>'
        for rot_name, _note, rot_key in ROTATIONS
    )
    # Anybody sitting third or deeper at a position is in neither rotation. That used
    # to be a footnote at the bottom of the page; now it is the pile you drag out of,
    # so it sits under the board it feeds and says how deep it is.
    bench = "".join(
        dc_chip(name, pos)
        for pos in order
        for name in (names_by_pos.get(pos) or [])[len(ROTATIONS):]
    )
    return (
        f'<div class="tablewrap dc-board-wrap"><table class="dc-board">'
        f'<thead><tr><th>Position</th>{head}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
        f'<div class="dc-bench"><p class="rot-h">Bench'
        f'<span class="rot-count" data-count="{side}-bench"></span></p>'
        f'<div class="dc-pool" data-side="{side}" data-rot="bench">{bench}</div></div>'
    )


def write_depth_chart(formations: list[dict], defenses: dict, root: Path) -> str:
    roster = {}
    path = root / "roster.json"
    if path.is_file():
        import json as _json
        roster = _json.loads(path.read_text(encoding="utf-8"))

    front = defenses.get("5-3")
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

    def_label = lambda p: DEFENSE_POSITION_NAMES.get(p, p)  # noqa: E731

    # A package only lists the spots that change for it. The line is the same seven
    # kids no matter what the backfield is doing, so repeating them here would just
    # be the base chart again with extra steps. It rides with Purple: a package is
    # a situational swap on the starting unit, not a third rotation.
    pkg_blocks = []
    for pkg in roster.get("offense_packages", []):
        positions = pkg.get("positions", {})
        pkg_order = [p for p in off_order if p in positions]
        pkg_note = (f'<p class="pkg-note">{esc(pkg["note"])}</p>' if pkg.get("note") else "")
        pkg_blocks.append(
            f'<div class="pkg"><p class="pkg-name">{esc(pkg.get("name", ""))} package</p>'
            f'{pkg_note}<div class="dc-list">'
            f'{depth_rows(pkg_order, positions, position_name)}</div></div>'
        )
    packages_html = "".join(pkg_blocks)

    # One section per side of the ball, each carrying both rotations as columns. The
    # split used to be Purple sheet / Gold sheet with offense and defense side by
    # side inside; it is now offense sheet / defense sheet with Purple and Gold side
    # by side. Same two sheets either way, and this way the coordinator who only ever
    # looks at one side of the ball is handed exactly his page.
    sides = (
        ("offense", "Offense", off_order, alt_order, position_name,
         "The base formation's eleven.", packages_html),
        ("defense", "Defense", def_order, [], def_label,
         "The 5–3, our everyday front.", ""),
    )
    sections = []
    for side, heading, order, alts, label, sub, tail in sides:
        sections.append(
            f'<section class="dc-side" data-side="{side}">'
            f'<p class="hero-head">{esc(heading)}'
            f'<span class="rot-sub">{esc(sub)}</span></p>'
            f'{side_board(side, order, alts, roster.get(side, {}), label)}{tail}</section>'
        )

    # What the page knows that the board alone cannot say. The squad is every name
    # anywhere in the roster, so a kid benched on both sides is still countable; the
    # roster goes along whole so Copy can hand back a file with the note and the
    # package still in it rather than a board-shaped fragment of one.
    squad = sorted({name
                    for side in ("offense", "defense")
                    for names in roster.get(side, {}).values()
                    for name in (names or [])})
    import json as _json
    # A literal "</script>" inside the blob would close the tag early. Every "<" in
    # JSON is inside a string, so escaping it is lossless and the parser never sees
    # the difference — cheaper than trusting that no kid is ever nicknamed "<3".
    data = _json.dumps({"squad": squad, "roster": roster,
                        "rotations": [k for _n, _t, k in ROTATIONS]},
                       ensure_ascii=False).replace("<", "\\u003c")

    note = roster.get("note") or "Who plays where, one and two deep."
    # One side per sheet — see the .dc-side rules in the print stylesheet.
    body = f"""<h1 class="page">Depth Chart</h1>
<p class="lede dc-note">{esc(note)}</p>
<script type="application/json" id="dc-data">{data}</script>
<div class="dc-bar" id="dc-bar">
  <p class="dc-tally" id="dc-tally"></p>
  <div class="dc-tools">
    <button type="button" class="btn" id="dc-reset" hidden>Reset</button>
    <button type="button" class="btn" id="dc-copy">Copy roster.json</button>
    <button type="button" class="btn solid" onclick="window.print()">Print</button>
  </div>
</div>
<p class="dc-hint" id="dc-hint">Drag a name to another spot, or tap a name and then tap
where it goes. Edits are kept in this browser only — nobody else sees them, and
<b>Copy roster.json</b> hands back a file to paste into the repo.</p>
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
        description="Purple and Gold rotations — offense and defense, who plays where.",
        # Pin the margin so a side cannot be pushed onto a second sheet by a print
        # dialog set to wide margins. Same 9mm the play-card book uses. The paper size
        # is deliberately not pinned: whatever is in the tray, Letter or A4, both fit.
        page_rule="margin: 9mm;",
    )


def write_defense_index(formations: list[dict], defenses: dict) -> str:
    cards = []
    for fid, f in defenses.items():
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
<p class="lede">{_count(len(defenses)).capitalize()} fronts, each checked against the
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
        description=f"{_count(len(defenses)).capitalize()} legal defensive fronts for "
        "8U tackle, with assignments.",
    )


def write_defense_page(front: dict, formations: list[dict], defenses: dict) -> str:
    ids = list(defenses)
    i = ids.index(front["id"])
    prev = defenses[ids[i - 1]] if i else None
    nxt = defenses[ids[i + 1]] if i + 1 < len(ids) else None

    actions = ('<div class="play-actions">'
               '<button type="button" class="btn solid" onclick="window.print()">Print</button>'
               "</div>")
    siblings = "".join(
        f'<a href="{d_href(f)}"{ACTIVE_ATTR if fid == front["id"] else ""}>{esc(f["call"])}</a>'
        for fid, f in defenses.items()
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
    total = sum(len(f["_plays"]) for f in formations) + len(defenses)
    arts = [play_article(f, p) for f in formations for p in f["_plays"]]
    arts += [defense_article(d) for d in defenses.values()]
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

    for front in defenses.values():
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
