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
`Regular I Slot Right 34 Power` is the Regular I, slot on the right, the tailback between the
tackle and the end.

Off tackle depends on the slot's kick-out block, so he lines up on the side it
has to happen: `Regular I Slot Left 35 Power` puts him on the left. The call says so out
loud, because a play that moves somebody silently is a play nobody can call.

| Back | Who |
|---|---|
| **1** | Quarterback — every formation |
| **2** | The fullback in the Regular I; the right back (RH) in the Split Backs and Shotgun — even-numbered holes |
| **3** | The tailback (TB) in the Regular I; the left back (LH) in the Split Backs and Shotgun — odd-numbered holes |
| **4** | The slot, split wide in every formation |

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

The digits describe the back the first digit names, not necessarily the ball carrier. So
`Regular I Slot Right 34 Power` is the tailback between the right tackle and end, and
`Regular I Slot Left 35 Power` is the same handoff to the left.

| Call | Play | Where it hits |
|---|---|---|
| `Regular I Slot Right 34 Power` / `Slot Left 35 Power` | Regular I - Slot Right - 34 Power / Slot Left - 35 Power | tailback, tackle–end |
| `Regular I Slot Right LTE Jet` / `Slot Left RTE Jet` | Regular I - Slot Right - LTE Jet / Slot Left - RTE Jet | the backside tight end on an end-around, all the way outside |
| `Regular I Slot Right 49 Jet` / `Slot Left 48 Jet` | Regular I - Slot Right - 49 Jet / Slot Left - 48 Jet | the slot, flat across the backfield and outside the other way |

The tight-end jet is a **word call** — no digits, because the tight end is not a numbered
back. It names him instead. A play has to opt in with `word_call`, so any other play
missing its number still fails the build.

Every play has a left and a right.

### Split Backs: formation + Slot + back + hole + play word

Two backs to number instead of three, and a slot out wide to declare — so the call reads
like the Regular I's. `Split Backs Slot Right 38 Pitch` is the Split Backs, slot on the right, the
3-back (left halfback) all the way outside at the 8 hole. In this formation the **3-back is
always the left back** (odd-numbered holes) and the **2-back is always the right back**
(even-numbered holes); the slot out wide keeps **4**, the number he carries in every look.

| Call | Play | Reads as |
|---|---|---|
| `Split Backs Slot Left 29 Pitch` / `Slot Right 38 Pitch` | Split Backs - Slot Left - 29 Pitch / Slot Right - 38 Pitch | the far back, all the way outside |

The back digit follows whoever actually carries it. On the pitch it is the far back,
because the near one is busy bubbling out to block.

### Shotgun: formation + Slot + who catches it + route

The Shotgun's pass names its receiver the way the tight-end jet names its runner — the
tight end is not a numbered back, so it is a word call. Its halfbacks number the same way
the Split Backs do: 3 is left, 2 is right.

| Call | Play | Reads as |
|---|---|---|
| `Shotgun Slot Right RTE Slant Out` / `Slot Left LTE Slant Out` | Shotgun - Slot Right - RTE Slant Out / Slot Left - LTE Slant Out | the play-side tight end, a flat slant out almost on the line of scrimmage |
| `Shotgun Slot Left 19 Sweep` / `Slot Right 18 Sweep` | Shotgun - Slot Left - 19 Sweep / Slot Right - 18 Sweep | the quarterback, all the way outside behind the near halfback |
| `Shotgun Slot Left 29 Sweep` / `Slot Right 38 Sweep` | Shotgun - Slot Left - 29 Sweep / Slot Right - 38 Sweep | the far halfback, across in front of the quarterback and all the way outside |

**Play word** — the Regular I carries `Power` and the tight-end and slot `Jet`; the Split Backs
carries `Pitch`, `Sweep` and `Fake Sweep`; the Shotgun carries the tight end's `Slant Out`, the
only pass in the book, which fakes nothing, and the quarterback `Sweep`.

## Formations

Three formations, 18 plays, in teaching order:

| # | Formation | Family | Plays | What it is for |
|---|---|---|---|---|
| 1 | **Regular I** | Regular I | 6 | Base offense. Fullback and tailback stacked behind the quarterback. Off tackle, the tailback between the tackle and the end behind the SL's kick-out, the tight-end jet and the slot jet, both ways. |
| 2 | **Split Backs** | Split Backs | 6 | Two backs at even depth and a slot just outside the tight end. 38/29 Pitch, the QB sweep and the fake-handoff QB sweep, both ways. |
| 3 | **Shotgun** | Shotgun | 6 | The quarterback five yards deep with a back either side. The tight-end slant out, the QB sweep and the RB sweep, both ways. |

Both are two-tight-end, downhill running formations, so the blocking language carries
over: "block down on the first defender inside you" means the same thing in either. That
is the reason to carry two related looks rather than two unrelated offenses.

**Neither formation is symmetric, so every left-handed play is written by hand.** The slot
sits split to the right unless a play moves him, so flipping a play would flip his path
while leaving him aligned on the same side. Both left-handed plays do move him — the
Regular I's `Slot Left 35 Power` and the Split Backs' `Slot Left 29 Pitch`, each the mirror of
its right-hand play — and say so in the call.

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
| `depth-chart.html` | **Depth chart** — six columns deep, offense and defense, drag-and-drop |
| `print.html` | The whole book for printing |

On every page the diagram is the main attraction — full width of the card, edge to edge
on a phone, with the assignments read underneath it rather than squeezed in beside it.

A play page carries **all three fronts**, and the toggle above the diagram switches
between them. The choice is remembered, so a coach who has scouted the team they are
playing sets it once and every play in the book is in that front. All three are already
in the page, so switching is instant on a sideline with no signal — and the Print button
prints whichever one is on screen.

