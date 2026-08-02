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

`id` (must equal the filename), `name`, and `assignments` with an entry for **all
eleven** positions in the formation. `--check` fails the build if one is missing.

Optional: `call`, `type`, `defense` (must match a file in `defense/`),
`install_week`, `direction`, `purpose`, `coaching_points`.

### `name` and `call` are different on purpose

Both are printed at the top of every card. `name` is the teaching name (*Power Right*);
`call` is the huddle call in the team's play-calling language (`Tight 6 Power` —
formation, hole number, play word). The numbering system is documented in the top-level
[README](../README.md). When you add a play, give it a call that fits the system —
inventing a nickname defeats the point of having a language.

Formations carry an `order` field, which is teaching order, not the alphabet. It controls
the sequence on the site and in `PLAYBOOK.md`.

## Mirroring

For a **symmetric** formation, left-handed plays are one file:

```json
{ "id": "power-l", "name": "Power Left", "call": "Tight 5 Power", "mirror_of": "power-r" }
```

The generator flips every path across the middle, swaps the position keys, and swaps the
words "left" and "right" in every rule, purpose and coaching point.

**Only use `mirror_of` when the formation is symmetric.** A position with no counterpart
in the `MIRROR` table maps to itself, which is correct for someone aligned on the middle
(`C`, `QB`, `FB`, `TB`) and wrong for a one-sided back or receiver.

- **Wishbone is symmetric** — it uses `mirror_of`, so a left-handed play is one line.
- **I is not.** The flanker (`Z`) sits to the right on every snap, so mirroring would
  flip his path while leaving him aligned on the same side. I-formation plays are
  authored in both directions by hand.

**This is also why rules never name a specific position.** Write "the playside end", "the
backside guard", "the center" — never "RE" or "LG". Position abbreviations are not
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
