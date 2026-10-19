// Small conveniences on top of pages that work without script.
//
// A link that pins a decision or a lit chain changes only the fragment
// of the address, so the page keeps its place instead of jumping to the
// pinned element. A click off the decision matrix while a decision is
// shown points the address at a fragment no element has, which hides the
// decision; folding or opening a diagram does not. Without script the
// page jumps, and a decision stays shown until another is chosen.
//
// A click on an annotation in the graph also chooses its entry in the
// argument under the decision matrix: the entry and those around it
// open, and braces mark it, without moving the page. Any other pin or
// unpin lets it go.

var keep = null;
var chosen = null;

function choose(key) {
  if (chosen) {
    chosen.classList.remove('chosen');
    chosen = null;
  }
  var entry = key ? document.getElementById(key) : null;
  if (!entry) {
    return;
  }
  for (var node = entry; node; node = node.parentElement) {
    if (node.tagName === 'DETAILS') {
      node.open = true;
    }
  }
  entry.classList.add('chosen');
  chosen = entry;
}

document.addEventListener('click', function (event) {
  var link = event.target.closest('a[href^="#"]');
  if (link) {
    var target = document.getElementById(link.getAttribute('href').slice(1));
    if (!target || target.matches('.decision, .decision-role, .lit-pin')) {
      keep = window.scrollY;
      choose(link.getAttribute('data-key'));
    }
    return;
  }
  var shown = document.querySelector('section.matrix :is(.decision, .decision-role):target');
  if (shown && !event.target.closest('section.matrix, details.diagram > summary')) {
    keep = window.scrollY;
    location.hash = 'unpin';
  }
});

window.addEventListener('hashchange', function () {
  if (keep !== null) {
    window.scrollTo(0, keep);
    keep = null;
  }
});
