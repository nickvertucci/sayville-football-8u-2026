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

Every play is named the same way it is called. The **name** on the card is
`{formation} - Slot {Left|Right} - {digits} {word}`; the **call** is that same language
without the dashes, what you yell on Saturday.

### Regular I: formation + Slot + back + hole + play word

The call names the formation, then `Slot Right` — where the slot lines up — then two
digits: the first says **who carries it**, the second says **where it goes**. So
`Regular I Slot Right 36 Power` is the Regular I, slot on the right, the tailback between the
tackle and the tight end.

Off tackle depends on the slot's kick-out block, so he lines up on the side it
has to happen: `Regular I Slot Left 37 Power` puts him on the left. The call says so out
loud, because a play that moves somebody silently is a play nobody can call.

| Back | Who |
|---|---|
| **1** | Quarterback — every formation |
| **2** | The fullback in the Regular I; the right back (RH) in the Split Backs and Shotgun — even-numbered holes |
| **3** | The tailback (TB) in the Regular I; the left back (LH) in the Split Backs and Shotgun — odd-numbered holes |
| **4** | The slot, split wide in every formation |

| Hole | Word | Where |
|---|---|---|
| **0** | Smash | Straight over the center |
| **2 / 3** | Smash | Between the center and the guard |
| **4 / 5** | Dive | Between the guard and the tackle |
| **6 / 7** | Power | Between the tackle and the tight end |
| **8 / 9** | Toss | Outside the tight end |

```
   9  |  7  |  5  |  3  | 0 |  2  |  4  |  6  |  8
     LTE    LT    LG     C     RG    RT   RTE
```

**0 is the middle.** From there the holes count outward, even to the right (2, 4, 6, 8)
and odd to the left (3, 5, 7, 9) — one number per gap in the line, and one for the
center himself. **There is no 1 hole**: the middle is one place, not two, and a number
that names the same place twice is a number nobody can call. The build rejects a call
that says 1.

The holes are anchored to the linemen, not to abstract gaps, so a call tells you which
two blockers the ball is going between. **Every play in the book is checked against
this.** The generator resolves the first digit to a back the formation actually defines,
measures where that back's path crosses the line of scrimmage, and fails the build if he
does not cross on the named side inside the hole the call names. A call sheet that lies is
worse than no call sheet, so the build will not publish one.

The digits describe the back the first digit names, not necessarily the ball carrier. So
`Regular I Slot Right 36 Power` is the tailback between the right tackle and tight end,
and `Regular I Slot Left 37 Power` is the same handoff to the left.

| Call | Play | Where it hits |
|---|---|---|
| `Regular I Slot Right 36 Power` / `Slot Left 37 Power` | Regular I - Slot Right - 36 Power / Slot Left - 37 Power | tailback, tackle–tight end |
| `Regular I Slot Right 32 Smash` / `Slot Left 33 Smash` | Regular I - Slot Right - 32 Smash / Slot Left - 33 Smash | tailback, A gap, fullback leading |
| `Regular I Slot Right 22 Smash` / `Slot Left 23 Smash` | Regular I - Slot Right - 22 Smash / Slot Left - 23 Smash | fullback, A gap, on the snap |
| `Regular I Slot Right LTE Sweep` / `Slot Left RTE Sweep` | Regular I - Slot Right - LTE Sweep / Slot Left - RTE Sweep | the backside tight end on an end-around, all the way outside |
| `Regular I Slot Right 49 Sweep` / `Slot Left 48 Sweep` | Regular I - Slot Right - 49 Sweep / Slot Left - 48 Sweep | the slot, flat across the backfield and outside the other way |

The tight-end sweep is a **word call** — no digits, because the tight end is not a numbered
back. It names him instead. A play has to opt in with `word_call`, so any other play
missing its number still fails the build.

Every play has a left and a right.

### Split Backs: formation + Slot + back + hole + play word

Two backs to number instead of three, and a slot out wide to declare — so the call reads
like the Regular I's. `Split Backs Slot Right 38 Toss` is the Split Backs, slot on the right, the
3-back (left halfback) all the way outside at the 8 hole. In this formation the **3-back is
always the left back** (odd-numbered holes) and the **2-back is always the right back**
(even-numbered holes); the slot out wide keeps **4**, the number he carries in every look.

| Call | Play | Reads as |
|---|---|---|
| `Split Backs Slot Left 29 Toss` / `Slot Right 38 Toss` | Split Backs - Slot Left - 29 Toss / Slot Right - 38 Toss | the far back, all the way outside |

The back digit follows whoever actually carries it. On the toss it is the far back,
because the near one is busy bubbling out to block.

### Shotgun: formation + Slot + who catches it + route

