# Sayville 8U Tackle Football — 2026

Playbook for 11-on-11 8U tackle. Every play is a JSON file; the diagrams, the printable
cards, the website and [PLAYBOOK.md](PLAYBOOK.md) are all generated from those files, so
there is one source of truth and no hand-drawn diagram that quietly goes stale.

**Website:** https://nickvertucci.github.io/sayville-football-8u-2026/ — mobile friendly,
and the Print button gives you the whole book in landscape, one play per sheet.

**In this repo:** [PLAYBOOK.md](PLAYBOOK.md) is the same book as markdown.
[RULES.md](RULES.md) is our summary of the league rules that shaped it — read that one
first. It lives in the repo only; the site carries the league's actual rulebook, which is
in [rulebook/](rulebook/), reproduced word for word, as the **Rules** page.

## Play calling language

Every play has two names, and both are printed on every card.

- The **name** is what you say while teaching it: *I Slant Right*.
- The **call** is what you yell on Saturday: `I Z Right 36 Slant`.

### Regular I: formation + Z + back + hole + play word

The call names the formation, then `Z Right` — where the Z lines up — then two
digits: the first says **who carries it**, the second says **where it goes**. So
`Regular I Z Right 20 Dive` is the Regular I, Z on the right, the fullback through
the 0 hole.

Every play in the book is `Z Right` today — the Z never moves. It is named in the
call anyway so a `Z Left` look can be added later without changing how a single play
is called.

| Back | Who |
|---|---|
| **1** | Quarterback — every formation |
| **2** | The fullback in the I looks and the Full House; the left back (LH) in the Split Backs |
| **3** | The tailback (TB) — behind the fullback in the I, the right-side back in the Full House; the right back (RH) in the Split Backs |
| **4** | The Z — the flanker in the I and the Split Backs, in the backfield in the Power I, the left-side back in the Full House |

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
two blockers the ball is going between. **Every play in the book is checked against
this.** The generator resolves the first digit to a back the formation actually defines,
measures where that back's path crosses the line of scrimmage, and fails the build if he
does not cross on the named side inside the hole the call names. A call sheet that lies is
worse than no call sheet, so the build will not publish one.

The digits describe the back the first digit names, not the ball carrier. On
`Regular I Z Right 16 Boot` the `1` is the quarterback going through the 6 hole; the
ball carrier is the Z he throws to.

So `Regular I Z Right 20 Dive` is the fullback through the 0 hole; `21 Dive` is the same
handoff through the 1 hole; and `Regular I Z Right 36 Slant` is the tailback outside the
tight end.

| Call | Play | Where it hits |
|---|---|---|
| `Regular I Z Right 10 Sneak` / `11 Sneak` | Regular I Sneak Right / Left | quarterback, center–guard |
| `Regular I Z Right 20 Dive` / `21 Dive` | Regular I Dive Right / Left | fullback, center–guard |
| `Regular I Z Right 30 Wedge` / `31 Wedge` | Regular I Wedge Right / Left | tailback, up the middle |
| `Regular I Z Right 32 Iso` / `33 Iso` | Regular I Iso Right / Left | guard–tackle |
| `Regular I Z Right 34 Power` / `35 Power` | Regular I Power Right / Left | tailback, tackle–end |
| `Regular I Z Right 34 Counter` / `35 Counter` | Regular I Counter Right / Left | tailback, tackle–end |
| `Regular I Z Right 16 Boot` / `17 Boot` | Regular I Boot Right / Left | quarterback, outside the tight end |
| `Regular I Z Right 16 Waggle` / `17 Waggle` | Regular I Waggle Right / Left | quarterback, outside the tight end |
| `Regular I Z Right 16 Jet Boot` / `17 Jet Boot` | Regular I Jet Boot Right / Left | quarterback, off the Jet fake |
| `Regular I Z Right 16 Power Boot` / `17 Power Boot` | Regular I Power Boot Right / Left | quarterback, off the Power fake |
| `Regular I Z Right 36 Slant` / `37 Slant` | Regular I Slant Right / Left | outside the tight end |
| `Regular I Z Right 38 Toss` / `39 Toss` | Regular I Toss Right / Left | all the way outside |
| `Regular I Z Right 48 Jet` / `49 Jet` | Regular I Jet Right / Left | the Z in motion, all the way outside |

The plays are taught in that order on purpose — inside first and working out, and within
each gap the quarterback (back 1), then the fullback (2), then the tailback (3), then the
Z (4). Every play has a left and a right.

### Power I: formation + strength + back + hole + play word

