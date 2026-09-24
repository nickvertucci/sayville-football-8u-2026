#!/usr/bin/env python3
"""Check the install calendar and the per-practice pages against install.json.

The install page is now two things that can drift apart from each other and from the
schedule underneath them: a month grid whose squares are links, and one page per
practice sitting behind those links. The failure that matters is silent — a practice
that has a page but no square, a square pointing at a page that was never written, or
a practice whose plays are listed on the schedule and then missing from the page a
coach actually reads on the field.

So this reads the generated HTML back and compares it against install.json:

    python generator/test_install.py

It also runs the date validator against deliberately broken schedules, because a check
that accepts everything passes just as quietly as one that works.

No dependencies, no browser. Run it after touching write_install(), write_install_day()
or validate_install().
"""

import copy
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render          # noqa: E402
import site_build      # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# (what it is, the practices to try, should the check reject it?)
DATE_CASES = [
    ("the real dates",        None,                                       False),
    ("no dates at all",       [{"n": 1}, {"n": 2}],                       False),
    ("a hand-typed weekday",  [{"n": 1, "date": "Mon, Aug 11"}],          True),
    ("a date the wrong way",  [{"n": 1, "date": "08/11/2026"}],           True),
    ("a month that does not exist", [{"n": 1, "date": "2026-13-01"}],     True),
    ("practice 2 before practice 1",
     [{"n": 1, "date": "2026-08-18"}, {"n": 2, "date": "2026-08-11"}],    True),
    ("two practices on one day",
     [{"n": 1, "date": "2026-08-11"}, {"n": 2, "date": "2026-08-11"}],    False),
    ("one practice still undated",
     [{"n": 1, "date": "2026-08-11"}, {"n": 2}, {"n": 3, "date": "2026-08-18"}], False),
]


# A rotation card is a lineup per snap, and the coach reads it on the field with boys
# already moving. Every way it can be wrong reads perfectly well on the page:
#
#   (what it is, the block to try, should the check reject it?)
#
# The good case is first and is deliberately the shape practice 8 uses, so this fails
# if the real card ever stops validating.
ROTATION_SPOTS_UNDER_TEST = ["X", "Y", "Z", "QB", "FB", "TB"]
GOOD_SNAP = ["Camden G.", "Michael M.", "Philip A.", "Brogan A.", "Jake G.", "Nico V."]

ROTATION_CASES = [
    ("the first eleven, every man on his own spot",
     [{"men": list(GOOD_SNAP)}],                                                False),
    # Brogan is the quarterback and nothing else. Putting him at tailback is the
    # mistake that looks most like coaching and is least like the chart.
    ("a boy at a spot he is not listed at",
     [{"men": ["Camden G.", "Michael M.", "Philip A.", "Brogan A.", "Jake G.",
               "Brogan A."]}],                                                  True),
    # One boy cannot be in two places on one snap, and on paper it is invisible.
    ("the same boy twice on one snap",
     [{"men": ["Camden G.", "Camden G.", "Philip A.", "Brogan A.", "Jake G.",
               "Nico V."]}],                                                    True),
    ("five men for six spots",
     [{"men": ["Camden G.", "Michael M.", "Philip A.", "Brogan A.", "Jake G."]}], True),
    ("a made-up name",
     [{"men": ["Nobody A.", "Michael M.", "Philip A.", "Brogan A.", "Jake G.",
               "Nico V."]}],                                                    True),
    # A rotation is not an install. Running a play nobody has been taught is the
    # same mistake the `review` rule already refuses.
    ("a snap on a play that is not installed yet",
     [{"play": "wb-toss-r", "men": list(GOOD_SNAP)}],                           True),
    ("a snap on a play that does not exist",
     [{"play": "not-a-play", "men": list(GOOD_SNAP)}],                          True),
    ("a snap on an installed play",
     [{"play": "sb-toss-r", "men": list(GOOD_SNAP)}],                           False),
]


# A practice already run is a record, so the chart check leaves it alone: the chart
# moves on after the night and the lineup that ran should not stop the build. The
# cases above are dated far ahead so they are always a plan and always checked.
FUTURE_DATE = "2099-08-11"
PAST_DATE = "2000-08-11"


def check_rotations(schedule, formations, defenses, roster) -> int:
    """Run the validator against deliberately broken rotation cards."""
    bad = 0
    cases = list(ROTATION_CASES) + [
        ("a boy off the chart, at a practice already run",
         [{"men": ["Nobody A.", "Michael M.", "Philip A.", "Brogan A.", "Jake G.",
                   "Nico V."]}], False, PAST_DATE),
    ]
    for what, snaps, should_reject, *on in cases:
        trial = copy.deepcopy(schedule)
        trial["practices"] = [{
            "n": 1,
            "date": on[0] if on else FUTURE_DATE,
            "phase": "preseason",
            "plays": ["sb-toss-r"],
            "blocks": [{"tag": "A", "kind": "rotation", "title": "Rotation",
                        "spots": list(ROTATION_SPOTS_UNDER_TEST), "snaps": snaps}],
        }]
        errors = [e for e in render.validate_install(trial, formations, defenses, roster)
                  if "Rotation" in e]
        rejected = bool(errors)
        if rejected != should_reject:
            verb = "accepted" if not rejected else "rejected"
            print(f"FAIL  rotation: {what} was {verb}")
            bad += 1
    print(f"{len(cases)} rotation cases behaved as expected "
          f"({sum(1 for c in cases if c[2])} rejected, "
          f"{sum(1 for c in cases if not c[2])} accepted).")
    return bad


