/* Printing from a phone.

   A phone lays a page out at the width of its own screen when it prints, then shrinks
   that onto the paper. Every rule written for a narrow screen fires on paper, the
   cards wrap and stack, and the depth chart's two sheets came out as four. A desktop
   lays the page out at the paper's own width instead, which is what the print
   stylesheet was measured against.

   So on a screen narrower than the paper, Print first sets the viewport to the
   paper's printable width -- the page carries it, worked out from its own @page
   rule -- lets the page lay out again at that width, and only then opens the print
   dialog. The viewport goes back once the dialog closes. Wrapping window.print
   rather than the buttons means every Print button on the site gets it. On a desktop
   the screen is already wider than the paper and nothing changes. */
(function () {
  var want = parseInt(document.documentElement.getAttribute('data-print-width'), 10);
  var meta = document.querySelector('meta[name="viewport"]');
  var native = window.print;
  if (!want || !meta || !native) return;
  var original = meta.getAttribute('content');
  var widened = false;

  function widen() {
    if (widened || document.documentElement.clientWidth >= want) return false;
    meta.setAttribute('content', 'width=' + want);
    widened = true;
    return true;
  }
  function restore() {
    if (!widened) return;
    meta.setAttribute('content', original);
    widened = false;
  }

  window.print = function () {
    if (!widen()) return native.call(window);
    // Two frames and a beat, so the page has laid out at the new width before the
    // print dialog takes its picture of it.
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        setTimeout(function () { native.call(window); }, 150);
      });
    });
  };
  // Printing from the share sheet rather than the button: too late to wait for a
  // layout, but widening here still reaches the browsers that lay out again for it.
  window.addEventListener('beforeprint', widen);
  window.addEventListener('afterprint', restore);
})();

/* The defensive-front toggle on a play page.

   Every front's diagram and assignments are already in the page, so this only moves a
   class. Two things make it worth its twenty lines: the choice is remembered, because
   a coach who has scouted the team they are playing wants every play in the book in
   that front and not to press a button fifty-six times; and it works on the print
   page too, where several plays are on one document at once. */
(function () {
  var KEY = 'sayville.front.v2';
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
   two chips in the SAME group widens the list — I Formation or Split Formation. Picking
   chips in DIFFERENT groups narrows it — Split Formation AND runs. The old single-string
   filter could not express that at all: formation and type shared one exclusive group,
   so "Split Formation runs" quietly turned into "all runs". */
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
     switching to it — pick I Formation then Split Formation and you are looking at every
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
