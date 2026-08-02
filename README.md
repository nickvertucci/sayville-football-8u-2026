# Sayville 8U Tackle Football — 2026

Playbook for 11-on-11 8U tackle. Every play is a JSON file; the diagrams, the printable
cards, the website and [PLAYBOOK.md](PLAYBOOK.md) are all generated from those files, so
there is one source of truth and no hand-drawn diagram that quietly goes stale.

**Website:** https://nickvertucci.github.io/sayville-football-8u-2026/ — mobile friendly,
and the Print button gives you the whole book in landscape, one play per sheet.

**In this repo:** [PLAYBOOK.md](PLAYBOOK.md) is the same book as markdown.
[RULES.md](RULES.md) is the league rules that shaped it — read that one first.
It is also published as a page on the site under **Rules**.

## Play calling language

Every play has two names, and both are printed on every card.

- The **name** is what you say while teaching it: *I Slant Right*.
- The **call** is what you yell on Saturday: `I Z Right 36 Slant`.

### I-Formation: formation + flanker + back + hole + play word

`Z Right` says where the flanker lines up. Then two digits: the first says
**who carries it**, the second says **where it goes**.

Every play in the book is `Z Right` today — the flanker never moves. It is named
in the call anyway so a `Z Left` look can be added later without changing how a
single play is called.

| Back | Who |
|---|---|
| **1** | Quarterback — both formations |
| **2** | Fullback — both formations |
| **3** | Tailback in the I · right halfback in the Wishbone |
| **4** | Left halfback — Wishbone only |

| Hole | Where |
|---|---|
| **0 / 1** | Between the center and the guard |
| **2 / 3** | Between the guard and the tackle |
| **4 / 5** | Between the tackle and the end |
| **6 / 7** | Outside the tight end |
| **8 / 9** | Wider still — all the way outside |

Even numbers go right (0, 2, 4, 6, 8), odd numbers go left (1, 3, 5, 7, 9), counting
outward from the center.

The holes are anchored to the linemen, not to abstract gaps, so a call tells you which
two blockers the ball is going between. Every play in the book is checked against this:
the generator measures where the ball carrier actually crosses the line of scrimmage and
it has to fall inside the hole its call names.

So `I Z Right 20 Dive` is flanker right, fullback, 0 hole; `I Z Right 21 Dive` is the
same handoff through the 1 hole; and `I Z Right 36 Slant` is the tailback outside the
tight end.

| Call | Play | Where it hits |
|---|---|---|
| `I Z Right 21 Dive` / `I Z Right 20 Dive` | I Dive Left / Right | center–guard |
| `I Z Right 33 Iso` / `I Z Right 32 Iso` | I Iso Left / Right | guard–tackle |
| `I Z Right 37 Slant` / `I Z Right 36 Slant` | I Slant Left / Right | outside the tight end |
| `I Z Right 39 Toss` / `I Z Right 38 Toss` | I Toss Left / Right | all the way outside |
| `I Z Right 35 Counter` | I Counter Left | tackle–end |
| `I Z Right 16 Boot` | I Boot Right | outside the tight end |

### Wishbone: formation + back + hole + play word

Same two digits, two more backs to number. No flanker, so nothing to declare there.

| Call | Play | Reads as |
|---|---|---|
| `Bone 21 Dive` / `Bone 20 Dive` | Bone Dive Left / Right | fullback, center–guard |
| `Bone 35 Power` / `Bone 44 Power` | Bone Power Left / Right | the far halfback, tackle–end |
| `Bone 39 Pitch` / `Bone 48 Pitch` | Bone Pitch Left / Right | the far halfback, all the way outside |
| `Bone 35 Counter` / `Bone 44 Counter` | Bone Counter Left / Right | the far halfback, tackle–end |

The back digit follows whoever actually carries it, which is why everything to the right is
a `4` — the *left* halfback takes the handoff on Power and Counter, and on Pitch he is the
trailing back who catches the ball. The near halfback is not idle on Pitch; he leads and
kicks out the edge, which is why the carrier is the far one.

**Play word** — `Dive`, `Iso`, `Slant`, `Toss`, `Counter`, `Boot` in the I;
`Dive`, `Power`, `Pitch`, `Counter` in the Wishbone.

## Formations

Two formations, 18 plays, in teaching order:

| # | Formation | Family | Plays | What it is for |
|---|---|---|---|---|
| 1 | **I** | I-Formation | 10 | Base offense. Fullback and tailback stacked, so the same look threatens the middle and both edges. Teaches a back to read a block. |
| 2 | **Wishbone** | Wishbone | 8 | Three backs, three threats every snap. Symmetric, so every play works both directions off identical rules. |

Both are two-tight-end, downhill running formations, so the blocking language carries
over: "block down on the first defender inside you" means the same thing in either one.
That is the reason to carry these two rather than two unrelated offenses.

## Defense

Four fronts, in `defense/`:

| Call | Front | When |
|---|---|---|
| **Base** | 5-3 | Most downs. Five down, three linebackers, a free safety behind. |
| **Goal Line** | 6-3 | Short yardage and inside the five. The heaviest front the league allows. |
| **Wide** | 4-4 | When they keep getting outside us. Trades a lineman for a fourth linebacker. |
| **Prevent** | 6-2-3 | Required by rule at an 18-point lead. Not a choice. |

**The generator refuses to publish an illegal front.** `render.py` checks every defense
against the league limits for 8- and 9-year-olds — at most six down linemen, at least
three linebackers, nobody in the second level closer than two yards — and fails the build
with an explicit error if one is violated. That check exists because getting it wrong is
not cosmetic: an illegal formation is a 15-yard unsportsmanlike penalty on the head coach
and a second one gets him ejected.


## The website

Not one long page — it is a real site, so you can get to a play in two taps and send
someone a link to exactly the play you mean.

| Page | What it is |
|---|---|
| `index.html` | Home: the formations, the install advice, the calling language |
| `calls.html` | **Call sheet** — every play, filter as you type, filter by formation or run/pass |
| `f-<formation>.html` | One formation: its notes and its plays |
| `rules.html` | The league rules, generated from `RULES.md` |
| `p-<play>.html` | One play. Deep-linkable, and prints to a single sheet |
| `defense.html` | The defensive playbook index |
| `d-<front>.html` | One defensive front, with every assignment |
| `print.html` | The whole book for printing |

On every page the diagram is the main attraction — full width of the card, edge to edge
on a phone, with the assignments read underneath it rather than squeezed in beside it.

## Printing

- **Print book** (top bar) → 22 landscape pages: 18 plays then 4 defensive fronts,
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

## Every offensive play is drawn and blocked against the 5-3

All fifteen plays are drawn against the **5-3**, and their assignments are written for
that front specifically rather than in general terms. Against a 5-3 our line is covered
like this:

| Us | Them |
|---|---|
| Center | nose, head up |
| **Both guards** | **uncovered** |
| Tackles | tackle on the inside shoulder |
| Ends | end, head up |

Two things follow, and they are why the assignments read the way they do:

- **"Block the man over you" is meaningless for a guard here.** Both guards are free, so
  they either help the center on the nose and climb to the middle linebacker, or they
  pull, or they cut off the backside.
- **The open gap is between our tackle and our end.** There is no down lineman in it,
  which is why every off-tackle play in the book — Power, Counter — aims there, and why
  the playside end releases inside to the linebacker instead of blocking down.

The 6-2, the most common front in youth football everywhere else, is **not legal in this
league** — it has only two linebackers, and the generator rejects it. See
[RULES.md](RULES.md).
