# League rules that shaped this playbook

Notes taken from the 2025 Suffolk County PAL rulebook (updated 10/5/2025) while building
this book. **This is a working summary, not the rulebook.** Check the current season's
rulebook before you rely on any of it — these are the points that actually changed plays
in here, not a complete list.

## We are an 11-man team

> 5.03 — 3rd grade: 8 year olds will participate in either 8 man tackle football or 11
> man tackle football

Both exist at this age. Everything in this repo is **11-man**. If our team ends up in the
Rookie Tackle 8v8 division instead, none of it is legal — that division is a separate
rulebook (Section 19) with 8 players, 5 linemen and 3 backs, and the differences below
are severe enough that the book would have to be rewritten, not adapted:

- Motion is illegal — that kills Jet.
- The quarterback sneak is specifically prohibited — that kills Sneak.
- The quarterback may only carry the ball once per four plays, and only outside the
  tackles — that limits Keep and Boot.
- Only one handoff per play, no double reverses.
- Backs may not line up more than one yard outside the last lineman — our wings and
  flankers are wider than that.

**Confirm the division before installing anything.**

## No blitzing, and a minimum of three linebackers

> 9.02 — NO BLITZING PERMITTED 8- & 9-YEAR OLDS IN ALL DIVISIONS.
> A MAXIMUM OF A 6 MAN DEFENSIVE LINE. GAP PENETRATION IS ALLOWED.
> A MINIMUM OF 3 LINEBACKERS AT A DISTANCE OF 2 YARDS BEHIND THE LINE OF SCRIMMAGE.
> DEFENSIVE BACKS ... MUST BE AT A MINIMUM DISTANCE OF 2 YARDS BEHIND THE LINE OF SCRIMMAGE.

This is the rule with the biggest effect on the playbook, and it cuts two ways.

**It changed which defenses we draw against.** A 6-2 is the most common front in youth
football and it is *not legal here* — it has only two linebackers. Every card in this
book that used to be drawn against a 6-2 is now drawn against a **6-3**, which is the
heaviest front they are allowed to show us: six down linemen is the cap, three
linebackers is the floor. The three fronts in `generator/defenses/` are all legal:

| Front | Down linemen | Linebackers | Legal |
|---|---|---|---|
| 6-3 | 6 | 3 | yes — this is the maximum front |
| 5-3 | 5 | 3 | yes |
| 4-4 | 4 | 4 | yes |

**It makes our passing game safer than it looks.** Nobody may cross the line before the
snap, so the quarterback always has time. That is why Boot and Waggle are in the book at
all — at this age they are close to free yards, and the coaching points say so.

Gap penetration *is* allowed, so down blocks still have to be fast. Do not read
"no blitzing" as "nobody is coming."

## Other things worth knowing

- **9.03 — punts are dead, no return.** No punt plays in this book by design.
- **9.04 — field goals and extra point kicks are dead balls, declared, no rush.**
- **15.03 — at an 18-point lead the leading team must replace its entire starting
  backfield, including the quarterback.** Every back should have real reps at more than
  one spot, which is one more reason the same blocking rules are reused across
  formations.
- **Officials work off NFHS rules** except where PAL modifies them (9.01), so normal
  seven-on-the-line and eligibility rules apply. Every formation in this book is checked
  for exactly seven on the line — see the coaching notes on each one.

## What is not restricted

Nothing in the rulebook prohibits wedge blocking for 11-man play, so the Wedge stays.
Motion is legal in 11-man (it is only banned in the 8v8 Rookie division), so Jet stays.
Both are worth re-checking each season — they are the first things leagues take away.
