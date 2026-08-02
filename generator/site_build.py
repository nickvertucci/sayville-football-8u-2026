"""Builds the multi-page playbook website.

Structure — flat files at the repo root so every page can use the same relative paths
to the card SVGs, and so GitHub Pages can serve from "/" with no build step:

    index.html          home: formations, install plan, the calling language
    calls.html          the call sheet — every play, searchable, the fastest way in
    f-<formation>.html  one formation: its notes and its plays
    p-<play>.html       one play, deep-linkable, prints to a single landscape sheet
    print.html          the whole book, one play per landscape sheet
    assets/site.css     one stylesheet for all of it
    assets/site.js      play switcher, arrow-key paging, call sheet filtering

On every page the diagram is the main attraction: full width of its card, with the
assignments read underneath it rather than squeezed into a column beside it.
"""

from __future__ import annotations

import re
from pathlib import Path

from common import call_prefix, esc, form_label, ordered_positions

SITE_TITLE = "Sayville 8U Tackle Football"

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
#count { color: var(--muted); font-size: 14px; margin: 12px 0 10px; }
.tablewrap {
  overflow-x: auto; background: var(--panel); border: 1px solid var(--line);
  border-radius: 12px; box-shadow: var(--shadow);
}
table.calls { width: 100%; border-collapse: collapse; min-width: 540px; }
table.calls th, table.calls td {
  text-align: left; padding: 11px 14px; border-bottom: 1px solid var(--line-soft);
  font-size: 14.5px; color: var(--ink);
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
.prose { max-width: 76ch; }
.prose h2 {
  font-size: clamp(19px, 3.6vw, 24px); letter-spacing: -.3px; color: var(--ink);
  margin: 38px 0 10px; padding-bottom: 8px; border-bottom: 1px solid var(--line);
}
.prose h3 { font-size: 17px; color: var(--accent-ink); margin: 26px 0 8px; }
.prose p { margin: 0 0 13px; color: var(--ink-2); }
.prose ul { margin: 0 0 15px; padding-left: 20px; }
.prose li { margin-bottom: 7px; color: var(--ink-2); }
.prose a { color: var(--accent-ink); }
.prose code {
  font-size: .92em; background: var(--panel-2); border-radius: 4px; padding: 1px 6px;
}
.prose strong { color: var(--ink); }
/* Quoted rulebook text — the actual wording, set apart from our summary of it. */
.prose blockquote {
  margin: 0 0 16px; padding: 12px 16px; background: var(--panel);
  border-left: 4px solid var(--accent-solid); border-radius: 0 8px 8px 0;
  color: var(--ink); font-size: 15px; box-shadow: var(--shadow);
}
.prose .tablewrap { margin: 0 0 18px; }
table.rules { width: 100%; border-collapse: collapse; min-width: 380px; }
table.rules th, table.rules td {
  text-align: left; padding: 9px 14px; border-bottom: 1px solid var(--line-soft);
  font-size: 14.5px; color: var(--ink);
}
table.rules th {
  font-size: 11px; text-transform: uppercase; letter-spacing: 1.1px; color: var(--muted);
  background: var(--panel-2);
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
  .chips, #count, .section-head, .btn, .print-intro,
  .crumbs, .playbar { display: none !important; }
  :root {
    --ink: #111318; --ink-2: #333b49; --muted: #5b6472;
    --line: #dde1e8; --line-soft: #eef1f6; --panel: #fff; --accent-solid: #14213d;
    --accent-ink: #14213d; --red: #b3001b;
  }
  body { background: #fff; color: #000; font-size: 10pt; }
  .wrap { max-width: none; padding: 0; }
  main { padding: 0; }
  article.play {
    box-shadow: none; border: 0; border-radius: 0; padding: 0; margin: 0;
    page-break-after: always; break-after: page;
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
    border: 0; margin: 0 0 4px; height: 116mm;
    display: flex; align-items: center; justify-content: center;
  }
  figure.diagram img { width: auto; height: auto; max-width: 100%; max-height: 100%; }
  /* The purpose is why you'd call the play — useful when planning, not when holding
     the card on a sideline. Dropping it is what buys the diagram its height. */
  .purpose, .legalblock { display: none; }
  /* Defensive rules run longer than offensive ones, so their card gives
     the assignments a little more room and the diagram a little less. */
  article.play.def figure.diagram { height: 104mm; }
  .block-title { font-size: 8pt; margin: 5px 0 0; padding-top: 4px; }
  dl.assign { columns: 3; column-gap: 16px; }
  dl.assign .row {
    padding: 1px 0; grid-template-columns: 28px minmax(0,1fr); gap: 5px; border: 0;
  }
  dl.assign dd, dl.assign dt { font-size: 8pt; line-height: 1.32; }
  ul.coach { columns: 2; column-gap: 18px; margin-top: 3px; }
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

(function () {
  var q = document.getElementById('q');
  if (!q) return;
  var rows = Array.prototype.slice.call(document.querySelectorAll('#calls tbody tr'));
  var chips = Array.prototype.slice.call(document.querySelectorAll('.chip'));
  var count = document.getElementById('count');
  var empty = document.getElementById('empty');
  var filter = 'all';

  function apply() {
    var term = q.value.trim().toLowerCase();
    var n = 0;
    rows.forEach(function (r) {
      var okGroup = filter === 'all' || r.dataset.form === filter || r.dataset.type === filter;
      var okTerm = !term || r.dataset.search.indexOf(term) !== -1;
      var show = okGroup && okTerm;
      r.hidden = !show;
      if (show) n++;
    });
    count.textContent = n + (n === 1 ? ' play' : ' plays');
    empty.hidden = n !== 0;
  }

  q.addEventListener('input', apply);
  chips.forEach(function (c) {
    c.addEventListener('click', function () {
      chips.forEach(function (o) { o.setAttribute('aria-pressed', 'false'); });
      c.setAttribute('aria-pressed', 'true');
      filter = c.dataset.filter;
      apply();
    });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement !== q) { e.preventDefault(); q.focus(); }
    if (e.key === 'Escape' && document.activeElement === q) { q.value = ''; apply(); }
  });
  apply();
})();
"""

# ------------------------------------------------------------------- helpers --


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
        + link(*NAV_LINKS[1])
        + link(*NAV_LINKS[2])
        + link(*NAV_LINKS[3])
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
<link rel="stylesheet" href="assets/site.css">{page_style}
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
<script src="assets/site.js"></script>
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


# ------------------------------------------------------------------ markdown --


def _inline(s: str) -> str:
    """Bold, inline code and links — the only inline markup RULES.md uses."""
    out = esc(s)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    # Singles only — the bold pass above has already consumed every double.
    out = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)
    return out


def md_to_html(md: str) -> str:
    """Render the subset of Markdown RULES.md actually uses.

    RULES.md stays the single source — this page is generated from it the same way
    every other page is generated from the play files, so the two cannot drift.
    """
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            text = _inline(line.lstrip("#").strip())
            # The page supplies its own h1, so demote the document title.
            out.append(f"<h2>{text}</h2>" if level == 1 else f"<h{level}>{text}</h{level}>")
            i += 1
            continue

        if line.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip(">").strip())
                i += 1
            out.append("<blockquote>"
                       + "<br>".join(_inline(q) for q in quote if q)
                       + "</blockquote>")
            continue

        if line.lstrip().startswith(("- ", "* ")):
            items = []
            while i < len(lines) and lines[i].lstrip().startswith(("- ", "* ")):
                item = lines[i].lstrip()[2:]
                i += 1
                # A wrapped bullet continues on the next indented, non-bullet line.
                while (i < len(lines) and lines[i].strip()
                       and not lines[i].lstrip().startswith(("- ", "* ", "#", ">", "|"))):
                    item += " " + lines[i].strip()
                    i += 1
                items.append(f"<li>{_inline(item)}</li>")
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            body = ""
            if len(rows) >= 2 and set("".join(rows[1])) <= set("-: "):
                body += "<thead><tr>" + "".join(
                    f"<th>{_inline(c)}</th>" for c in rows[0]) + "</tr></thead>"
                rows = rows[2:]
            body += "<tbody>" + "".join(
                "<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>"
                for r in rows) + "</tbody>"
            out.append(f'<div class="tablewrap"><table class="rules">{body}</table></div>')
            continue

        para = []
        while (i < len(lines) and lines[i].strip()
               and not lines[i].startswith(("#", ">", "|"))
               and not lines[i].lstrip().startswith(("- ", "* "))):
            para.append(lines[i].strip())
            i += 1
        out.append("<p>" + _inline(" ".join(para)) + "</p>")

    return "\n".join(out)


def write_rules(formations: list[dict], defenses: dict, root: Path) -> str:
    src = (root / "RULES.md").read_text(encoding="utf-8")
    # The page supplies its own title, so drop the document's leading H1.
    if src.lstrip().startswith("# "):
        src = src.split(chr(10), 1)[1]
    body = f"""<h1 class="page">League rules</h1>
<p class="lede">What the league allows, what it forbids, and the two questions we have not
been able to answer from the document. Generated from <code>RULES.md</code> in the repo,
so the page and the source cannot drift apart.</p>
<div class="prose">
{md_to_html(src)}
</div>"""
    return page(
        f"League rules — {SITE_TITLE}",
        body,
        formations,
        defenses=defenses,
        active_nav="rules",
        description="The league rules that constrain this playbook, and the two questions "
                    "we have not resolved.",
    )


# --------------------------------------------------------------------- pages --

BACKS = [
    ("1", "Quarterback — both formations"),
    ("2", "Fullback — both formations"),
    ("3", "Tailback in the I &nbsp;·&nbsp; right halfback in the Wishbone"),
    ("4", "Left halfback — Wishbone only"),
]

HOLES = [
    ("1 / 2", "A gap — left / right of the center"),
    ("3 / 4", "B gap — between guard and tackle"),
    ("5 / 6", "Off tackle — outside the tackle"),
    ("7 / 8", "Outside — around the end"),
]


def write_home(formations: list[dict], defenses: dict) -> str:
    total = sum(len(f["_plays"]) for f in formations)
    cards = []
    for f in formations:
        blurb = f.get("summary") or f.get("notes", "")
        cards.append(
            f'<a class="fcard" href="{f_href(f)}">'
            f'<div class="ftop"><h3>{esc(form_label(f))}</h3>'
            f'<span class="n">{len(f["_plays"])} plays</span></div>'
            f"<p>{esc(blurb)}</p>"
            f'<span class="fcall">Calls start with '
            f'<code>{esc(call_prefix(f))}</code></span></a>'
        )
    defcards = "".join(
        f'<a class="fcard" href="{d_href(f)}">'
        f'<div class="ftop"><h3>{esc(f["call"])}</h3>'
        f'<span class="n">{esc(f["name"])}</span></div>'
        f'<p>{esc(f.get("summary", ""))}</p></a>'
        for f in defenses.values()
    )
    body = f"""<h1 class="page">The 2026 playbook</h1>
<p class="lede">Two offensive formations, {total} plays, three defensive fronts, built for
11-on-11 8U tackle. Every
diagram is generated from the play files in the repo — so what is on this site is
exactly what is in the binder.</p>
<p class="sub">Fastest way to find a play: the <a href="calls.html">call sheet</a>.</p>

<p class="section-head">Formations, in teaching order</p>
<div class="cards">
  {chr(10).join('  ' + c for c in cards).strip()}
</div>

<p class="section-head">Defensive playbook</p>
<p class="lede">Three fronts, each checked against the league rulebook by the generator:
a base for most downs, a goal-line front for when they have to have a yard, and a wider
front for when they keep getting outside us.</p>
<div class="cards">{defcards}</div>

<p class="section-head">How we call plays</p>
<p class="lede">Every play has a teaching name (<em>I Slant Right</em>) and a huddle call
(<code>I Z Right 36 Slant</code>). Both are printed on every card. In the I-formation
the call is <strong>formation + flanker + back + hole + play word</strong>. <code>Z Right</code> is where the flanker lines up, then the first number says who
carries it and the second says where it goes.</p>
<p class="lede"><strong>Who carries it</strong></p>
<dl class="assign holes">
  {chr(10).join(f'  <div class="row"><dt>{esc(n)}</dt><dd>{esc(d)}</dd></div>'
                for n, d in BACKS).strip()}
</dl>
<p class="lede"><strong>Where it goes</strong> — odd numbers to the left, even to the
right, counting outward from the center. This is the only part the kids have to
memorize.</p>
<dl class="assign holes">
  {chr(10).join(f'  <div class="row"><dt>{esc(n)}</dt><dd>{esc(d)}</dd></div>'
                for n, d in HOLES).strip()}
</dl>
<p class="lede">So <code>I Z Right 22 Dive</code> is flanker right, fullback, 2 hole,
and <code>I Z Right 36 Slant</code> is flanker right, tailback, off tackle right. A kid
who knows the two numbers can run a play the first time he hears it.</p>
<p class="sub">Every play in the book is <code>Z Right</code> today. It is in the call
anyway so a <code>Z Left</code> look can be added later without changing the language.</p>
<p class="sub">The Wishbone uses the same two digits — <code>Bone 22 Dive</code>,
<code>Bone 44 Power</code> — it just has two more backs to number.</p>

<p class="section-head">Before you install anything</p>
<div class="callout">
  <p>The league rulebook constrains this playbook in ways that matter: 8- and 9-year-olds
  face a <strong>minimum of three linebackers and no blitzing</strong>, which makes the
  6-2 illegal, and 8-year-olds may be placed in an <strong>8-man</strong> division where
  none of this is legal at all.</p>
  <p>Read
  <a href="rules.html">the rules page</a>
  first.</p>
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


def write_calls(formations: list[dict], defenses: dict) -> str:
    rows = []
    for f in formations:
        for p in f["_plays"]:
            search = " ".join(
                str(x).lower()
                for x in (p["name"], p.get("call", ""), f["name"], f.get("family", ""),
                          p.get("type", ""), p.get("ball_carrier", ""))
            )
            rows.append(
                f'<tr data-form="{esc(f["id"])}" data-type="{esc(p.get("type", ""))}" '
                f'data-search="{esc(search)}">'
                f'<td class="c"><span class="call">{esc(p.get("call", ""))}</span></td>'
                f'<td><a href="{p_href(p)}">{esc(p["name"])}</a></td>'
                f'<td>{esc(form_label(f))}</td>'
                f'<td class="c">{esc(p.get("type", ""))}</td>'
                f'<td class="c">{esc(p.get("ball_carrier", "—"))}</td></tr>'
            )
    chips = ['<button class="chip" data-filter="all" aria-pressed="true">All</button>']
    for f in formations:
        chips.append(
            f'<button class="chip" data-filter="{esc(f["id"])}" '
            f'aria-pressed="false">{esc(form_label(f))}</button>'
        )
    for t in ("run", "pass"):
        chips.append(
            f'<button class="chip" data-filter="{t}" aria-pressed="false">'
            f"{t.capitalize()}</button>"
        )

    body = f"""<h1 class="page">Call sheet</h1>
<p class="lede">Every play in the book. Type to filter by name, call, formation or ball
carrier — press <kbd>/</kbd> to jump to the search box.</p>
<div class="searchbar">
  <input id="q" type="search" placeholder="Search plays, calls, formations…"
         autocomplete="off" aria-label="Search plays">
</div>
<div class="chips">{''.join(chips)}</div>
<p id="count"></p>
<div class="tablewrap">
  <table class="calls" id="calls">
    <thead><tr>
      <th>Call</th><th>Play</th><th>Formation</th><th>Type</th><th>Ball</th>
    </tr></thead>
    <tbody>
      {chr(10).join('      ' + r for r in rows).strip()}
    </tbody>
  </table>
  <p class="empty" id="empty" hidden>No plays match that search.</p>
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
        f'<a href="{p_href(p)}"{" class=\"active\"" if p["id"] == play["id"] else ""}>'
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


def write_defense_index(formations: list[dict], defenses: dict) -> str:
    cards = []
    for fid, f in defenses.items():
        counts = {}
        for r in f.get("roles", {}).values():
            counts[r] = counts.get(r, 0) + 1
        cards.append(
            f'<a class="fcard" href="{d_href(f)}">'
            f'<div class="ftop"><h3>{esc(f["call"])}</h3>'
            f'<span class="n">{esc(f["name"])}</span></div>'
            f'<p>{esc(f.get("summary", ""))}</p>'
            f'<span class="fcall">{counts.get("DL", 0)} down &nbsp;&middot;&nbsp; '
            f'{counts.get("LB", 0)} linebackers &nbsp;&middot;&nbsp; '
            f'{counts.get("DB", 0)} defensive backs</span></a>'
        )
    body = f"""<h1 class="page">Defensive playbook</h1>
<p class="lede">Three fronts. One for most downs, one for when they have to have a yard,
and one for when they keep getting outside us. Every alignment here is checked against
the league rulebook by the generator &mdash; an illegal front fails the build.</p>

<p class="section-head">The fronts</p>
<div class="cards">{''.join(cards)}</div>

<p class="section-head">What the rulebook allows</p>
<div class="callout">
  <p>For 8- and 9-year-olds the league caps the defensive line at <strong>six</strong>,
  requires at least <strong>three linebackers</strong> no closer than <strong>two
  yards</strong>, and keeps defensive backs at <strong>two yards</strong> or deeper.</p>
  <p><strong>Blitzing is illegal at all times.</strong> No defender may move forward
  before the snap. Gap penetration after the snap is fine &mdash; that is not a blitz.</p>
  <p>Circumventing this is a 15-yard unsportsmanlike penalty on the head coach, and a
  second offense gets him ejected. Full detail in
  <a href="rules.html">the rules page</a>.</p>
</div>"""
    return page(
        f"Defensive playbook — {SITE_TITLE}",
        body,
        formations,
        defenses=defenses,
        active_nav="defense",
        description="Three legal defensive fronts for 8U tackle, with assignments.",
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
        f'<a href="{d_href(f)}"{' class=\"active\"' if fid == front["id"] else ""}>{esc(f["call"])}</a>'
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
    (root / "calls.html").write_text(write_calls(formations, defenses), encoding="utf-8")
    (root / "print.html").write_text(
        write_print_book(formations, defenses), encoding="utf-8")
    (root / "defense.html").write_text(
        write_defense_index(formations, defenses), encoding="utf-8")
    (root / "rules.html").write_text(
        write_rules(formations, defenses, root), encoding="utf-8")
    written += 5

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
