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
