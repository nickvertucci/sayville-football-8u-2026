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
"LG": {"rule": "Pull right, wrap", "type": "block", "path": [[0.4, -1.2], [5.0, -1.0], [6.2, 1.5]]}
```

means the left guard goes 0.4 right / 1.2 back, then 5.0 right / 1.0 back of where he
started, then up to 5.0 right / 1.5 downfield.

## Path types

| `type` | Drawn as | Use for |
|---|---|---|
| `block` | solid line, perpendicular bar at the end | any blocking assignment |
| `run` | solid line, arrowhead | the ball carrier |
| `pass` | dashed line, arrowhead | routes and the quarterback's drop or roll |
| `fake` | dashed line, arrowhead | decoys carrying out fakes |
| `motion` | dashed line, arrowhead | pre-snap motion |

The ball carrier's line is drawn thicker and in red — set `ball_carrier` to his position
key. On pass plays, set it to the primary receiver.

## Required fields

**A play** needs `id` (must equal the filename, and be unique across every formation),
`name`, and `assignments` with an entry for **all eleven** positions in the formation.
`--check` fails the build if one is missing.

Optional: `call`, `type`, `defense` (must match a file in `defense/`),
`order`, `direction`, `purpose`, `coaching_points`, `alignment`.

### `alignment` — moving somebody for one play

A formation has one alignment, but a formation is not always one picture. A play may
move a player who has more than one legal spot in the same eleven-man look:

```json
"alignment": { "Z": [-2.6, -3.3] }
```

That is a Power I play offsetting the Z to the weak side instead of its default
strong-side backfield spot. Everything else — the line rules, the other ten spots — is
unchanged, and the player's `path` is still relative to wherever he ends up, so the
assignment does not have to know which look it is in.

**Say it in the call.** `Power I Left 35 Power` tells the huddle which side the Z is
offset to, the same way `Regular I Z Right 20 Dive` names the Z's side. A play that moves
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

**A formation** needs `id` (must equal the folder name), `name`, an `alignment` of
exactly eleven players, and `backs` — the digit-to-position map its calls are numbered
from:

```json
"backs": { "1": "QB", "2": "FB", "3": "TB", "4": "Z" }
```

`backs` is not documentation. It is what the generator resolves the first digit of every
call against, and it is what the calling-language table on the home page is built from,
so there is one copy of the numbering rather than three that can disagree.

### `name` and `call` are different on purpose

Both are printed at the top of every card. `name` is the teaching name (*House Power
Right*); `call` is the huddle call in the team's play-calling language (`House 44 Power` —
formation, then **two digits: who carries it and where it goes**, then the play word).
The numbering system is documented in the top-level [README](../README.md).

**The build checks the call against the diagram**, so a call is not free text:

- The first digit is a back number from the formation's `backs` map, so it has to be one
  the formation actually defines.
- The second digit is the hole. Even is right, odd is left, counting outward from the
  center. The generator measures where that back's path crosses the line of scrimmage and
  fails the build if it does not land in the hole the call names.

That means the digits describe **the back the first digit names**, not the ball carrier.
On `I Z Right 16 Boot` the `1` is the quarterback going through the 6 hole; `ball_carrier`
is the Z he throws to, which is a different thing.

Inventing a nickname instead of a call defeats the point of having a language, and now
also fails `--check`.

Formations carry an `order` field too, which is teaching order, not the alphabet.
Both control the sequence on the site and in `PLAYBOOK.md`.

### Write assignments for the 5-3

Every offensive play is drawn against the 5-3, so write the rules for that front:
the center has the nose head up, **both guards are uncovered**, each tackle has a
tackle on his inside shoulder, each end has an end head up, and the gap between our
tackle and our end is open. A rule that tells a guard to block the man over him is
wrong against this front.

## Mirroring

For a **symmetric** formation, left-handed plays are one file:

```json
{ "id": "fh-power-l", "name": "House Power Left", "call": "House 35 Power", "mirror_of": "fh-power-r" }
```

The generator flips every path across the middle, swaps the position keys, and swaps the
words "left" and "right" in every rule, purpose and coaching point.

**The call is not mirrored — you write it.** Mirroring swaps `TB` and `Z`, so the back
digit changes too: `House 44 Power` is the `Z` (the left back) through the 4 hole, and its
mirror is `House 35 Power` — the `TB`, back 3, through the 5 hole. Get that wrong and
the call check catches it, because the digits no longer match the flipped path.

**Only use `mirror_of` when the formation is symmetric.** A position with no counterpart
in the `MIRROR` table maps to itself, which is correct for someone aligned on the middle
(`C`, `QB`, `FB`) and wrong for a one-sided back or receiver; the two side backs are
named `TB` and `Z` and the table swaps them.

- **Full House is symmetric** — it uses `mirror_of`, so a left-handed play is a
  four-line file.
- **Regular I, Power I and Split Backs are not.** The `Z` sits on the right on every
  snap — out wide in the Regular I and the Split Backs, in the backfield in the Power
  I — so mirroring would flip its path while leaving it aligned on the same side. Their
  left-handed plays are authored by hand, and their two side backs carry keys the
  `MIRROR` table would not swap anyway (`LH` and `RH` in the Split Backs).

**This is also why rules never name a specific position.** Write "the playside end", "the
backside guard", "the center" — never "RTE" or "LG". Position abbreviations are not
mirrored and end up pointing at the wrong player. For the same reason, avoid words that
merely contain "left" or "right" as a substring.

## House style for rules

- One assignment per player, phrased as a command to an eight-year-old.
- Say what to do, then the one thing that makes it fail. "Block down on the first
  defender inside you. Do not let him cross your face."
- Use playside/backside, not left/right, except where the direction is the point.
- Coaching points are for the coach, not the player — when to call it, what to drill,
  what it looks like when it goes wrong.

## Before adding a formation or a play

Check it against [RULES.md](../RULES.md). The league mandates a minimum of three
linebackers and bans blitzing at this age, caps the defensive line at six, and requires
seven on the line of scrimmage. Put the seven-on-the-line check in the formation's
`coaching_notes` the way the existing ones do.