The Shotgun's pass names its receiver the way the tight-end sweep names its runner — the
tight end is not a numbered back, so it is a word call. Its halfbacks number the same way
the Split Backs do: 3 is left, 2 is right.

| Call | Play | Reads as |
|---|---|---|
| `Shotgun Slot Right RTE Slant Out` / `Slot Left LTE Slant Out` | Shotgun - Slot Right - RTE Slant Out / Slot Left - LTE Slant Out | the play-side tight end, a flat slant out almost on the line of scrimmage |
| `Shotgun Slot Left 19 Sweep` / `Slot Right 18 Sweep` | Shotgun - Slot Left - 19 Sweep / Slot Right - 18 Sweep | the quarterback, all the way outside behind the near halfback |
| `Shotgun Slot Left 29 Toss` / `Slot Right 38 Toss` | Shotgun - Slot Left - 29 Toss / Slot Right - 38 Toss | the far halfback, across in front of the quarterback and all the way outside |

**Play word** — a numbered run's word is the hole: Smash at 0 and 2/3, Dive at 4/5,
Power at 6/7, Toss at 8/9.
**Sweep** is the quarterback (`18` / `19`) or the slot coming across at 8/9,
or a tight end on an end-around (a word call, no hole digit). Digit 4 is the
slot only in looks that have one — Wishbone's 4 is the right halfback, so
`49 Toss` is Toss. The tight-end `Slant Out` is a word call too.

### Wishbone: formation + back + hole + play word

Three backs and no slot, so the call drops Slot Right/Left. `Wishbone 22 Smash`
is the fullback between the center and the right guard. `46 Power` is the right
halfback off tackle; `38 Toss` is the left halfback all the way outside.

| Call | Play | Reads as |
|---|---|---|
| `Wishbone 22 Smash` / `23 Smash` | Wishbone - 22 Smash / 23 Smash | the fullback, A gap |
| `Wishbone 24 Dive` / `25 Dive` | Wishbone - 24 Dive / 25 Dive | the fullback, guard–tackle |
| `Wishbone 46 Power` / `37 Power` | Wishbone - 46 Power / 37 Power | the playside halfback, tackle–tight end |
| `Wishbone 38 Toss` / `49 Toss` | Wishbone - 38 Toss / 49 Toss | the far halfback, outside the tight end |

### Trips: formation + bunch + who + play word

Empty backfield. Backs **2, 3 and 4** (fullback, tailback, slot) bunched
outside the tight end; the quarterback is alone. The call names the bunch —
`Trips Right`, `Trips Left` — then who gets it. With nobody in the backfield
to hand to, everything here goes outside or in the air, so the only numbers
that come up are 8s and 9s and the rest are word calls.

| Call | Play | Reads as |
|---|---|---|
| `Trips Right 18 Sweep` / `Trips Left 19 Sweep` | Trips - Right - 18 Sweep / Left - 19 Sweep | the quarterback, alone in the backfield, outside the bunch |
| `Trips Right 38 Quick Pass` / `Trips Left 39 Quick Pass` | Trips - Right - 38 Quick Pass / Left - 39 Quick Pass | the tailback out of the bunch, thrown to outside the tight end |
| `Trips Right LTE Sweep` / `Trips Left RTE Sweep` | Trips - Right - LTE Sweep / Left - RTE Sweep | the backside tight end on an end-around |
| `Trips Right RTE Slant Out` / `Trips Left LTE Slant Out` | Trips - Right - RTE Slant Out / Left - LTE Slant Out | the play-side tight end, flat out on the line |

## Formations

Six formations, 52 plays, in teaching order. Every numbered run is one of four
blocking families — Smash, Dive, Power, Toss — plus Sweep when the
quarterback, the slot or a tight end is coming across, and Protect on a dropback.

| # | Formation | Plays | What it is for |
|---|---|---|---|
| 1 | **Regular I** | 12 | Base offense. Fullback and tailback stacked behind the quarterback. Power, both Smashes, the tight-end sweep, the slot sweep and the tight-end slant out, both ways. |
| 2 | **Wishbone** | 8 | Three backs, no slot. Fullback Smash and Dive, halfback Power and Toss, both ways. |
| 3 | **Split Backs** | 14 | Two backs at even depth and a slot just outside the tight end. Toss, Power, QB sweep, fake sweep, slot sweep, TE sweep and the tight-end slant out, both ways. |
| 4 | **Shotgun** | 6 | The quarterback five yards deep with a back either side. The tight-end slant out, the QB sweep and the RB toss, both ways. |
| 5 | **Trips** | 8 | Empty backfield. Backs 2, 3 and 4 bunched to one side (fullback, tailback, slot). QB sweep, the quick pass, TE sweep and slant out, both ways. |
| 6 | **Power I** | 4 | The Regular I with the slot brought in behind the fullback. Smash with two lead blockers in the same gap, and Toss, both ways. |

