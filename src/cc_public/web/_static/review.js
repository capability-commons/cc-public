// Small conveniences on top of pages that work without script.
//
// A link that pins a decision or a lit chain changes only the fragment
// of the address, so the page keeps its place instead of jumping to the
// pinned element. A click off the decision matrix while a decision is
// shown points the address at a fragment no element has, which hides the
// decision; folding or opening a diagram does not, nor does a click in a
// form opened over the page. Without script the
// page jumps, and a decision stays shown until another is chosen.
//
// A click on an annotation in the graph also chooses its entry in the
// argument under the decision matrix: the entry and those around it
// open, and braces mark it, without moving the page. Any other pin or
// unpin lets it go.
//
// Each diagram stays open or closed as it was last left, on every
// page, so moving from issue to issue keeps the same view. The page
// remembers this in the browser; without script, or where the browser
// keeps nothing, each diagram opens as the page sets it.

var KEY_DIAGRAM = 'cc-review-diagram-';

document.querySelectorAll('details.diagram').forEach(function (diagram) {
  var name = KEY_DIAGRAM + diagram.className.replace('diagram', '').trim();
  try {
    var state = localStorage.getItem(name);
    if (state !== null) {
      diagram.open = state === 'open';
    }
  } catch (error) {
    return;
  }
  diagram.addEventListener('toggle', function () {
    try {
      localStorage.setItem(name, diagram.open ? 'open' : 'closed');
    } catch (error) {
      return;
    }
  });
});

// The braces that mark a chosen entry are drawn as one curve each, at
// the height of the entry, and drawn again whenever it opens or
// closes. Without script, the style sheet draws square brackets.

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
  watch.observe(entry);
}

// The outline of a brace of height h, 12 units wide, as an SVG path:
// a centre line from the curled end down to the beak, thickest midway
// along the arm and tapering to a hairline at the end and at the point
// of the beak, and the same line turned over below.
// The ends and the beak keep their size until the brace is short, then
// shrink with it, so it bends the same way at every height.

function braceOutline(h, isRight) {
  var half = h / 2;
  var reach = Math.min(12, half * 0.4);
  var bend = Math.min(10, half * 0.4);
  var line = [];
  var steps = 24;
  var index;
  function cubic(p0, p1, p2, p3, t) {
    var u = 1 - t;
    return [u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0],
            u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1]];
  }
  for (index = 0; index <= steps; index++) {
    line.push(cubic([11.2, 0.6], [8.3, 1.0], [7, reach * 0.45], [7, reach], index / steps));
  }
  var count = Math.max(2, Math.round((half - reach - bend) / 3));
  for (index = 1; index <= count; index++) {
    line.push([7, reach + (half - reach - bend) * index / count]);
  }
  for (index = 1; index <= steps; index++) {
    line.push(cubic([7, half - bend], [7, half - bend * 0.3], [4.2, half - 0.4], [0.6, half],
                    index / steps));
  }
  var length = [0];
  for (index = 1; index < line.length; index++) {
    length.push(length[index - 1] + Math.hypot(line[index][0] - line[index - 1][0],
                                               line[index][1] - line[index - 1][1]));
  }
  var total = length[length.length - 1];
  var sideA = [];
  var sideB = [];
  for (index = 0; index < line.length; index++) {
    var before = line[Math.max(0, index - 1)];
    var after = line[Math.min(line.length - 1, index + 1)];
    var dx = after[0] - before[0];
    var dy = after[1] - before[1];
    var norm = Math.hypot(dx, dy) || 1;
    var fromEnd = Math.min(1, length[index] / Math.min(14, total / 3));
    var fromBeak = Math.min(1, (total - length[index]) / Math.min(8, total / 4));
    var width = 0.15 + 1.45 * Math.pow(fromEnd * fromBeak, 0.8)
                * (0.75 + 0.25 * Math.sin(Math.PI * length[index] / total));
    var nx = -dy / norm * width / 2;
    var ny = dx / norm * width / 2;
    sideA.push([line[index][0] + nx, line[index][1] + ny]);
    sideB.push([line[index][0] - nx, line[index][1] - ny]);
  }
  function below(point) {
    return [point[0], h - point[1]];
  }
  var outline = sideA.concat(sideA.slice().reverse().map(below),
                             sideB.map(below), sideB.slice().reverse());
  return 'M' + outline.map(function (point) {
    var x = isRight ? 12 - point[0] : point[0];
    return x.toFixed(2) + ' ' + point[1].toFixed(2);
  }).join(' L') + ' Z';
}

