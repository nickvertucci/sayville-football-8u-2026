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
`{formation} - Z {Left|Right} - {digits} {word}`; the **call** is that same language
without
the dashes, what you yell on Saturday.

**X, Y and Z are the three men outside the tackles** — the left end is the **X**, the
right end is the **Y**, the split man is the **Z**. One letter each, on the diagram, on
the card, on the depth chart and in the call, so a boy never has to work out that LTE,
RTE and SL were three abbreviations of three different things.

### Regular I: formation + Z + back + hole + play word

The call names the formation, then `Z Right` — which side the Z lines up on — then two
digits: the first says **who carries it**, the second says **where it goes**, and then
the word says what happens to the ball. So `Regular I Z Right 36 Handoff` is the Regular I,
Z on the right, the ball handed to the tailback between the tackle and the end.

Off tackle depends on the Z's kick-out block, so he lines up on the side it has to
happen: `Regular I Z Left 37 Handoff` puts him on the left. The call says so out loud,
because a play that moves somebody silently is a play nobody can call.

| Back | Who |
|---|---|
| **1** | Quarterback — every formation |
| **2** | The fullback in the Regular I; the right back (RH) in the Split Backs and Shotgun — even-numbered holes |
| **3** | The tailback (TB) in the Regular I; the left back (LH) in the Split Backs and Shotgun — odd-numbered holes |
| **4** | A fourth back where a formation has one — the Wishbone's right halfback |

**X, Y and Z have no digit.** They are already letters, so when one of them carries it
or catches it the call says the letter, the play word, and then **which way it is
going**: `Regular I Z Right X Sweep Right`, `Split Backs Z Left Y Sweep Left`,
`Trips Right Y Slant Pass Right`. A digit would be a second name for a man who already
has one.

The last word is not decoration. A back's hole digit already says the direction — even
right, odd left — and the letter calls have no digit, on exactly the plays where a
nine-year-old cannot guess it. The **X is the left end and `X Sweep` sends him right**;
the Z lines up right on `Z Right Z Sweep` and runs **left**. So the call says it out
loud, and the build checks it against the diagram like everything else.

| Hole | Word | Where | Blocking |
|---|---|---|---|
| **0** | Handoff | Straight over the center | Smash |
| **2 / 3** | Handoff | Between the center and the guard | Smash |
| **4 / 5** | Handoff | Between the guard and the tackle | Dive |
| **6 / 7** | Handoff | Between the tackle and the end | Power |
| **8 / 9** | Toss | Outside the end | Toss |

**The word is what happens to the ball, not how the line blocks it.** Smash, Dive and
Power are three names for the same event as far as the boy carrying it is concerned —
the quarterback puts it in his belly — so the huddle says **Handoff** and the two digits
say which of them it is. Toss keeps its word because a pitch is not a handoff, and
**Sweep** keeps its because coming across the formation is not either. Behind it the
blocking families are unchanged: the last column is what the line is still running, and
what `--check` still holds every play to.

