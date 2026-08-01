/* Play switcher: close it on an outside click or Escape, the way a menu should. */
(function () {
  var sw = document.querySelector('.switcher');
  if (!sw) return;
  document.addEventListener('click', function (e) {
    if (sw.open && !sw.contains(e.target)) sw.open = false;
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && sw.open) { sw.open = false; sw.querySelector('summary').focus(); }
  });
  sw.addEventListener('toggle', function () {
    if (!sw.open) return;
    var here = sw.querySelector('a.here');
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