Every one of them is two-tight-end and downhill, so the blocking language carries
across: "block down on the first defender inside you" means the same thing in all six.
That is the reason to carry related looks rather than unrelated offenses.

**None of them is symmetric, so every left-handed play is written by hand.** The slot
sits split to the right unless a play moves him, so flipping a play would flip his path
while leaving him aligned on the same side. A left-handed play that needs him on the
left moves him and says so in the call — the Regular I's `Slot Left 37 Power`, the
Split Backs' `Slot Left 29 Toss` — each the mirror of its right-hand play.

## Defense

Four fronts we call, in `defense/`:

| Call | Front | When |
|---|---|---|
| **Base** | 4-4 | Most downs. Four down, four linebackers, two corners and a free safety. The outside pair force everything back in. |
| **Tight** | 5-3 | When they are winning the middle. Trades the fourth linebacker back for a nose tackle so no guard is uncovered. |
| **Goal Line** | 6-3 | Short yardage and inside the five. The heaviest front the league allows. |
| **Prevent** | 6-2-3 | Required by rule at an 18-point lead. Not a choice. |

**Base is the 4-4 because of what actually beats us.** At this age the run that scores is
the one that gets outside, and a fourth linebacker is a defender who can run to it — a
fifth down lineman can only push. The cost is real and it is inside: both guards are
uncovered in this front. `Tight` is the call that buys it back, and the 5-3 page is still
in the book because we expect to need it.

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
| `calls.html` | **Call sheet** — one sheet per offensive package: the I-formation lineup with names, and blank Left, Middle and Right columns for plays |
| `f-<formation>.html` | One formation: its notes and its plays |
| `install.html` | **Install schedule** — a month calendar of the practices, generated from `install.json` |
| `install-<n>.html` | One practice: what goes in, and the run of practice block by block |
| `rules.html` | **The league rulebook, verbatim**, generated from `rulebook/*.txt` |
| `p-<play>.html` | One play. Deep-linkable, and prints to a single sheet |
| `defense.html` | The defensive playbook index |
| `d-<front>.html` | One defensive front, with every assignment |
| `depth-chart.html` | **Depth chart** — six columns deep, offense and defense, generated from `roster.json` |
| `print.html` | The whole book for printing |

On every page the diagram is the main attraction — full width of the card, edge to edge
on a phone, with the assignments read underneath it rather than squeezed in beside it.

A play page carries **all three fronts**, and the toggle above the diagram switches
between them. The choice is remembered, so a coach who has scouted the team they are
playing sets it once and every play in the book is in that front. All three are already
in the page, so switching is instant on a sideline with no signal — and the Print button
prints whichever one is on screen.

## The depth chart

Two boards, offense and defense, both the same six numbered columns, generated from
[`roster.json`](roster.json). It is a published chart — names on a grid, like Ourlads —
not a board you rearrange in the browser. Edit the file and rebuild.

Depth **is** the column: the first name at a position is the starter, the second is
second string, and so on to the sixth. Anybody past that is on the squad but in
nothing. A gap is written as a blank, not closed up, so deleting a third-string
fullback does not silently promote everybody below him.

**Column 2 is not the second eleven. It is "second in line here."** The same backup can
be second at left tackle and second at right tackle. A name may repeat, down a column
and across one.

### Packages

Six on offense, five on defense, under each board. The offense calls them **Offensive
FB-TB-SL Packages**: FB, TB and SL, then LTE and RTE, then LT, LG, RG and RT, because a
package can change the ends and the interior line too. The call sheet plays a package's
linemen where they are set and the depth chart's starters where they are not. Each box
carries a **Sub card** in the upper right: who comes off and who goes on versus the
base package, by spot. A package without a name under `package_names` is shown by its
number.

## Printing

- **Print playbook** (home page) → every play against the 4-4, one diagram
  per landscape letter sheet — 18 pages, the same sheet each play prints from its own page.
- **Print** (on any play or front page) → that one card, one landscape sheet.
- **Print** (on the depth chart) → two portrait sheets, offense then defense, each with
  every column on it. One goes in each coordinator's pocket.

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

Individual cards are standalone SVGs under `playbook/<formation>/cards/` if you want to
drop one into a practice plan. Two versions of each:

- `<play>.svg` — the full card, name and call in the header, assignments printed on it.
- `<play>-field.svg` — the diagram alone, used by the website.

## Building

```
python generator/render.py            # rebuild cards, site, READMEs, PLAYBOOK.md
python generator/render.py --check    # validate the JSON only, write nothing
python generator/test_calls.py        # prove the call check still rejects a wrong call
python generator/test_print_pages.py  # prove every card still prints on one sheet
python generator/test_rulebook.py     # prove the rules page still quotes the rulebook exactly
python generator/test_blocking.py     # prove every block is drawn onto the man it names
python generator/preview.py <play-id> # read one play's assignments against all three fronts
```