```
   9  |  7  |  5  |  3  | 0 |  2  |  4  |  6  |  8
     X    LT    LG     C     RG    RT   Y
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
`Regular I Z Right 36 Handoff` is the tailback between the right tackle and tight end,
and `Regular I Z Left 37 Handoff` is the same handoff to the left.

| Call | Play | Where it hits |
|---|---|---|
| `Regular I Z Right 36 Handoff` / `Z Left 37 Handoff` | Regular I - Z Right - 36 Handoff / Z Left - 37 Handoff | tailback, tackle–tight end |
| `Regular I Z Right 32 Handoff` / `Z Left 33 Handoff` | Regular I - Z Right - 32 Handoff / Z Left - 33 Handoff | tailback, A gap, fullback leading |
| `Regular I Z Right 22 Handoff` / `Z Left 23 Handoff` | Regular I - Z Right - 22 Handoff / Z Left - 23 Handoff | fullback, A gap, on the snap |
| `Regular I Z Right X Sweep Right` / `Z Left Y Sweep Left` | Regular I - Z Right - X Sweep Right / Z Left - Y Sweep Left | the backside tight end on an end-around, all the way outside |
| `Regular I Z Right Y Slant Pass Right` / `Z Left X Slant Pass Left` | Regular I - Z Right - Y Slant Pass Right / Z Left - X Slant Pass Left | the play-side tight end, flat out along the line |
| `Regular I Z Right Z Sweep Left` / `Z Left Z Sweep Right` | Regular I - Z Right - Z Sweep Left / Z Left - Z Sweep Right | the slot, lined up one way and flat across the backfield the other |
| `Regular I Z Right 38 Toss` / `Z Left 39 Toss` | Regular I - Z Right - 38 Toss / Z Left - 39 Toss | tailback, pitched wide and outside the tight end |
| `Regular I Z Right 38 Toss Pass` / `Z Left 39 Toss Pass` | Regular I - Z Right - 38 Toss Pass / Z Left - 39 Toss Pass | the same pitch, and the tailback pulls up behind the line and throws |

**A call names its man once, and always says which way.** A back has a digit, so a
back's call carries two of them — who and where — and the hole is the direction.
X, Y and Z have a letter, so their call is the letter, the word, and the way:
`X Sweep Right` is the X coming all the way across to the right, `Y Slant Pass Right`
is the Y flat out along the line. There is no hole to say, because a man already
outside the tackle does not run through a gap to get there. Anything else — a nickname,
a back with no digit, a letter that is not X, Y or Z, a letter call with the way left
off or backwards — fails the build.

Every play has a left and a right.

### Split Backs: formation + Z + back + hole + play word

Two backs to number instead of three, and a Z out wide to declare — so the call reads
like the Regular I's. `Split Backs Z Right 38 Toss` is the Split Backs, Z on the right, the
3-back (left halfback) all the way outside at the 8 hole. In this formation the **3-back is
always the left back** (odd-numbered holes) and the **2-back is always the right back**
(even-numbered holes); the Z keeps **4**, the number he carries in every look.

| Call | Play | Reads as |
|---|---|---|
| `Split Backs Z Left 29 Toss` / `Z Right 38 Toss` | Split Backs - Z Left - 29 Toss / Z Right - 38 Toss | the far back, all the way outside |
| `Split Backs Z Left 29 Toss Pass` / `Z Right 38 Toss Pass` | Split Backs - Z Left - 29 Toss Pass / Z Right - 38 Toss Pass | the same pitch, and the far back pulls up behind the line and throws |

The back digit follows whoever actually carries it. On the toss it is the far back,
because the near one is busy bubbling out to block.

### Shotgun: formation + Z + back + hole + play word

The Shotgun's pass is called off the end who catches it — `Y Slant Pass Right`,
`X Slant Pass Left` — and its halfbacks number the same way the Split Backs do: 3 is
left, 2 is right.

| Call | Play | Reads as |
|---|---|---|
| `Shotgun Z Right Y Slant Pass Right` / `Z Left X Slant Pass Left` | Shotgun - Z Right - Y Slant Pass Right / Z Left - X Slant Pass Left | the play-side tight end, a flat slant out almost on the line of scrimmage |
| `Shotgun Z Left 19 Sweep` / `Z Right 18 Sweep` | Shotgun - Z Left - 19 Sweep / Z Right - 18 Sweep | the quarterback, all the way outside behind the near halfback |
| `Shotgun Z Left 29 Toss` / `Z Right 38 Toss` | Shotgun - Z Left - 29 Toss / Z Right - 38 Toss | the far halfback, across in front of the quarterback and all the way outside |

**Play word** — a numbered run's word is what happens to the ball: **Handoff** from 0
through 7, **Toss** at 8/9. The blocking family is still the hole — Smash, Dive, Power,
Toss — and it is still what `--check` holds the play to; it is just not what gets
yelled.
**Sweep** is *who*, not where: the quarterback (`18` / `19`) or one of the three
letters (`X Sweep Right`, `Y Sweep Left`, `Z Sweep Left`) coming across to get there. A
back at 8/9 is a Toss. Digits belong to backs, so a digit never names a letter — the
Wishbone's `49 Toss` is its right halfback, not the Z.
**A letter call ends with the way it goes** — `Left` or `Right`, checked against the
diagram. The digit calls say it in the hole; these have no hole, and these are the
plays where the man's own side is the wrong guess.
**A pass's word is its route, not its hole** — `Y Slant Pass Right`, `38 Quick Pass`,
`38 Toss Pass`. Where a pass does carry digits they are still checked against the
diagram; only the word is free, because a route is not a gap.
**Toss Pass** keeps the toss's digits — `38 Toss Pass` is the 38 Toss right up
until the back pulls up behind the line and throws, so it is called the same way and
the first digit is still the man who takes the pitch. He never crosses the line, and
the build rejects a diagram that shows him doing it: a forward pass from past the line
of scrimmage is a penalty.

### Wishbone: formation + back + hole + play word

Three backs and no Z, so the call drops the Z Right / Z Left. `Wishbone 22 Handoff`
is the fullback between the center and the right guard. `46 Handoff` is the right
halfback off tackle; `38 Toss` is the left halfback all the way outside.

| Call | Play | Reads as |
|---|---|---|
| `Wishbone 22 Handoff` / `23 Handoff` | Wishbone - 22 Handoff / 23 Handoff | the fullback, A gap |
| `Wishbone 24 Handoff` / `25 Handoff` | Wishbone - 24 Handoff / 25 Handoff | the fullback, guard–tackle |
| `Wishbone 46 Handoff` / `37 Handoff` | Wishbone - 46 Handoff / 37 Handoff | the playside halfback, tackle–tight end |
| `Wishbone 38 Toss` / `49 Toss` | Wishbone - 38 Toss / 49 Toss | the far halfback, outside the tight end |

### Trips: formation + bunch + who + play word

Empty backfield. The fullback, the tailback and the Z bunched
outside the end; the quarterback is alone. The call names the bunch —
`Trips Right`, `Trips Left` — then who gets it. With nobody in the backfield
to hand to, everything here goes outside or in the air, so every number that comes
up is an 8 or a 9 — and the two ends, who are called by letter.

| Call | Play | Reads as |
|---|---|---|
| `Trips Right 18 Sweep` / `Trips Left 19 Sweep` | Trips - Right - 18 Sweep / Left - 19 Sweep | the quarterback, alone in the backfield, outside the bunch |
| `Trips Right 38 Quick Pass` / `Trips Left 39 Quick Pass` | Trips - Right - 38 Quick Pass / Left - 39 Quick Pass | the tailback out of the bunch, thrown to outside the tight end |
| `Trips Right X Sweep Right` / `Trips Left Y Sweep Left` | Trips - Right - X Sweep Right / Left - Y Sweep Left | the backside tight end on an end-around |
| `Trips Right Y Slant Pass Right` / `Trips Left X Slant Pass Left` | Trips - Right - Y Slant Pass Right / Left - X Slant Pass Left | the play-side tight end, flat out on the line |

## Formations

Six formations, 58 plays, in teaching order. Every numbered run is one of four
blocking families — Smash, Dive, Power, Toss — plus Sweep when the
quarterback, the slot or a tight end is coming across, and Protect on a dropback.

| # | Formation | Plays | What it is for |
|---|---|---|---|
| 1 | **Regular I** | 16 | Base offense. Fullback and tailback stacked behind the quarterback. Power, both Smashes, the tight-end sweep, the slot sweep, the toss, the toss pass and the tight-end slant out, both ways. |
| 2 | **Wishbone** | 8 | Three backs, no slot. Fullback Smash and Dive, halfback Power and Toss, both ways. |
| 3 | **Split Backs** | 16 | Two backs at even depth and a slot just outside the tight end. Toss, the toss pass off it, Power, QB sweep, fake sweep, slot sweep, TE sweep and the tight-end slant out, both ways. |
| 4 | **Shotgun** | 6 | The quarterback five yards deep with a back either side. The tight-end slant out, the QB sweep and the RB toss, both ways. |
| 5 | **Trips** | 8 | Empty backfield. Backs 2, 3 and 4 bunched to one side (fullback, tailback, slot). QB sweep, the quick pass, TE sweep and slant out, both ways. |
| 6 | **Power I** | 4 | The Regular I with the slot brought in behind the fullback. Smash with two lead blockers in the same gap, and Toss, both ways. |

Every one of them is two-tight-end and downhill, so the blocking language carries
across: "block down on the first defender inside you" means the same thing in all six.
That is the reason to carry related looks rather than unrelated offenses.

**None of them is symmetric, so every left-handed play is written by hand.** The slot
sits split to the right unless a play moves him, so flipping a play would flip his path
while leaving him aligned on the same side. A left-handed play that needs him on the
left moves him and says so in the call — the Regular I's `Z Left 37 Handoff`, the
Split Backs' `Z Left 29 Toss` — each the mirror of its right-hand play.

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
| `calls.html` | **Call sheet** — the whole book on one sheet: a block per formation by scheme and side, the possession script down the right, the packages and what each calls, a blank field to draw on, and the base eleven with every package's substitutions under it. Defense is the second tab |
| `wristbands.html` | **Wristbands** — every callable play by number, three 5″ × 3″ pouches to a band, one band to a sheet, cut on the dashes |
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
FB-TB-Z Packages**: FB, TB and Z, then X and Y, then LT, LG, RG and RT, because a
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

Every play also has a **number**, printed big in the top-right corner of its diagram,
down the left of every cell on the call sheet, and on the boys' wristbands. One plain
number per play across the whole book — `#7`, not `#I-7` — because a child reading a
band through a facemask should not have to work out which formation he is in before he
can find the row.

