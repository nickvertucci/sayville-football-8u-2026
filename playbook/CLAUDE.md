# Authoring plays

Everything in this folder is source. `PLAYBOOK.md`, `index.html`, the formation
`README.md` files and everything under `cards/` are generated — do not hand-edit them,
they get overwritten. Change the JSON and re-run:

```
python generator/render.py            # rebuild cards, site, READMEs, PLAYBOOK.md
python generator/render.py --check    # validate the JSON only, write nothing
```

## Layout

```
playbook/<formation>/formation.json   the 11 alignment spots
playbook/<formation>/plays/*.json     one file per play, filename = play id
playbook/<formation>/cards/*.svg      generated: full card + diagram-only version
defense/<front>.json                  the defensive playbook; also the fronts
                                      offensive cards are drawn against
```

## Every diagram shares one frame

`diagram_frame()` in `render.py` computes a single window that fits every play in the
book, and every diagram and card is drawn in it. That is why the line of scrimmage, the
formation and the defense land on the same spot on every image.

**Do not crop diagrams to their own content.** It uses the pixels better and it makes the
book look assembled from different sources — the same play drawn at two sizes reads as
two different plays. If a new play runs wider or deeper than anything already in the
book, the frame grows for everything at once, which is the intended behaviour.

## Coordinates

Field yards. **x is positive to the right, y is positive downfield.** The line of
scrimmage is `y = 0`, so the offensive line sits at `y = -0.5`.

A player's `path` is a list of points **relative to that player's own alignment spot**,
so you never do field math. This:

```json
"TB": {"rule": "Take the handoff and aim at our tackle's outside hip", "type": "run", "path": [[1.2, 1.5], [2.6, 3.6], [3.4, 5.6]]}
```

means the tailback goes 1.2 right / 1.5 downfield of where he started, then 2.6 right /
3.6 downfield, and so on. Only ball carriers, fakes, routes and motion carry a path —
a blocker's is derived from the front.

## Path types

| `type` | Drawn as | Use for |
|---|---|---|
| `block` | solid line, perpendicular bar at the end | any blocking assignment |
| `run` | solid line, arrowhead | the ball carrier |
| `pass` | dashed line, arrowhead | routes and the quarterback's drop or roll |
| `fake` | dashed line, arrowhead | decoys carrying out fakes |
| `motion` | dashed line, arrowhead | pre-snap motion |
| `rollout` | dotted line, arrowhead | the quarterback rolling out after he pitches |

The ball carrier's line is drawn thicker and in red — set `ball_carrier` to his position
key. On pass plays, set it to the primary receiver.

**A pitch is a dotted line.** Give the play a `pitch` — `from` (default `QB`), `to`, and
`at`, the waypoint on the receiver's path where he catches it, counting from 1 — and the
card draws a red dotted line from the pitcher to that point, with no arrowhead. The
build checks the receiver's path is that long.

```json
"pitch": { "from": "QB", "to": "LH", "at": 1 }
```

## Required fields

**A play** needs `id` (must equal the filename, and be unique across every formation),
`name`, `scheme` (Smash, Dive, Power, Slant, Toss, Sweep or Protect), and
`assignments` for the ball carrier, fakes and routes. The line, the slot and the
lead come from the scheme — do not restate them. `--check` fails the build if a
position still has no job after the fill, or if a written block disagrees with
the scheme.

Optional: `call`, `type`, `defense` (must match a file in `defense/`),
`order`, `direction`, `coaching_points`, `alignment`, `code`.

`code` is the play's short name, printed big in the top-right corner of its diagram:
the formation's `code_prefix` (I, S, G), a dash and a number — `I-1`. The build rejects a
code with the wrong letter or one another play already has. A new play takes the next
number in its formation; codes are never renumbered, so a coach's I-3 stays I-3. There is no introductory
paragraph: a play is its name, call, diagram, assignments and coaching points.

### `alignment` — moving somebody for one play

A formation has one alignment, but a formation is not always one picture. A play may
move a player who has more than one legal spot in the same eleven-man look:

