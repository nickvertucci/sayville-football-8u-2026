"""Builds the multi-page playbook website.

Structure — flat files at the repo root so every page can use the same relative paths
to the card SVGs, and so GitHub Pages can serve from "/" with no build step:

    index.html          home: formations, install plan, the calling language
    calls.html          the call sheet — every play, searchable, the fastest way in
    f-<formation>.html  one formation: its notes and its plays
    p-<play>.html       one play, deep-linkable, prints to a single landscape sheet
    print.html          the whole book, one play per landscape sheet
    assets/site.css     one stylesheet for all of it
    assets/site.js      call sheet filtering

On every page the diagram is the main attraction: full width of its card, with the
assignments read underneath it rather than squeezed into a column beside it.
"""

from __future__ import annotations

from pathlib import Path

from common import esc, ordered_positions

SITE_TITLE = "Sayville 8U Tackle Football"

# --------------------------------------------------------------------------- css --

SITE_CSS = """
:root {
  --ink: #111318; --muted: #5b6472; --line: #e2e6ee;
  --navy: #14213d; --navy-2: #1d3059; --red: #b3001b;
  --bg: #eef1f5; --panel: #ffffff; --chip: #eef1f5; --chip-ink: #47506180;
}
@media (prefers-color-scheme: dark) {
  :root { --ink: #e8ecf3; --muted: #9aa4b6; --line: #262c3a; --bg: #0f1219; }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font: 16px/1.55 "Segoe UI", system-ui, -apple-system, Helvetica, Arial, sans-serif;
}
a { color: inherit; }
.wrap { max-width: 1040px; margin: 0 auto; padding: 0 18px; }

/* ---------------------------------------------------------------- navigation -- */
header.site {
  position: sticky; top: 0; z-index: 20; background: var(--navy); color: #fff;
  box-shadow: 0 1px 0 rgba(255,255,255,.08);
}
header.site .wrap {
  display: flex; align-items: center; gap: 12px; min-height: 54px; flex-wrap: wrap;
}
.brand {
  font-size: 17px; font-weight: 800; letter-spacing: -.3px;
  color: #fff; text-decoration: none; white-space: nowrap;
}
.brand span { font-weight: 500; color: #9db0d0; }
nav.primary { margin-left: auto; display: flex; gap: 6px; }
nav.primary a {
  font-size: 13.5px; font-weight: 600; color: #cdd8ea; text-decoration: none;
  padding: 6px 13px; border-radius: 999px; background: rgba(255,255,255,.09);
}
nav.primary a:hover { background: rgba(255,255,255,.2); color: #fff; }
nav.primary a.active { background: #fff; color: var(--navy); }

.formbar { background: var(--navy-2); overflow-x: auto; -webkit-overflow-scrolling: touch; }
.formbar .wrap {
  display: flex; gap: 6px; padding-top: 8px; padding-bottom: 8px; white-space: nowrap;
}
.formbar a {
  font-size: 13px; font-weight: 600; color: #c3d0e6; text-decoration: none;
  padding: 5px 12px; border-radius: 999px; background: rgba(255,255,255,.08);
}
.formbar a:hover { background: rgba(255,255,255,.18); color: #fff; }
.formbar a.active { background: #fff; color: var(--navy); }

main { padding-bottom: 60px; }
h1.page { font-size: clamp(24px, 5vw, 34px); letter-spacing: -.5px; margin: 26px 0 6px; }
.lede { color: var(--muted); max-width: 72ch; margin: 0 0 8px; }
.sub { color: var(--muted); font-size: 14px; margin: 0 0 22px; }
.section-head {
  font-size: 12px; text-transform: uppercase; letter-spacing: 1.4px; color: var(--muted);
  margin: 34px 0 12px; padding-bottom: 7px; border-bottom: 1px solid var(--line);
}

/* -------------------------------------------------------------------- pieces -- */
.callout {
  background: var(--panel); border-left: 4px solid var(--red); border-radius: 8px;
  padding: 14px 16px; margin: 20px 0; color: #2f3645; box-shadow: 0 1px 3px rgba(16,20,30,.1);
}
.callout strong { color: var(--navy); }
.callout p { margin: 0 0 8px; }
.callout p:last-child { margin: 0; }

.cards { display: grid; gap: 14px; grid-template-columns: 1fr; }
@media (min-width: 680px) { .cards { grid-template-columns: repeat(2, minmax(0,1fr)); } }
.fcard {
  display: block; text-decoration: none; color: #111318; background: var(--panel);
  border-radius: 11px; padding: 16px 17px; box-shadow: 0 1px 3px rgba(16,20,30,.14);
  border-top: 3px solid var(--navy); transition: box-shadow .15s, transform .15s;
}
.fcard:hover { box-shadow: 0 6px 18px rgba(16,20,30,.18); transform: translateY(-2px); }
.fcard h3 { margin: 0 0 2px; font-size: 19px; color: var(--navy); }
.fcard .fam { font-size: 12.5px; color: var(--muted); font-weight: 600;
  text-transform: uppercase; letter-spacing: .8px; }
.fcard p { margin: 9px 0 0; font-size: 14.5px; color: #3d4553; }
.fcard .n { float: right; font-size: 13px; font-weight: 700; color: var(--muted); }

.plist { display: grid; gap: 10px; grid-template-columns: 1fr; }
@media (min-width: 620px) { .plist { grid-template-columns: repeat(2, minmax(0,1fr)); } }
@media (min-width: 900px) { .plist { grid-template-columns: repeat(3, minmax(0,1fr)); } }
.pcard {
  display: block; text-decoration: none; color: #111318; background: var(--panel);
  border-radius: 10px; overflow: hidden; box-shadow: 0 1px 3px rgba(16,20,30,.14);
  transition: box-shadow .15s, transform .15s;
}
.pcard:hover { box-shadow: 0 6px 18px rgba(16,20,30,.18); transform: translateY(-2px); }
.pcard .thumb { background: #fff; border-bottom: 1px solid var(--line); }
.pcard .thumb img { display: block; width: 100%; height: auto; }
.pcard .body { padding: 10px 12px 12px; }
.pcard h4 { margin: 0 0 6px; font-size: 16px; color: var(--navy); }

.call {
  display: inline-block; font-size: 12.5px; font-weight: 700; letter-spacing: .4px;
  color: #fff; background: var(--navy); border-radius: 4px; padding: 3px 9px;
}
.tag {
  display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: .6px;
  color: #5b6472; background: var(--chip); border-radius: 4px; padding: 3px 7px;
}
.tags { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }

/* ---------------------------------------------------------------- the play -- */
article.play {
  background: var(--panel); color: #111318; border-radius: 12px; padding: 15px;
  box-shadow: 0 1px 3px rgba(16,20,30,.14); margin: 0 0 20px;
}
@media (min-width: 700px) { article.play { padding: 20px 22px; } }
article.play > header {
  display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap;
  border-bottom: 2px solid var(--navy); padding-bottom: 10px; margin-bottom: 14px;
}
article.play h2 { margin: 0; font-size: clamp(20px, 4.2vw, 26px); color: var(--navy); }

/* The picture is the main attraction: full width, nothing beside it. */
/* Edge to edge on a phone — the 15px card padding is worth more as diagram. */
figure.diagram {
  margin: 0 -15px 14px; background: #fff; border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line); overflow: hidden;
}
figure.diagram img { display: block; width: 100%; height: auto; }
@media (min-width: 700px) {
  figure.diagram { margin: 0 0 16px; border: 1px solid var(--line); border-radius: 9px; }
}

.purpose { margin: 0 0 4px; color: #333b49; font-size: 15.5px; max-width: 78ch; }
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
  padding: 7px 0; border-bottom: 1px solid #f0f2f6;
}
dl.assign dt { font-weight: 700; color: #111318; }
dl.assign dd { margin: 0; color: #1c2230; font-size: 15px; }
dl.assign .row.ball dt, dl.assign .row.ball dd { color: var(--red); font-weight: 600; }
dl.assign.holes { background: var(--panel); border-radius: 9px; padding: 4px 16px;
  box-shadow: 0 1px 3px rgba(16,20,30,.12); columns: 1; max-width: 520px; }
dl.assign.holes dt { color: var(--navy); }
ul.coach { margin: 6px 0 0; padding-left: 20px; }
ul.coach li { margin-bottom: 6px; color: #333b49; font-size: 15px;
  break-inside: avoid; page-break-inside: avoid; }

.btn {
  display: inline-block; cursor: pointer; font: inherit; font-size: 13.5px;
  font-weight: 600; color: var(--navy); background: #fff; border: 1px solid var(--line);
  border-radius: 999px; padding: 6px 15px; text-decoration: none; white-space: nowrap;
}
.btn:hover { background: var(--navy); border-color: var(--navy); color: #fff; }
.btn.solid { background: var(--navy); border-color: var(--navy); color: #fff; }
.btn.solid:hover { background: var(--navy-2); }
header.site .btn { margin-left: 0; }
.play-actions { margin-left: auto; display: flex; gap: 8px; }

.pager { display: flex; gap: 10px; justify-content: space-between; margin: 4px 0 30px; }
.pager a { font-size: 14px; font-weight: 600; color: var(--navy); text-decoration: none;
  background: var(--panel); border-radius: 8px; padding: 10px 14px;
  box-shadow: 0 1px 3px rgba(16,20,30,.12); max-width: 48%; }
.pager a:hover { box-shadow: 0 4px 12px rgba(16,20,30,.18); }
.pager .dir { display: block; font-size: 11px; text-transform: uppercase;
  letter-spacing: 1px; color: var(--muted); }

/* ------------------------------------------------------------- call sheet -- */
.searchbar { display: flex; gap: 10px; flex-wrap: wrap; align-items: center;
  margin: 4px 0 14px; }
#q {
  flex: 1 1 260px; font: inherit; font-size: 16px; padding: 10px 14px;
  border: 1px solid var(--line); border-radius: 999px; background: var(--panel);
  color: var(--ink); min-width: 0;
}
#q:focus { outline: 2px solid var(--navy); outline-offset: 1px; }
.chips { display: flex; gap: 6px; flex-wrap: wrap; }
.chip {
  cursor: pointer; font: inherit; font-size: 13px; font-weight: 600; color: #3d4553;
  background: var(--panel); border: 1px solid var(--line); border-radius: 999px;
  padding: 6px 13px;
}
.chip:hover { border-color: var(--navy); }
.chip[aria-pressed="true"] { background: var(--navy); border-color: var(--navy); color: #fff; }
#count { color: var(--muted); font-size: 14px; margin: 0 0 10px; }
.tablewrap { overflow-x: auto; background: var(--panel); border-radius: 10px;
  box-shadow: 0 1px 3px rgba(16,20,30,.14); }
table.calls { width: 100%; border-collapse: collapse; min-width: 560px; }
table.calls th, table.calls td { text-align: left; padding: 10px 14px;
  border-bottom: 1px solid #eef0f4; font-size: 14.5px; color: #1c2230; }
table.calls th { font-size: 11px; text-transform: uppercase; letter-spacing: 1.1px;
  color: var(--muted); background: #f7f8fb; position: sticky; top: 0; }
table.calls tbody tr:hover { background: #f5f7fb; }
table.calls a { color: var(--navy); font-weight: 600; text-decoration: none; }
table.calls a:hover { text-decoration: underline; }
table.calls td.c { white-space: nowrap; }
.empty { padding: 26px 16px; color: var(--muted); }

footer.site { color: var(--muted); font-size: 13.5px; border-top: 1px solid var(--line);
  margin-top: 40px; padding: 18px 0 40px; }
footer.site code { background: rgba(127,127,127,.16); padding: 1px 5px; border-radius: 3px; }
footer.site a { color: var(--navy); }

/* -------------------------------------------------------------------- print -- */
@media print {
  header.site, .formbar, footer.site, .pager, .play-actions, .searchbar,
  .chips, #count, .section-head, .btn, .print-intro { display: none !important; }
  body { background: #fff; color: #000; font-size: 10pt; }
  .wrap { max-width: none; padding: 0; }
  main { padding: 0; }
  article.play {
    box-shadow: none; border-radius: 0; padding: 0; margin: 0;
    page-break-after: always; break-after: page;
  }
  article.play:last-of-type { page-break-after: auto; break-after: auto; }
  article.play > header { padding-bottom: 5px; margin-bottom: 8px; }
  article.play h2 { font-size: 16pt; }
  .call, .tag { font-size: 8.5pt; padding: 2px 6px; }
  /* Picture leads. The figure is pinned to a fixed height with the diagram centred
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
  .purpose { display: none; }
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


def card_src(form: dict, play: dict, full: bool = False) -> str:
    suffix = "" if full else "-field"
    return f"playbook/{form['id']}/cards/{play['id']}{suffix}.svg"


def page(
    title: str,
    body: str,
    formations: list[dict],
    active_nav: str = "",
    active_form: str = "",
    description: str = "",
    landscape: bool = False,
    show_formbar: bool = True,
) -> str:
    nav_items = [("index.html", "Home", "home"),
                 ("calls.html", "Call sheet", "calls"),
                 ("print.html", "Print book", "print")]
    nav = "\n      ".join(
        f'<a href="{href}"{" class=\"active\"" if key == active_nav else ""}>{esc(label)}</a>'
        for href, label, key in nav_items
    )
    formbar = ""
    if show_formbar:
        pills = "\n      ".join(
            f'<a href="{f_href(f)}"'
            f'{" class=\"active\"" if f["id"] == active_form else ""}>{esc(f["name"])}</a>'
            for f in formations
        )
        formbar = f'<div class="formbar"><div class="wrap">\n      {pills}\n    </div></div>'

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
<header class="site"><div class="wrap">
  <a class="brand" href="index.html">Sayville 8U <span>Playbook</span></a>
  <nav class="primary">
      {nav}
  </nav>
</div></header>
{formbar}
<main><div class="wrap">
{body}
</div></main>
<footer class="site"><div class="wrap">
  Generated by <code>generator/render.py</code> — edit the JSON under
  <code>playbook/</code>, never these pages.
  <a href="https://github.com/nickvertucci/sayville-football-8u-2026">Source</a>
</div></footer>
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


# --------------------------------------------------------------------- pages --

HOLES = [
    ("0", "Straight up the middle"),
    ("1 / 2", "A gap — left / right of the center"),
    ("3 / 4", "B gap — between guard and tackle"),
    ("5 / 6", "Off tackle — outside the tackle"),
    ("7 / 8", "Outside — around the end"),
]


def write_home(formations: list[dict]) -> str:
    total = sum(len(f["_plays"]) for f in formations)
    cards = []
    for f in formations:
        blurb = f.get("summary") or f.get("notes", "")
        cards.append(
            f'<a class="fcard" href="{f_href(f)}">'
            f'<span class="n">{len(f["_plays"])} plays</span>'
            f'<div class="fam">{esc(f.get("family", ""))}</div>'
            f'<h3>{esc(f["name"])}</h3>'
            f"<p>{esc(blurb)}</p></a>"
        )
    body = f"""<h1 class="page">The 2026 playbook</h1>
