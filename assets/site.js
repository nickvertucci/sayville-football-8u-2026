/* The defensive-front toggle on a play page.

   Every front's diagram and assignments are already in the page, so this only moves a
   class. Two things make it worth its twenty lines: the choice is remembered, because
   a coach who has scouted the team they are playing wants every play in the book in
   that front and not to press a button fifty-six times; and it works on the print
   page too, where several plays are on one document at once. */
(function () {
  var KEY = 'sayville.front';
  var groups = [].slice.call(document.querySelectorAll('.play'));
  if (!groups.length) return;

  function apply(play, front) {
    var hit = false;
    [].forEach.call(play.querySelectorAll('.dpanel'), function (p) {
      var on = p.dataset.front === front;
      p.classList.toggle('on', on);
      hit = hit || on;
    });
    [].forEach.call(play.querySelectorAll('.dtab'), function (t) {
      var on = t.dataset.front === front;
      t.classList.toggle('on', on);
      t.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    return hit;
  }

  function show(front) {
    groups.forEach(function (play) { apply(play, front); });
    try { localStorage.setItem(KEY, front); } catch (e) { /* private window */ }
  }

  groups.forEach(function (play) {
    [].forEach.call(play.querySelectorAll('.dtab'), function (tab) {
      tab.addEventListener('click', function () { show(tab.dataset.front); });
    });
  });

  /* A remembered front that this build no longer has would blank the diagram, so it
     is only applied if a panel actually answers to it. */
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) { saved = null; }
  if (saved && groups[0].querySelector('.dpanel[data-front="' + saved + '"]')) {
    show(saved);
  }
}());

/* Site navigation: hamburger drawer on a phone, dropdown on a desktop. */
(function () {
  var burger = document.getElementById('burger');
  var drawer = document.getElementById('drawer');
  var scrim = document.getElementById('scrim');
  var close = document.getElementById('dclose');
  var drops = [
    [document.getElementById('ddbtn'), document.getElementById('ddpanel')],
    [document.getElementById('dfbtn'), document.getElementById('dfpanel')]
  ].filter(function (d) { return d[0] && d[1]; });

  function openDrawer(on) {
    if (!drawer) return;
    if (on) drawer.hidden = false;
    // Let the element paint before transitioning in, or it jumps instead of sliding.
    requestAnimationFrame(function () { drawer.classList.toggle('open', on); });
    scrim.hidden = !on;
    burger.setAttribute('aria-expanded', on ? 'true' : 'false');
    document.body.classList.toggle('locked', on);
    if (!on) setTimeout(function () {
      if (!drawer.classList.contains('open')) drawer.hidden = true;
    }, 250);
  }

  function openDrop(which, on) {
    drops.forEach(function (d) {
      var show = on && d === which;
      d[1].hidden = !show;
      d[0].setAttribute('aria-expanded', show ? 'true' : 'false');
    });
  }

  function anyDropOpen() {
    return drops.some(function (d) { return !d[1].hidden; });
  }

  if (burger) burger.addEventListener('click', function () {
    openDrawer(burger.getAttribute('aria-expanded') !== 'true');
  });
  if (close) close.addEventListener('click', function () { openDrawer(false); burger.focus(); });
  if (scrim) scrim.addEventListener('click', function () { openDrawer(false); });

  drops.forEach(function (d) {
    d[0].addEventListener('click', function (e) {
      e.stopPropagation();
      openDrop(d, d[1].hidden);
    });
  });
  document.addEventListener('click', function (e) {
    if (!anyDropOpen()) return;
    var inside = drops.some(function (d) {
      return d[1].contains(e.target) || e.target === d[0];
    });
    if (!inside) openDrop(null, false);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (anyDropOpen()) openDrop(null, false);
    if (drawer && drawer.classList.contains('open')) { openDrawer(false); burger.focus(); }
  });
  // Crossing the breakpoint with the drawer open would leave the page scroll locked.
  window.addEventListener('resize', function () {
    if (window.innerWidth >= 1000 && drawer && drawer.classList.contains('open')) {
      openDrawer(false);
    }
    if (window.innerWidth < 1000) openDrop(null, false);
  });

  // Bring the current play into view in whichever menu is open.
  [document.getElementById('ddpanel'), document.getElementById('dfpanel'),
   drawer].forEach(function (root) {
    if (!root) return;
    var here = root.querySelector('.mplay.here');
    if (here) here.scrollIntoView({ block: 'nearest' });
  });
})();

/* The install calendar: which square is today, which practice is next.
   Both are done here rather than in the generator on purpose — a "today" baked into a
   static page is wrong the morning after the page was built, and this site is rebuilt
   whenever a play changes, not every night. */
(function () {
  var cells = document.querySelectorAll('.cal-cell[data-date]');
  if (!cells.length) return;
  var now = new Date();
  var today = now.getFullYear() + '-' +
    String(now.getMonth() + 1).padStart(2, '0') + '-' +
    String(now.getDate()).padStart(2, '0');

  var next = null;
  cells.forEach(function (cell) {
    var d = cell.dataset.date;
    if (d === today) cell.classList.add('is-today');
    else if (d < today) cell.classList.add('is-past');
    var ev = cell.querySelector('.cal-ev');
    if (ev && !next && d >= today) next = { cell: cell, ev: ev, date: d };
  });

  var box = document.getElementById('calnext');
  if (!box || !next) return;
  var when = next.date === today ? 'Today' : new Date(next.date + 'T12:00:00')
    .toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
  var name = next.ev.querySelector('.cal-ev-n');
  var focus = next.ev.querySelector('.cal-ev-t');
  box.innerHTML = '<b>Next up &mdash; ' + when + '.</b> ' +
    '<a href="' + next.ev.getAttribute('href') + '">' +
    (name ? name.textContent : 'Next practice') + '</a> ' +
    '<span>' + (focus ? focus.textContent : '') + '</span>';
  box.hidden = false;
  next.ev.classList.add('is-next');
})();

/* Arrow keys walk through the plays in a formation. */
(function () {
  var main = document.querySelector('main');
  if (!main) return;
  var prev = main.dataset.prev, next = main.dataset.next;
  if (!prev && !next) return;
  document.addEventListener('keydown', function (e) {
    var t = e.target.tagName;
    if (t === 'INPUT' || t === 'TEXTAREA' || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === 'ArrowLeft' && prev) location.href = prev;
    if (e.key === 'ArrowRight' && next) location.href = next;
  });
})();

/* Call sheet filtering.

   Every chip belongs to a group (formation, type, zone, direction, carrier). Picking
   two chips in the SAME group widens the list — Regular I or Split Backs. Picking
   chips in DIFFERENT groups narrows it — Split Backs AND runs. The old single-string
   filter could not express that at all: formation and type shared one exclusive group,
   so "Split Backs runs" quietly turned into "all runs". */
(function () {
  var q = document.getElementById('q');
  if (!q) return;
  var rows = Array.prototype.slice.call(document.querySelectorAll('#calls tbody tr'));
  var chips = Array.prototype.slice.call(document.querySelectorAll('.chip'));
  var count = document.getElementById('count');
  var empty = document.getElementById('empty');
  var clear = document.getElementById('clear');
  var moreBtn = document.getElementById('morebtn');
  var more = document.getElementById('morefilters');
  var badge = document.getElementById('morebadge');
  var summary = document.getElementById('activefilters');
  var total = rows.length;
  var active = {};

  // Groups whose chips live in the collapsed panel, so an active filter there can be
  // reported on the toggle instead of being hidden.
  var HIDDEN_GROUPS = ['zone', 'dir', 'carrier'];

  function chosen(group) { return active[group] || []; }

  function activeTotal() {
    var n = 0;
    for (var g in active) n += active[g].length;
    return n;
  }

  function apply() {
    var term = q.value.trim().toLowerCase();
    var n = 0;
    rows.forEach(function (r) {
      var show = true;
      for (var g in active) {
        var picked = active[g];
        // An empty group is not a filter — it means "any".
        if (picked.length && picked.indexOf(r.dataset[g]) === -1) { show = false; break; }
      }
      if (show && term && r.dataset.search.indexOf(term) === -1) show = false;
      r.hidden = !show;
      if (show) n++;
    });

    var filtered = activeTotal() > 0 || term;
    count.textContent = filtered
      ? n + ' of ' + total + (total === 1 ? ' play' : ' plays')
      : total + (total === 1 ? ' play' : ' plays');
    empty.hidden = n !== 0;
    clear.hidden = !filtered;

    var hiddenCount = 0;
    HIDDEN_GROUPS.forEach(function (g) { hiddenCount += chosen(g).length; });
    badge.hidden = hiddenCount === 0;
    badge.textContent = hiddenCount;

    drawSummary();
  }

  /* Every filter currently applied, spelled out and individually removable.

     Multi-select means a second click on a different formation ADDS it rather than
     switching to it — pick Regular I then Split Backs and you are looking at every
     plays, not five. That is correct behaviour and it is also the easiest thing in
     the world to do by accident, so what is applied has to be readable in one glance
     rather than inferred from which chips look dark. */
  function drawSummary() {
    summary.innerHTML = '';
    var any = false;
    chips.forEach(function (c) {
      if (chosen(c.dataset.group).indexOf(c.dataset.value) === -1) return;
      any = true;
      var pill = document.createElement('button');
      pill.type = 'button';
      pill.className = 'pill';
      pill.innerHTML = '<span class="pg">' + c.dataset.glabel + '</span> '
        + c.dataset.label + '<span class="px">\u00d7</span>';
      pill.setAttribute('aria-label', 'Remove filter ' + c.dataset.glabel + ' '
        + c.dataset.label);
      pill.addEventListener('click', function () { c.click(); });
      summary.appendChild(pill);
    });
    summary.hidden = !any;
  }

  q.addEventListener('input', apply);

  chips.forEach(function (c) {
    c.addEventListener('click', function () {
      var g = c.dataset.group, v = c.dataset.value;
      var picked = active[g] || (active[g] = []);
      var at = picked.indexOf(v);
      if (at === -1) picked.push(v); else picked.splice(at, 1);
      c.setAttribute('aria-pressed', at === -1 ? 'true' : 'false');
      apply();
    });
  });

  clear.addEventListener('click', function () {
    active = {};
    chips.forEach(function (c) { c.setAttribute('aria-pressed', 'false'); });
    q.value = '';
    apply();
    q.focus();
  });

  if (moreBtn && more) moreBtn.addEventListener('click', function () {
    var open = moreBtn.getAttribute('aria-expanded') === 'true';
    moreBtn.setAttribute('aria-expanded', open ? 'false' : 'true');
    more.hidden = open;
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement !== q) { e.preventDefault(); q.focus(); }
    if (e.key === 'Escape' && document.activeElement === q) { q.value = ''; apply(); }
  });
  apply();
})();