```json
"alignment": { "SL": [-5.6, -1.5] }
```

That is Power Left putting the SL on the side his kick-out has to happen on, instead of
the right, where he lines up on every other snap. Everything else — the line rules, the other ten spots — is
unchanged, and the player's `path` is still relative to wherever he ends up, so the
assignment does not have to know which look it is in.

**Say it in the call.** `Regular I Slot Left 35 Power` tells the huddle which side the slot is
on, the same way `Regular I Slot Right 34 Power` does. A play that moves
somebody silently is a play nobody can call.

An override may only move a player the formation already has, and the coordinates must be
`[x, y]`. `--check` rejects both mistakes — a typo'd key would otherwise be ignored in
silence and the play would render at the unmoved spot looking perfectly fine.

Do not reach for this to build a different formation. If most of the eleven move, or the
line changes, that is a new `formation.json`.

`order` is the position in the formation's teaching sequence — it decides the order
plays appear on the site and in `PLAYBOOK.md`, nothing more.

**[`install.json`](../install.json) is the practice-by-practice schedule** behind the
Install page. It is built out a practice at a time, so a play does not have to be on it
— a half-written schedule is the normal state of one in August, and failing the build
over it would mean you could not publish until the whole season was planned. Anything
not scheduled is listed at the bottom of the Install page instead, so it cannot go
missing quietly.

What the build *does* reject: a play scheduled twice, an id that does not exist, practice
numbers out of order, and a practice whose `requires` list names something installed
later. That last one is the point of the file — the dependencies are already written in
the plays' own coaching points ("do not install this until Power Right is real"), and
`requires` makes them checkable instead of hoping somebody read carefully.

A practice's `date` is ISO — `"2026-09-02"`, never `"Wed, Sep 2"`. The site puts it on a
month calendar and computes the weekday from it, so the weekday cannot disagree with the
date printed beside it. The build rejects anything else, and rejects a practice dated
before the one numbered ahead of it. A practice with no date at all is fine: it keeps its
own page and its row in the list, it just does not land on a square yet.

**A formation** needs `id` (must equal the folder name), `name`, an `alignment` of
exactly eleven players, and `backs` — the digit-to-position map its calls are numbered
from:

```json
"backs": { "1": "QB", "2": "FB", "3": "TB", "4": "SL" }
```

`backs` is not documentation. It is what the generator resolves the first digit of every
call against, and it is what the calling-language table on the home page is built from,
so there is one copy of the numbering rather than three that can disagree.

### `name` and `call` are the numbering

Both are printed at the top of every card. `name` is `{formation} - Slot {Left|Right} -
{digits} {word}` (*Regular I - Slot Right - 34 Power*); `call` is the same language
yelled in the huddle (`Regular I Slot Right 34 Power` — formation, the slot's side,
then **two digits: who carries it and where it goes**, then the play word).
The numbering system is documented in the top-level [README](../README.md).

**The build checks the call against the diagram**, so a call is not free text:

- The first digit is a back number from the formation's `backs` map, so it has to be one
  the formation actually defines.
- The second digit is the hole. Even is right, odd is left, counting outward from the
  center. The generator measures where that back's path crosses the line of scrimmage and
  fails the build if it does not land in the hole the call names.
- **The play word is the hole.** A numbered run has to say this word, or `Fake` plus
  this word:

  | Hole | Word |
  |---|---|
  | **0 / 1** | Smash |
  | **2 / 3** | Dive |
  | **4 / 5** | Power |
  | **6 / 7** | Slant |
  | **8 / 9** | Toss |

  **Sweep** is who, not a hole: the quarterback at 8/9 is `18 Sweep` / `19 Sweep`,
  the slot coming across is `49 Sweep` / `48 Sweep`, and a tight end on an
  end-around is a word call (`LTE Sweep`). Digit 4 is the slot only in looks
  that have one — Wishbone's 4 is the right halfback, so `49 Toss` is Toss.
  So `34 Power` is right, `34 Smash` fails, and `18 Toss` fails because the
  quarterback sweeping is Sweep. Word calls (a tight-end sweep, a slant-out
  pass) opt out of the hole table because they have no hole digit.