<p class="lede">{total} plays across {len(formations)} formations, every diagram generated
from the play files in the repo — so what is on this site is exactly what is in the
binder. Built for 11-on-11 8U tackle.</p>
<p class="sub">Fastest way to find a play: the <a href="calls.html">call sheet</a>.</p>

<p class="section-head">Formations, in teaching order</p>
<div class="cards">
  {chr(10).join('  ' + c for c in cards).strip()}
</div>

<p class="section-head">How we call plays</p>
<p class="lede">Every play has a teaching name (<em>Power Right</em>) and a huddle call
(<code>Tight 6 Power</code>). Both are printed on every card. The call is always
<strong>formation + hole + play word</strong>, and the hole numbers are the only thing the
kids have to memorize — odd to the left, even to the right, counting outward.</p>
<dl class="assign holes">
  {chr(10).join(f'  <div class="row"><dt>{esc(n)}</dt><dd>{esc(d)}</dd></div>'
                for n, d in HOLES).strip()}
</dl>
<p class="lede">So <code>Bone 8 Pitch</code> is the wishbone, outside right, pitch — and a
kid who knows the system can run it the first time he hears it.</p>

<p class="section-head">Before you install anything</p>
<div class="callout">
  <p>The league rulebook constrains this playbook in ways that matter: 8- and 9-year-olds
  face a <strong>minimum of three linebackers and no blitzing</strong>, which makes the
  6-2 illegal, and 8-year-olds may be placed in an <strong>8-man</strong> division where
  none of this is legal at all.</p>
  <p>Read
  <a href="https://github.com/nickvertucci/sayville-football-8u-2026/blob/main/RULES.md">RULES.md</a>
  first.</p>
