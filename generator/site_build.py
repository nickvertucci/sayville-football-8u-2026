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

/* What is in the book but not yet on the schedule. Deliberately quieter than the
   practices above it — it is a backlog, not a plan. */
.ins-todo {
  margin: 34px 0 0; padding: 18px 18px 14px; border: 1px dashed var(--line);
  border-radius: 12px; background: var(--panel-2);
}
.ins-todo h2 { margin: 0 0 6px; font-size: 17px; color: var(--ink); }
.ins-todo > p { margin: 0 0 14px; font-size: 14px; color: var(--muted); max-width: 66ch; }
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
   two chips in the SAME group widens the list — Wishbone or Full House. Picking chips
   in DIFFERENT groups narrows it — Wishbone AND runs. The old single-string filter
   could not express that at all: formation and type shared one exclusive group, so
   "Wishbone runs" quietly turned into "all runs". */
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
             ("rules.html", "Rules", "rules"),
             ("print.html", "Print book", "print")]


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
        '\n<style>@page { size: landscape; margin: 9mm; }</style>' if landscape else ""
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
            # Wishbone. Name every formation, or the table quietly drops one.
            parts = []
            for pos, forms_with in spots.items():
                where = " and the ".join(esc(f) for f in forms_with)
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
    Right"."""
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
        fav_section = f"""<p class="section-head">Favorite Plays</p>
<p class="lede">{intro}</p>
<div class="favgrid">
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
{fav_section}<p class="section-head">All Plays</p>
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
        warm = pr.get("warmup", "")
        warm_html = f'<p class="ins-em"><b>Warm-up.</b> {esc(warm)}</p>' if warm else ""
        fin = pr.get("finisher", "")
        fin_html = f'<p class="ins-em"><b>Finisher.</b> {esc(fin)}</p>' if fin else ""
        blocks.append(
            f'<article class="ins">'
            f'<div class="ins-n"><span>Practice</span><b>{pr["n"]}</b>{date_html}</div>'
            f'<div class="ins-body"><h3>{esc(pr.get("focus", ""))}</h3>'
            f'{warm_html}'
            f'<div class="ins-list">{"".join(items)}</div>'
            f'<p class="ins-em">{esc(pr.get("emphasis", ""))}</p>'
            f'{fin_html}{needs}</div></article>'
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
        todo_block = (
            '<div class="ins-todo"><h2>Not scheduled yet</h2>'
            f'<p>{left} plays and {len(rest_fronts)} defensive front'
            f'{"" if len(rest_fronts) == 1 else "s"} are in the book but not on the '
            "schedule. Add them to <code>install.json</code> as you decide where they "
            "go &mdash; the build will tell you if one lands before something it needs.</p>"
            f'{"".join(todo)}</div>'
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
    written += 6

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
