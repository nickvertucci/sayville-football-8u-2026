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
    if (window.innerWidth >= 900 && drawer && drawer.classList.contains('open')) {
      openDrawer(false);
    }
    if (window.innerWidth < 900) openDrop(null, false);
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

(function () {
  var q = document.getElementById('q');
  if (!q) return;
  var rows = Array.prototype.slice.call(document.querySelectorAll('#calls tbody tr'));
  var chips = Array.prototype.slice.call(document.querySelectorAll('.chip'));
  var count = document.getElementById('count');
  var empty = document.getElementById('empty');
  var filter = 'all';

  function apply() {
    var term = q.value.trim().toLowerCase();
    var n = 0;
    rows.forEach(function (r) {
      var okGroup = filter === 'all' || r.dataset.form === filter || r.dataset.type === filter;
      var okTerm = !term || r.dataset.search.indexOf(term) !== -1;
      var show = okGroup && okTerm;
      r.hidden = !show;
      if (show) n++;
    });
    count.textContent = n + (n === 1 ? ' play' : ' plays');
    empty.hidden = n !== 0;
  }

  q.addEventListener('input', apply);
  chips.forEach(function (c) {
    c.addEventListener('click', function () {
      chips.forEach(function (o) { o.setAttribute('aria-pressed', 'false'); });
      c.setAttribute('aria-pressed', 'true');
      filter = c.dataset.filter;
      apply();
    });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement !== q) { e.preventDefault(); q.focus(); }
    if (e.key === 'Escape' && document.activeElement === q) { q.value = ''; apply(); }
  });
  apply();
})();