</div>"""
    return page(
        f"{SITE_TITLE} — 2026 Playbook",
        body,
        formations,
        active_nav="home",
        description=f"{total} plays across {len(formations)} formations for 11-on-11 8U "
        "tackle football, with diagrams, assignments and coaching points.",
    )


def write_calls(formations: list[dict]) -> str:
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
                f'<td>{esc(f["name"])}</td>'
                f'<td class="c">{esc(p.get("type", ""))}</td>'
                f'<td class="c">{esc(p.get("ball_carrier", "—"))}</td>'
                f'<td class="c">{esc(p.get("install_week", "—"))}</td></tr>'
            )
    chips = ['<button class="chip" data-filter="all" aria-pressed="true">All</button>']
    for f in formations:
        chips.append(
            f'<button class="chip" data-filter="{esc(f["id"])}" '
            f'aria-pressed="false">{esc(f["name"])}</button>'
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
      <th>Call</th><th>Play</th><th>Formation</th><th>Type</th><th>Ball</th><th>Wk</th>
    </tr></thead>
    <tbody>
      {chr(10).join('      ' + r for r in rows).strip()}
    </tbody>
  </table>
  <p class="empty" id="empty" hidden>No plays match that search.</p>
</div>
<script src="assets/site.js"></script>"""
    return page(
        f"Call sheet — {SITE_TITLE}",
        body,
        formations,
        active_nav="calls",
        description="Searchable list of every play and its huddle call.",
    )


