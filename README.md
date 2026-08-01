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
- The **call** is what you yell on Saturday: `Tight 6 Power`.

The call is always **formation + hole + play word**.

**Formation** — `Tight`, `I`, `Wing`, `Pro`, `Bone`, `Ace`.

**Hole** — odd numbers go left, even numbers go right, counting outward from the center.
This is the only thing the kids have to memorize:

```
        7   5   3   1   0   2   4   6   8
          E   T   G   C   G   T   E
   outside  off-  B   A     A   B  off-  outside
             tackle  gap   gap    tackle
```

**Play word** — `Wedge`, `Power`, `Trap`, `Belly`, `Jet`, `Counter`, `Keep`, `Boot`,
`Dive`, `Iso`, `Sweep`, `Buck`, `Down`, `Waggle`, `Toss`, `Quick`, `Draw`, `Pitch`,
`Zone`, `Sneak`.

So `Bone 8 Pitch` is the wishbone, outside right, pitch play — and a kid who knows the
system can line up and run it the first time he hears it. That is the whole point of
having a language instead of a list of nicknames.

## Formations

Six formations, 47 plays, in teaching order:

| # | Formation | Family | Plays | What it is for |
|---|---|---|---|---|
| 1 | **Tight** | Double Wing | 18 | Base offense. Foot-to-foot splits, everything behind a double team or a kick-out. |
| 2 | **I** | I-Formation | 8 | Teaches a back to read a block instead of running to a spot. |
| 3 | **Wing-T** | Delaware Wing-T | 6 | A series offense — Buck Sweep, Trap and Waggle all start identically. |
| 4 | **Pro** | Pro Set | 5 | Two backs, receivers wide. Makes them defend the whole field. |
| 5 | **Wishbone** | Wishbone | 7 | Three backs, three threats, symmetric rules. |
| 6 | **Ace** | Single Back | 3 | Spread them out when they stack the box. |

### Please do not install all six

Forty-seven plays is a reference book, not a season plan. An 8U team that runs **Tight
plus one other formation** well will beat a team that runs six badly. The realistic use
of this repo is:

1. Install **Tight** weeks 1–4. That alone is a complete offense.
2. Pick **one** second formation based on what your kids actually do well — the I if you
   have one back clearly better than the rest, the Wing-T if your guards can pull, the
   Pro or Ace if you have someone who can throw.
3. Leave the rest here for next season.

The install weeks on each play are within a formation, not across the whole book.

## Printing

Open the website and hit **Print playbook** — it is already set to landscape, one play
per page, with the diagram on the left and the assignments and coaching points on the
right. Print to PDF and it is a binder.

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
playbook/<formation>/plays/*.json     one file per play
playbook/<formation>/cards/*.svg      generated
generator/render.py                   the generator
generator/defenses/*.json             6-3, 5-3 and 4-4 looks to draw plays against
index.html                            generated — the GitHub Pages site
PLAYBOOK.md                           generated
RULES.md                              league rules that constrain the playbook
```

## A note on the defenses

Cards are drawn against whichever legal front is most useful for teaching that play. The
alignment on a card is a teaching aid, not a prediction — blocking rules are written by
leverage ("first defender inside you", "the man over you"), so they hold up against
whatever actually lines up across from us.

The 6-2, which is the most common front in youth football everywhere else, is **not legal
in this league** — it has only two linebackers. See [RULES.md](RULES.md).