The play word **is** the blocking scheme. `34 Power` fills Power; `18 Sweep`
fills Sweep; a dropback `RTE Slant Out` fills Protect. Dive and Slant are
named and ready — there is just no play in the book at those holes yet.

That means the digits describe **the back the first digit names**, not necessarily the
ball carrier. On a play-action pass they follow the quarterback's path, while
`ball_carrier` is the receiver he throws to, which is a different thing.

Inventing a nickname instead of a call defeats the point of having a language, and now
also fails `--check`.

**The one exception is a word call**, for a ball carrier the numbering has no digit for —
a tight end on an end-around. Set `"word_call": true` and name him in the call
(`Regular I Slot Right LTE Sweep`); the play must also have `direction`, which is where its
playside comes from with no hole digit. Only a play that opts in is exempt, and digits
added to a word call are still checked.

Formations carry an `order` field too, which is teaching order, not the alphabet.
Both control the sequence on the site and in `PLAYBOOK.md`.

### Name the scheme. Write the paths that are the play.

A play does not list eleven blocking verbs. It names the family, and the generator
fills the line, the slot and the lead from `SCHEMES` in `generator/blocking.py`:

```json
{
  "scheme": "Power",
  "ball_carrier": "TB",
  "assignments": {
    "QB": { "rule": "Open right, hand deep to the tailback, then fake the boot.",
            "type": "fake", "path": [[1.2, -0.5], [4.6, -1.6]] },
    "TB": { "rule": "Take the handoff downhill at our tackle's outside hip.",
            "type": "run", "path": [[1.2, 1.5], [3.4, 5.6]] }
  }
}
```

Roles, not position keys, so Regular I, Split Backs and the next formation all
get the same Power: playside end releases, slot kicks, fullback (or the playside
halfback) leads. A stacked I always leads with the fullback. Two halfbacks lead
with the one on the playside.

| Scheme | Playside end | Slot | Lead | Where |
|---|---|---|---|---|
| **Smash** | cutoff | screen | through the hole | A-gap (0/1) |
| **Dive** | cutoff | screen | through the hole | B-gap (2/3) |
| **Power** | release | kick | through the hole | C-gap (4/5) |
| **Slant** | base inside | screen | through the hole | outside the end (6/7) |
| **Toss** | base inside | screen | force man | all the way outside (8/9) |
| **Sweep** | base inside | screen | force man | 8/9, QB or slot or a tight end |
| **Protect** | protect | screen | protect | dropback pass |

A leftover back the scheme does not name stays on the play — the trailing
halfback who also leads on a tight-end sweep, a `note` on the toss lead. A
tight-end sweep is still Sweep: the backside end is gone, so the backside
tackle cuts off instead of blocking down.

Do not restate a scheme verb on the play. `--check` rejects a Power whose
playside end cuts off, because that is Smash. A `note` with no verb is merged
onto the scheme job.

A dropback is `{who} {route}` (`RTE Slant Out`) and scheme **Protect**. Do not
number it with a hole word — Slant is the 6/7 run. Play-action (none in the
book yet) takes the run's scheme and its digits; `ball_carrier` is the receiver.

### Blocking intents

What the scheme fills, and what a leftover back writes, is **a verb, not a
sentence**:

```json
"RT": { "block": "down" },
"SL":  { "block": "kick" },
"FB": { "block": "lead" },
"RTE": { "block": "release", "note": "You are the widest man we have — if he beats you outside, it is a touchdown." }
```

`generator/blocking.py` resolves that against a real defensive front and produces both
the sentence on the card and the line on the diagram. That is what lets every play in
the book be drawn against the **4-4**, the **5-3** and the **5-4-2** without anybody
typing three versions of it — and it is why a blocker no longer has a `rule` or a
`path`. He has a job; where the job puts him is the front's business.