/* The depth chart board.

   Drag a name to another spot, or tap a name and then tap where it goes. Both run
   the same move(): a drag is tap-then-tap with the finger held down in between, and
   implementing it twice is how the two quietly come to disagree.

   The DOM is the state. Every cell carries its side, position and rotation, so "what
   does the chart say" is a query and there is no second copy to keep honest.
   localStorage holds placements only — the roster the page shipped with stays both
   the reset point and the baseline the Copy button edits, which is what keeps a
   local rearrangement from ever being mistaken for the roster in the repo. */
(function () {
  var board = document.getElementById('dc-board');
  var blob = document.getElementById('dc-data');
  if (!board || !blob) return;
  var data = JSON.parse(blob.textContent);
  var KEY = 'sayville-depth-chart-v1';
  var LEGACY_ROT = { purple: 'd1', gold: 'd2', white: 'd3' };
  var edited = document.getElementById('dc-edited');
  var resetBtn = document.getElementById('dc-reset');
  var copyBtn = document.getElementById('dc-copy');
  // Every drop target on the page. A package slot is one of these too: it takes a
  // name the same way a board cell does, so it goes in the selector rather than into
  // a second set of handlers that would have to be kept in step with this one.
  var SLOT = 'td.dc-cell, .dc-pkg-slot, .dc-pool';
  var HOLDER = 'td.dc-cell, .dc-pkg-slot';

  function all(sel, ctx) {
    return Array.prototype.slice.call((ctx || board).querySelectorAll(sel));
  }
  function sideOf(el) {
    var side = el.closest('.dc-side');
    return side ? side.dataset.side : '';
  }
  function chipIn(slot) { return slot.querySelector('.dc-chip'); }

  /* A cell with nobody in it says Open, and says it as a button so that the spot can
     be tabbed to and chosen from a keyboard exactly like a name can. The squad rail
     needs no such marker — it is never empty. */
  function fill(slot) {
    if (!slot.matches(HOLDER)) return;
    var has = chipIn(slot), open = slot.querySelector('.dc-open');
    if (has && open) open.remove();
    if (!has && !open) {
      slot.innerHTML = '<button type="button" class="dc-open">Open</button>';
    }
  }

  function isPool(el) { return el.classList.contains('dc-pool'); }

  /* Three rules, and every gesture on this page is one of them.

       squad rail -> spot   assign. The rail is a source, not a container, so the kid
                            stays in it and the board gets a copy. This is the whole
                            reason a kid can be on all three units at once.
       spot -> spot         move, swapping with whoever is there.
       spot -> squad rail   take him out of that spot.

     The one thing none of them may produce is the same kid twice in one rotation. He
     cannot be at left tackle and centre on the unit that is on the field, so an
     assignment that would do it takes him off the first spot instead — which turns
     out to read as a move, which is what a coach expected anyway. */
  function move(chip, target) {
    var from = chip.parentNode;
    if (!target || from === target) return;
    // Offense chips stay on offense. The two sides are separate problems and a kid
    // is on both of them; dragging across would merge two answers into one.
    if (sideOf(target) !== sideOf(chip)) return;

    if (isPool(target)) {
      // Off the board. A rail chip dropped back on the rail is a no-op, caught above.
      if (isPool(from)) return;
      chip.remove();
      fill(from);
      refresh();
      return;
    }

    // From the rail the chip is a template: clone it and leave the original in place.
    var moving = isPool(from) ? chip.cloneNode(true) : chip;
    if (moving !== chip) moving.classList.remove('picked', 'ghost', 'placed');

    var held = chipIn(target);
    if (held) {
      // A swap when he came off the board, a bump to nowhere when he came off the
      // rail — there is no spot to send the incumbent back to in that case.
      if (moving === chip) from.appendChild(held); else held.remove();
    }
    var open = target.querySelector('.dc-open');
    if (open) open.remove();
    target.appendChild(moving);

    // A kid may appear as many times in a column as the coach wants. This used to
    // clear him out of every other spot in the same column on the grounds that he
    // cannot be in two places at once — which is true of a unit that takes the field
    // together and false of a depth chart. Column 2 is not the second eleven; it is
    // "second in line here", and the same backup can be second at left tackle and
    // second at right tackle without ever playing both at once.

    fill(from);
    fill(target);
    refresh();
  }

  /* Every placement on the board — the cells only. The squad rail is the roster and
     never changes, so saving it would be saving the input. A record names its spot
     rather than pointing at it, so one whose spot has since gone from roster.json is
     skipped instead of taking the whole save down with it. */
  function snapshot() {
    var out = [];
    all(HOLDER).forEach(function (td) {
      var c = chipIn(td);
      if (!c) return;
      // A package slot has no rot/pos, so it names itself: "pkg" and its number, then
      // which of the two it is. Same four-part shape as a board record, so restore()
      // needs no second branch and an old save stays readable.
      out.push(td.dataset.pkg
        ? [sideOf(td), 'pkg', td.dataset.pkg + ':' + td.dataset.at, c.dataset.name]
        : [sideOf(td), td.dataset.rot, td.dataset.pos, c.dataset.name]);
    });
    return out;
  }

  var pristine = JSON.stringify(snapshot());

  function persist() {
    var now = JSON.stringify(snapshot());
    var dirty = now !== pristine;
    try {
      if (dirty) localStorage.setItem(KEY, now);
      // Dragging the last kid back where he started is a reset. Clearing the key
      // rather than storing a board identical to the shipped one means there is only
      // one way to be unedited, and the banner cannot get stuck on.
      else localStorage.removeItem(KEY);
    } catch (e) { /* private mode: the board still works, it just will not keep */ }
    if (edited) edited.hidden = !dirty;
    if (resetBtn) resetBtn.hidden = !dirty;
  }

  function restore() {
    var raw = null, at;
    try { raw = localStorage.getItem(KEY); } catch (e) { return; }
    if (!raw) return;
    try { at = JSON.parse(raw); } catch (e) { return; }
    if (!Array.isArray(at)) return;

    var byKey = {}, template = {};
    all(HOLDER).forEach(function (td) {
      byKey[td.dataset.pkg
        ? sideOf(td) + '/pkg/' + td.dataset.pkg + ':' + td.dataset.at
        : sideOf(td) + '/' + td.dataset.rot + '/' + td.dataset.pos] = td;
    });
    all('.dc-pool .dc-chip').forEach(function (c) {
      template[sideOf(c) + '/' + c.dataset.name] = c;
    });
    // Clear the board and set it out again from the save. Every chip on it is a copy
    // of a rail chip, so there is nothing here to preserve — only to rebuild.
    all(HOLDER).forEach(function (td) { td.innerHTML = ''; fill(td); });

    at.forEach(function (rec) {
      // A board saved while the columns were still called Purple, Gold and White.
      // Without this every record misses its cell, and the coach who rearranged his
      // line at halftime opens the page to the shipped roster and no explanation.
      var rot = LEGACY_ROT[rec[1]] || rec[1];
      var td = byKey[rec[0] + '/' + rot + '/' + rec[2]];
      var src = template[rec[0] + '/' + rec[3]];
      // A spot or a kid that has left roster.json since this was saved. Dropping the
      // one record keeps the rest of the board, which is the point of naming spots.
      if (!td || !src || chipIn(td)) return;
      var chip = src.cloneNode(true);
      chip.classList.remove('picked', 'ghost', 'placed');
      var open = td.querySelector('.dc-open');
      if (open) open.remove();
      td.appendChild(chip);
    });
  }

  function refresh() {
    /* The rail carries the whole squad now, so it needs to say who in it is actually
       doing something. A kid already on the board is dimmed and wears the number of
       spots he holds; the ones left bright are the ones nobody has given a job. That
       is the question the rail is scanned for.

       Spots, not rotations: two of them can be in the same column now, because a
       backup can be second in line at two different positions. */
    ['offense', 'defense'].forEach(function (side) {
      var sec = board.querySelector('.dc-side[data-side="' + side + '"]');
      if (!sec) return;
      var spots = {};
      all('td.dc-cell .dc-chip, .dc-pkg-slot .dc-chip', sec).forEach(function (c) {
        spots[c.dataset.name] = (spots[c.dataset.name] || 0) + 1;
      });
      var idle = 0, squad = [];
      all('.dc-pool .dc-chip', sec).forEach(function (c) {
        var n = spots[c.dataset.name] || 0;
        squad.push(c.dataset.name);
        c.classList.toggle('placed', n > 0);
        // The badge earns its space only past one. A kid in a single spot is the
        // ordinary case and does not need a number to say so.
        c.dataset.count = n > 1 ? String(n) : '';
        c.title = n
          ? c.dataset.name + ' is in ' + n + (n === 1 ? ' spot' : ' spots')
          : c.dataset.name + ' has no spot yet';
        if (!n) idle++;
      });

      var el = board.querySelector('[data-count="' + side + '-idle"]');
      if (el) {
        el.textContent = idle ? idle + ' with no spot' : 'everybody is in';
        el.classList.toggle('warn', idle > 0);
      }
    });

    persist();
  }

  /* ------------------------------------------------------------ tap to place -- */
  var picked = null, suppress = false;

  function clearPick() {
    if (picked) picked.classList.remove('picked');
    picked = null;
    board.classList.remove('placing');
  }
  function pick(chip) {
    var same = picked === chip;
    clearPick();
    if (same) return;
    picked = chip;
    chip.classList.add('picked');
    board.classList.add('placing');
  }

  board.addEventListener('click', function (e) {
    if (suppress) return;           // the drag that just ended already decided this
    var chip = e.target.closest('.dc-chip');
    var slot = e.target.closest(SLOT);
    if (picked && chip && isPool(slot) && isPool(picked.parentNode)) {
      pick(chip);
      return;
    }
    if (picked && slot && chip !== picked) {
      var held = picked;
      // A name tapped in the squad rail stays picked after it lands. Putting the same
      // left tackle on all three units is one tap and then three, instead of
      // six — and it is the reason the rail is a source in the first place, so the
      // interface should not make you re-say it every time. A name picked up off the
      // board has been moved, and moving is finished when it lands.
      if (!isPool(held.parentNode)) clearPick();
      move(held, slot);
      return;
    }
    if (chip) { pick(chip); return; }
    clearPick();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') clearPick();
  });

  /* --------------------------------------------------------------- drag it -- */
  /* One handler for mouse and finger both. The native HTML5 drag events never fire
     on touch, and a coach uses this on a phone on a sideline, so native drag was
     never an option here.

     A finger has to hold still for a moment before the drag takes. Without that,
     every attempt to scroll the page would pick a kid up instead — and because the
     hold elapses before the first move, the touchmove that follows can be cancelled
     and the scroll never starts. Moving first is a scroll, and lets go of the chip. */
  var HOLD = 180, SLOP = 5;
  var down = null, dragged = null, fly = null, over = null;

  function cleanup() {
    if (down && down.timer) clearTimeout(down.timer);
    if (fly) fly.remove();
    if (dragged) dragged.classList.remove('ghost');
    if (over) over.classList.remove('over');
    down = null; dragged = null; fly = null; over = null;
  }

  function begin(e) {
    dragged = down.chip;
    var r = dragged.getBoundingClientRect();
    fly = dragged.cloneNode(true);
    fly.classList.add('flying');
    fly.classList.remove('picked');
    fly.style.width = r.width + 'px';
    down.dx = e.clientX - r.left;
    down.dy = e.clientY - r.top;
    document.body.appendChild(fly);
    dragged.classList.add('ghost');
    clearPick();
  }

  function hover(e) {
    var el = document.elementFromPoint(e.clientX, e.clientY);
    var slot = el && el.closest ? el.closest(SLOT) : null;
    if (slot && sideOf(slot) !== sideOf(dragged)) slot = null;
    if (slot === over) return;
    if (over) over.classList.remove('over');
    over = slot;
    if (over) over.classList.add('over');
  }

  board.addEventListener('pointerdown', function (e) {
    if (e.button) return;
    var chip = e.target.closest('.dc-chip');
    if (!chip) return;
    cleanup();
    down = { chip: chip, x: e.clientX, y: e.clientY, id: e.pointerId, ready: false };
    // A mouse means it — the button went down on a chip and nothing else was going
    // to happen. A finger might be starting a scroll, so it waits out the hold.
    if (e.pointerType === 'mouse') down.ready = true;
    else down.timer = setTimeout(function () { if (down) down.ready = true; }, HOLD);
  });

  window.addEventListener('pointermove', function (e) {
    if (!down || e.pointerId !== down.id) return;
    if (!dragged) {
      if (Math.abs(e.clientX - down.x) < SLOP && Math.abs(e.clientY - down.y) < SLOP) return;
      if (!down.ready) { cleanup(); return; }   // moved before the hold: a scroll
      begin(e);
    }
    e.preventDefault();
    fly.style.left = (e.clientX - down.dx) + 'px';
    fly.style.top = (e.clientY - down.dy) + 'px';
    hover(e);
  }, { passive: false });

  // Belt and braces for iOS, where a scroll the compositor has already taken over
  // cannot be called back by preventing a pointermove.
  window.addEventListener('touchmove', function (e) {
    if (dragged) e.preventDefault();
  }, { passive: false });

  function finish(e) {
    if (!down || (e && e.pointerId !== down.id)) return;
    var chip = dragged, target = over;
    cleanup();
    if (!chip) return;
    if (target) move(chip, target);
    // The click that follows a drag must not also pick the chip back up.
    suppress = true;
    setTimeout(function () { suppress = false; }, 0);
  }
  window.addEventListener('pointerup', finish);
  window.addEventListener('pointercancel', finish);

  /* ------------------------------------------------------------ back to JSON -- */
  /* roster.json as this board would write it. Built by editing the file the page
     shipped with rather than emitting a fresh one, so the note, the packages and
     anything else a coach put in that file survive the round trip. */
  function exported() {
    var out = JSON.parse(JSON.stringify(data.roster));
    /* Packages go back into the file too. The button says it hands you the whole
       roster, and a coach who sets his packages, hits Copy and pastes the result into
       the repo should not find them missing — the one thing worse than not saving is
       looking like you did. Trailing empty packages are dropped so an untouched board
       writes nothing rather than ten empty pairs. */
    var packs = out.packages || (out.packages = {});
    ['offense', 'defense'].forEach(function (side) {
      var sec = board.querySelector('.dc-side[data-side="' + side + '"]');
      if (!sec) return;
      var rows = [];
      all('.dc-pkg', sec).forEach(function (box) {
        var row = all('.dc-pkg-slot', box).map(function (sl) {
          var c = chipIn(sl);
          return c ? c.dataset.name : '';
        });
        // Empty slots at the end are dropped too, so a package with only its backs
        // set writes three names rather than three and four blanks.
        while (row.length && !row[row.length - 1]) row.pop();
        rows.push(row);
      });
      while (rows.length && !rows[rows.length - 1].join('')) rows.pop();
      if (rows.length) packs[side] = rows; else delete packs[side];
    });
    if (!Object.keys(packs).length) delete out.packages;
    ['offense', 'defense'].forEach(function (side) {
      var lists = out[side] || (out[side] = {});
      Object.keys(lists).forEach(function (pos) { lists[pos] = []; });
      var sec = board.querySelector('.dc-side[data-side="' + side + '"]');
      if (!sec) return;
      // The columns, in depth order. Both sides run the same six.
      var cols = data.rotations[side] || [];
      var playing = {};
      all('td.dc-cell', sec).forEach(function (td) {
        var at = cols.indexOf(td.dataset.rot);
        if (at < 0) return;
        var list = lists[td.dataset.pos] || (lists[td.dataset.pos] = []);
        while (list.length < at) list.push('');
        // An empty 1st spot above a filled 2nd one has to keep 2nd at index 1, so the
        // hole is written as a blank rather than closed up. A kid in more than one
        // spot is simply written more than once, which is exactly how the file is read
        // back — depth is the index, so the same name at index 0 and index 1 says he
        // is the starter and his own backup, and the same name at index 1 of two
        // different positions says he is second in line at both.
        var chip = chipIn(td);
        list[at] = chip ? chip.dataset.name : '';
        if (chip) playing[chip.dataset.name] = true;
      });
      // Behind every rotation go the kids in none of them. The rail holds the whole
      // squad now, so it is the ones NOT on the board that belong here — appending
      // all of them would write every name back twice.
      all('.dc-pool .dc-chip', sec).forEach(function (chip) {
        if (playing[chip.dataset.name]) return;
        var list = lists[chip.dataset.home] || (lists[chip.dataset.home] = []);
        while (list.length < cols.length) list.push('');
        list.push(chip.dataset.name);
      });
      // Trailing blanks say nothing, and a list of nothing but blanks is a spot with
      // nobody on it — which is what an empty list already means.
      Object.keys(lists).forEach(function (pos) {
        while (lists[pos].length && !lists[pos][lists[pos].length - 1]) lists[pos].pop();
      });
    });
    return JSON.stringify(out, null, 2) + '\n';
  }

  function fallback(text) {
    var ta = document.getElementById('dc-out');
    if (!ta) {
      ta = document.createElement('textarea');
      ta.id = 'dc-out';
      ta.className = 'dc-out';
      ta.rows = 12;
      ta.readOnly = true;
      var bar = document.getElementById('dc-bar');
      if (bar) bar.insertAdjacentElement('afterend', ta);
    }
    ta.value = text;
    ta.hidden = false;
    ta.focus();
    ta.select();
  }

  function flash(btn, label) {
    if (btn._was) return;
    btn._was = btn.textContent;
    btn.textContent = label;
    setTimeout(function () { btn.textContent = btn._was; btn._was = null; }, 1500);
  }

  if (copyBtn) copyBtn.addEventListener('click', function () {
    var text = exported();
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () { flash(copyBtn, 'Copied'); },
        function () { fallback(text); });
    } else fallback(text);
  });

  // Two taps to throw the board away. A single misplaced tap on a phone should not
  // cost a coach the rearrangement he just spent halftime on.
  var armed = 0;
  if (resetBtn) resetBtn.addEventListener('click', function () {
    if (!armed) {
      armed = setTimeout(function () { armed = 0; resetBtn.textContent = 'Reset'; }, 4000);
      resetBtn.textContent = 'Reset — tap again';
      return;
    }
    try { localStorage.removeItem(KEY); } catch (e) {}
    // Reloading restores the roster the page ships with, which means there is no
    // second copy of the default here to fall out of step with the real one.
    location.reload();
  });

  restore();
  refresh();
})();