The base I with the Z dropped off the line into the backfield, offset beside the
fullback as a third back. He is back **4**, though every Power I play today hands to the
tailback and uses the Z to lead or to fake.

**`Right`** or **`Left`** in the call is the strength — which side the Z is offset to —
the same way `Z Right` names his side in the base I. He leads that way on Power and Toss;
on Counter he sets to the strength and runs his lead path there while the ball goes back
the other way.

| Call | Play | Reads as |
|---|---|---|
| `Power I Right 34 Power` / `Power I Left 35 Power` | Power I Power Right / Left | tailback, tackle–end |
| `Power I Right 35 Counter` / `Power I Left 34 Counter` | Power I Counter Left / Right | tailback, back the other way |
| `Power I Left 46 Power` / `Power I Right 45 Power` | Power I Z Power Right / Left | the Z, away from his side behind three leads |
| `Power I Right 38 Toss` / `Power I Left 39 Toss` | Power I Toss Right / Left | tailback, all the way outside |

### Split Backs: formation + Z + back + hole + play word

Two backs to number instead of three, and a Z out wide to declare — so the call reads
like the Regular I's. `Split Z Right 24 Power` is the Split Backs, Z on the right, the
left back through the 4 hole. The two halfbacks are back **2** (LH, the left one) and
back **3** (RH, the right one); the Z out wide keeps **4**, the number he carries in
both I looks.

| Call | Play | Reads as |
|---|---|---|
| `Split Z Right 21 Dive` / `30 Dive` | Split Dive Left / Right | the near back, center–guard |
| `Split Z Right 35 Power` / `24 Power` | Split Power Left / Right | the far back, tackle–end |
| `Split Z Right 35 Counter` / `24 Counter` | Split Counter Left / Right | the far back, tackle–end |
| `Split Z Right 17 Waggle` / `16 Waggle` | Split Waggle Left / Right | quarterback, off the dive fake |
| `Split Z Right 39 Pitch` / `28 Pitch` | Split Pitch Left / Right | the far back, all the way outside |

The back digit follows whoever actually carries it. On Dive it is the back on the play
side, going straight ahead off the double team; on Power, Counter and Pitch it is the far
back, because the near one is busy leading through the hole or holding the linebackers
with a fake.

### Full House: formation + back + hole + play word

Three backs in a straight line, numbered the way the rest of the book numbers backs —
`2` fullback, `3` the right back (TB), `4` the left back (Z). A kid who knows the I's
numbers already knows `House` calls.

| Call | Play | Reads as |
|---|---|---|
| `House 21 Dive` / `House 20 Dive` | House Dive Left / Right | fullback, center–guard |
| `House 35 Power` / `House 44 Power` | House Power Left / Right | the far back, tackle–end |
| `House 39 Sweep` / `House 48 Sweep` | House Sweep Left / Right | the far back, all the way outside |
| `House 17 Boot` | House Boot Left | quarterback, off the Power fake |

Same rule as the Split Backs: the far back carries, because the near one is busy kicking
out the edge.

**Play word** — the Regular I carries `Dive`, `Iso`, `Slant`, `Toss`, `Counter`, `Sneak`,
`Power`, `Wedge` and `Jet`, plus the play-action `Boot`, `Waggle`, `Jet Boot` and
`Power Boot`; the Power I runs `Power`, `Counter` and `Toss`; the Split Backs `Dive`,
`Power`, `Counter`, `Pitch`; the Full House `Dive`, `Power`, `Sweep`. Every formation carries at
least one play-action pass, on the play word `Boot` or `Waggle`.

## Formations

Four formations, 52 plays, in teaching order:

| # | Formation | Family | Plays | What it is for |
|---|---|---|---|---|
| 1 | **Regular I** | Regular I | 26 | Base offense. Fullback and tailback stacked, so the same look threatens the middle and both edges. Teaches a back to read a block, and carries the Power, Wedge and Jet package built around the Z. |
| 2 | **Power I** | Power I | 8 | The base I with the Z dropped into the backfield as a third back — an extra runner and blocker at the point of attack. Power, Counter and Toss each way, plus a Z Power that hands the third back the ball and leads him the other way. |
| 3 | **Split Backs** | Split Backs | 10 | Two backs at even depth and a Z split out wide. One fewer back than a three-back look, and the receiver out there blocks the corner the pitch has to get around. |
| 4 | **Full House** | Full House | 8 | Three backs in a straight line at the same depth. The alignment gives nothing away, and every run splits the same three jobs — carry, kick out, lead. |

All four are two-tight-end, downhill running formations, so the blocking language carries
over: "block down on the first defender inside you" means the same thing in any of them.
That is the reason to carry these four rather than four unrelated offenses.