def check_pages(schedule, formations, defenses) -> int:
    """Every practice has a page, the calendar links to it, and the page says what the
    schedule says it says."""
    bad = 0
    practices = schedule.get("practices", [])
    index = (ROOT / "install.html").read_text(encoding="utf-8")
    plays = {p["id"]: p for f in formations for p in f["_plays"]}

    for pr in practices:
        href = site_build.install_href(pr)
        page = ROOT / href

        if not page.is_file():
            print(f"FAIL  practice {pr['n']}: no {href}")
            bad += 1
            continue
        html = page.read_text(encoding="utf-8")

        # The schedule page has to reach it, from the calendar and from the list.
        for where, pattern in (
            ("calendar", f'<a class="cal-ev" href="{href}"'),
            ("practice list", f'<a class="ins-row" href="{href}"'),
        ):
            if pattern not in index:
                print(f"FAIL  practice {pr['n']}: not on the install page's {where}")
                bad += 1

        # Its own page has to carry the practice, not just its number.
        if pr.get("focus", "") and site_build.esc(pr["focus"]) not in html:
            print(f"FAIL  {href}: does not name its focus")
            bad += 1

        day = site_build.practice_date(pr)
        if day and site_build.date_label(day, long=True) not in html:
            print(f"FAIL  {href}: does not print {site_build.date_label(day, long=True)}")
            bad += 1

        # The install itself — the one thing a coach opens the page for.
        for pid in pr.get("plays", []):
            if f'href="{site_build.p_href(plays[pid])}"' not in html:
                print(f"FAIL  {href}: does not link the play it installs, {pid}")
                bad += 1
        for fid in pr.get("fronts", []):
            if f'href="{site_build.d_href(defenses[fid])}"' not in html:
                print(f"FAIL  {href}: does not link the front it installs, {fid}")
                bad += 1

        # Everything on the schedule for that practice, block by block.
        for blk in site_build.practice_agenda(pr):
            if blk.get("title") and site_build.esc(blk["title"]) not in html:
                print(f"FAIL  {href}: block {blk.get('tag')} "
                      f"({blk.get('title')}) is missing")
                bad += 1
        if pr.get("emphasis") and site_build.esc(pr["emphasis"]) not in html:
            print(f"FAIL  {href}: the coaching emphasis is missing")
            bad += 1
        if pr.get("huddle") and site_build.esc(pr["huddle"]) not in html:
            print(f"FAIL  {href}: the team huddle is missing")
            bad += 1

    # And nothing links at a practice page that does not exist.
    for href in sorted(set(re.findall(r'href="(install-\d+\.html)"', index))):
        if not (ROOT / href).is_file():
            print(f"FAIL  install.html links {href}, which was never written")
            bad += 1

    numbers = {pr["n"] for pr in practices}
    for page in sorted(ROOT.glob("install-*.html")):
        n = int(page.stem.split("-")[1])
        if n not in numbers:
            print(f"FAIL  {page.name} is left over — no practice {n} on the schedule")
            bad += 1

    if not bad:
        print(f"{len(practices)} practice page(s) match install.json, and the calendar "
              f"reaches every one of them.")
    return bad


def check_dates(schedule, formations, defenses) -> int:
    """The date check rejects what it is there to reject."""
    bad = 0
    for label, practices, should_reject in DATE_CASES:
        trial = copy.deepcopy(schedule)
        if practices is not None:
            trial["practices"] = practices
            trial.pop("phases", None)
        errors = [e for e in render.validate_install(trial, formations, defenses)
                  if "date" in e or "dated before" in e]
        if bool(errors) != should_reject:
            bad += 1
            wanted = "rejected" if should_reject else "accepted"
            print(f"FAIL  {label}: should have been {wanted}")
            for e in errors:
                print(f"        {e}")
    if not bad:
        print(f"{len(DATE_CASES)} date cases behaved as expected.")
    return bad


def main() -> int:
    formations = render.load_formations()
    defenses = render.load_defenses()
    schedule = render.load_install()

    if not (ROOT / "install.html").is_file():
        print("install.html has not been generated — run generator/render.py first.")
        return 1

    bad = check_pages(schedule, formations, defenses)
    bad += check_dates(schedule, formations, defenses)
    bad += check_rotations(schedule, formations, defenses, render.load_roster())
    if bad:
        print(f"\n{bad} problem(s).")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