def write_formation_page(form: dict, formations: list[dict]) -> str:
    weeks: dict[int, list] = {}
    for p in form["_plays"]:
        weeks.setdefault(p.get("install_week", 99), []).append(p)

    blocks = []
    for w in sorted(weeks):
        label = f"Week {w}" if w != 99 else "Unscheduled"
        cards = []
        for p in weeks[w]:
            cards.append(
                f'<a class="pcard" href="{p_href(p)}">'
                f'<div class="thumb"><img loading="lazy" src="{card_src(form, p)}" '
                f'alt="{esc(p["name"])} diagram"></div>'
                f'<div class="body"><h4>{esc(p["name"])}</h4>'
                f'<span class="call">{esc(p.get("call", ""))}</span></div></a>'
            )
        blocks.append(
            f'<p class="section-head">{esc(label)}</p>\n'
            f'<div class="plist">\n  {chr(10).join("  " + c for c in cards).strip()}\n</div>'
        )

    notes = ""
    if form.get("coaching_notes"):
        items = "\n    ".join(f"<li>{esc(c)}</li>" for c in form["coaching_notes"])
        notes = (
            '<p class="section-head">Coaching notes</p>\n'
            f'<ul class="coach">\n    {items}\n  </ul>'
        )

    body = f"""<h1 class="page">{esc(form['name'])}</h1>
<p class="sub">{esc(form.get('family', ''))} &nbsp;·&nbsp; {len(form['_plays'])} plays
&nbsp;·&nbsp; {esc(form.get('personnel', ''))}</p>
<p class="lede">{esc(form.get('notes', ''))}</p>
{notes}
{chr(10).join(blocks)}"""
    return page(
        f"{form['name']} — {SITE_TITLE}",
        body,
        formations,
        active_form=form["id"],
        description=form.get("notes", "")[:160],
    )