## The depth chart

Two boards, offense and defense, and both run the same six numbered columns. Six is
room to name a rotation deep at every spot without editing the file first; the columns
nobody has reached yet sit empty and are there to be filled.

The sixth used to be **Jumbo**, a short-yardage package rather than a depth, and it was
the last thing on the page that had to be explained before it could be read. It is
column six now.

They were called Purple, Gold and White until the page stopped being readable. A colour
is a fine name for a practice jersey and a poor one for a column: it carries no order,
so "who is behind him" needed a key nobody had, and once the header had scrolled off the
top the board was a row of anonymous columns of names. A depth chart numbers its columns,
because the number is the one label that answers the question the page exists to
answer — and the ids changed with it, so a board saved under the old names is migrated
rather than silently dropped. Rotation is on the across axis because the question the page
exists to answer is *"the left tackle just came off — who goes in"*, and the answer should
be the next cell over rather than a scroll away.

`roster.json` is the chart. Depth in it **is** the column — the first name at a position
is the starter, the second is second string, and so on to the fifth; on offense the sixth
and so on to the sixth, and anybody past that is on the squad but in nothing. One
ordered list per position stays the thing a coach edits, and nothing has to be kept
agreeing with anything else.

**A gap is written as a blank, not closed up.** Depth is the index, so deleting a name
from the middle of a list promotes everybody below it — which is how removing a third-string
fullback would quietly promote everybody below him. An empty string holds the spot
and renders as *Open*.

### Packages

Boxes above the squad on each board: six on offense, five on defense. The offense
calls them **Offensive FB-TB-SL Packages**. Each offensive box is seven slots: FB, TB
and SL, then LT, LG, RG and RT under a dashed rule, because a package can change the
line too. The call sheet plays a package's linemen where they are set and the depth
chart's starters where they are not. Each slot is labelled with the spot it is, so an empty
package says which three it is short of rather than showing three identical *Open*
rows, and a name in the wrong slot is visible.

The label is drawn from a data attribute in CSS rather than sitting in the slot as an
element: the slot's contents are rewritten every time it empties or fills, so a child
element would be gone the first time somebody took a name out. Defense has no fixed
trio of spots, so its slots carry no labels. A package is the group who go on and
come off together, which is the other question a coach asks at this age and the one the
board could not answer: the columns say who plays left guard, and these say who you are
sending in next.

They are fixed slots rather than a list because the group is the thing being
named, and the count and size live in one constant per side — the markup, the roster round-trip and the
print sheet all take their shape from it. They
take a name exactly the way a board cell does — same drag, same tap, same *Open* marker —
because they are in the same drop-target list and not a second set of handlers that would
have to be kept in step.

`roster.json` carries them under `packages`, one array of groups per side, and **Copy
roster.json** writes them back. A package can have a name under `package_names`, in the
same order — the offense's are Shifty, Fortnite, Total Recall, Maverick, Bigshow and Tiny —
and a package without one is shown by its number. Trailing empty packages are dropped, so an untouched board
adds nothing to the file rather than a page of empty groups. Offense package one ships
named; the squad rail is how you fill the rest.

**A name may repeat, down a column and across one.** The same left tackle at three
depths is that name three times in the list — the normal case for a kid you never take
off. And the same backup can be second in line at two different positions, because a
column is "second here", not "the second eleven". Both round-trip through the page
without a second concept to learn.

**You can rearrange it in the browser.** Under each board is the squad — everybody on that
side of the ball, always. It is a *source*, not a pile of leftovers: drag a name onto a spot
and he goes there while staying in the squad, so putting one kid on all three units is
three drags rather than a special mode. Tap works too, and a name tapped in the squad
stays picked after it lands — tap him once, then tap all three spots. Drag a name from the
board back to the squad to take him out of that spot.

Names already on the board are dimmed in the squad rail and carry the number of rotations
they hold, which leaves the bright ones — the kids nobody has given a job — as the thing
your eye lands on. The heading counts them.

Moving a name that is already on the board is a move, swapping with whoever is there. A
kid may hold as many spots as you like, including more than one in the same column. The
board used to forbid that on the grounds that he cannot be at left tackle and centre at
the same time — which is true of a unit that takes the field together and false of a
depth chart. **Column 2 is not the second eleven. It is "second in line here."** The same
backup can be second at left tackle and second at right tackle and never play both at
once.

Everything works with a finger; on a phone, hold a moment before dragging, or the swipe
scrolls the page instead. Every spot is a button, so the whole board works from a keyboard
too.

Those edits live in that one browser's `localStorage` and nowhere else. Nobody else sees
them, they do not touch `roster.json`, and a banner says so whenever the board on screen is
not the board in the repo. Two things close the loop:

- **Reset** puts the shipped roster back. It only appears once you have changed something,
  and takes two taps.
- **Copy roster.json** hands back the whole file with your board written into it, to paste
  into the repo when a halftime rearrangement turns out to be the real answer. It rewrites
  only `offense` and `defense` and carries the note through untouched, and it writes each
  side to its own depth — six slots for offense, five for defense.

The column headers used to carry a live filled-of-eleven count. It went with the
Jumbo column: a depth chart is not eleven deep at every spot and is not meant to be, so
"0/11" over a column nobody has filled yet was reporting a shortfall that is not one. The
squad rail still counts the kids in no spot at all, which is the number that does mean
something.

## Printing

- **Print playbook** (home page) → every play against the 4-4, one diagram
  per landscape letter sheet — 18 pages, the same sheet each play prints from its own page.
- **Print** (on any play or front page) → that one card, one landscape sheet.
- **Print** (on the depth chart) → two portrait sheets, offense then defense, each with
  every column on it. One goes in each coordinator's pocket. Whatever the board
  says when you print is what comes out, local edits included.

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