No dependencies beyond Python 3. `--check` fails if any play is missing an assignment for
any of the eleven positions, which is deliberate: a card with a blank spot on it is worse
than no card.

## Adding or changing plays

Edit the JSON under `playbook/`, then re-run the generator. Do not edit `PLAYBOOK.md`,
`index.html`, the `README.md` inside a formation folder, or anything in `cards/` — they
are overwritten on every build.

Every play also has a short **code**, printed big in the top-right corner of its diagram:
the formation letter, then its number — `#I-1` is the first I formation play, `#S-1` the
first Split Backs play, `#G-1` the first Shotgun play. A new play takes the next number in
its formation; the build rejects a code with the wrong letter or one already taken.

Full authoring rules, the blocking verbs, the coordinate system and the house style:
[playbook/CLAUDE.md](playbook/CLAUDE.md).

## Layout

```
playbook/<formation>/formation.json   the 11 alignment spots
playbook/<formation>/plays/*.json     one file per play          <- source
playbook/<formation>/cards/*.svg      generated — one card per play per front
defense/<front>.json                  one file per defensive front   <- source
                                      (a `scout` front is one we block
                                      against, not one we call)
install.json                          the practice-by-practice install schedule  <- source
defense/cards/*.svg                   generated
rulebook/*.docx                       the league's rulebook as published  <- source, gitignored
rulebook/*.txt, rulebook/media/       generated by generator/extract_rulebook.py
generator/blocking.py                 blocking verbs, resolved against a front
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

## Every offensive play is blocked three ways

Every play in the book is drawn and blocked against **three** fronts, and the play page
has a toggle that switches between them:

| Front | What it is | What it costs us |
|---|---|---|
| **4-4** | Four down, four linebackers. Guards covered, tackles and centre free. | The edge is heavy. Our lead blocks have an outside linebacker to find, not a corner. |
| **5-3** | Five down, three linebackers. Guards free, a tackle on each of our tackles' inside shoulders. | The default. What an 8U team lines up in against us once the 6-2 is off the table. |
| **5-4-2** | The 5-3 with the free safety traded for a fourth linebacker. | Everything is blocked and there is still a spare defender in the box. Two deep is the price they pay. |

**These are fronts we expect to face, not fronts we play.** Our own base is the 4-4 and
that is a separate question; the 5-4-2 is not in our defensive book at all, because
nobody on this team is going to call it. Changing our base does not change what the
offense is blocked against.

### Nobody pulls

No guard and no tackle leaves his spot. A pulling lineman is the one block on a card
that asks an eight-year-old to abandon the only spot he has learned, run flat behind two
bodies he cannot see over, and get somewhere before a linebacker does — and when he is a
half-count late, the hole he left is the hole the play was going to. The seventeen pulls
this book used to carry are gone, and the build rejects a new one by name.

The work went to players who were already standing there: the playside end kicks the end
out, a back leads through the hole, and the backside guard cuts off behind the play.
Power is now a down block, a kick-out and one lead back, which is a thing you can teach
in a practice.

### The card is computed, not typed

A blocker's assignment in the JSON is a **verb**, not a sentence:

```json
"RT": { "block": "down" },
"SL":  { "block": "kick" },
"FB": { "block": "lead" }
```

`generator/blocking.py` resolves that verb against a front — working out who is head up
on him, who is in the gap, which linebacker is the playside one — and produces both the
sentence on the card and the line on the diagram. Which is why one line of JSON is three
different blocks, and why they cannot disagree with each other.

It also means the half of every old assignment that was a *statement about the defence*
is gone from the source. "Nobody is over you" and "The tackle is on your inside shoulder"
were typed 111 times between them, were true only of the 5-3, and are now derived. What
is left in a play file is the part a human actually decided.

The same change is what makes the difference between fronts legible instead of
theoretical. On Power, against the 5-3 the playside guard is free and doubles the nose;
against the 4-4 a tackle is head up on him and the same one-word rule — "help inside if
you are free" — resolves to *he is yours*. Nobody has to remember that. The card says it.

**Reading all three is part of authoring a play**, and there is a tool for it:

```
python generator/preview.py i-power-r              # all three fronts, side by side
python generator/preview.py --formation i-form --audit
```

`--audit` flags the two failures a single-front book could never surface: a defender on
the playside nobody blocks, and blockers piling onto one man. A verb that reads perfectly
against the 5-3 and leaves an outside linebacker unblocked against the 4-4 is exactly the
bug this whole system exists to catch.

The 6-2, the most common front in youth football everywhere else, is **not legal in this
league** — it has only two linebackers, and the generator rejects it. See
[RULES.md](RULES.md).