def write_play_page(
    form: dict, play: dict, prev: dict | None, nxt: dict | None, formations: list[dict]
) -> str:
    actions = (
        '<div class="play-actions">'
        f'<a class="btn" href="{f_href(form)}">All {esc(form["name"])} plays</a>'
        '<button type="button" class="btn solid" onclick="window.print()">Print</button>'
        "</div>"
    )
    pager = ['<div class="pager">']
    if prev:
        pager.append(
            f'<a href="{p_href(prev)}"><span class="dir">Previous</span>'
            f'{esc(prev["name"])}</a>'
        )
    else:
        pager.append("<span></span>")
    if nxt:
        pager.append(
            f'<a href="{p_href(nxt)}" style="text-align:right">'
            f'<span class="dir">Next</span>{esc(nxt["name"])}</a>'
        )
    else:
        pager.append("<span></span>")
    pager.append("</div>")

    body = play_article(form, play, actions=actions) + "\n" + "\n".join(pager)
    return page(
        f"{play['name']} ({play.get('call', '')}) — {SITE_TITLE}",
        body,
        formations,
        active_form=form["id"],
        description=play.get("purpose", "")[:160],
        landscape=True,
    )


def write_print_book(formations: list[dict]) -> str:
    total = sum(len(f["_plays"]) for f in formations)
    arts = [
        play_article(f, p) for f in formations for p in f["_plays"]
    ]
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
        active_nav="print",
        description=f"All {total} plays formatted one per landscape page.",
        landscape=True,
        show_formbar=False,
    )


# ---------------------------------------------------------------------- entry --


def write_all(formations: list[dict], root: Path) -> int:
    assets = root / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "site.css").write_text(SITE_CSS.strip() + "\n", encoding="utf-8")
    (assets / "site.js").write_text(SITE_JS.strip() + "\n", encoding="utf-8")

    written = 0
    (root / "index.html").write_text(write_home(formations), encoding="utf-8")
    (root / "calls.html").write_text(write_calls(formations), encoding="utf-8")
    (root / "print.html").write_text(write_print_book(formations), encoding="utf-8")
    written += 3

    for form in formations:
        (root / f_href(form)).write_text(
            write_formation_page(form, formations), encoding="utf-8"
        )
        written += 1
        plays = form["_plays"]
        for i, play in enumerate(plays):
            prev = plays[i - 1] if i else None
            nxt = plays[i + 1] if i + 1 < len(plays) else None
            (root / p_href(play)).write_text(
                write_play_page(form, play, prev, nxt, formations), encoding="utf-8"
            )
            written += 1
    return written