| Verb | The job | Options |
|---|---|---|
| `base` | Drive the man over you. Falls back to `down` if nobody is over him. | `drive`: `back` (default), `out`, `in` |
| `down` | The first defender on or inside you. The bread-and-butter block. | |
| `reach` | Get your head across the playside shoulder of the man in the playside gap. Climbs instead if that gap is empty. | |
| `double` | Uncovered? Help inside, then climb. **Covered? He is yours** — the verb resolves to a base block by itself. | `target`: which linebacker to climb to |
| `climb` | Straight past the line to a linebacker. | `target` |
| `release` | Leave the man being kicked out alone and take a linebacker. The end man on a kick-out play. Defaults to `outside`, which is the whole adjustment between a three- and a four-linebacker front. | `target` |
| `cutoff` | The backside. Nobody chases this from behind. | |
| `kick` | Kick the edge defender out. The ball runs inside the block. | |
| `lead` | Through the hole, first defender who shows — aimed at the **hole**, not at a man, because "whoever shows" is not somebody you can pick before the snap. | `target: force` only, which instead names the man outside our end |
| `hinge` | Protect the side the quarterback ends up on. | |
| `wedge` | Shoulder to shoulder and push. Nobody picks a man. | |
| `screen` | Get in a defensive back's way and stay there. | |
| `decoy` | Sell a fake. **Keeps its hand-drawn `path`** — the lie copies another play's path, which is not derivable from the defence. Give it `sell`. | `sell`, `path` |
| `protect` | Pass block. A lineman steps back and sets; a back beside a shotgun quarterback steps up and out to pick up the rush. Nobody picks a man before the snap. | |
| `man` | Block the defender the coach names. **Only under `fronts`**, because a label means a man in one front. `help` adds a first stop on another man; `via` is waypoints to get round somebody first, with `how` saying so in words; `with` names the teammate on the same man, for a double team ("…double team the W with the tailback"). | `man`, `help`, `via`, `how`, `with` |

`target` names a linebacker by job: `playside` (the innermost one actually on the
playside — the man who fills the hole), `middle`, `backside` or `outside`. **They are
not always four different men.** Only the 5-3 has a linebacker standing on the ball; in
the 4-4 and the 5-4-2 `middle` breaks the tie toward the play and lands on the same body
`playside` does. That is correct — he is the man who makes the tackle — but it means two
blockers given `middle` and `playside` can end up on one defender, which is what
`--audit` is for.

`lead` is the exception: it accepts only `target: force`, and the build rejects any
other value rather than accepting one it would ignore.

**Verbs read the line of scrimmage, so give line verbs to linemen.** `base`, `down`,
`reach`, `double`, `climb` and `cutoff` open by saying who is lined up over the blocker.
A player who starts more than a yard behind the line has nobody over him, so that clause
is dropped for him automatically — but the verb is still a lineman's verb, and a back is
almost always better served by `lead`, `kick`, `hinge` or `decoy`.

### `fronts` — who blocks whom against one front

When the coach has decided the blocks against a particular front, write them under
`fronts`, keyed by the front's id. They replace the play's own assignments for that front
only; every other front still works its blocks out from the intents above.

```json
"fronts": {
  "4-4": {
    "C":  { "block": "man", "man": "S", "help": "RT" },
    "RH": { "block": "man", "man": "R", "how": "Bubble around the right tight end",
            "via": [[3.4, 2.0], [3.6, 4.2]] }
  }
}
```

The build rejects a front that does not exist, a position the formation does not have, and
a `man` or `help` who is not standing in that front.

### Nobody pulls

There is no `pull` verb and there is not meant to be one. A pulling guard asks an
eight-year-old to leave the only spot he has learned, run flat behind two bodies he
cannot see over, and arrive somewhere before a linebacker does — and when he is a
half-count late, which he is, the hole he vacated is the hole the play was going to.
The build rejects one by name.

Every job a puller used to do belongs to somebody who was already standing there: the
**playside end kicks the end out** (`base` with `drive: out`), **a back leads through the
hole** (`lead`), and the **backside guard cuts off** behind the play (`cutoff`).

### `fakes` — what a play-action pass is pretending to be

```json
{ "id": "i-power-boot-l", "type": "pass", "fakes": "i-power-r", ... }
```

