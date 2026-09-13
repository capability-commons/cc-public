/*
---

id_self:                js_cc_public.web.static.surface
guid_self:              js_db8d0ba313cb438db710a065861fd836
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Workbench cursor script
brief:                  |
                        The cursor, the three levels of contrast
                        around it, and the acts that open, read and
                        collapse a row.
description:            |
                        The script holds where the reader is and
                        nothing else. Contrast is computed from the
                        cursor rather than from the root, so a tree of
                        any depth needs three levels. Opening and
                        reading each fetch into a region of their own,
                        so neither waits on the other. Collapsing
                        moves the focus up to a row still shown,
                        because a hidden focus loses the reader their
                        place.
relation:               []

...
*/

// The cursor, and the three levels of contrast around it. Position is
// relative to the cursor and not to the root, so a tree of any depth
// needs three levels and nothing is indented (ddr_navigation_surface).

(function () {
  'use strict';

  var NEAR = 'near', CURSOR = 'cursor', OPEN = 'open';

  function node(el) { return el.closest('.node'); }

  function rowOf(n) { return n ? n.querySelector(':scope > .row') : null; }

  function mark(row) {
    document.querySelectorAll('.row.' + CURSOR + ', .row.' + NEAR).forEach(
      function (r) { r.classList.remove(CURSOR, NEAR); });

    if (!row) { return; }
    row.classList.add(CURSOR);

    var self = node(row), near = [];
    for (var up = self.parentElement.closest('.node'); up; up = up.parentElement.closest('.node')) {
      near.push(rowOf(up));
    }
    self.parentElement.querySelectorAll(':scope > .node').forEach(
      function (n) { if (n !== self) { near.push(rowOf(n)); } });
    self.querySelectorAll(':scope > .sub > .groups > .group > .node').forEach(
      function (n) { near.push(rowOf(n)); });

    near.forEach(function (r) { if (r && r !== row) { r.classList.add(NEAR); } });
  }

  function view() {
    return new URLSearchParams(window.location.search).get('view') || '';
  }

  function toggle(row) {
    var self = node(row), sub = self.querySelector(':scope > .sub');
    if (self.classList.contains(OPEN)) {
      self.classList.remove(OPEN);
      return;
    }
    self.classList.add(OPEN);
    if (!sub.dataset.filled) {
      sub.dataset.filled = '1';
      window.htmx.ajax('GET', '/groups?view=' + encodeURIComponent(view()) +
                       '&path=' + encodeURIComponent(row.dataset.path),
                       sub.querySelector(':scope > .groups'));
    }
  }

  function read(row) {
    var self = node(row), sub = self.querySelector(':scope > .sub');
    if (!self.classList.contains(OPEN)) { toggle(row); }
    window.htmx.ajax('GET', '/record?id=' + encodeURIComponent(row.dataset.id),
                     sub.querySelector(':scope > .record'));
  }

  // Collapsing may hide the row the reader is on, which would drop
  // focus to the document and lose their place. Focus moves up to the
  // nearest row that is still shown, and the cursor follows it.
  function visible(row) {
    return row && row.getClientRects().length > 0;
  }

  function collapse() {
    var here = document.activeElement && document.activeElement.closest('.row');

    document.querySelectorAll('.node.' + OPEN).forEach(function (n) {
      n.classList.remove(OPEN);
    });

    if (!here || visible(here)) { return; }

    var up = node(here).parentElement.closest('.node');
    while (up && !visible(rowOf(up))) { up = up.parentElement.closest('.node'); }

    var land = rowOf(up) || document.querySelector('#roots > .node > .row');
    if (land) { land.focus(); mark(land); }
  }

  // The contrast levels are relative to the cursor, so without one
  // there is no reference and the whole page reads at the lowest.
  // The first row is the cursor until a reader moves it.
  function start() {
    var first = document.querySelector('#roots > .node > .row');
    if (first && !document.querySelector('.row.' + CURSOR)) { mark(first); }
  }

  document.addEventListener('DOMContentLoaded', start);
  document.addEventListener('htmx:afterSwap', function (e) {
    if (e.target && e.target.id === 'roots') { start(); }
  });

  document.addEventListener('click', function (e) {
    var row = e.target.closest('.row');
    if (row) { mark(row); row.focus(); toggle(row); }
  });

  document.addEventListener('focusin', function (e) {
    var row = e.target.closest('.row');
    if (row) { mark(row); }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { collapse(); return; }
    var row = document.activeElement && document.activeElement.closest('.row');
    if (!row) { return; }
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(row); }
    if (e.key === 'r') { e.preventDefault(); read(row); }
  });
}());