// Draw the braces of entry at its height, into custom properties the
// style sheet paints them from.

function brace(entry) {
  var inset = parseFloat(getComputedStyle(document.documentElement).fontSize) * 0.15;
  var h = entry.getBoundingClientRect().height - 2 * inset;
  if (h <= 0) {
    return;
  }
  ['left', 'right'].forEach(function (side) {
    var svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 " + h.toFixed(2) +
              "' preserveAspectRatio='none'><path fill='#5e5648' d='" +
              braceOutline(h, side === 'right') + "'/></svg>";
    entry.style.setProperty('--brace-' + side,
                            'url("data:image/svg+xml,' + encodeURIComponent(svg) + '")');
  });
}

var watch = new ResizeObserver(function (list) {
  list.forEach(function (item) {
    brace(item.target);
  });
});

function watchTarget() {
  var target = document.querySelector('details.annotation:target');
  if (target) {
    watch.observe(target);
  }
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
  if (shown && !event.target.closest('section.matrix, details.diagram > summary, dialog')) {
    keep = window.scrollY;
    location.hash = 'unpin';
  }
});

window.addEventListener('load', watchTarget);

window.addEventListener('hashchange', function () {
  watchTarget();
  if (keep !== null) {
    window.scrollTo(0, keep);
    keep = null;
  }
});

// The forms that change the data open over the page they are opened
// from, in a dialog that shades the page behind it. The pill is a link
// to the page of its form, which is fetched, and its form shown in the
// dialog. A form sent from the dialog is sent by script: a refusal
// comes back into the dialog with its failures, and an edit that is
// written reloads the page at what it made. Escape or Cancel closes
// the dialog and changes nothing. Without script the pill opens the
// page of the form, and the form is sent from there.

var dialog = null;

function formDialog() {
  if (dialog) {
    return dialog;
  }
  dialog = document.createElement('dialog');
  dialog.className = 'edit';
  dialog.addEventListener('click', function (event) {
    if (event.target.closest('a.cancel')) {
      event.preventDefault();
      dialog.close();
    }
  });
  dialog.addEventListener('submit', function (event) {
    event.preventDefault();
    send(event.target);
  });
  document.body.appendChild(dialog);
  return dialog;
}

function showForm(html) {
  var page = new DOMParser().parseFromString(html, 'text/html');
  var box = formDialog();
  var head = document.createElement('header');
  ['h1', '.subtitle'].forEach(function (selector) {
    var part = page.querySelector('.masthead ' + selector);
    if (part) {
      head.appendChild(document.importNode(part, true));
    }
  });
  box.replaceChildren(head);
  var section = page.querySelector('section.edit-form');
  if (section) {
    box.appendChild(document.importNode(section, true));
  }
  if (!box.open) {
    box.showModal();
  }
  var first = box.querySelector('textarea, input[type=text]');
  if (box.querySelector('.refused')) {
    box.scrollTop = 0;
  } else if (first) {
    first.focus();
  }
}

function send(form) {
  var press = form.querySelector('button[type=submit]');
  if (press) {
    press.disabled = true;
    press.textContent = 'Checking';
  }
  fetch(form.action, { method: 'POST', body: new URLSearchParams(new FormData(form)) })
    .then(function (response) {
      if (response.redirected) {
        arrive(response.url);
        return null;
      }
      return response.text().then(showForm);
    })
    .catch(function () {
      form.submit();
    });
}

// The address of a written edit names what it made in its query as
// well as its fragment, since a fetch is not told the fragment. Going
// to an address that differs only in its fragment would not read the
// page again, so the page is reloaded there instead.

function arrive(url) {
  var address = new URL(url);
  var to = address.searchParams.get('to');
  var target = address.pathname + address.search + (to ? '#' + encodeURIComponent(to) : '');
  if (address.pathname + address.search === location.pathname + location.search) {
    history.replaceState(null, '', target);
    location.reload();
  } else {
    location.href = target;
  }
}

document.addEventListener('click', function (event) {
  var pill = event.target.closest('a.pill');
  if (!pill || event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) {
    return;
  }
  event.preventDefault();
  fetch(pill.href)
    .then(function (response) { return response.text(); })
    .then(showForm)
    .catch(function () { location.href = pill.href; });
});