A play-action pass takes its **blocking side and hole from the run it names**, not from
the direction the quarterback finishes in. Without that, "playside" meant the boot, and
every side-sensitive rule on the line came out backwards — the fake blocked the mirror
image of the run it was selling, on ten of the twelve passes in the book. A pass that
fakes nothing — a quick throw out of the shotgun — leaves `fakes` out and gives its
`direction` instead; `--check` rejects a pass with neither.

`test_blocking.py` then holds it honest: where the pass and the run give a lineman the
**same verb**, it has to resolve to the **same block**. They are allowed to differ where
the verbs differ — the boot-side tackle hinges and the centre cuts off, because somebody
has to protect a quarterback the run never had — but one verb coming out two ways means
the side is wrong again.

**A play-action pass must block exactly like the run it fakes.** Eight of them were
selling a pulling guard after the runs stopped pulling, which is a fake advertising a
play the defence has never been shown. If you change how a run blocks, change its boot
and its waggle in the same commit.

**Keep it to about fifteen words.** The verb writes a short sentence on purpose; a note
that doubles it undoes the point. If the note restates the verb, delete it.

**`note` is for the one thing this play adds** and nothing else. If the note restates
what the verb already says, delete it. Most blockers need no note at all.

**Ball carriers, fakes, routes and motion keep their `rule`, `type` and `path`**, because
none of those depend on where the defence lines up. Only blocking is resolved.

### Read all three before you commit an intent

```
python generator/preview.py i-power-r          # all three fronts, side by side
python generator/preview.py --formation i-form --audit
python generator/test_schemes.py               # templates, role mapping, fill
```

`--audit` is the one that catches a badly chosen verb: it flags a defender on the
playside nobody blocks, and three blockers arriving on the same man. A verb that reads
well against the 5-3 and leaves an outside linebacker unblocked against the 4-4 is the
exact bug this whole system exists to prevent, and it is invisible unless you look.

## Every left-handed play is written by hand

Neither formation is symmetric — the SL is split to the right on every snap, so flipping
a play would flip his path and leave him aligned on the same side. There is no
`mirror_of` and no mirroring machinery; a left-handed play is its own file.

A left-handed play that leaves the SL on the right is a different play, a blocker short
on the side the ball goes, and `--audit` will tell you so.

**A play that moves the slot says so in its call.** `Regular I Slot Left 35 Power` and
`Split Backs Slot Left 29 Toss` both do, each mirroring its right-hand play so the slot is out
there on the side the ball goes. Use `alignment` to move him and name his side in the
call; a play that moves somebody silently is a play nobody can call.

## House style for rules

- One assignment per player, phrased as a command to an eight-year-old.
- Say what to do, then the one thing that makes it fail. "Block down on the first
  defender inside you. Do not let him cross your face."
- Use playside/backside, not left/right, except where the direction is the point.
- Coaching points are for the coach, not the player — when to call it, what to drill,
  what it looks like when it goes wrong.

## Before adding a formation or a play

The system is the seven-man line (`LTE` … `RTE`), a quarterback, and a
backfield of either a stacked I (`FB` + `TB`), two halfbacks (`LH` + `RH`),
or Wishbone (`FB` + `LH` + `RH`). A slot (`SL`) is the split man when the
look has one; Wishbone does not, so Power kicks with the playside end and
the call has no Slot Right/Left. A new formation that keeps those keys
drops in: give it `formation.json` (alignment, `backs`, `code_prefix`) and
plays that name a scheme and write the paths. Power in the new look is
`"scheme": "Power"` plus the handoff — not eleven new verbs.

A new play in an existing formation is the same: `scheme`, `call`, the carrier's
path, leftover backs if the family does not name them. Dive (2/3) and Slant
(6/7) are reserved and empty; use those words when the hole is those holes.

Check it against [RULES.md](../RULES.md). The league mandates a minimum of three
linebackers and bans blitzing at this age, caps the defensive line at six, and requires
seven on the line of scrimmage. Put the seven-on-the-line check in the formation's
`coaching_notes` the way the existing ones do.
