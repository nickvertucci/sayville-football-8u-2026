# Sayville 8U Tackle Football — 2026

Playbook for 11-on-11 8U tackle. Every play is a JSON file; the diagrams, the printable
cards, the website and [PLAYBOOK.md](PLAYBOOK.md) are all generated from those files, so
there is one source of truth and no hand-drawn diagram that quietly goes stale.

**Website:** https://nickvertucci.github.io/sayville-football-8u-2026/ — mobile friendly,
and the Print button gives you the whole book in landscape, one play per sheet.

**In this repo:** [PLAYBOOK.md](PLAYBOOK.md) is the same book as markdown.
[RULES.md](RULES.md) is the league rules that shaped it — read that one first.

## Play calling language

Every play has two names, and both are printed on every card.

- The **name** is what you say while teaching it: *Power Right*.
- The **call** is what you yell on Saturday: `I 6 Power`.

The call is always **formation + hole + play word**.

**Formation** — `I` for the I-formation, `Bone` for the wishbone.

**Hole** — odd numbers go left, even numbers go right, counting outward from the center.
This is the only thing the kids have to memorize:

```
        7   5   3   1   0   2   4   6   8
          E   T   G   C   G   T   E
   outside  off-  B   A     A   B  off-  outside
             tackle  gap   gap    tackle
```

**Play word** — `Dive`, `Iso`, `Power`, `Counter`, `Sweep`, `Pitch`, `Boot`. Seven words
covering fifteen plays, because the same word means the same thing in both formations.

So `Bone 8 Pitch` is the wishbone, outside right, pitch, and `I 4 Iso` is the
I-formation, right B gap, isolation — a kid who knows the system can line up and run
either one the first time he hears it. That is the whole point of having a language
instead of a list of nicknames.

## Formations

Two formations, 15 plays, in teaching order:

| # | Formation | Family | Plays | What it is for |
|---|---|---|---|---|
| 1 | **I** | I-Formation | 8 | Base offense. Fullback and tailback stacked, so the same look threatens the middle and both edges. Teaches a back to read a block. |
| 2 | **Wishbone** | Wishbone | 7 | Three backs, three threats every snap. Symmetric, so every play works both directions off identical rules. |

Both are two-tight-end, downhill running formations, so the blocking language carries
over: "block down on the first defender inside you" means the same thing in either one.
That is the reason to carry these two rather than two unrelated offenses.

## Defense

Three fronts, in `defense/`:

| Call | Front | When |
|---|---|---|
| **Base** | 5-3 | Most downs. Five down, three linebackers, a free safety behind. |
| **Goal Line** | 6-3 | Short yardage and inside the five. The heaviest front the league allows. |
| **Wide** | 4-4 | When they keep getting outside us. Trades a lineman for a fourth linebacker. |

**The generator refuses to publish an illegal front.** `render.py` checks every defense
against the league limits for 8- and 9-year-olds — at most six down linemen, at least
three linebackers, nobody in the second level closer than two yards — and fails the build
with an explicit error if one is violated. That check exists because getting it wrong is
not cosmetic: an illegal formation is a 15-yard unsportsmanlike penalty on the head coach
and a second one gets him ejected.

The install weeks on each play are within a formation, not across the whole book.

## The website

Not one long page — it is a real site, so you can get to a play in two taps and send
someone a link to exactly the play you mean.

| Page | What it is |
|---|---|
| `index.html` | Home: the formations, the install advice, the calling language |
| `calls.html` | **Call sheet** — every play, filter as you type, filter by formation or run/pass |
| `f-<formation>.html` | One formation: its notes, and its plays grouped by install week |
| `p-<play>.html` | One play. Deep-linkable, and prints to a single sheet |
| `defense.html` | The defensive playbook index |
| `d-<front>.html` | One defensive front, with every assignment |
| `print.html` | The whole book for printing |

On every page the diagram is the main attraction — full width of the card, edge to edge
on a phone, with the assignments read underneath it rather than squeezed in beside it.

## Printing

- **Print book** (top bar) → 18 landscape pages: 15 plays then 3 defensive fronts,
  one per sheet.
- **Print** (on any play or front page) → that one card, one landscape sheet.

Both are already set to landscape, so there is no page setup to fiddle with. Print to PDF
for a binder, or print the single sheet you need for tonight's practice. Page counts are
verified on every change by rendering to PDF and counting — a play that overflows onto a
second sheet is a bug.

The one thing the printed sheet drops is the play's "purpose" paragraph. That is context
for planning, not for holding on a sideline, and cutting it is what buys the diagram its
height. It is still on the website.

Individual cards are standalone SVGs under `playbook/<formation>/cards/` if you want to
drop one into a practice plan. Two versions of each:

- `<play>.svg` — the full card, name and call in the header, assignments printed on it.
- `<play>-field.svg` — the diagram alone, used by the website.

## Building

```
python generator/render.py            # rebuild cards, site, READMEs, PLAYBOOK.md
python generator/render.py --check    # validate the JSON only, write nothing
```

No dependencies beyond Python 3. `--check` fails if any play is missing an assignment for
any of the eleven positions, which is deliberate: a card with a blank spot on it is worse
than no card.

## Adding or changing plays

Edit the JSON under `playbook/`, then re-run the generator. Do not edit `PLAYBOOK.md`,
`index.html`, the `README.md` inside a formation folder, or anything in `cards/` — they
are overwritten on every build.

Full authoring rules, the coordinate system and the house style for writing assignments:
[playbook/CLAUDE.md](playbook/CLAUDE.md).

## Layout

```
playbook/<formation>/formation.json   the 11 alignment spots
playbook/<formation>/plays/*.json     one file per play          <- source
playbook/<formation>/cards/*.svg      generated
defense/<front>.json                  one file per defensive front   <- source
defense/cards/*.svg                   generated
generator/render.py                   diagrams, cards, PLAYBOOK.md
generator/site_build.py               the website
generator/common.py                   shared by both
*.html, assets/                       generated — the GitHub Pages site
PLAYBOOK.md                           generated
RULES.md                              league rules that constrain the playbook
```

Only the JSON under `playbook/` and `defense/` is source. Everything else with a `.html`, `.svg` or
`PLAYBOOK.md` name is rebuilt from it.

## A note on the defenses

Cards are drawn against whichever legal front is most useful for teaching that play. The
alignment on a card is a teaching aid, not a prediction — blocking rules are written by
leverage ("first defender inside you", "the man over you"), so they hold up against
whatever actually lines up across from us.

The 6-2, which is the most common front in youth football everywhere else, is **not legal
in this league** — it has only two linebackers. The generator rejects it. See
[RULES.md](RULES.md).