They run in call sheet order, so everything called on a Saturday is 1–42:

| Numbers | Formation |
|---|---|
| **1–16** | Regular I |
| **17–32** | Split Backs |
| **33–38** | Shotgun |
| **39–42** | Power I |
| 43–50 | Trips — a teaching formation, not on the call sheet |
| 51–58 | Wishbone — the same |

**A number is never reused and never renumbered.** A play that has been learned keeps
its number, and a new play takes the next free one; gaps where a play was retired stay
gaps. Renumbering would make every wristband already printed wrong, so the build only
checks that a number is a whole number and that no two plays share one.

The bands themselves are [`wristbands.html`](wristbands.html): the same 1–42, one
formation to a pouch — Regular I, Split Backs, then Shotgun with Power I behind it. A
pouch is 5″ × 3″ and landscape, because it wraps a forearm, and three of them stacked
is nine inches of a portrait page. So a sheet is one whole wristband: print a copy per
boy, cut on the dashes, load them top to bottom.

Three pouches instead of one window is what pays for the type. Forty-two plays in one
window is a column of nine-point rows; fourteen in a panel, two columns of eight, is
fifteen and a half with room to breathe between them. A row reads `1 · Z Right 36 Handoff`
— the number, then the call word for word, minus the formation the pouch already names.
The reader is nine years old, outdoors, and somebody is shouting a number at him.

It is generated like everything else, so adding a play adds a row — and because
numbers never move, the bands already on wrists stay correct.

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
"Z":  { "block": "kick" },
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