**Every pass is play-action, and run-first.** Each fakes one of that formation's best
runs and boots the quarterback the other way, so it is the same first three steps the
defense has already been punished for respecting. They exist so nobody can put nine in the
box and forget the edge — not to throw the ball. Every one says *run first, throw second*,
because no blitzing is allowed at this age (9.02) and the quarterback usually walks into
ten yards before anybody finds him. The Split Backs and Full House keep one each; the
Regular I, holding the most plays, carries several off the toss, the dive, the jet and the
power.

Two of them are nearly free to install. The **Power I** is the base I with the Z dropped into the backfield, so no line rule
changes at all. The **Full House** shares the Split Backs' carry/kick-out/lead division of
labour and adds a third back to it, so a team that knows `Split` calls is most of the way
to `House` calls.

**Symmetric formations author left-handed plays in one line.** The Full House is
mirror-symmetric, so `House 35 Power` is a four-line file that says
`"mirror_of": "fh-power-r"` — the generator flips every path, swaps the position keys and
swaps the left/right wording. The Regular I, the Power I and the Split Backs are *not*
symmetric (the Z sits right on every snap — out wide in the Regular I and the Split Backs,
in the backfield in the Power I), so their left-handed plays are written by hand. In the
Split Backs that is not busywork: the two sides are genuinely different plays, because
only the right one has a receiver out there to crack the linebacker or block the corner.

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
| `calls.html` | **Call sheet** — every play, searchable, filterable by formation, run/pass, where it hits, direction and who touches it |
| `f-<formation>.html` | One formation: its notes and its plays |
| `install.html` | **Install schedule** — practice by practice, generated from `install.json` |
| `rules.html` | **The league rulebook, verbatim**, generated from `rulebook/*.txt` |
| `p-<play>.html` | One play. Deep-linkable, and prints to a single sheet |
| `defense.html` | The defensive playbook index |
| `d-<front>.html` | One defensive front, with every assignment |
| `print.html` | The whole book for printing |

On every page the diagram is the main attraction — full width of the card, edge to edge
on a phone, with the assignments read underneath it rather than squeezed in beside it.

## Printing

- **Print book** (top bar) → 56 landscape pages: 52 plays then 4 defensive fronts,
  one per sheet.
- **Print** (on any play or front page) → that one card, one landscape sheet.

Both are already set to landscape, so there is no page setup to fiddle with. Print to PDF
for a binder, or print the single sheet you need for tonight's practice.

**A card that spills onto a second sheet is a bug**, and it is checked rather than
assumed — `generator/test_print_pages.py` renders the book and every play page with
headless Chrome and counts the pages in the PDF. Run it after anything that changes the
print layout or adds text to a card.

Each card is exactly one page box tall and lays itself out as a column: the header,
assignments and coaching points take the room they need and the diagram takes whatever is
left. A play with four coaching points therefore gets a bigger picture than one with five,
and no card can push past the page, because the only thing on it that can stretch is the
part that can afford to shrink.

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
python generator/test_calls.py        # prove the call check still rejects a wrong call
python generator/test_call_sheet.py   # prove the call sheet filters show the right plays
python generator/test_print_pages.py  # prove every card still prints on one sheet
python generator/test_rulebook.py     # prove the rules page still quotes the rulebook exactly
python generator/test_blocking.py     # prove every block is drawn to the right side of its man
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
install.json                          the practice-by-practice install schedule  <- source
defense/cards/*.svg                   generated
rulebook/*.docx                       the league's rulebook as published  <- source, gitignored
rulebook/*.txt, rulebook/media/       generated by generator/extract_rulebook.py
generator/render.py                   diagrams, cards, PLAYBOOK.md
generator/site_build.py               the website
generator/extract_rulebook.py         the rulebook .docx -> verbatim text
generator/common.py                   shared by both
*.html, assets/                       generated — the GitHub Pages site
PLAYBOOK.md                           generated
RULES.md                              our notes on the rules that constrain the playbook
```

Only the JSON under `playbook/` and `defense/` is source. Everything else with a `.html`, `.svg` or
`PLAYBOOK.md` name is rebuilt from it.

## Every offensive play is drawn and blocked against the 5-3

Forty-eight of the 52 plays are drawn against the **5-3**, and their assignments are
written for that front specifically rather than in general terms. The four exceptions are
the short-yardage plays — **Regular I Sneak** and **Regular I Wedge**, each way — drawn
against the **6-3** because that is the heaviest front the league allows and it is what
you actually see on fourth and one.

Against a 5-3 our line is covered like this:

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
