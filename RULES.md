# League rules that shaped this playbook

Notes taken from the 2025 Suffolk County PAL rulebook (updated 10/5/2025) while building
this book. **This is a working summary, not the rulebook.** These are the points that
actually changed plays in here, not a complete list.

The rulebook itself is in [rulebook/](rulebook/), reproduced word for word from the
league's document — quote that one, not this one. Check the league's current release
before relying on either.

## We are an 11-man team

> 5.03: 3rd grade: 8 year olds will participate in either 8 man tackle football or 11
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

> 9.02 – SPECIALIZED GAME MODIFICATIONS FOR INCREASED SAFETY
>
> NO BLITZING PERMITTED 8- & 9-YEAR OLDS IN ALL DIVISIONS.
> IN ASSOCIATION WITH THIS NEW RULE IN DIVISIONS 1 & 2, THE FOLLOWING DEFENSIVE FORMATIONS ARE REQUIRED.
> 1. A MAXIMUM OF A 6 MAN DEFENSIVE LINE. GAP PENETRATION IS ALLOWED.
> 2. A MINIMUM OF 3 LINEBACKERS AT A DISTANCE OF 2 YARDS BEHIND THE LINE OF SCRIMMAGE.
> 3. DEFENSIVE BACKS MAY COVER THE WIDE OUTS BUT MUST BE AT A MINIMUM DISTANCE OF 2 YARDS BENIND THE LINE OF SCRIMMAGE.

`BENIND` is the rulebook's spelling, not a typo here — quotes in this file are exact so
they can be read aloud to an official. The full text is on
[the rules page](https://nickvertucci.github.io/sayville-football-8u-2026/rules.html#section-9)
and in [rulebook/](rulebook/).

The second line is the reason for [the ambiguity below](#an-ambiguity-we-have-not-resolved) —
the no-blitz sentence says *all divisions*, but the formation requirements that follow are
qualified *in Divisions 1 & 2*.

This is the rule with the biggest effect on the playbook, and it cuts two ways.

**It changed which defenses we draw against.** A 6-2 is the most common front in youth
football and it is *not legal here* — it has only two linebackers. Every card in this
book that used to be drawn against a 6-2 is now drawn against a **6-3**, which is the
heaviest front they are allowed to show us: six down linemen is the cap, three
linebackers is the floor. The three fronts in `defense/` are all legal, and the generator fails the build if a new one is not:

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

## The 18-point rule changes the defense (15.04, 15.05)

> 15.04 - The team ahead on defense shall switch to a 6-2-3 defense, two linebackers
> shall drop back 5 yards off the ball, and three safeties shall line up 5-yards behind
> the linebackers.   They may line up anywhere across the field if they stay in a 6-2-3.
>
> 15.05 - Defensive ends are to line up 7 yards outside the offensive tackles.

This is not optional and it is not a coaching choice. The moment the margin reaches 18,
after the extra point, this exact front with these exact depths is required until the
margin drops back under 18 (15.09). It is in the book as **Prevent**.

Note that it **contradicts the minimum of three linebackers in 9.02** — a 6-2-3 has two by
definition. The 18-point rule is the more specific one and wins in that situation, so the
generator's legality check carries an explicit, documented exemption for this front and
for nothing else.

Two more from the same section that catch coaches out:

- **15.03** — at the same moment, the team ahead must also replace its **starting
  backfield, including quarterback**.
- **15.07** — there are no mandatory substitutions on defense under this rule.

What happens to those backfield players next depends on roster size, and 15.03 is
explicit about it:

> On teams of 15 or more players, these players must leave the game on offense. (Clear
> the bench) On teams of 14 or less they must play offensive line (tackle to tackle).
> Under no circumstances will they be permitted to carry the ball.

A roster starts the season at 17 to 32 players (7.01), so the first sentence is the one
that will apply to us: they come off the field, they do not slide down to the line.

## An ambiguity we have not resolved

Rule 9.02 reads:

> NO BLITZING PERMITTED 8- & 9-YEAR OLDS IN ALL DIVISIONS.
> **IN ASSOCIATION WITH THIS NEW RULE IN DIVISIONS 1 & 2**, THE FOLLOWING DEFENSIVE
> FORMATIONS ARE REQUIRED.

The no-blitz rule plainly covers us — it says all divisions. But the defensive formation
requirements that follow are qualified by "in Divisions 1 & 2", and divisions in this
league are competitive tiers assigned from the previous year's record (14.02), not age
groups. So it is genuinely unclear whether the six-lineman cap and the three-linebacker
minimum bind a team in Division 3 or lower.

**This playbook assumes they bind us**, because complying with the stricter reading costs
nothing and the penalty for guessing wrong is 15 yards on the head coach and ejection on a
second offence. Worth one question to the league to confirm.

## Other things worth knowing

- **9.03 — punts are dead, no return.** No punt plays in this book by design.
- **9.04 — field goals and extra point kicks are dead balls, declared, no rush.**
- **15.03 — at an 18-point lead the leading team must replace its starting backfield,
  including quarterback.** Every back should have real reps at more than one spot, which
  is one more reason the same blocking rules are reused across formations.
- **Officials work off NFHS rules** except where PAL modifies them (9.01), so normal
  seven-on-the-line and eligibility rules apply. Every formation in this book is checked
  for exactly seven on the line — see the coaching notes on each one.

## What is not restricted

Nothing in the rulebook prohibits wedge blocking for 11-man play, so the Wedge stays.
Motion is legal in 11-man (it is only banned in the 8v8 Rookie division), so Jet stays.
Both are worth re-checking each season — they are the first things leagues take away.
