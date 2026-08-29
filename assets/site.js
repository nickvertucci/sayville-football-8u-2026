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
   two chips in the SAME group widens the list — Split Backs or Full House. Picking
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
     switching to it — pick Regular I then Power I and you are looking at eighteen
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
  var tally = document.getElementById('dc-tally');
  var edited = document.getElementById('dc-edited');
  var resetBtn = document.getElementById('dc-reset');
  var copyBtn = document.getElementById('dc-copy');
  var SLOT = 'td.dc-cell, .dc-pool';

  function all(sel, ctx) {
    return Array.prototype.slice.call((ctx || board).querySelectorAll(sel));
  }
  function sideOf(el) {
    var side = el.closest('.dc-side');
    return side ? side.dataset.side : '';
  }
  function chipIn(slot) { return slot.querySelector('.dc-chip'); }

  /* A cell with nobody in it says Open, and says it as a button so that the spot can
     be tabbed to and chosen from a keyboard exactly like a name can. The bench needs
     no such marker — its :empty rule speaks for it. */
  function fill(slot) {
    if (!slot.classList.contains('dc-cell')) return;
    var has = chipIn(slot), open = slot.querySelector('.dc-open');
    if (has && open) open.remove();
    if (!has && !open) {
      slot.innerHTML = '<button type="button" class="dc-open">Open</button>';
    }
  }

  function move(chip, target) {
    var from = chip.parentNode;
    if (!target || from === target) return;
    // Offense chips stay on offense. The two sides are separate problems and a kid
    // is on both of them; dragging across would merge two answers into one.
    if (sideOf(target) !== sideOf(chip)) return;
    var held = target.classList.contains('dc-cell') ? chipIn(target) : null;
    // A swap, not a shove: whoever is already there goes back where this one came
    // from. Dropping onto the bench is not a swap, because the bench holds any number.
    if (held) from.appendChild(held);
    var open = target.querySelector('.dc-open');
    if (open) open.remove();
    target.appendChild(chip);
    fill(from);
    fill(target);
    refresh();
  }

  /* Every placement on the board, in a shape that survives a roster.json edit: a
     record names the spot rather than pointing at it, so one whose spot has since
     gone is skipped instead of taking the whole save down with it. */
  function snapshot() {
    var out = [];
    all(SLOT).forEach(function (s) {
      all('.dc-chip', s).forEach(function (c) {
        out.push([sideOf(s), s.dataset.rot, s.dataset.pos || '',
                  c.dataset.name, c.dataset.home]);
      });
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

    var byKey = {};
    all(SLOT).forEach(function (s) {
      byKey[sideOf(s) + '/' + s.dataset.rot + '/' + (s.dataset.pos || '')] = s;
    });
    // Lift every chip off the board, then set them back down where the save says.
    // Two chips can share a name — the same kid is on both sides — so they come off
    // into a list per side and are matched out of it one at a time.
    var loose = { offense: [], defense: [] };
    all('.dc-chip').forEach(function (c) {
      var side = sideOf(c);
      if (loose[side]) loose[side].push(c);
      c.remove();
    });
    all(SLOT).forEach(function (s) { s.innerHTML = ''; fill(s); });

    function take(side, name) {
      var list = loose[side] || [];
      for (var i = 0; i < list.length; i++) {
        if (list[i].dataset.name === name) return list.splice(i, 1)[0];
      }
      return null;
    }

    at.forEach(function (rec) {
      var slot = byKey[rec[0] + '/' + rec[1] + '/' + (rec[2] || '')];
      if (!slot) return;
      if (slot.classList.contains('dc-cell') && chipIn(slot)) return;
      var chip = take(rec[0], rec[3]);
      if (!chip) return;
      var open = slot.querySelector('.dc-open');
      if (open) open.remove();
      slot.appendChild(chip);
    });
    // Anybody the save never mentions is somebody added to roster.json since it was
    // written. The bench is the honest place for him: unplaced, and visibly so.
    Object.keys(loose).forEach(function (side) {
      var bench = byKey[side + '/bench/'];
      loose[side].forEach(function (c) { if (bench) bench.appendChild(c); });
    });
    all(SLOT).forEach(fill);
  }

  function refresh() {
    var counts = {}, seen = {};
    // Alt rows are off the count. They are spots no formation on this board aligns,
    // carried only because somebody is standing on one, and counting them would make
    // a complete eleven read as twelve.
    all('tbody tr[data-pos]').forEach(function (tr) {
      if (tr.classList.contains('dc-alt')) return;
      all('td.dc-cell', tr).forEach(function (td) {
        var k = sideOf(td) + '-' + td.dataset.rot;
        var c = counts[k] || (counts[k] = { on: 0, of: 0 });
        c.of++;
        var chip = chipIn(td);
        if (!chip) return;
        c.on++;
        var rot = seen[td.dataset.rot] || (seen[td.dataset.rot] = {});
        rot[chip.dataset.name] = (rot[chip.dataset.name] || 0) + 1;
      });
    });

    // A name on both sides of one rotation is a kid who never leaves the field. It
    // is the most consequential thing this page knows and it used to say none of it.
    all('.dc-chip').forEach(function (c) {
      var rot = seen[c.parentNode.dataset.rot];
      var two = !!(rot && rot[c.dataset.name] > 1);
      c.classList.toggle('two-way', two);
      c.title = two ? c.dataset.name + ' plays both ways in this rotation' : '';
    });

    Object.keys(counts).forEach(function (k) {
      var el = board.querySelector('[data-count="' + k + '"]');
      if (!el) return;
      el.textContent = counts[k].on + '/' + counts[k].of;
      el.classList.toggle('warn', counts[k].on < counts[k].of);
    });
    ['offense', 'defense'].forEach(function (side) {
      var pool = board.querySelector('.dc-pool[data-side="' + side + '"]');
      var el = board.querySelector('[data-count="' + side + '-bench"]');
      if (pool && el) el.textContent = String(all('.dc-chip', pool).length);
    });

    if (tally) {
      var open = 0;
      Object.keys(counts).forEach(function (k) { open += counts[k].of - counts[k].on; });
      var both = data.rotations.map(function (r) {
        var n = 0, m = seen[r] || {};
        Object.keys(m).forEach(function (name) { if (m[name] > 1) n++; });
        return r.charAt(0).toUpperCase() + r.slice(1) + ' ' + n;
      }).join(', ');
      tally.innerHTML = '<b>' + data.squad.length + '</b> on the squad &middot; '
        + (open
            ? '<span class="warn">' + open + (open === 1 ? ' spot' : ' spots') + ' open</span>'
            : 'every spot filled')
        + ' &middot; playing both ways: ' + both;
    }
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
    if (picked && slot && chip !== picked) {
      var held = picked;
      clearPick();
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
    ['offense', 'defense'].forEach(function (side) {
      var lists = out[side] || (out[side] = {});
      Object.keys(lists).forEach(function (pos) { lists[pos] = []; });
      var sec = board.querySelector('.dc-side[data-side="' + side + '"]');
      if (!sec) return;
      all('td.dc-cell', sec).forEach(function (td) {
        var at = data.rotations.indexOf(td.dataset.rot);
        if (at < 0) return;
        var list = lists[td.dataset.pos] || (lists[td.dataset.pos] = []);
        while (list.length < at) list.push('');
        // An empty Purple spot above a filled Gold one has to keep Gold at index 1,
        // so the hole is written as a blank rather than closed up.
        var chip = chipIn(td);
        list[at] = chip ? chip.dataset.name : '';
      });
      all('.dc-pool[data-side="' + side + '"] .dc-chip', sec).forEach(function (chip) {
        var list = lists[chip.dataset.home] || (lists[chip.dataset.home] = []);
        while (list.length < data.rotations.length) list.push('');
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
