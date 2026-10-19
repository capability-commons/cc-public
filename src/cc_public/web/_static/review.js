// Small conveniences on top of pages that work without script.
//
// A link that pins a decision or a lit chain changes only the fragment
// of the address, so the page keeps its place instead of jumping to the
// pinned element. A click off the decision matrix while a decision is
// shown points the address at a fragment no element has, which hides the
// decision; folding or opening a diagram does not. Without script the
// page jumps, and a decision stays shown until another is chosen.

var keep = null;

document.addEventListener('click', function (event) {
  var link = event.target.closest('a[href^="#"]');
  if (link) {
    var target = document.getElementById(link.getAttribute('href').slice(1));
    if (!target || target.matches('.decision, .decision-role, .lit-pin')) {
      keep = window.scrollY;
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
